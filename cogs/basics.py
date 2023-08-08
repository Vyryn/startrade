import asyncio
import time
from datetime import datetime
import discord  # pylint: disable=import-error
from discord.ext import commands  # pylint: disable=import-error

from bot import log, logready
from cogs.database import new_user, update_activity
from functions import now, set_polls


def get_activity_worth(msg: str) -> int:
    """Calcluates the activity points due for a given message"""
    # if not message.author.bot:
    if len(msg) < 3:
        return 0  # No activity score for teeny messages.
    if msg[0] == "(" or msg[0] == "/":  # or msg[0] == '$' or msg[0] == ',':
        return 0  # No activity score for ooc comments.
    words = msg.split(" ")
    valid_words = list(set([word.casefold() for word in words if len(word) > 3]))
    new_words = len(valid_words)
    return max(new_words - 2, 0)


async def do_activity_update(
    bot, channel: discord.TextChannel, author: discord.Member, content: str
):
    if author.bot:
        return
    if channel.id not in bot.activity_channels:
        return  # No activity score for messages not in rp channels.
    added_activity_score = get_activity_worth(content)

    recently_spoke = (
        time.time() - bot.recent_actives.get(author.id, 0) < bot.ACTIVITY_COOLDOWN
    )
    if added_activity_score > 0 and not recently_spoke:
        bot.recent_actives[author.id] = time.time()
        await update_activity(author, added_activity_score)


async def remind_routine(increments, user, author, message):
    if user is author:
        message = ":alarm_clock: **Reminder:** \n" + message
    else:
        message = f":alarm_clock: **Reminder from {author}**: \n" + message
    await asyncio.sleep(increments)
    await user.send(message)
    log(f"{user} has been sent their reminder {message}")


async def send_to_log_channel(log_channel, ctx, content: str, event_name: str = ""):
    author = ctx.author
    m_id = ctx.message.id
    embed = discord.Embed(
        title="", description=f"{event_name}\n" + content, timestamp=datetime.now()
    )
    embed.set_footer(text=f"Author: {author} | Message ID: {m_id}")
    await log_channel.send(embed=embed)


