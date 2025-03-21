import datetime
import logging
import os
from typing import List
from dateutil import relativedelta

import discord
from discord.ext import tasks
from dotenv import load_dotenv

load_dotenv()

GUILD_ID = int(os.getenv("GUILD_ID"))
utc = datetime.timezone.utc

discord.utils.setup_logging(
    level=getattr(logging, os.getenv("LOG_LEVEL")), root=False
)


class RobinClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)
        self.app_commands = discord.app_commands
        self.guild: discord.Guild = None

    async def setup_hook(self):
        # Retrieve the full guild instance.
        guild = self.get_guild(GUILD_ID)
        if guild is None:
            guild = await self.fetch_guild(GUILD_ID)
        self.guild = guild

        # Sync global commands to this guild.
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    async def on_ready(self):
        # Ensure the guild is set.
        if self.guild is None:
            self.guild = self.get_guild(GUILD_ID)

        # Start the daily leaderboard task.
        if not daily_leaderboard.is_running():
            daily_leaderboard.start()
        logging.info("Ready!")
        print("Ready!")


intents = discord.Intents.default()
intents.members = True
client = RobinClient(intents=intents)

@client.tree.command(
    name="add",
    description="Add number of robins at the current time.",
)
async def add(interaction: discord.Interaction, number: int):
    from lib.mongo import log_robins

    log_robins(
        interaction.user.id,
        number,
        datetime.datetime.now(tz=utc),
    )
    await interaction.response.send_message(
        f"Added {number} robins for {interaction.user.display_name}!",
        ephemeral=True,
    )


@client.tree.context_menu(name="Get current user robins.")
async def user_robins(interaction: discord.Interaction, member: discord.Member):
    from lib.mongo import get_robins

    await interaction.response.send_message(
        f"{member} has logged {get_robins(user_id=member.id)} robins!",
        ephemeral=True,
    )


@client.tree.command(
    name="leaderboard", description="Show the top robin users."
)
@client.app_commands.choices(timeframe=[
        client.app_commands.Choice(name="Weekly", value="weekly"),
        client.app_commands.Choice(name="Daily", value="daily"),
        client.app_commands.Choice(name="All Time", value="all"),
        ])
async def leaderboard(interaction: discord.Interaction, timeframe: str = "weekly"):
    from lib.leaderboard import get_leaderboard_embed

    await interaction.response.defer(ephemeral=False)

    # Calculate accurate date for EST
    now = datetime.datetime.now(tz=utc)
    if now.hour < 4:
        now = now - datetime.timedelta(days = 1)

    match timeframe:
        case "all":
            embed=get_leaderboard_embed(guild=interaction.guild, 
                                        start_date=datetime.datetime(1970, 1, 1, 0, 0, 0, 0, tzinfo=utc), 
                                        end_date=datetime.datetime.now(utc), 
                                        timeframe=timeframe)

        case "daily":
            embed=get_leaderboard_embed(guild=interaction.guild,
                                        start_date=now.replace(hour=4, minute=0, second=0, microsecond=0),
                                        end_date=datetime.datetime.now(utc), 
                                        timeframe=timeframe)
        case "weekly":
            today = datetime.date.today()
            start = now + relativedelta.relativedelta(weekday=relativedelta.SU(-1))
            start = start.replace(hour=4, minute=0, second=0, microsecond=0)
            embed=get_leaderboard_embed(guild=interaction.guild,
                                        start_date=start,
                                        end_date=datetime.datetime.now(utc),
                                        timeframe=timeframe)
        case _:
            #TODO fix this so it'll actually return properly 
            embed = "Error! Timeframe not recognized!"

    await interaction.followup.send(
        embed=embed
    )

@client.tree.command(
        name="progress", description="Show the server's progress toward its goal!"
)
@client.app_commands.choices(timeframe=[
        client.app_commands.Choice(name="Weekly", value="weekly"),
        client.app_commands.Choice(name="Daily", value="daily"),
        # client.app_commands.Choice(name="Seasonal", value="seasonal"),
        ])
async def progress(interaction: discord.Interaction, timeframe: str = "weekly"):
    from lib.mongo import get_all_in_timeframe
    from lib.progressbar import get_progress_bar

    await interaction.response.defer(ephemeral=False)

    # Calculate accurate date for EST
    now = datetime.datetime.now(tz=utc)
    if now.hour < 4:
        now = now - datetime.timedelta(days = 1)

    robin_data = None
    embed = ""
    wgoal = int(os.getenv("WEEKLY_GOAL"))
    goal = wgoal

    match timeframe:
        # case "seasonal":
        #     robin_data=get_all_in_timeframe( 
        #                                 start_date=datetime.datetime(1970, 1, 1, 0, 0, 0, 0, tzinfo=utc), 
        #                                 end_date=datetime.datetime.now(utc)
        #                                 )
        #     goal=None

        case "daily":
            robin_data=get_all_in_timeframe(
                                        start_date=now.replace(hour=4, minute=0, second=0, microsecond=0),
                                        end_date=datetime.datetime.now(utc)
                                        )
            goal = wgoal/7
        case "weekly":
            today = datetime.date.today()
            start = now + relativedelta.relativedelta(weekday=relativedelta.SU(-1))
            start = start.replace(hour=4, minute=0, second=0, microsecond=0)
            robin_data=get_all_in_timeframe(
                                        start_date=start,
                                        end_date=datetime.datetime.now(utc)
                                        )
        case _:
            print("Error! Unable to get robin data")
            
    if not robin_data:
        await interaction.followup.send(
            embed=embed
        )
        return
    
    total = int(robin_data[0]["_id"])
    progress_bar: str = get_progress_bar(goal=goal, total=total)
    print(progress_bar)
    
    embed = discord.Embed(
            title="Robin Data",
            description = progress_bar,
        )
    await interaction.followup.send(
        embed=embed
    )


@tasks.loop(
    time=[
        datetime.time(hour=21, tzinfo=utc), # 9pm UTC
        datetime.time(hour=1, tzinfo=utc),  # 9pm EST
    ]
)
async def daily_leaderboard():
    from lib.leaderboard import get_daily_leaderboard_embed

    guilds = client.guilds

    for guild in guilds:
        env_channel = os.getenv("CHANNEL_ID")
        channel = client.get_channel(int(env_channel)) or guild.system_channel
        print(client.get_channel(env_channel))
        print(f"Active channel: {channel}")

        embed = get_daily_leaderboard_embed(
            guild=guild
        )

        # Set robin thumbnail
        file = discord.File("images/tiny_winner_robin.png")
        embed.set_thumbnail(url="attachment://tiny_winner_robin.png")

        await channel.send(embed=embed, file=file)
        logging.info(
            f"Daily leaderboard sent in '{channel.name}' in '{guild.name}' at "
            f"{datetime.datetime.now(tz=utc)}"
        )


@daily_leaderboard.before_loop
async def before_daily_leaderboard():
    # Wait until the bot is fully ready before starting the task.
    await client.wait_until_ready()
    logging.info("Daily leaderboard task is starting...")


client.run(os.getenv("DISCORD_TOKEN"))
