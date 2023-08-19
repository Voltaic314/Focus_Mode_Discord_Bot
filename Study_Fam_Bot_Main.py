import discord
from discord import app_commands
import secrets
from time_modulation import Time_Stuff
from database import Database
from text_processing import Text_Processing
from video_processing import Video_Processing
import os
import asyncio
import random


class Focus_Bot_Client(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True  # Enable the GUILD_MEMBERS intent
        intents.messages = True
        super().__init__(intents=intents)
        self.synced = False  # we use this so the bot doesn't sync commands more than once
        # define our variables
        self.server_id = secrets.discord_bot_credentials["Server_ID_for_Study_Fam"]
        self.SELF_CARE_CHANNEL_ID = secrets.discord_bot_credentials["Self_Care_Channel_ID"]
        self.user_id = secrets.discord_bot_credentials["Client_ID"]

    async def on_ready(self):
        # wait for the bot to be set up properly
        await self.wait_until_ready()
        if not self.synced:  # check if slash commands have been synced
            await tree.sync()
            self.synced = True
        print(f"We have logged in as {self.user}.")

        # when we start up the bot, run the check to remove anyone in the database who shouldn't be in there anymore.
        self.loop.create_task(self.bot_routines())

        # Start the message posting loop
        self.loop.create_task(self.self_care_reminder_time_loop())

    async def bot_routines(self):
        await self.wait_until_ready()

        # Passing in our variables to create our objects & object attributes.
        guild = client.get_guild(self.server_id)
        auto_delete_channel = guild.get_channel(secrets.discord_bot_credentials["Auto_Delete_Channel_ID"])

        while True:

            # This is a list of tuples, where each item in the tuple is a cell in the row.
            database_entries = database_instance.retrieve_values_from_table("Study_Fam_People_Currently_In_Focus_Mode")

            # make sure the list is not empty
            if database_entries:

                for entry in database_entries:
                    current_time = Time_Stuff.get_current_time_in_epochs()
                    Focus_Role_object = discord.utils.get(guild.roles, name="Focus")

                    # check to see if the user is past their expired focus ending time. If so, remove them from the
                    # database and remove their focus role. Do this for every user in the database.
                    if entry[2] <= current_time:
                        current_user = await guild.fetch_member(entry[1])
                        await current_user.remove_roles(Focus_Role_object)
                        database_instance.delete_user_info_from_table(
                            name_of_table="Study_Fam_People_Currently_In_Focus_Mode",
                            User_ID=entry[1])

            # now we'll look to see if any messages need to be deleted from the auto delete channel
            # if so, then delete them, if not just ignore.
            async for message in auto_delete_channel.history(limit=None, oldest_first=True):
                if not message.pinned and Time_Stuff.is_input_time_past_threshold(message.created_at.timestamp(),
                                                                                  86400, True):
                    await message.delete()

            for thread in auto_delete_channel.threads:
                thread_needs_to_be_deleted = Time_Stuff.is_input_time_past_threshold(thread.created_at.timestamp(),
                                                                                     86400, True)
                if thread_needs_to_be_deleted:
                    await thread.delete()

            await asyncio.sleep(60)

    # Function to start posting messages on a fixed interval (every 2 hours)
    async def self_care_reminder_time_loop(self):
        await self.wait_until_ready()

        # define our variables for later on
        guild = client.get_guild(self.server_id)
        self_care_channel = guild.get_channel(self.SELF_CARE_CHANNEL_ID)
        self_care_message_to_send = "Posture & hydration check! I'm watching you! :eyes:"
        number_of_seconds_in_one_hour = 3600
        number_of_seconds_in_four_hours = number_of_seconds_in_one_hour * 4

        while True:

            last_message_sent_time = await self.get_last_message_time_sent_from_user(user_id=self.user_id,
                                                                                     channel=self_care_channel)

            # delete all previous unpinned messages from the bot to clear out the channel.
            async for message in self_care_channel.history(limit=None, oldest_first=True):
                if not message.pinned:
                    message_is_older_than_a_day = Time_Stuff.is_input_time_past_threshold(message.created_at.timestamp(),
                                                                                          86400, True)
                    if message_is_older_than_a_day:
                        await message.delete()

            if not last_message_sent_time:
                # post the self-care reminder to the channel.
                await post_channel_message(self.SELF_CARE_CHANNEL_ID, self_care_message_to_send)

            else:
                last_message_is_older_than_an_hour = Time_Stuff.is_input_time_past_threshold(last_message_sent_time, 3600, True)

                # This is so in case we have to reboot the bot it's not just spamming the channel every single time.
                if last_message_is_older_than_an_hour:

                    # delete the previous message before we post again
                    last_message = await self.get_last_message_from_user(self.user_id, channel=self_care_channel)
                    if last_message:
                        await last_message.delete()

                    # post the self-care reminder to the channel.
                    await post_channel_message(self.SELF_CARE_CHANNEL_ID, self_care_message_to_send)

            # pick a random number of seconds to wait between 1 hour minimum and 4 hours maximum
            # This ensures the bot will never post less than at least 6 times a day, but up to 24 times a day max.
            sleep_time = random.randint(number_of_seconds_in_one_hour, number_of_seconds_in_four_hours)

            # sleep until it's time to post again.
            await asyncio.sleep(sleep_time)

    @staticmethod
    async def get_last_message_time_sent_from_user(user_id: int, channel: object):
        channel_history = channel.history(limit=None, oldest_first=False)
        async for message_from_user in channel_history:
            if message_from_user.author.id == user_id and not message_from_user.pinned:
                return message_from_user.created_at.timestamp()

    @staticmethod
    async def get_last_message_from_user(user_id: int, channel: object):
        channel_history = channel.history(limit=None, oldest_first=False)
        async for message_from_user in channel_history:
            if message_from_user.author.id == user_id and not message_from_user.pinned:
                return message_from_user

    async def able_to_post_nofication_message(self, channel):
        bot_id = 1073370831356440680
        time_of_last_message_sent = await self.get_last_message_time_sent_from_user(user_id=bot_id, channel=channel)
        thirty_minutes_in_seconds = 1800
        if time_of_last_message_sent:
            we_havent_posted_since_thirty_min_ago = Time_Stuff.is_input_time_past_threshold(time_of_last_message_sent,
                                                                                            thirty_minutes_in_seconds,
                                                                                            True)
            return we_havent_posted_since_thirty_min_ago

        else:
            return True


def return_file_name_with_current_directory(filename: str) -> str:

    # get the current file path we're operating in, so we don't have to hard code this in.
    # this also requires that the file be in the same working directory as this script.
    CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
    FILE_PATH_AND_NAME = os.path.join(CURRENT_DIRECTORY, filename)
    return FILE_PATH_AND_NAME


client = Focus_Bot_Client()
tree = app_commands.CommandTree(client)
Focus_Role_int: int = secrets.discord_bot_credentials["Focus_Role_ID"]
database_file_name_and_path = return_file_name_with_current_directory("Focus_Mode_Info.db")
database_instance = Database(database_file_name_and_path)


@client.event
async def on_message(message):
    # Defining our variables for our function here
    Dr_K_Content_Ping_Role_ID = 1138514811114770522
    Carl_Bot_User_ID = 235148962103951360
    Dr_K_Content_Channel_ID = 1078121853266165870

    # Passing in our variables to create our objects & object attributes.
    guild = client.get_guild(client.server_id)
    Dr_K_Content_Ping_Role = guild.get_role(Dr_K_Content_Ping_Role_ID)
    Dr_K_Content_Channel = guild.get_channel(Dr_K_Content_Channel_ID)

    if message.channel.id == Dr_K_Content_Channel_ID and message.author.id == Carl_Bot_User_ID:
        if "youtu.be/" in message.content or "youtube.com" in message.content:
            video_link = Text_Processing.extract_video_url(message.content)
            video_title = Video_Processing.get_video_title(video_link)
            video_processing_instance = Video_Processing()
            transcribed_text_filename = Video_Processing.transcribe_a_YT_video(video_processing_instance, video_link)
            thread = await message.create_thread(video_title)
            txt_file_to_upload = discord.File(filename=transcribed_text_filename)
            await thread.send(content="Transcription File:", file=txt_file_to_upload)
        notification_message = f"{Dr_K_Content_Ping_Role.mention} - Dr. K has uploaded new content posted above!"
        await Dr_K_Content_Channel.send(notification_message)


@tree.command(name="focus_mode_in_x_minutes", description="Gives user focus mode role.")
async def FocusMode(interaction: discord.Interaction, minutes: int):
    Focus_Role_object = interaction.guild.get_role(Focus_Role_int)
    appropriate_response: str = Time_Stuff.time_responses(minutes)

    if minutes > 10080 or minutes < 0:
        await interaction.response.send_message(appropriate_response, ephemeral=True)

    else:
        user_info_from_db = database_instance.check_if_user_in_database(interaction.user.id)

        # check the database to see if they are just updating their current time left. If not, then create a new entry.
        # if they are updating their time, make sure it's only adding more time, not lessening their time.
        if user_info_from_db:
            await interaction.response.defer()
            seconds = minutes * 60

            new_time = Time_Stuff.get_current_time_in_epochs() + seconds

            if new_time > user_info_from_db[2]:
                await interaction.followup.send(content=appropriate_response, ephemeral=True)
                database_instance.update_user_info_from_focus_table(interaction.user.id, new_time)

        # This will execute if the user is not in the database already. Thus, the user_info_from_db value is False.
        elif not user_info_from_db:
            await interaction.response.send_message(appropriate_response, ephemeral=True)
            await interaction.user.add_roles(Focus_Role_object)
            print(f"Successfully given Focus role to {interaction.user.display_name}")

            # set up our variables into a human-readable format, so it's clear what order things go into the database.
            username = interaction.user.display_name
            user_id = interaction.user.id
            seconds = minutes * 60
            end_time_for_user_session = Time_Stuff.get_current_time_in_epochs() + seconds
            start_time_for_user_session = Time_Stuff.convert_epochs_to_human_readable_time(
                Time_Stuff.get_current_time_in_epochs())
            user_info_tuple_to_log_to_database = (
                username, user_id, end_time_for_user_session, start_time_for_user_session)

            # now time to actually log all of that to the database.
            database_instance.log_to_DB(user_info_tuple_to_log_to_database, "Study_Fam_People_Currently_In_Focus_Mode")


@tree.command(name="time_left_in_focus", description="This will display how much time you have left in focus mode.")
async def display_time_left_for_user(interaction: discord.Interaction):
    database_entries = database_instance.retrieve_values_from_table("Study_Fam_People_Currently_In_Focus_Mode")

    current_time = Time_Stuff.get_current_time_in_epochs()

    if database_entries:

        for entry in database_entries:

            if interaction.user.id in entry:
                time_left = Time_Stuff.how_many_minutes_apart(entry[2], current_time)
                minutes = time_left[0]
                hours = time_left[1]
                days = time_left[2]

                await interaction.channel.send(
                    f"{interaction.user.mention} - You have {days} days, {hours} hours, and {minutes} minutes left "
                    f"in Focus Mode.")

            else:
                await interaction.channel.send(
                    f"{interaction.user.mention} - You are not in the Focus mode database currently.")


@tree.command(name="display_all_in_focus_mode", description="Displays all of the users currently in Focus Mode")
async def display_all_in_focus_mode(interaction: discord.Interaction):
    string_to_send_to_users = ""
    Focus_Role_Object = interaction.guild.get_role(Focus_Role_int)

    # builds the list of users in focus from the database and in the line after, all the users who have focus that are
    # not in the database too.
    database_entries = database_instance.retrieve_values_from_table("Study_Fam_People_Currently_In_Focus_Mode")

    # This is a list of member objects that are not in the database. It compares the role members' IDs with the
    # IDs in the list of tuples.
    all_focus_members = [member for member in interaction.guild.members if Focus_Role_Object in member.roles]
    non_database_users_in_focus = [member for member in all_focus_members if member.id
                                   not in [user[1] for user in database_entries]]

    # if there are no users with the focus role at all, then just say that.
    if not Focus_Role_Object.members:
        string_to_send_to_users += "There are currently no users in focus mode right now."
        await interaction.channel.send(string_to_send_to_users)

    else:
        # if there are any users who had the focus role via the bot, list their info out.
        if database_entries:

            # setting up the initial string
            string_to_send_to_users = "Here is the list of users currently in Focus Mode: \n" \
                                      "(Note that times listed are in Eastern time (UTC - 5:00) in 24h time format)\n\n"

            # format the string to be sent to the channel for each user.
            for entry in database_entries:
                string_to_send_to_users += f"User's name: {entry[0]}, \n"
                string_to_send_to_users += f"User's session start time: {entry[3]}, \n"
                string_to_send_to_users += f"User's session end time: " \
                                           f"{Time_Stuff.convert_epochs_to_human_readable_time(entry[2])}, \n\n"

        # for anyone else who is in focus not via the bot, list them out too.
        if non_database_users_in_focus:
            string_to_send_to_users += "Users in focus (not in the database) include: \n"
            for user in non_database_users_in_focus:
                string_to_send_to_users += f"{user.display_name}\n"

        # finally, send the message to the channel that we've spent all this time building.
        await interaction.channel.send(content=string_to_send_to_users)


@tree.command(name="test_response", description="If the bot is truly online, it will respond back with a response.")
async def test_response(interaction: discord.Interaction):
    await interaction.response.send_message("I have received a test response and I am working fine!",
                                            ephemeral=False)


@tree.command(name="give_max_focus_time", description="Warning, this will give you the focus role for a week straight.")
async def give_max_focus_time(interaction: discord.Interaction):
    Focus_Role_object = interaction.guild.get_role(Focus_Role_int)
    appropriate_response: str = Time_Stuff.time_responses(10080)
    user_info_from_db = database_instance.check_if_user_in_database(interaction.user.id)
    current_time = Time_Stuff.get_current_time_in_epochs()
    number_of_seconds_in_a_week = 604800
    max_time = current_time + number_of_seconds_in_a_week
    time_to_put_user_in_focus = max_time

    # if the user is in the database already, just update their time.
    if user_info_from_db:
        await interaction.response.defer()

        if time_to_put_user_in_focus > user_info_from_db[2]:
            await interaction.followup.send(content=appropriate_response, ephemeral=True)
            database_instance.update_user_info_from_focus_table(interaction.user.id, time_to_put_user_in_focus)

    # if the user is not already in the database, create an entry with the max focus time as their focus period.
    else:
        await interaction.response.send_message(appropriate_response, ephemeral=True)
        await interaction.user.add_roles(Focus_Role_object)
        print(f"Successfully given Focus role to {interaction.user.display_name}")

        username = interaction.user.display_name
        user_id = interaction.user.id
        end_time_for_user_session = time_to_put_user_in_focus
        start_time_for_user_session = Time_Stuff.convert_epochs_to_human_readable_time(current_time)
        user_info_tuple_to_log_to_database = (username, user_id, end_time_for_user_session, start_time_for_user_session)
        database_instance.log_to_DB(user_info_tuple_to_log_to_database, "Study_Fam_People_Currently_In_Focus_Mode")


@tree.command(name="remove_user_focus_override", description="Removes a user from focus role and their database entry "
                                                             "(mod only)")
async def remove_user_focus_override(interaction: discord.Interaction, user_to_be_removed: discord.User):
    await interaction.response.defer()
    server_id = secrets.discord_bot_credentials["Server_ID_for_Study_Fam"]
    guild = client.get_guild(server_id)
    member = interaction.user
    focus_role_id = secrets.discord_bot_credentials["Focus_Role_ID"]
    mod_role_id = secrets.discord_bot_credentials["Server_Mod_Role_ID"]
    botmod_role_id = secrets.discord_bot_credentials["Server_Botmod_Role_ID"]
    admin_role_id = secrets.discord_bot_credentials["Server_Admin_Role_ID"]

    # All we care about is if the user has the correct role, out of the 3 roles above, as long as they have at least one
    user_doing_command_has_correct_authorization = discord.utils.get(member.roles, id=mod_role_id) or discord.utils.get(
        member.roles, id=botmod_role_id) or discord.utils.get(member.roles, id=admin_role_id)

    if user_doing_command_has_correct_authorization:
        user_to_be_removed_has_focus_role_currently = discord.utils.get(member.roles, id=focus_role_id)
        user_is_in_db = database_instance.check_if_user_in_database(user_to_be_removed.id)

        if user_to_be_removed_has_focus_role_currently:
            current_user = await guild.fetch_member(user_to_be_removed.id)
            Focus_Role_object = discord.utils.get(guild.roles, name="Focus")
            await current_user.remove_roles(Focus_Role_object)
            print("User has been removed from the focus role")

        if user_is_in_db:
            database_instance.delete_user_info_from_table("Study_Fam_People_Currently_In_Focus_Mode",
                                                          user_to_be_removed.id)
            print("User has been removed from the database")

        appropriate_response = f"{user_to_be_removed.mention} has been removed from the database and set to not be in focus anymore!"
        await interaction.followup.send(content=appropriate_response, ephemeral=True)

    else:
        appropriate_response = "You do not have an authorized role to do this, sorry."
        await interaction.followup.send(content=appropriate_response, ephemeral=True)


@tree.command(name="give_endless_focus_mode", description="Gives focus mode until a mod pulls you out.")
async def give_endless_focus_mode(interaction: discord.Interaction):
    Focus_Role_object = interaction.guild.get_role(Focus_Role_int)
    appropriate_response = "You will now be in focus mode with no set end date. Please message or tag a moderator to " \
                           "be removed from focus."
    await interaction.response.send_message(appropriate_response, ephemeral=True)
    await interaction.user.add_roles(Focus_Role_object)
    print(f"Successfully given Focus role to {interaction.user.display_name}")


@tree.command(name="question_of_the_day", description="Provides a random question of the day")
async def question_of_the_day(interaction: discord.Interaction):
    current_channel = interaction.channel

    # We need to do this if the script is being run in a directory that is different from the working directory.
    questions_list_file_path_and_name = return_file_name_with_current_directory("conversation starters.txt")

    # get our question from the text file
    question_pulled_from_text_file = Text_Processing.get_random_line_from_text_file(questions_list_file_path_and_name)

    # send the question of the day to the channel the user typed the command in.
    message_to_send = f"**Question of the Day:** {question_pulled_from_text_file}"
    await current_channel.send(message_to_send)
    await interaction.delete_original_response()


# Function to post a random message in the specified channel
async def post_channel_message(channel_id: int, message: str):
    channel = client.get_channel(channel_id)
    await channel.send(message)


TOKEN = secrets.discord_bot_credentials["API_Key"]
client.run(TOKEN)
