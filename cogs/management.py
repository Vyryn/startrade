import json
import typing

import discord
from discord.ext import commands
from functions import auth, now
from bot import log, logready


class Management(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # Events
    @commands.Cog.listener()
    async def on_ready(self):
        logready(self)

    # Custom prefix upon joining guild
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        with open('prefixes.json', 'r') as f:
            prefixes = json.load(f)

        prefixes[str(guild.id)] = self.bot.global_prefix

        with open('prefixes.json', 'w') as f:
            json.dump(prefixes, f, indent=4)
        log(f'Bot added to server {guild}.')

    # remove custom prefix from bot record
    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        with open('prefixes.json', 'r') as f:
            prefixes = json.load(f)

        prefixes.pop(str(guild.id))

        with open('prefixes.json', 'w') as f:
            json.dump(prefixes, f, indent=4)
        log(f'Bot removed from server {guild}.')

    # change server prefix
    @commands.group(name='prefix', description='Check or change the server prefix')
    @commands.guild_only()
    async def prefix(self, ctx):
        """Check or change the server prefix
                With no parameters, tells you what the prefix is.
                Considering you need to know what the prefix is to run the command, it's very helpful, I know.
                However, prefix set <prefix> is used to change the server prefix."""
        with open('prefixes.json', 'r') as f:
            prefixes = json.load(f)
        await ctx.send(f'Prefix is {prefixes[str(ctx.guild.id)]}')
        log(f'Prefix checked by {ctx.author} in server {ctx.guild}.', self.bot.cmd)

    @prefix.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def set(self, ctx, prefix=None):
        if prefix is None:
            prefix = self.bot.global_prefix
        with open('prefixes.json', 'r') as f:
            prefixes = json.load(f)
        log(f'Changing {ctx.guild} prefix to {prefix}')
        prefixes[str(ctx.guild.id)] = prefix
        with open('prefixes.json', 'w') as f:
            json.dump(prefixes, f, indent=4)
        await ctx.send(f'Changed server prefix to {prefixes[str(ctx.guild.id)]}')
        log(f'Prefix set command used by {ctx.author} in server {ctx.guild}, set to {prefix}.', self.bot.cmd)

    @commands.check(auth(3))
    @commands.guild_only()
    @commands.command(description='Edit a bot message')
    async def edit(self, ctx, m_id, channel: typing.Optional[discord.TextChannel] = None, *, new):
        channel = channel or ctx.channel
        message = await channel.fetch_message(m_id)
        await message.edit(content=new)
        await ctx.message.add_reaction('✅')


async def setup(bot):
    await bot.add_cog(Management(bot))
