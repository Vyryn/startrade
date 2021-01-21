import asyncio
import copy
import time
import typing

import discord
import json
import ast
from discord.ext import commands
from functions import auth, set_commanders, get_commanders, now, DEFAULT_AUTH
from bot import log, logready


# For saying the footnote was requested by someone
def embed_footer(author):
    return f'Requested by {str(author)} at {now()}.'


def insert_returns(body):
    # Return the last value set in the command
    if isinstance(body[-1], ast.Expr):
        body[-1] = ast.Return(body[-1].value)
        ast.fix_missing_locations(body[-1])
    # Insert if statements into body
    if isinstance(body[-1], ast.If):
        insert_returns(body[-1].body)
        insert_returns(body[-1].orelse)
    # Insert with blocks into body
    if isinstance(body[-1], ast.With):
        insert_returns(body[-1].body)


class Dev(commands.Cog):

    def __init__(self, bot):
        set_commanders()
        self.bot = bot
        self.deltime = None

    # Events
    @commands.Cog.listener()
    async def on_ready(self):
        self.deltime = self.bot.deltime
        logready(self)

    # Commands
    # Echo what you said
    @commands.command(aliases=['repeat', 'say'], pass_context=True, description='Have the bot say your message.')
    @commands.check(auth(1))
    async def echo(self, ctx, *, message: str):
        """
        Have the bot repeat your message.
        Requires: Auth level 1
        """
        await ctx.message.delete()  # delete the command
        await ctx.send(message)
        log(f'Echo command used by {ctx.author} with message {message}.', self.bot.cmd)

    # Have the bot send a dm to someone with your message
    @commands.command(name='sendmsg', aliases=['dm', 'tell', 'message'], pass_context=True,
                      description='DM someone from the bot.')
    @commands.check(auth(2))
    async def send(self, ctx, user: discord.User, *, message: str = None):
        """
        Sends a DM to a user of your choice
        Requires: Auth level 2
        User: The user to message
        Message: The message to send
        """
        message = message or 'Someone is pranking you bro.'
        await ctx.message.delete()  # delete the command
        await ctx.send('Message sent.', delete_after=self.deltime)
        await user.send(message)
        log(f'Send command used by {ctx.author} to user {user} with message {message}.', self.bot.cmd)

    # Check someone's  auth level
    @commands.group(name='auth', aliases=['who', 'check', 'authorize'], description='Check the Auth Level of a user')
    @commands.check(auth(1))
    async def autho(self, ctx):
        """
        Auth check returns the auth level of a given user
        Requires: Auth level 1
        Member: The discord member to check the auth level of
        You can use auth set <user> <level> if you have auth level 7
        """
        # await ctx.send('Use auth check, auth set or auth all')
        log(f'Auth command used by {ctx.author}.', self.bot.cmd)

    # Checks a user's auth level
    @autho.command()
    async def check(self, ctx, user: discord.User = None, detail: str = ''):
        if not user:
            user = ctx.author
        auth_level = get_commanders().get(str(user.id), DEFAULT_AUTH)
        embed = discord.Embed(title='', description='', color=user.color)
        embed.set_author(icon_url=user.avatar_url, name=f'{user} is '
                                                        f'authorized at level {auth_level}')
        if detail != '':
            perms = ''
            for perm in sorted(self.bot.PERMS_INFO.keys(), reverse=True):
                if perm <= auth_level:
                    perms += str(perm) + ': ' + self.bot.PERMS_INFO.get(perm) + '\n'
            embed.add_field(name='The Details:', value=perms)
        embed.set_footer(text=embed_footer(ctx.author))
        await ctx.send(content=None, embed=embed, delete_after=self.deltime * 5)
        await ctx.message.delete(delay=self.deltime)  # delete the command
        log(f'Auth check command used by {ctx.author}, {user} is authorized at level {auth_level}.',
            self.bot.cmd)

    # sets a user's auth level
    @commands.command()
    @commands.check(auth(7))
    async def authset(self, ctx, level: int, user: discord.User):
        commanders = get_commanders()
        if commanders[str(ctx.author.id)] > level and commanders.get(user.id, 0) < commanders[str(ctx.author.id)]:
            with open('auths.json', 'r') as f:
                auths = json.load(f)
            log(f'Changing {user} auth level to {level}', self.bot.prio)
            auths[str(user.id)] = level
            with open('auths.json', 'w') as f:
                json.dump(auths, f, indent=4)
            set_commanders()  # update variable in memory after having written to disc new perms
            await ctx.send(f'Changed {user} auth level to {auths[str(user.id)]}', delete_after=self.deltime)
        elif commanders[str(ctx.author.id)] <= level:
            await ctx.send(f"I'm sorry, but you can't set someone's auth level higher than your own.")
        else:
            await ctx.send(f"I'm sorry, but you can't change the auth level of someone with an auth level equal to or "
                           f"higher than you.")
        log(f'Authset command used by {ctx.author} to set {user}\'s auth level to {level}.', self.bot.cmd)

    # lists all bot commanders and their auth levels
    @autho.command(name='all')
    @commands.check(auth(4))
    async def all_commanders(self, ctx):
        commanders = get_commanders()
        embed = discord.Embed(title='', description='', color=ctx.author.color)
        embed.set_author(icon_url=ctx.author.avatar_url, name='Here you go:')
        message = ''
        for c in commanders:
            message += (str(await self.bot.fetch_user(c)) + ': ' + str(commanders[c]) + '\n')
        embed.add_field(name='Bot Commanders:', value=message)
        embed.set_footer(text=embed_footer(ctx.author))
        await ctx.send(content=None, embed=embed)
        log(f'Auth All command used by {ctx.author}.', self.bot.cmd)

    # Unload a cog
    @commands.command(description='Unload a cog')
    @commands.check(auth(4))
    async def unload(self, ctx, extension: str):
        """
        Unload a cog
        Requires: Auth level 4
        Extension: The cog to unload
        """
        self.bot.unload_extension(f'cogs.{extension}')
        log(f'Unloaded {extension}')
        await ctx.send(f'Unloaded {extension}.', delete_after=self.deltime)
        await ctx.message.delete(delay=self.deltime)  # delete the command
        log(f'Unload command used by {ctx.author} on cog {extension}.', self.bot.cmd)

    # Reload a cog
    @commands.command(description='Reload a cog')
    @commands.check(auth(3))
    async def reload(self, ctx, extension: str):
        """
        Reload a cog
        Requires: Auth level 4
        Extension: The cog to reload
        """
        try:
            self.bot.unload_extension(f'cogs.{extension}')
        except discord.ext.commands.errors.ExtensionNotLoaded:
            await ctx.send(f"Cog {extension} wasn't loaded, loading it now.")
        self.bot.load_extension(f'cogs.{extension}')
        log(f'Reloaded {extension}')
        await ctx.send(f'Reloaded {extension}', delete_after=self.deltime)
        await ctx.message.delete(delay=self.deltime)  # delete the command
        log(f'Reload command used by {ctx.author} on cog {extension}.', self.bot.cmd)

    # Update bot status
    @commands.command(description='Change what the bot is playing')
    @commands.check(auth(5))
    async def status(self, ctx, *, message: str = ''):
        """
        Change the bot's "playing" status
        Requires: Auth level 5
        Message: The message to change it to
        """
        await self.bot.change_presence(activity=discord.Game(message))
        log(f'Updated status to {message}.')
        await ctx.send(f'Updated status to {message}.', delete_after=self.deltime)
        await ctx.message.delete(delay=self.deltime)  # delete the command
        log(f'Status command used by {ctx.author} to set bot status to {message}.', self.bot.cmd)

    @commands.command(name='eval', description='Evaluates input.')
    @commands.check(auth(9))
    async def eval_fn(self, ctx, *, cmd: str):
        """
        Evaluates input.
        This command requires Auth 9 for obvious reasons.
        """
        log(f'Evaluating {cmd} for {ctx.author}.', self.bot.cmd)
        starttime = time.time_ns()
        fn_name = "_eval_expr"
        cmd = cmd.strip("` ")
        if cmd[0:2] == 'py':  # Cut out py for ```py``` built in code blocks
            cmd = cmd[2:]
        # add a layer of indentation
        cmd = "\n".join(f"    {i}" for i in cmd.splitlines())
        # wrap in async def body
        body = f"async def {fn_name}():\n{cmd}"
        parsed = ast.parse(body)
        body = parsed.body[0].body
        insert_returns(body)
        env = {
            'bot': ctx.bot,
            'discord': discord,
            'commands': commands,
            'ctx': ctx,
            'guild': ctx.guild,
            'channel': ctx.channel,
            'me': ctx.author,
            'self': self,
            '__import__': __import__
        }
        exec(compile(parsed, filename="<ast>", mode="exec"), env)
        result = (await eval(f"{fn_name}()", env))
        endtime = time.time_ns()
        await ctx.send(f'Command took {int((endtime - starttime) / 10000) / 100}ms to run.')
        if result is not None:
            await ctx.send(f'Result: {result}')
        log(f'Evaluation of {cmd} for {ctx.author} gave the following result: {result}.', self.bot.cmd)

    @commands.command(description='Delete a single message by ID')
    @commands.check(auth(6))
    async def delete(self, ctx, message_id: int):
        """
        Deletes a single message.
        Requires: Auth 6.
        Used for cleaning up bot mistakes.
        """
        await (await ctx.channel.fetch_message(message_id)).delete()
        await ctx.message.delete(delay=self.deltime)  # delete the command
        log(f'Deleted message {message_id} in channel {ctx.channel} for user {ctx.author}.', self.bot.cmd)

    @commands.command()
    @commands.check(auth(3))
    async def tofile(self, ctx, *, text=None):
        """
        Puts your text into a file that it uploads.
        :param ctx:
        :param text:
        :return:
        """
        with open('temp_file.txt', 'w+', encoding='utf-8') as f:
            f.write(text)
        await ctx.send("Here's your file.", file=discord.File('temp_file.txt'))

    @commands.command(description='Invoke a command as another user', hidden=True)
    @commands.check(auth(8))
    async def sudo(self, ctx, channel: typing.Optional[discord.TextChannel], user: discord.User, *, command: str):
        """Invoke a command as another user, in another channel."""
        message = copy.copy(ctx.message)
        channel = channel or ctx.channel
        message.channel = channel
        message.author = channel.guild.get_member(user.id) or user
        message.content = ctx.prefix + command
        ctx = await self.bot.get_context(message, cls=type(ctx))
        await self.bot.invoke(ctx)

    @commands.command()
    @commands.check(auth(5))
    async def shoo(self, ctx, user: discord.User, name: str = 'Vyryn'):
        await ctx.message.delete()
        await user.send(f"{name} is busy and his temper is short right now. He is already aware of whatever you just "
                        f"bothered him about, likely because 20+ people have already informed him of it in the same "
                        f"somewhat annoying way you did. He's either been troubleshooting it since he was made aware,"
                        f" or he can't fix it. In fact, whatever brought this issue to your attention probably "
                        f"told you to contact someone else entirely if you were paying attention. Oh, and it's most "
                        f"likely 4am for him.\n\n\n\nSo, in summary, this is {name} telling you politely and kindly to"
                        f" please leave him alone. I'm the messenger here because if he'd told you this personally, "
                        f"it would be nowhere near as polite or patient. Please don't ping him, and if you're feeling"
                        f" nice maybe send him a thank you or tell him to stop and go to sleep.")

    @commands.command()
    @commands.check(auth(5))
    async def shooo(self, ctx, user: discord.User):
        await ctx.message.delete()
        await ctx.send(f"{user.mention}, leave him alone! He already told you what the matter is, and asked you to "
                       f"leave him alone, and you didn't listen.", delete_after=20)
        for i in range(3):
            await asyncio.sleep(2)
            await user.send(f"Vyryn told you to leave him alone.")
            await asyncio.sleep(4)
            await user.send(f'It is a very good idea for you to do so.')
            await asyncio.sleep(10)
            await user.send('Seriously.')
            await asyncio.sleep(20)
            await ctx.send(f"{user.mention} ***Seriously, lay off.***", delete_after=20)

    @commands.command()
    @commands.check(auth(8))
    async def get_dms(self, ctx, target: discord.User):
        await ctx.send(f'Looking up messages {target.name} has sent me.')
        async for message in target.history(limit=None):
            if message.author.id == target.id:
                await ctx.send(message.content)


def setup(bot):
    bot.add_cog(Dev(bot))
