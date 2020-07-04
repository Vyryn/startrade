import asyncio

import discord
from discord.ext import commands

from cogs.basics import send_to_log_channel
from cogs.database import add_funds
from functions import deltime, auth, confirmed_ids, now


async def confirmation_on(user):
    await asyncio.sleep(deltime * 2)
    confirmed_ids[user] = 0
    return


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Events
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'Cog {self.qualified_name} is ready.')

    # Commands
    @commands.command(aliases=['clear', 'del'], description='Delete a number of messages')
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        """Delete a bunch of messages
                Requires: Manage Message perms on your server
                Amount: The number of messages to purge. Typically limited to 100.
                People with Auth level 4 can delete more messages at once."""
        if int(amount) <= 100:
            await ctx.channel.purge(limit=int(amount) + 1)
            return print(f'{ctx.author} deleted {amount} messages in channel {ctx.channel} in guild {ctx.guild}.')
        elif await auth(4)(ctx):
            await ctx.channel.purge(limit=int(amount) + 1)
            return print(f'{ctx.author} deleted {amount} messages in channel {ctx.channel} in guild {ctx.guild}.')
        else:
            await ctx.send('You may only delete up to 100 messages', delete_after=deltime)

    @commands.command(description='Delete a number of messages')
    @commands.check(auth(6))
    async def forcepurge(self, ctx, amount: int):
        """Delete a bunch of messages
                Requires: Auth 6. This is meant for use only in cases where the bot has caused spam that it shouldn't
                have.
                Amount: The number of messages to purge. Typically limited to 100.
                People with Auth level 4 can delete more messages at once."""
        if int(amount) <= 100:
            await ctx.channel.purge(limit=int(amount) + 1)
            return print(f'{ctx.author} deleted {amount} messages in channel {ctx.channel} in guild {ctx.guild}.')
        elif await auth(4)(ctx):
            await ctx.channel.purge(limit=int(amount) + 1)
            return print(f'{ctx.author} deleted {amount} messages in channel {ctx.channel} in guild {ctx.guild}.')
        else:
            await ctx.send('You may only delete up to 100 messages', delete_after=deltime)

    @commands.command(description='Kick a member from the server.')
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = 'No reason provided.'):
        """Kick someone out of the server
                Requires: Kick Members permission
                Member: the person to kick
                Reason: the reason why, defaults to 'No reason provided.'"""
        reason = f'{ctx.author} kicked {member} for reason {reason}'
        await member.kick(reason=reason)

    @commands.command(description='Ban a member.')
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = 'No reason provided.'):
        """Ban someone from the server
                Requires: Ban Members permission
                Member: the person to ban
                Reason: the reason why, defaults to 'No reason provided.'"""
        reason = f'{ctx.author} banned {member} for reason {reason}'
        await member.ban(reason=reason)
        await ctx.send(f'Banned {member.mention} for {reason}.')

    @commands.command(description='Unban a member')
    @commands.has_permissions(manage_guild=True)
    async def unban(self, ctx, *, member: discord.Member):
        """Unban someone from the server
                Requires: Manage Server permission
                Member: the person to unban"""
        async for ban in await ctx.guild.bans():
            if ban.user.id == member.id:
                await ctx.guild.unban(ban.user)
                await ctx.send(f'Unbanned {ban.user}')
        print(f'Unban command used by {ctx.author} at {now()} on user {member}.')

    @commands.command(description='Remove *all* the pins from a channel')
    @commands.has_permissions(manage_messages=True)
    async def clearpins(self, ctx):
        """Clear all the pinned messages from a channel.
                Requires: Manage Messages permission
                Note: It is highly recommended to be absolutely sure before using this command."""
        if confirmed_ids.get(ctx.author.id, 0) > 0:
            i = 0
            for pin in await ctx.channel.pins():
                await pin.unpin()
                i += 1
            await ctx.send(f'Okay {ctx.author}, {i} pins have been cleared.')
            confirmed_ids[ctx.author.id] = 0
            await ctx.message.delete()  # delete the command
        else:
            await ctx.send("Are you certain you wish to clear all the pins from this channel? This can not be undone. "
                           "If so, use this command again.", delete_after=deltime)
            confirmed_ids[ctx.author.id] = 1
            await ctx.message.delete()  # delete the command
            self.bg_task = self.bot.loop.create_task(confirmation_on(ctx.author.id))
        print(f'Clearpins command used by {ctx.author} at {now()} in channel {ctx.channel.name}.')

    @commands.command(description='Bestow upon someone the Certified Literate role!')
    async def certify(self, ctx, *, member: discord.Member):
        GRANT_AMOUNT = 1000
        literate = ctx.guild.get_role(728796399692677160)
        if literate not in ctx.author.roles:  #Don't allow people without the role to grant it
            return await ctx.send(f'{ctx.author}, you need to be Certified Literate to use that command.')
        if literate in member.roles:  # Don't allow getting the role twice
            return await ctx.send(f'That user has already been granted the Certified Literate role.')
        await ctx.send(f'{member.mention}\n```\nI hereby declare you an outstanding writer. May you be granted'
                       f' fortune in your future endeavours.```')
        await add_funds(member, GRANT_AMOUNT)
        log_channel = ctx.guild.get_channel(725817803273404618)
        await send_to_log_channel(ctx, f'{ctx.author.mention} bestowed the Certified Literate role upon'
                                       f' {member.mention}. ${GRANT_AMOUNT} granted.',
                                  event_name='**Certified Literate**')
        await member.add_roles(literate)


def setup(bot):
    bot.add_cog(Moderation(bot))
