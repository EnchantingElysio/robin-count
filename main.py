import datetime
import logging
import os
import traceback
from typing import List
from dateutil import relativedelta

import discord
from discord.ext import tasks
from dotenv import load_dotenv

load_dotenv()

GUILD_ID = int(os.getenv("GUILD_ID"))
utc = datetime.timezone.utc
robin_orange = discord.Color.from_str("#d15236")

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
    try:
        match timeframe:
            case "all":
                embed=get_leaderboard_embed(guild=interaction.guild, 
                                            start_date=datetime.datetime(1970, 1, 1, 0, 0, 0, 0, tzinfo=utc), 
                                            end_date=datetime.datetime.now(utc), 
                                            timeframe=timeframe,
                                            color=robin_orange)

            case "daily":
                embed=get_leaderboard_embed(guild=interaction.guild,
                                            start_date=now.replace(hour=4, minute=0, second=0, microsecond=0),
                                            end_date=datetime.datetime.now(utc), 
                                            timeframe=timeframe,
                                            color=robin_orange)
            case "weekly":
                today = datetime.date.today()
                start = now + relativedelta.relativedelta(weekday=relativedelta.SU(-1))
                start = start.replace(hour=4, minute=0, second=0, microsecond=0)
                embed=get_leaderboard_embed(guild=interaction.guild,
                                            start_date=start,
                                            end_date=datetime.datetime.now(utc),
                                            timeframe=timeframe,
                                            color=robin_orange)
            case _:
                embed = "Error! Timeframe not recognized!"
    
    except Exception as e:
        traceback.print_stack()
        logging.error(traceback.format_exc())
        embed=discord.Embed(title="Robin Leaderboard", description="Error retrieving leaderboard!")

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

    try:
        match timeframe:
            # TODO: add seasonal support
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
                embed=discord.Embed("Error: Unable to get robin data!")
            )
            return

        total = int(robin_data[0]["total"])
    except Exception as e:
        traceback.print_stack()
        logging.error(traceback.format_exc())
        await interaction.followup.send(embed=discord.Embed(title="Robin Progress", description="Error! Unable to get robin data"))
        return

    progress_bar: str = get_progress_bar(goal=goal, total=total)
    
    embed = discord.Embed(
            title=f"Robin Progress ({str.capitalize(timeframe)})",
            color=discord.Color.from_str("#e7bf59")
        )
    
    percentage_value=f"You're {round((total/goal)*100)}% there!"

    if total == int(goal):
        percentage_value="Woo! You've hit your goal! 🎉"
    elif total/goal > 1:
        percentage_value=f"Wow! You exceeded your goal by {round((total/goal)*100)}%! 🎉🎉🎉"
        #TODO: change colors across rainbow as we exceed goal further?
    else:
        embed.color=robin_orange   # set embed color to orange if goal not met

    embed.add_field(name=f"{total}/{round(goal)} Robins logged",
                    value=percentage_value,
                    inline=False)
    
    embed.add_field(name=progress_bar, value="")
    
    # Set robin thumbnail
    file = discord.File("images/tiny_winner_robin.png")
    embed.set_thumbnail(url="attachment://tiny_winner_robin.png")

    await interaction.followup.send(embed=embed, file=file)


@client.tree.command(
        name="total", description="Get the total amount of robins logged!"
)
async def total(interaction: discord.Interaction):
    from lib.mongo import get_all_in_timeframe

    await interaction.response.defer(ephemeral=False)

    try:
        robin_data=get_all_in_timeframe( 
                                    start_date=datetime.datetime(1970, 1, 1, 0, 0, 0, 0, tzinfo=utc), 
                                    end_date=datetime.datetime.now(utc)
                                    )
            
        if not robin_data:
            await interaction.followup.send(
                embed=discord.Embed("Error: Unable to get robin data!")
            )
            return
        
        total = int(robin_data[0]["total"])
    except Exception as e:
        traceback.print_stack()
        logging.error(traceback.format_exc())
        await interaction.followup.send(embed=discord.Embed(title="Total", description="Error! Unable to get robin data"))
        return
    await interaction.followup.send(embed=discord.Embed(title=f"A total of {total} robins have been logged!", color=robin_orange))

@tasks.loop(
    time=[
        datetime.time(hour=21, tzinfo=utc), # 9pm UTC
        datetime.time(hour=1, tzinfo=utc),  # 9pm EST
    ]
)
async def daily_leaderboard():
    from lib.leaderboard import get_daily_leaderboard_embed
    try:
        guilds = client.guilds

        for guild in guilds:
            env_channel = os.getenv("CHANNEL_ID")
            channel = client.get_channel(int(env_channel)) or guild.system_channel
            print(client.get_channel(env_channel))
            print(f"Active channel: {channel}")

            embed = get_daily_leaderboard_embed(
                guild=guild,
                color=robin_orange
            )

            # Set robin thumbnail
            file = discord.File("images/tiny_winner_robin.png")
            embed.set_thumbnail(url="attachment://tiny_winner_robin.png")

            await channel.send(embed=embed, file=file)
            logging.info(
                f"Daily leaderboard sent in '{channel.name}' in '{guild.name}' at "
                f"{datetime.datetime.now(tz=utc)}"
            )

    except Exception as e:
        traceback.print_stack()
        logging.error(traceback.format_exc())
        embed=discord.Embed(title="Robin Leaderboard", description="Error retrieving daily leaderboard!")
        await channel.send(embed=embed)



@daily_leaderboard.before_loop
async def before_daily_leaderboard():
    # Wait until the bot is fully ready before starting the task.
    await client.wait_until_ready()
    logging.info("Daily leaderboard task is starting...")


client.run(os.getenv("DISCORD_TOKEN"))
