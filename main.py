import datetime
import logging
import os
from typing import List

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
        client.app_commands.Choice(name="All", value="all"),
        ])
async def leaderboard(interaction: discord.Interaction, timeframe: discord.app_commands.Choice[str] = "weekly"):
    from lib.leaderboard import get_leaderboard_embed

    await interaction.response.defer(ephemeral=False)
    await interaction.followup.send(
        embed=get_leaderboard_embed(guild=interaction.guild)
    )

@tasks.loop(
    time=[
        datetime.time(hour=21, tzinfo=utc), # 9pm UTC
        datetime.time(hour=1, tzinfo=utc),  # 9pm EST
        datetime.time(hour=19, minute=22, tzinfo=utc), #TEST
    ]
)
async def daily_leaderboard():
    from lib.leaderboard import get_leaderboard_embed

    guilds = client.guilds

    for guild in guilds:
        channel = guild.system_channel

        now = datetime.datetime.now(tz=utc)
        if now.hour < 4:
            now = now - datetime.timedelta(days = 1)
        # update leaderboard to include weekly (since sunday)
        # datetime.date.today()
        # sun = today - datetime.timedelta(7+((today.isoweekday() + 1) % 7)))
        embed = get_leaderboard_embed(
            guild=guild,
            start_date=now.replace(hour=0, minute=0, second=0, microsecond=0),
            end_date=now,
        )
        await channel.send(embed=embed)
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
