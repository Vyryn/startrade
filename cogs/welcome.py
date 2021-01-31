import discord
from discord.ext import commands
from bot import logready

welcome_msg = "Welcome to the Galactic Faction War. In addition to the ping you've received in " \
              "<#801688443641790554>, we'd like to inform you that the server can be rough. If " \
              "you feel harassed by another member, tell them to stop. If they continue, contact" \
              " a member of staff via pinging or a DM."


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
