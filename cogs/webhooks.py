import aiohttp
from discord import Webhook, AsyncWebhookAdapter, Embed, TextChannel
from discord.ext import commands
from functions import now, auth

HOOK_URL = 'https://discordapp.com/api/webhooks/723354196988133376/ioftOOV89uBH_A_cJhwBGOaFXBHisCzgZI_fHVVyGJYKtuQ5AvlNVKqk75pIjjB2t0yn'

images = {
    'Man': 'https://i.pinimg.com/originals/94/6e/82/946e829a135f68d7a041e3a83b445f55.jpg',
    'Woman': 'https://miro.medium.com/max/11030/1*GXLLjBU4IIZswmZrG4w3OA.jpeg',
    'Testman': 'https://bbts1.azureedge.net/images/p/full/2019/07/71fdc93f-13b6-4de8-b032-ee7c34843ef2.jpg',
    'Old Man': 'https://i.pinimg.com/originals/5c/66/c6/5c66c624f16feab720c601f832b2235e.jpg',
    'Old Woman': 'https://media.graytvinc.com/images/690*394/survives+two+pandemics.JPG'
}


class Webhooks(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(description='use a webhook')
    async def sayw(self, ctx, name: str = None, *, content):
        await ctx.message.delete()
        if name is None:
            name = 'Startrade'
        else:
            name = name.replace('_', ' ').title()
        avatar = images.get(name, None)
        try:
            hook = (await ctx.channel.webhooks())[0]
        except IndexError:
            hook = await TextChannel.create_webhook(ctx.channel, name='Startrade',
                                                    reason=f'Startrade NPC creation for #{ctx.channel.name}.')
        async with aiohttp.ClientSession() as session:
            # webhook = Webhook.from_url(HOOK_URL, adapter=AsyncWebhookAdapter(session))
            embed = Embed(description=content)
            await hook.send(content=None, username=name, embed=embed, avatar_url=avatar)


def setup(bot):
    bot.add_cog(Webhooks(bot))
