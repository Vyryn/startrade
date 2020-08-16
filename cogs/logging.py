import datetime
import os
from discord.ext import commands
from bot import log, logready
from functions import now, today


def writeline(path: str, line: str):
    with open(path, 'a+', encoding='utf-8') as f:
        try:
            f.write(line + '\n')
        except UnicodeEncodeError:
            f.write(f'[WRN] {now()}: A UnicodeEncodeError occurred trying to write a message log.\n')


def do_log_msg(message):
    # Build a log of this message
    log_msg = f'{message.author}'
    if message.author.bot:
        log_msg += f' [B]'
    log_content = message.system_content.replace('\n', '\\n')
    log_msg += f' >  {log_content}  |  {now()}'
    if len(message.embeds) > 0:
        eb = message.embeds[0]
        fields = '  &  '.join(f"'{field.name}': {field.value}" for field in eb.fields)
        log_msg += f'  |  Embed "{eb.author.name}  {eb.description}": {fields}'
    if len(message.attachments) > 0:
        log_msg += f'  |  Attachment: {message.attachments[0].url}'
    try:
        log(f'{log_msg}  |  {message.channel.name}  |  {message.guild.name}', 'MESG')
        send_log(log_msg, message.guild.name, message.channel.name)
    except AttributeError:
        log(f'{log_msg}  |  DMs  |  {message.channel.recipient}', 'MESG')
        send_log(log_msg, "DMs", message.channel.recipient)


# Log a message.
def send_log(message: str, guild: str, channel: str):
    try:
        writeline(f'./logs/{guild}/{channel}_{today()}_log.log', message)
    except OSError:
        try:
            os.makedirs(f'./logs/{guild}')
            log(f"Created a new guild log folder for {guild}.")
            writeline(f'./logs/{guild}/{today()}_log.log', message)
        except OSError:
            os.makedirs(f'./logs')
            os.makedirs(f'./logs/{guild}')
            log(f"Created a new guild log folder for {guild}.")
            writeline(f'./logs/{guild}/{today()}_log.log', message)

    return


class Logging(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # Events
    # When bot is ready, print to console
    @commands.Cog.listener()
    async def on_ready(self):
        logready(self)

    # =============================Message handler=========================
    @commands.Cog.listener()
    async def on_message(self, message):
        # Don't do stuff for messages in ignored guilds
        if message.guild is not None and message.guild.id in self.bot.ignored_guilds:
            return
        # ===========================LOG=============================
        do_log_msg(message)


def setup(bot):
    bot.add_cog(Logging(bot))
