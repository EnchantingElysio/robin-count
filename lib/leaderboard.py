from datetime import datetime, timezone, timedelta
from dateutil import relativedelta

import discord


def get_leaderboard_embed(
    guild: discord.Guild, start_date: datetime = None, end_date: datetime = None, timeframe="all"
):
    from lib.mongo import get_leaderboard

    if timeframe == "all":
        timeframe="All Time"
    timeframe = timeframe.capitalize()

    # Get the top 10 leaderboard entries.
    leaderboard_data = get_leaderboard(
        limit=10, start_date=start_date, end_date=end_date
    )
    if not leaderboard_data:
        return discord.Embed(
            title="Robin Leaderboard",
            description="No leaderboard data available",
        )

    # Build description using member sorted leaderboard     
    top = ""
    lists = "" 
    description = f"{timeframe} stats:"

    embed = discord.Embed(title="Robin Leaderboard", description=description, color=discord.Color.from_str("#d15236"), timestamp=discord.utils.utcnow())
    for rank, entry in enumerate(leaderboard_data, start=1):
        # Attempt to get the member object from the guild.
        member = guild.get_member(int(entry["user_id"])) if guild else None
        if rank == 1:
            top_member = member
            top=f":crown: **{member.display_name}**: {entry['total']} <:tiny_winner_robin:1351970472916680744>"
            continue
        lists=f"{rank}. {member.display_name}: {entry['total']} <:tiny_robin:1351821803156279336>\n"
    embed.add_field(name=top, value=lists, inline=False)
    embed.set_thumbnail(url=top_member.display_avatar.url)

    return embed

def get_daily_leaderboard_embed(
    guild: discord.Guild
):
    from lib.mongo import get_leaderboard

    utc = timezone.utc

    now = datetime.now(tz=utc)
    if now.hour < 4:
        now = now - timedelta(days = 1)

    # Get the top 10 DAILY leaderboard entries.
    daily_leaderboard_data = get_leaderboard(
        limit=10, 
        start_date=now.replace(hour=4, minute=0, second=0, microsecond=0),
        end_date=datetime.now(tz=utc), 
    )
    
    # Get the top 10 WEEKLY leaderboard entries.
    start=now + relativedelta.relativedelta(weekday=relativedelta.SU(-1))
    weekly_leaderboard_data = get_leaderboard(
        limit=10,                                         
        start_date=start.replace(hour=4, minute=0, second=0, microsecond=0),
        end_date=datetime.now(tz=utc)
    )

    if not daily_leaderboard_data and not weekly_leaderboard_data:
        return discord.Embed(
            title="Robin Leaderboard",
            description="No leaderboard data available",
        )
    
        # Build description using member sorted leaderboard     
    daily_top = ""
    daily_lists = "No data available." 
    weekly_top = ""
    weekly_lists = "No data available."
    description = ""

    embed = discord.Embed(title="Robin Leaderboard", description=description, color=discord.Color.from_str("#d15236"), timestamp=discord.utils.utcnow())
    embed.add_field(name="Daily Roundup", value="", inline=False)
    for rank, entry in enumerate(daily_leaderboard_data, start=1):
        # Attempt to get the member object from the guild.
        member = guild.get_member(int(entry["user_id"])) if guild else None
        if rank == 1:
            top_member = member
            daily_top=f":crown: **{member.display_name}**: {entry['total']} <:tiny_winner_robin:1351970472916680744>"
            continue
        daily_lists=f"{rank}. {member.display_name}: {entry['total']} <:tiny_robin:1351821803156279336>\n"
    embed.add_field(name=daily_top, value=daily_lists, inline=False)

    embed.add_field(name="\u200b", value="", inline=False)
    embed.add_field(name="Weekly Stats", value="", inline=False)

    for rank, entry in enumerate(weekly_leaderboard_data, start=1):
        # Attempt to get the member object from the guild.
        member = guild.get_member(int(entry["user_id"])) if guild else None
        if rank == 1:
            top_member = member
            weekly_top=f":crown: **{member.display_name}**: {entry['total']} <:tiny_winner_robin:1351970472916680744>"
            continue
        weekly_lists=f"{rank}. {member.display_name}: {entry['total']} <:tiny_robin:1351821803156279336>\n"
    embed.add_field(name=weekly_top, value=weekly_lists, inline=False)

    return embed