from discord import Embed, TextChannel
from discord.ext import commands
from functions import auth
from bot import log, logready

IMAGES = {
    "Man": "https://i.pinimg.com/originals/94/6e/82/946e829a135f68d7a041e3a83b445f55.jpg",
    "Woman": "https://miro.medium.com/max/11030/1*GXLLjBU4IIZswmZrG4w3OA.jpeg",
    "Testman": "https://bbts1.azureedge.net/images/p/full/2019/07/71fdc93f-13b6-4de8-b032-ee7c34843ef2.jpg",
    "Old Man": "https://i.pinimg.com/originals/5c/66/c6/5c66c624f16feab720c601f832b2235e.jpg",
    "Old Woman": "https://media.graytvinc.com/images/690*394/survives+two+pandemics.JPG",
    "Boss": "https://liquipedia.net/commons/images/d/de/BOSS_Esports_logo.png",
    "Shopkeeper": "https://thumbs.dreamstime.com/b/asian-shopkeeper-photograph-indian-36072672.jpg",
    "Shopkeeper 2": "https://criticallyrated.files.wordpress.com/2016/03/26n21shopkeeper-472494.jpg?w=584",
    "Shopkeeper 3": "https://starofmysore.com/wp-content/uploads/2018/07/news-10-5.jpg",
    "Shopkeeper 4": "https://www.familyfuncanada.com/vancouver/files/2013/09/156_preview.jpeg-e1510089878605.jpg",
    "Shady Businessman": "https://i0.wp.com/cdn-prod.medicalnewstoday.com/content/images/articles/323/323360/shady"
    "-businessman.jpg?w=1155&h=1541",
    "Businessman": "https://upload.wikimedia.org/wikipedia/commons/0/0d/Dr._Ken_Chu%2C_Chairman_%26_CEO"
    "%2C_Mission_Hills_Group.jpg",
    "Businesswoman": "https://www.botswanayouth.com/wp-content/uploads/2016/04/career-woman.jpg",
    "Ceo": "https://personalexcellence.co/files/ceo.jpg",
    "Ai": "https://www.aithority.com/wp-content/uploads/2019/06/Terminator-Teaches-Us-About-AI-and-the-Need-for"
    "-Better-Data-guest-post.jpg ",
    "Ai Joe": "https://i.pinimg.com/originals/30/f4/93/30f4932ab53d3225987ba33c5e09a21f.png",
    "Bob": "https://www.biography.com/.image/t_share/MTIwNjA4NjMzOTU5NTgxMTk2/bob-ross-9464216-1-402.jpg",
    "Flemming": "https://assets.blabbermouth.net/media/flemmingrasmussen2014solorockhall_638.jpg",
    "Teressa": "https://i0.wp.com/www.usmagazine.com/wp-content/uploads/2019/08/Teressa-Foglia-Hats-Promo.jpg?crop"
    "=241px%2C72px%2C1762px%2C996px&resize=1600%2C900&ssl=1",
    "Amanda": "https://a.espncdn.com/combiner/i?img=/i/headshots/mma/players/full/2516131.png&w=350&h=254",
    "Assassin": "https://cdn.arstechnica.net/wp-content/uploads/2016/12/assassin-s-creed-ACFirstLook_rgb-1.jpg",
    "Worker 1": "https://www.ishn.com/ext/resources/900x550/older-worker-mature-senior-900.jpg?1554230646",
    "Worker 2": "https://www.fairobserver.com/wp-content/uploads/2017/08/Factory-workers-America-news-manufacturing"
    "-jobs-world-news-1.jpg",
    "Worker 3": "https://www.liberaldictionary.com/wp-content/uploads/2018/11/worker.jpg",
    "Factory Worker": "https://www.aljazeera.com/mritems/imagecache/mbdxxlarge/mritems/Images/2019/12/26"
    "/09231dd8b5c242c496e3fe0c64a3ecd0_18.jpg",
    "Lawyer": "https://www.glassdoor.com/blog/app/uploads/sites/2/GettyImages-713774487-1-1024x450.jpg",
    "Professional Team": "https://www.naceweb.org/uploadedImages/images/2018/feature/using-the-principles"
    "-professional-standards-and-competencies.jpg ",
}


class Webhooks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        logready(self)

    @commands.command(
        description=f"""Make an immersive NPC say something. If a profile picture exists for the name 
        provided, it will be used 
        otherwise the discord default will be used instead.
        Multi-space names can be provided either in quotes or with underscores as spaces.
        Names are case insensitive but must be an exact match otherwise to use the existing profile pictures.
        Known names are:
        {IMAGES.keys()}"""
    )
    @commands.check(auth(1))
    async def sayw(self, ctx, name: str = None, *, content):
        f"""Make an imersive NPC say something. If a profile picture exists for the name provided, it will be used
        otherwise the discord default will be used instead.
        Multi-space names can be provided either in quotes or with underscores as spaces.
        Names are case insensitive but must be an exact match otherwise to use the existing profile pictures.
        {IMAGES.keys()}"""
        await ctx.message.delete()
        if name is None:
            name = self.bot.name
        else:
            name = name.replace("_", " ").title()
        avatar = IMAGES.get(name, None)
        try:
            hook = (await ctx.channel.webhooks())[0]
        except IndexError:
            hook = await TextChannel.create_webhook(
                ctx.channel,
                name=self.bot.name,
                reason=f"{self.bot.name} NPC creation for #{ctx.channel.name}.",
            )
        embed = Embed(description=content)
        await hook.send(content="", username=name, embed=embed, avatar_url=avatar)
        log(
            f"{ctx.author} used a webhook named {name} to send {content} in channel {ctx.channel}."
        )


async def setup(bot):
    await bot.add_cog(Webhooks(bot))
