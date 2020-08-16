import asyncio
import json
import time
from datetime import datetime
import discord
from discord.ext import commands

from bot import log, logready
from cogs.database import new_user, update_activity, update_n_word
from functions import poll_ids, now, set_polls, auth


async def do_activity_update(bot, author: discord.Member, content: str):
    # if not message.author.bot:
    words = content.split(' ')
    valid_words = []
    for word in words:
        case_word = word.casefold()
        if len(case_word) > 2 and case_word not in valid_words:
            valid_words.append(case_word)
    # valid_words = [word for word in words if len(word) > 2]
    new_words = len(valid_words)
    added_activity_score = max(new_words - 2, 0)
    recently_spoke = time.time() - bot.recent_actives.get(author.id, 0) < bot.ACTIVITY_COOLDOWN
    if added_activity_score > 0 and not recently_spoke:
        bot.recent_actives[author.id] = time.time()
        await update_activity(author, added_activity_score)


async def do_n_word_update(author: discord.Member, content: str, word_list: [str]):
    if any(substring in content.casefold() for substring in word_list):
        await update_n_word(author, 1)


async def remind_routine(increments, user, author, message):
    if user is author:
        message = ':alarm_clock: **Reminder:** \n' + message
    else:
        message = f':alarm_clock: **Reminder from {author}**: \n' + message
    await asyncio.sleep(increments)
    await user.send(message)
    log(f'{user} has been sent their reminder {message}')


async def send_to_log_channel(log_channel, ctx, content: str, event_name: str = ''):
    author = ctx.author
    m_id = ctx.message.id
    embed = discord.Embed(title='',
                          description=f'**{event_name}**\n' + content,
                          timestamp=datetime.now())
    embed.set_footer(text=f'Author: {author} | Message ID: {m_id}')
    await log_channel.send(embed=embed)