class Basics(commands.Cog):
    def __init__(self, bot):
        set_polls()
        self.bot = bot
        self.verified_role = None
        self.log_channel = None
        self.deltime = None
        self.bot.recent_actives = dict()

    # Events
    # When bot is ready, print to console
    @commands.Cog.listener()
    async def on_ready(self):
        # self.verified_role = self.bot.server.get_role(self.bot.verified_role_id)
        self.log_channel = self.bot.log_channel
        self.deltime = self.bot.deltime
        logready(self)

    # =============================Message handler=========================
    @commands.Cog.listener()
    async def on_message(self, message):
        if not hasattr(self.bot, "server"):
            return  # Not fully initialized yet
        if message.guild is not self.bot.server:
            return
        if message.author.bot:
            return
        # =========================NEW USER==========================
        if (
            message.author.id not in self.bot.list_of_users
            and not message.content.startswith("$paycheck")
        ):
            await new_user(message.author)
            self.bot.list_of_users.append(message.author.id)
        # =========================ACTIVITY==========================
        try:
            if message.content[0] == "$":
                return
        except IndexError:
            return
        await do_activity_update(
            self.bot, message.channel, message.author, message.content
        )

    # Deleted message handler
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.guild.id == self.bot.server.id:
            if len(message.content) > self.bot.content_max + 3:
                content = message.content[: self.bot.content_max] + "..."
            else:
                content = message.content
        embed = discord.Embed(
            title="",
            description=f"**Message by {message.author.mention} deleted in "
            f"{message.channel.mention}**\n" + content,
            timestamp=datetime.now(),
        )
        embed.set_author(
            icon_url=message.author.display_avatar.url, name=message.author
        )
        embed.set_footer(text=f"Author: {message.author.id} | Message ID: {message.id}")
        await self.bot.log_channel.send(embed=embed)
        log(f"Message {message} deleted in {message.channel}", self.bot.info)

    # Edited message handler
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        log("on message edit triggered", self.bot.debug)
        if (
            before.guild.id == self.bot.server.id and not after.author.bot
        ):  # If in GFW and not a bot message
            log("edit log triggered", self.bot.debug)
            if len(before.content) > self.bot.content_max - 7:
                before_content = before.content[: self.bot.content_max - 10] + "..."
            else:
                before_content = before.content
            if len(after.content) > self.bot.content_max + 3:
                after_content = after.content[: self.bot.content_max] + "..."
            else:
                after_content = after.content
            if len(before_content) + len(after_content) > self.bot.content_max + 3:
                embed_1 = discord.Embed(
                    title="",
                    description=f"**Message by {before.author.mention} edited in "
                    f"{before.channel.mention}**\n**Before:**\n" + before_content,
                    timestamp=datetime.now(),
                )
                embed_2 = discord.Embed(
                    title="",
                    description="**After:**\n" + after_content,
                    timestamp=datetime.now(),
                )
                embed_1.set_author(
                    icon_url=before.author.display_avatar.url, name=before.author
                )
                embed_1.set_footer(
                    text=f"Author: {before.author.id} | Message ID: {after.id}"
                )
                embed_2.set_author(
                    icon_url=before.author.display_avatar.url, name=before.author
                )
                embed_2.set_footer(
                    text=f"Author: {before.author.id} | Message ID: {after.id}"
                )
                await self.bot.log_channel.send(embed=embed_1)
                await self.bot.log_channel.send(embed=embed_2)
            else:
                embed = discord.Embed(
                    title="",
                    description=f"**Message by {before.author.mention} edited in "
                    f"{before.channel.mention}**\n**Before:**\n"
                    + before_content
                    + "\n**After:**\n"
                    + after_content,
                    timestamp=datetime.now(),
                )
                embed.set_author(
                    icon_url=before.author.display_avatar.url, name=before.author
                )
                embed.set_footer(
                    text=f"Author: {before.author.id} | Message ID: {after.id}"
                )
                await self.bot.log_channel.send(embed=embed)

    # Bulk delete handler
    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        if messages[0].guild.id != self.bot.server.id:
            return
        for message in messages:
            if len(message.content) > self.bot.content_max + 3:
                content = message.content[: self.bot.content_max] + "..."
            else:
                content = message.content
            embed = discord.Embed(
                title="",
                description=f"**Message by {message.author.mention} deleted in "
                f"{message.channel.mention}**\n" + content,
                timestamp=datetime.now(),
            )
            embed.set_author(
                icon_url=message.author.display_avatar.url, name=message.author
            )
            embed.set_footer(
                text=f"Author: {message.author.id} | Message ID: {message.id}"
            )
            await self.bot.log_channel.send(embed=embed)

    # Commands
    @commands.command(aliases=["plonk"], description="Pong!")
    async def ping(self, ctx):
        """
        Returns the ping to the bot.
        """
        ping = round(self.bot.latency * 1000)
        await ctx.message.delete(delay=self.deltime)  # delete the command
        await ctx.send(f"Ping is {ping}ms.", delete_after=self.deltime)
        log(f"Ping command used by {ctx.author} with ping {ping}.", self.bot.cmd)

    # Send you a reminder DM with a custom message in a custom amount of time
    @commands.command(
        name="remind",
        aliases=["rem", "re", "r", "remindme", "tellme", "timer"],
        pass_context=True,
        description="Send reminders!",
    )
    async def remind(self, ctx, *, reminder=None):
        """
        Reminds you what you tell it to.
        Example: remind do a paycheck in 1h
        Your reminder needs to end with in and then the amount of time you want to be reminded in.
        10s: 10 seconds from now
        10m: 10 minutes from now
        1h:   1 hour from now
        1d: tomorrow at this time
        1w: next week at this time
        1y: next year (or probably never, as the bot forgets reminders when it restarts)
        """
        if reminder is None:
            return await ctx.send('Incorrect usage. Try "remind do xyz in 1h"')
        try:
            log(ctx.message.raw_mentions[0], self.bot.debug)
            user = (
                ctx.author
            )  # ctx.guild.get_member(ctx.message.raw_mentions[0]) turned off for spam
        except IndexError:
            user = None
        if user is None:
            user = ctx.author
        t = reminder.rsplit(" in ", 1)
        reminder = t[0]
        increments = 0
        try:
            if t[1][
                :-1
            ].isdecimal():  # true if in 15m format is proper, 1 letter at the end preceded by
                # a number preceded by in
                increments = int(t[1][:-1])  # number of increment to wait
                increment = t[1][-1]  # s, m, h, d, w, y
                increments *= self.bot.time_options.get(increment, 1)
                log(
                    f"{ctx.author} created a reminder to {user} for {increments} seconds from now;"
                    f"{t}"
                )
                self.bot.loop.create_task(
                    remind_routine(increments, user, ctx.author, reminder)
                )
                await ctx.send(
                    f"Got it. I'll send the reminder in {increments} seconds.",
                    delete_after=self.deltime,
                )
            else:
                await ctx.send(
                    "Please enter a valid time interval. You can use s, m, h, d, w, y as"
                    " your interval time prefix.",
                    delete_after=self.deltime,
                )
        except IndexError:
            return await ctx.send('Incorrect usage. Try "remind do xyz 1h"')
        await ctx.message.delete(delay=self.deltime)  # delete the command
        log(
            f"Remind command used by {ctx.author} with reminder {reminder} to user {user} for "
            f"time {increments}.",
            self.bot.cmd,
        )

    @commands.command(description="Check the current time")
    async def time(self, ctx):
        """
        Check the current time
        """
        await ctx.send(f"It is currently {now()}.")
        log(f"Time command used by {ctx.author}.", self.bot.cmd)


async def setup(bot):
    await bot.add_cog(Basics(bot))
