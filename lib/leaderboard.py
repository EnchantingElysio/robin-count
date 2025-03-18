from datetime import datetime

import discord


def get_leaderboard_embed(
    guild: discord.Guild, start_date: datetime = None, end_date: datetime = None
):
    from lib.mongo import get_leaderboard

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
    description = ""
    for rank, entry in enumerate(leaderboard_data, start=1):
        # Attempt to get the member object from the guild.
        member = guild.get_member(int(entry["_id"])) if guild else None
        if rank == 1:
            top_member = member
        description += (
            f"{rank}. **{member.display_name}**: {entry['total']} "
            "<:tiny_robin:1350570765719961700>"
        )

    embed = discord.Embed(title="Robin Leaderboard", description=description)
    embed.set_thumbnail(url=top_member.display_avatar.url)

    return embed
