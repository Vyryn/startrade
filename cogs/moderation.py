import asyncio
import discord
from discord.ext import commands
from cogs.basics import send_to_log_channel
from cogs.database import add_funds
from functions import auth, now
from bot import log, logready


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.literate = None
        self.confirmed_ids = None

    async def confirmation_on(self, user: int):
        await asyncio.sleep(self.bot.deltime * 2)
        self.confirmed_ids[user] = 0
        return

    # Events
    @commands.Cog.listener()
    async def on_ready(self):
        # self.literate = self.bot.server.get_role(bot.literate_role_id)  # Certified Literate role
        self.confirmed_ids = self.bot.confirmed_ids
        logready(self)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        # ===================================== The automatic staff-hirer ========================================
        if payload.channel_id != 718896231706787940:  # Only consider messages in #staff-candidates
            return
        user = self.bot.server.get_member(payload.user_id)
        u_roles = [role.name for role in user.roles]
        if ('Administrator/Bot Developer' not in u_roles and 'GM Instructor' not in u_roles) or str(payload.emoji) != \
                '✅':
            return
            # Only interested if the reaction is a green checkmark and user has staff management authority
        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        try:
            for field in message.embeds[0].fields:
                if field.name == 'Username':
                    username = field.value
                    if username[0] == '@':
                        username = username[1:]
                elif field.name == 'Position':
                    rolename = field.value
        except IndexError:
            # Message doesn't have embeds.
            return await message.channel.send("Failure attempting to add role: Application improperly formatted.")
        if username is None or rolename is None:
            return await message.channel.send("The username or position fields weren't found in the embed;"
                                              "add the role manually.")
        elif rolename != 'Game Master' and 'Administrator/Bot Developer' not in u_roles:
            # Only admin/dev can promote staff, but GM Instructors can promote Game Masters
            return await message.channel.send("GM Instructors can only promote Game Masters.")
        for member in self.bot.server.members:  # Transform username string into a member to add roles to
            if str(member) == username:
                to_hire = member
                break
        else:  # If got to the end of the loop with no user found, they aren't on server
            return await message.channel.send("Couldn't find member in server. They probably misspelled"
                                              " their discriminator; add the role manually.")
        for role in self.bot.server.roles:
            if role.name == rolename:
                to_position = role
                break
        else:  # If got to the end of the loop with no role found, role names were probably changed recently
            return await message.channel.send("Couldn't find role on server. Check that role names are still"
                                              " up to date on the form and add the role manually.")
        if role in to_hire.roles:
            return await message.channel.send(f"{to_hire} is already a {to_position}.")
        await message.channel.send(f"Hired {to_hire.mention} as a new {to_position}. Congratulations!")
        await to_hire.add_roles(to_position)
        if to_position.name != 'Game Master':  # Also add staff role
            for role in self.bot.server.roles:
                if role.name == "Staff":
                    await member.add_roles(role)
                    staff_lounge = self.bot.server.get_channel(718896175452913755)
                    await staff_lounge.send(f"Hello {to_hire.mention}. This is where the real work gets done ;)")
                    break
        announcements = self.bot.server.get_channel(718897329981096069)
        await announcements.send(
            f"**Please congratulate {self.bot.server.name}'s newest {rolename}, {to_hire.mention}!**")

    @commands.Cog.listener()
    async def on_message(self, message):
        # ==============================Add checkmark for staff apps======================================
        if message.channel.id == 718896231706787940 \
                and message.author.bot \
                and message.author.id != message.guild.me.id:  # Messages in #staff-candidates by webhooks
            try:
                for field in message.embeds[0].fields:
                    if field.name == 'Position':
                        await message.add_reaction('✅')
            except IndexError:
                # message has no embeds
                pass
        return

    # Commands
    @commands.command(aliases=['clear', 'del'], description='Delete a number of messages')
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        """Delete a bunch of messages
                Requires: Manage Message perms on your server
                Amount: The number of messages to purge. Typically limited to 100.
                People with Auth level 4 can delete more messages at once."""
        log(f'{ctx.author} attempted to delete {amount} messages in {ctx.channel} in guild {ctx.guild}.', self.bot.cmd)
        if int(amount) <= self.bot.MAX_PURGE:
            await ctx.channel.purge(limit=int(amount) + 1)
            log(f'{ctx.author} successfully deleted {amount} messages in channel {ctx.channel} in guild {ctx.guild}.')
        elif await auth(4)(ctx):
            await ctx.channel.purge(limit=int(amount) + 1)
            log(f'{ctx.author} successfully deleted {amount} messages in channel {ctx.channel} in guild {ctx.guild}.')
        else:
            await ctx.send(f'You may only delete up to {self.bot.MAX_PURGE} messages.', delete_after=self.bot.deltime)

    @commands.command(description='Delete a number of messages')
    @commands.check(auth(6))
    async def forcepurge(self, ctx, amount: int):
        f"""Delete a bunch of messages
                Requires: Auth 6. This is meant for use only in cases where the bot has caused spam that it shouldn't
                have.
                Amount: The number of messages to purge. Typically limited to {self.bot.MAX_PURGE}.
                People with Auth level 4 can delete more messages at once."""
        log(f'{ctx.author} attempted to delete {amount} messages in {ctx.channel} in guild {ctx.guild}.', self.bot.cmd)
        if int(amount) <= self.bot.MAX_PURGE * 10:
            await ctx.channel.purge(limit=int(amount) + 1)
            log(f'{ctx.author} successfully deleted {amount} messages in channel {ctx.channel} in guild {ctx.guild}.')
        elif await auth(7)(ctx):
            await ctx.channel.purge(limit=int(amount) + 1)
            log(f'{ctx.author} successfully deleted {amount} messages in channel {ctx.channel} in guild {ctx.guild}.')
        else:
            await ctx.send(f'You may only delete up to {self.bot.MAX_PURGE * 10} messages.',
                           delete_after=self.bot.deltime)

    @commands.command(description='Kick a member from the server.')
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = 'No reason provided.'):
        """Kick someone out of the server
                Requires: Kick Members permission
                Member: the person to kick
                Reason: the reason why, defaults to 'No reason provided.'"""
        reason = f'{ctx.author} kicked {member} for reason {reason}.'
        await member.kick(reason=reason)
        log(f'{ctx.author} kicked {member} from {ctx.guild} for {reason}.')

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
        log(f'{ctx.author} banned {member} from {ctx.guild} for {reason}.', self.bot.prio)

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
        log(f'{ctx.author} unbanned {member} from {ctx.guild}.', self.bot.cmd)

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
                           "If so, use this command again.", delete_after=self.bot.deltime)
            self.bot.confirmed_ids[ctx.author.id] = 1
            await ctx.message.delete()  # delete the command
            self.bot.loop.create_task(self.confirmation_on(ctx.author.id))
        log(f'Clearpins command used by {ctx.author} in channel {ctx.channel.name}.', self.bot.cmd)

    @commands.command(description='Bestow upon someone the Certified Literate role!')
    async def certify(self, ctx, *, member: discord.Member):
        if self.literate not in ctx.author.roles:  # Don't allow people without the role to grant it
            return await ctx.send(f'{ctx.author}, you need to be Certified Literate to use that command.')
        if self.literate in member.roles:  # Don't allow getting the role twice
            return await ctx.send(f'That user has already been granted the Certified Literate role.')
        await ctx.send(f'{member.mention}\n```\nI hereby declare you an outstanding writer. May you be granted'
                       f' fortune in your future endeavours.```')
        await add_funds(member, self.bot.GRANT_AMOUNT)
        await send_to_log_channel(self.bot.log_channel, ctx,
                                  f'{ctx.author.mention} bestowed the Certified Literate role upon {member.mention}.'
                                  f' ${self.bot.GRANT_AMOUNT} granted.',
                                  event_name='**Certified Literate**')
        await member.add_roles(self.literate)
        log(f'{ctx.author} granted {member} the Certified Literate role.', self.bot.cmd)


def setup(bot):
    bot.add_cog(Moderation(bot))
