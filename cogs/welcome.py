import discord
from discord.ext import commands
from bot import logready

welcome_msg = 'Hello. This is a test.'


class Welcome(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # Events
    @commands.Cog.listener()
    async def on_ready(self):
        logready(self)

    # Welcome
    @commands.Cog.listener()
    async def on_member_join(self, member):
        embed = discord.Embed(title=f'{member.name}, welcome to {self.bot.server}', description=welcome_msg)

        try:
            await member.send(embed=embed)
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass


def setup(bot):
    bot.add_cog(Welcome(bot))
