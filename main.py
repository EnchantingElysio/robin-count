import datetime
import logging
import os

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
            daily_leaderboard.start(self.guild)
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
async def leaderboard(interaction: discord.Interaction):
    from lib.leaderboard import get_leaderboard_embed

    await interaction.response.defer(ephemeral=False)
    await interaction.followup.send(
        embed=get_leaderboard_embed(guild=interaction.guild)
    )


# TODO: fix scheduling
@tasks.loop(
    time=[
        datetime.time(hour=13, tzinfo=utc), # 9am
        datetime.time(hour=1, tzinfo=utc),  # 9pm
    ]
)
async def daily_leaderboard(guild: discord.Guild):
    from lib.leaderboard import get_leaderboard_embed

    channel = guild.system_channel

    now = datetime.datetime.now(tz=utc)
    embed = get_leaderboard_embed(
        guild=guild,
        # TODO: Have 9pm shows past 24 hours instead of 12
        start_date=now - datetime.timedelta(hours=12),
        end_date=now,
    )
    await channel.send(embed=embed)
    logging.info(
        f"Daily leaderboard sent in '{channel.name}' at "
        f"{datetime.datetime.now(tz=utc)}"
    )


@daily_leaderboard.before_loop
async def before_daily_leaderboard():
    # Wait until the bot is fully ready before starting the task.
    await client.wait_until_ready()
    logging.info("Daily leaderboard task is starting...")


client.run(os.getenv("DISCORD_TOKEN"))
