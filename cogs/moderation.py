import asyncio
import discord
from discord.ext import commands
from cogs.basics import send_to_log_channel
from cogs.database import add_funds
from functions import auth, now


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.MAX_PURGE = 100  # Max number of messages that can be purged with ,forcepurge command at once
        self.GRANT_AMOUNT = 1000  # Certified Literate payout amount
        self.server = None
        self.literate = None
        self.deltime = None
        self.confirmed_ids = None

    async def confirmation_on(self, user):
        await asyncio.sleep(self.deltime * 2)
        self.confirmed_ids[user] = 0
        return

    # Events
    @commands.Cog.listener()
    async def on_ready(self):
        self.server = self.bot.get_guild(718893913976340561)
        # self.literate = self.server.get_role(728796399692677160)  # Certified Literate role
        self.deltime = self.bot.deltime
        self.confirmed_ids = self.bot.confirmed_ids
        print(f'Cog {self.qualified_name} is ready.')

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        # TODO: Check for verified and add has character role as necessary
        pass

    # Commands
    @commands.command(aliases=['clear', 'del'], description='Delete a number of messages')
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        """Delete a bunch of messages
                Requires: Manage Message perms on your server
                Amount: The number of messages to purge. Typically limited to 100.
                People with Auth level 4 can delete more messages at once."""
        if int(amount) <= self.MAX_PURGE:
            await ctx.channel.purge(limit=int(amount) + 1)
            return print(f'{ctx.author} deleted {amount} messages in channel {ctx.channel} in guild {ctx.guild}.')
        elif await auth(4)(ctx):
            await ctx.channel.purge(limit=int(amount) + 1)
            return print(f'{ctx.author} deleted {amount} messages in channel {ctx.channel} in guild {ctx.guild}.')
        else:
            await ctx.send(f'You may only delete up to {self.MAX_PURGE} messages', delete_after=self.deltime)

    @commands.command(description='Delete a number of messages')
    @commands.check(auth(6))
    async def forcepurge(self, ctx, amount: int):
        f"""Delete a bunch of messages
                Requires: Auth 6. This is meant for use only in cases where the bot has caused spam that it shouldn't
                have.
                Amount: The number of messages to purge. Typically limited to {self.MAX_PURGE}.
                People with Auth level 4 can delete more messages at once."""
        if int(amount) <= self.MAX_PURGE:
            await ctx.channel.purge(limit=int(amount) + 1)
            return print(f'{ctx.author} deleted {amount} messages in channel {ctx.channel} in guild {ctx.guild}.')
        elif await auth(4)(ctx):
            await ctx.channel.purge(limit=int(amount) + 1)
            return print(f'{ctx.author} deleted {amount} messages in channel {ctx.channel} in guild {ctx.guild}.')
        else:
            await ctx.send('You may only delete up to 100 messages', delete_after=self.deltime)

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
        if self.bot.confirmed_ids.get(ctx.author.id, 0) > 0:
            i = 0
            for pin in await ctx.channel.pins():
                await pin.unpin()
                i += 1
            await ctx.send(f'Okay {ctx.author}, {i} pins have been cleared.')
            self.bot.confirmed_ids[ctx.author.id] = 0
            await ctx.message.delete()  # delete the command
        else:
            await ctx.send("Are you certain you wish to clear all the pins from this channel? This can not be undone. "
                           "If so, use this command again.", delete_after=self.deltime)
            self.bot.confirmed_ids[ctx.author.id] = 1
            await ctx.message.delete()  # delete the command
            self.bot.loop.create_task(self.confirmation_on(ctx.author.id))
        print(f'Clearpins command used by {ctx.author} at {now()} in channel {ctx.channel.name}.')

    @commands.command(description='Bestow upon someone the Certified Literate role!')
    async def certify(self, ctx, *, member: discord.Member):
        if self.literate not in ctx.author.roles:  # Don't allow people without the role to grant it
            return await ctx.send(f'{ctx.author}, you need to be Certified Literate to use that command.')
        if self.literate in member.roles:  # Don't allow getting the role twice
            return await ctx.send(f'That user has already been granted the Certified Literate role.')
        await ctx.send(f'{member.mention}\n```\nI hereby declare you an outstanding writer. May you be granted'
                       f' fortune in your future endeavours.```')
        await add_funds(member, self.GRANT_AMOUNT)
        await send_to_log_channel(ctx, f'{ctx.author.mention} bestowed the Certified Literate role upon'
                                       f' {member.mention}. ${self.GRANT_AMOUNT} granted.',
                                  event_name='**Certified Literate**')
        await member.add_roles(self.literate)


def setup(bot):
    bot.add_cog(Moderation(bot))
