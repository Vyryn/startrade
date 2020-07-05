import time

import discord
import json
import ast
from discord.ext import commands
from functions import auth, set_commanders, get_commanders, now, DEFAULT_AUTH

# Bot commanders levels
PERMS_INFO = {0: '(No other dev perms)', 1: 'Can use echo and auth check', 2: 'Can make bot send DMs',
              3: 'Can reload cogs', 4: 'Can load and unload cogs', 5: 'Can update bot status',
              6: 'Can see the list of all bot commanders', 7: 'Can set other people\'s auth levels',
              8: 'Trusted for dangerous dev commands', 9: 'Can use eval', 10: 'Created me'}


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
        print(f'Cog {self.qualified_name} is ready.')

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
        print(f'Echo command used by {ctx.author} at {now()} with message {message}')

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
        print(f'Send command used by {ctx.author} at {now()} to user {user} with message {message}')

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
        print(f'Auth command used by {ctx.author} at {now()}')
        pass

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
            for perm in sorted(PERMS_INFO.keys(), reverse=True):
                if perm <= auth_level:
                    perms += str(perm) + ': ' + PERMS_INFO.get(perm) + '\n'
            embed.add_field(name='The Details:', value=perms)
        embed.set_footer(text=embed_footer(ctx.author))
        await ctx.send(content=None, embed=embed, delete_after=self.deltime * 5)
        await ctx.message.delete(delay=self.deltime)  # delete the command
        print(f'Auth check command used by {ctx.author} at {now()}, {user} is authorized at level {auth_level}.')

    # sets a user's auth level
    @commands.command()
    @commands.check(auth(7))
    async def authset(self, ctx, level: int, user: discord.User):
        commanders = get_commanders()
        if commanders[str(ctx.author.id)] > level and commanders.get(user.id, 0) < commanders[str(ctx.author.id)]:
            with open('auths.json', 'r') as f:
                auths = json.load(f)
            print(f'Changing {user} auth level to {level}')
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
        print(f'Authset command used by {ctx.author} at {now()} to set {user}\'s auth level to {level}')

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
        print(f'Auth All command used by {ctx.author} at {now()}')

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
        print(f'Unloaded {extension}')
        await ctx.send(f'Unloaded {extension}.', delete_after=self.deltime)
        await ctx.message.delete(delay=self.deltime)  # delete the command
        print(f'Unload command used by {ctx.author} at {now()} on cog {extension}')

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
        print(f'Reloaded {extension}')
        await ctx.send(f'Reloaded {extension}', delete_after=self.deltime)
        await ctx.message.delete(delay=self.deltime)  # delete the command
        print(f'Reload command used by {ctx.author} at {now()} on cog {extension}')

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
        print(f'Updated status to {message}.')
        await ctx.send(f'Updated status to {message}.', delete_after=self.deltime)
        await ctx.message.delete(delay=self.deltime)  # delete the command
        print(f'Status command used by {ctx.author} at {now()} to set bot status to {message}')

    @commands.command(name='eval', description='Evaluates input.')
    @commands.check(auth(9))
    async def eval_fn(self, ctx, *, cmd: str):
        """
        Evaluates input.
        This command requires Auth 9 for obvious reasons.
        """
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
        await ctx.send(f'Command took {int((endtime - starttime) / 10000) / 100}ms to run.\nResult: {result}')

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
        print(f'Deleted message {message_id} in channel {ctx.channel} for user {ctx.author} at {now()}')


def setup(bot):
    bot.add_cog(Dev(bot))