class Basics(commands.Cog):

    def __init__(self, bot):
        set_polls()
        self.bot = bot
        self.verified_role = None
        self.log_channel = None
        self.deltime = None
        self.bot.recent_actives = dict()
        # This was specially requested by the client.
        self.word_list = [i.casefold() for i in ['nigga', 'nigger', 'niger', 'niga', 'niggah']]

    # Events
    # When bot is ready, print to console
    @commands.Cog.listener()
    async def on_ready(self):
        # self.verified_role = self.bot.server.get_role(self.bot.verified_role_id)
        self.log_channel = self.bot.server.get_channel(self.bot.log_channel_id)
        self.deltime = self.bot.deltime
        logready(self)

    # =============================Message handler=========================
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is not self.bot.server:
            return
        # =========================NEW USER==========================
        if not message.author.bot and message.author.id not in self.bot.list_of_users:
            await new_user(message.author)
            self.bot.list_of_users += [message.author.id]
        # =========================ACTIVITY==========================
        await do_activity_update(self.bot, message.author, message.content)
        # ========================N-Word=============================
        await do_n_word_update(message.author, message.content, self.word_list)

    # ==============================Reaction handler======================================
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        log(f'Reaction {payload.emoji.name} added to message {payload.message_id} by user'
            f' {self.bot.get_user(payload.user_id)} ({payload.emohi}, {payload.user_id}).')
        # =============================Verification Check======================

        # if payload.message_id == verification_message_id:
        #    target = self.bot.server.get_member(payload.user_id)
        #     if self.verified_role not in target.roles:
        #        log(await (new_user(target)))
        #        await target.add_roles(self.verified_role)
        #        log(f'Verified role added to {target}')
        # Ignore bots
        if payload.user_id == self.bot.user.id:
            return
        # # ===============================Polls==================================
        # if payload.message_id in poll_ids.keys():
        #     for channel in self.bot.get_all_channels():
        #         if channel.id is poll_ids[payload.message_id]["id"]:
        #             user = self.bot.get_user(payload.user_id)
        #             try:
        #                 user_responses = poll_ids[payload.message_id][user.id]
        #             except KeyError:
        #                 poll_ids[payload.message_id][user.id] = 0
        #                 user_responses = 0
        #             if user_responses < poll_ids[payload.message_id]['max']:
        #                 log(f'New reaction on poll {payload.message_id} by {user}.')
        #                 poll_ids[payload.message_id][reactions_to_nums[payload.emoji.name] - 1] += [user.id]
        #                 try:
        #                     poll_ids[payload.message_id][user.id] += 1
        #                 except KeyError:
        #                     poll_ids[payload.message_id][user.id] = 1
        #                 log(poll_ids)
        #                 try:
        #                     msg = await channel.fetch_message(payload.message_id)
        #                     new_embed = discord.Embed(title='', description='',
        #                                               color=user.color)
        #                     new_embed.set_author(icon_url=user.avatar_url,
        #                                          name=poll_ids[payload.message_id]["title"])
        #                     for i in range(0, 9):
        #                         if len(poll_ids[payload.message_id].get(i, [])) > 0:
        #                             new_embed.add_field(name=f"Option {i + 1}:",
        #                                                 value=str(len(poll_ids[payload.message_id][i])))
        #                     await msg.edit(embed=new_embed)
        #                     return
        #                 except NotFound:
        #                     continue
        #             else:
        #                 await self.bot.get_channel(payload.channel_id).send(f'{user}, you have already replied '
        #                                                                     f'the maximum number of times '
        #                                                                     f'to that poll. If you want to change '
        #                                                                     f'your responses, remove '
        #                                                                     f'your previous reaction(s) and try '
        #                                                                     f'again.',
        #                                                                     delete_after=self.deltime)
        #                 await (await self.bot.get_channel(payload.channel_id).fetch_message(
        #                     payload.message_id)).remove_reaction(payload.emoji,
        #                                                          self.bot.get_guild(payload.guild_id).get_member(
        #                                                              payload.user_id))

    # Reaction removal handler
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        log(f'Reaction {payload.emoji.name} removed from message {payload.message_id} by user'
            f' {self.bot.get_user(payload.user_id)} ({payload.emohi}, {payload.user_id}).')
        # =============================Verification Check======================

        # if payload.message_id == verification_message_id:
        #    target = self.bot.server.get_member(payload.user_id)
        #    if self.verified_role in target.roles:
        #        await target.remove_roles(self.verified_role)
        #        log(f'Verified role removed from {target}')
        # # =============================Polls===================================
        #
        # if payload.message_id in poll_ids.keys():
        #     for channel in self.bot.get_all_channels():
        #         if channel.id is poll_ids[payload.message_id]["id"]:
        #             user = self.bot.get_user(payload.user_id)
        #             poll_ids[payload.message_id][reactions_to_nums[payload.emoji.name] - 1].remove(user.id)
        #             poll_ids[payload.message_id][user.id] -= 1
        #             log(poll_ids)
        #             try:
        #                 msg = await channel.fetch_message(payload.message_id)
        #                 new_embed = discord.Embed(title='', description='', color=user.color)
        #                 new_embed.set_author(icon_url=user.avatar_url, name=poll_ids[payload.message_id]["title"])
        #                 for i in range(0, 9):
        #                     if len(poll_ids[payload.message_id].get(i, [])) > 0:
        #                         new_embed.add_field(name=f"Option {i + 1}:",
        #                                             value=str(len(poll_ids[payload.message_id][i])))
        #                 if len(new_embed.fields) == 0:
        #                     new_embed.add_field(name="Poll Results:", value="No votes yet.")
        #                 await msg.edit(embed=new_embed)
        #                 return
        #             except NotFound:
        #                 continue

    # Deleted message handler
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.guild.id == self.bot.server.id:
            if len(message.content) > self.bot.content_max + 3:
                content = message.content[:self.bot.content_max] + '...'
            else:
                content = message.content
            embed = discord.Embed(title='',
                                  description=f'**Message by {message.author.mention} deleted in '
                                              f'{message.channel.mention}**\n' + content,
                                  timestamp=datetime.now())
            embed.set_author(icon_url=message.author.avatar_url, name=message.author)
            embed.set_footer(text=f'Author: {message.author.id} | Message ID: {message.id}')
            await self.bot.log_channel.send(embed=embed)
            log(f'Message {message} deleted in {message.channel}', self.bot.info)

    # Edited message handler
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        log('on message edit triggered', self.bot.debug)
        if before.guild.id == self.bot.server.id and not after.author.bot:  # If in GFW and not a bot message
            log('edit log triggered', self.bot.debug)
            if len(before.content) > self.bot.content_max - 7:
                before_content = before.content[:self.bot.content_max - 10] + '...'
            else:
                before_content = before.content
            if len(after.content) > self.bot.content_max + 3:
                after_content = after.content[:self.bot.content_max] + '...'
            else:
                after_content = after.content
            if len(before_content) + len(after_content) > self.bot.content_max + 3:
                embed_1 = discord.Embed(title='',
                                        description=f'**Message by {before.author.mention} edited in '
                                                    f'{before.channel.mention}**\n**Before:**\n' + before_content,
                                        timestamp=datetime.now())
                embed_2 = discord.Embed(title='',
                                        description='**After:**\n' + after_content, timestamp=datetime.now())
                embed_1.set_author(icon_url=before.author.avatar_url, name=before.author)
                embed_1.set_footer(text=f'Author: {before.author.id} | Message ID: {after.id}')
                embed_2.set_author(icon_url=before.author.avatar_url, name=before.author)
                embed_2.set_footer(text=f'Author: {before.author.id} | Message ID: {after.id}')
                await self.bot.log_channel.send(embed=embed_1)
                await self.bot.log_channel.send(embed=embed_2)
            else:
                embed = discord.Embed(title='',
                                      description=f'**Message by {before.author.mention} edited in '
                                                  f'{before.channel.mention}**\n**Before:**\n' + before_content +
                                                  '\n**After:**\n' + after_content,
                                      timestamp=datetime.now())
                embed.set_author(icon_url=before.author.avatar_url, name=before.author)
                embed.set_footer(text=f'Author: {before.author.id} | Message ID: {after.id}')
                await self.bot.log_channel.send(embed=embed)

    # Bulk delete handler
    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        if messages[0].guild.id != self.bot.server.id:
            return
        for message in messages:
            if len(message.content) > self.bot.content_max + 3:
                content = message.content[:self.bot.content_max] + '...'
            else:
                content = message.content
            embed = discord.Embed(title='',
                                  description=f'**Message by {message.author.mention} deleted in '
                                              f'{message.channel.mention}**\n' + content,
                                  timestamp=datetime.now())
            embed.set_author(icon_url=message.author.avatar_url, name=message.author)
            embed.set_footer(text=f'Author: {message.author.id} | Message ID: {message.id}')
            await self.bot.log_channel.send(embed=embed)

    # Commands
    @commands.command(aliases=['plonk'], description='Pong!')
    async def ping(self, ctx):
        """
        Returns the ping to the bot.
        """
        ping = round(self.bot.latency * 1000)
        await ctx.message.delete(delay=self.deltime)  # delete the command
        await ctx.send(f'Ping is {ping}ms.', delete_after=self.deltime)
        log(f'Ping command used by {ctx.author} with ping {ping}.', self.bot.cmd)

    # Send you a reminder DM with a custom message in a custom amount of time
    @commands.command(name='remind', aliases=['rem', 're', 'r', 'remindme', 'tellme', 'timer'], pass_context=True,
                      description='Send reminders!')
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
        1y: next year (or probably never, as the bot intentionally forgets reminders when it restarts)
        """
        try:
            log(ctx.message.raw_mentions[0], self.bot.debug)
            user = ctx.author  # ctx.guild.get_member(ctx.message.raw_mentions[0]) turned off for spam
        except IndexError:
            user = None
        if user is None:
            user = ctx.author
        t = reminder.rsplit(' in ', 1)
        reminder = t[0]
        increments = 0
        if t[1][:-1].isdecimal():  # true if in 15m format is proper, 1 letter at the end preceded by a number
            # preceded by in
            increments = int(t[1][:-1])  # number of increment to wait
            increment = t[1][-1]  # s, m, h, d, w, y
            increments *= self.bot.time_options.get(increment, 1)
            log(f'{ctx.author} created a reminder to {user} for {increments} seconds from now; {t}')
            self.bot.loop.create_task(remind_routine(increments, user, ctx.author, reminder))
            await ctx.send(f"Got it. I'll send the reminder in {increments} seconds.", delete_after=self.deltime)
        else:
            await ctx.send('Please enter a valid time interval. You can use s, m, h, d, w, y as your interval time '
                           'prefix.', delete_after=self.deltime)
        await ctx.message.delete(delay=self.deltime)  # delete the command
        log(f'Remind command used by {ctx.author} with reminder {reminder} to user {user} for '
            f'time {increments}.', self.bot.cmd)

    @commands.command(name='poll', pass_context=True, description='Create a poll.')
    @commands.check(auth(1))
    async def create_poll(self, ctx, num_options=2, max_options=1, *, text):
        """
        Creates a poll.
        num_options is how many options your poll has
        max_options is the maximum number someone can select
        text is what your poll is asking
        """
        if num_options < 1:
            num_options = 1
        elif num_options > 9:
            num_options = 9
        embed = discord.Embed(title=f'Poll Results', color=ctx.author.color)
        embed.set_author(icon_url=ctx.author.avatar_url, name=f'{text}')
        results = f'No Votes Yet.'
        embed.add_field(name='Poll Results:', value=results)
        poll_message = await ctx.send(content=None, embed=embed)
        log(f'Created a new poll from the message in channel {poll_message.channel.id} with id {poll_message.id}.')
        poll_ids[poll_message.id] = {'id': poll_message.channel.id}
        poll_ids[poll_message.id]['title'] = text
        poll_ids[poll_message.id]['max'] = max_options
        for i in range(0, num_options):
            await poll_message.add_reaction(self.bot.number_reactions[i])
            poll_ids[poll_message.id][i] = []
            await asyncio.sleep(0.1)
        with open('polls.json', 'r') as f:
            polls = json.load(f)
        polls[poll_message.id] = poll_ids[poll_message.id]
        with open('polls.json', 'w') as f:
            json.dump(polls, f, indent=4)
        log(poll_message.embeds[0].fields[0].value, self.bot.debug)
        log(f'Poll command used by {ctx.author} with poll {text}.', self.bot.cmd)

    @commands.command(description='Check the current time')
    async def time(self, ctx):
        """
        Check the current time
        """
        await ctx.send(f'It is currently {now()}.')
        log(f'Time command used by {ctx.author}.', self.bot.cmd)


def setup(bot):
    bot.add_cog(Basics(bot))
