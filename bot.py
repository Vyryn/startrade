import json
import traceback
import aiohttp
import discord
import os
import random
import sys
import asyncio
from discord.ext import commands
from functions import get_prefix, global_prefix, get_ignored_channels, set_ignored_channels, confirmed_ids, auth, now
from privatevars import TOKEN

intents = discord.Intents.all()
intents.typing = False

bot = commands.Bot(command_prefix=get_prefix, case_insensitive=True, intents=intents)
# ========================== Easily Configurable Values ========================
# The id of the bot creator
owner_id = 125449182663278592
# Default number of seconds to wait before deleting many bot responses and player commands
deltime = 10
# The id of the primary guild the bot is operating in
bot.serverid = 407481043856261120  # 718893913976340561 for startrade
bot.settings_modifiers = [125449182663278592, 171810360473550849,
                          185496547436396545]  # allow settings to be modified by Vyryn, Xifi and Brom
bot.BUMP_PAYMENT = 0  # Payment for disboard bumps
bot.PAYCHECK_AMOUNT_MIN = 4_000_000  # Minimum paycheck payout
bot.PAYCHECK_AMOUNT_MAX = 4_000_000  # Maximum paycheck payout
bot.PAYCHECK_INTERVAL = 3600  # Time between paychecks, in seconds
bot.REFUND_PORTION = 0.9  # Portion of buy price to refund when selling an item
bot.WEALTH_FACTOR = 0.0005  # Currently set to 0.05-0.1% payout per hour
bot.STARTING_BALANCE = 50_000_000  # New user starting balance
bot.PAYOUT_FREQUENCY = 60 * 60  # How frequently to send out investments, in seconds
bot.GRANT_AMOUNT = 1000  # Certified Literate payout amount
bot.log_channel_id = 408254707388383232  # The channel set up for logging message edits and the like.
# bot.verified_role_id = 718949160170291203  # The verification role id
# bot.literate_role_id = 728796399692677160  # The certified literate role id
# bot.verification_message_id = 718980234380181534  # The startrade verification message id
bot.DISBOARD = 302050872383242240  # Disboard uid
bot.credit_emoji = '<:Credits:423873771204640768>'
# Constants to do with the goolge sheet pulls the bot makes.
bot.SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
bot.SHEET_ID = '1ZU6pTfdIGkQ9zzOH6lW0zkEQuF7-xFsyxgwSgGz4WcM'
bot.RANGE_SHIPS = 'AllShips!A1:T1500'
bot.RANGE_WEAPONS = 'Weapons!A1:J150'
# Don't log or do any other on_message action in the following guilds
bot.ignored_guilds = [336642139381301249]  # (this one is d.py)
bot.ACTIVITY_COOLDOWN = 7  # Minimum number of seconds after last activity to have a message count as activity
bot.MOVE_ACTIVITY_THRESHOLD = 100  # Number of activity score that must be gained when moving to a new location
bot.DEFUALT_DIE_SIDES = 20  # Default number of sides to assume a rolled die has
bot.MAX_DIE_SIDES = 100  # Max number of sides each die may have
bot.MAX_DIE_ROLES = 100000  # Max number of dice that can be rolled with one ,roll command
bot.ITEMS_PER_TOP_PAGE = 10  # Number of items to show per page in ,top
bot.AUTH_LOCKDOWN = 1  # The base level for commands from this cog; set to 0 to enable public use, 1 to disable it
bot.MAX_PURGE = 100  # Max number of messages that can be purged with ,forcepurge command at once

# ============================ Less Easily Configured Values =======================
# The bot randomly selects one of these statuses at startup
statuses = ["Being an adult is just walking around wondering what you're forgetting.",
            'A clean house is the sign of a broken computer.',
            "I have as much authority as the Pope, i just don't have as many people who believe it.",
            'A conclusion is the part where you got tired of thinking.',
            'To the mathematicians who thought of the idea of zero, thanks for nothing!',
            'My job is secure. No one else wants it.',
            "If at first you don't succeed, we have a lot in common.",
            'I think we should get rid of democracy. All in favor raise your hand.']
# Which discord perms are consider basic/important
basicperms = ['administrator', 'manage_guild', 'ban_members', 'manage_roles', 'manage_messages']
# Which discord perms are consider significant/notable
sigperms = ['deafen_members', 'kick_members', 'manage_channels', 'manage_emojis',
            'manage_nicknames', 'manage_webhooks', 'mention_everyone', 'move_members', 'mute_members',
            'priority_speaker', 'view_audit_log']
# The directory for cogs
cogs_dir = 'cogs'
bot.global_prefix = global_prefix
bot.deltime = deltime
bot.confirmed_ids = confirmed_ids
bot.content_max = 1970  # The maximum number of characters that can safely be fit into a logged message
bot.time_options = {'s': 1, 'm': 60, 'h': 60 * 60, 'd': 60 * 60 * 24, 'w': 60 * 60 * 24 * 7,
                    'y': 60 * 60 * 24 * 365}
bot.number_reactions = ["1\u20e3", "2\u20e3", "3\u20e3", "4\u20e3", "5\u20e3", "6\u20e3", "7\u20e3",
                        "8\u20e3", "9\u20e3"]
bot.reactions_to_nums = {"1⃣": 1, "2⃣": 2, "3⃣": 3, "4⃣": 4, "5⃣": 5, "6⃣": 6, "7⃣": 7, "8⃣": 8, "9⃣": 9}
# Bot commanders levels
bot.PERMS_INFO = {0: '(No other dev perms)', 1: 'Can use echo and auth check', 2: 'Can make bot send DMs',
                  3: 'Can reload cogs', 4: 'Can load and unload cogs', 5: 'Can update bot status',
                  6: 'Can see the list of all bot commanders', 7: 'Can set other people\'s auth levels',
                  8: 'Trusted for dangerous dev commands', 9: 'Can use eval', 10: 'Created me'}
# Array to contain ids of each database-registered user to check for inclusion without database query
bot.list_of_users = []
# Set debug display values
bot.debug = 'DBUG'
bot.info = 'INFO'
bot.warn = 'WARN'
bot.error = 'EROR'
bot.critical = 'CRIT'
bot.cmd = 'CMMD'
bot.tofix = 'TOFX'
bot.prio = 'PRIO'
bot.rankup = 'RKUP'
bot.msg = 'MESG'

bot.logging_status = [bot.debug, bot.msg]  # Any logging levels here will be *excluded* from being logged


def botget(arg: str):
    return bot.__dict__[arg]


def log(message: str, severity='INFO'):
    if severity in bot.logging_status:
        return
    print(f'[{severity}] {message}  |  {now()}')


def logready(item):
    try:
        log(f'{item.qualified_name} is ready.')
    except AttributeError:
        log(f'{item} is ready.')


# Events
@bot.event
async def on_ready():
    bot.server = bot.get_guild(bot.serverid)
    bot.log_channel = bot.get_channel(bot.log_channel_id)
    # Pick a random current status on startup
    await bot.change_presence(status=discord.Status.online, activity=discord.Game(random.choice(statuses)))
    await asyncio.sleep(2)

    log(f'{bot.server.name} bot is fully ready.', bot.prio)


# ================================= Error Handler =================================
@bot.event
async def on_command_error(ctx, error):
    print(type(error))
    error = getattr(error, 'original', error)
    print(type(error))
    if hasattr(ctx.command, 'on_error'):
        log('An error occurred, but was handled command-locally.', bot.error)
        return
    if isinstance(error, commands.NoPrivateMessage):
        await ctx.send(f'The {ctx.command} command can not be used in private messages.', delete_after=5)
        return log(f'Error, NoPrivateMessage in command {ctx.command}: {error.args}', bot.info)
    elif isinstance(error, commands.CommandNotFound):
        log(f'Error, {ctx.author} triggered CommandNotFound in command {ctx.command}: {error.args[0]}', bot.debug)
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Incomplete command.", delete_after=5)
        return log(f'Error, MissingRequiredArgument in command {ctx.command}: {error.args[0]}', bot.debug)
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send(f'{ctx.author}, {error}', delete_after=5)
        return log(f'{ctx.author} tried to use {ctx.command} without sufficient permissions.', bot.info)
    elif isinstance(error, commands.CheckFailure):
        await ctx.send(f'{ctx.author}, you are not authorized to perform this command.')
        return log(f'{ctx.author} tried to use {ctx.command} without sufficient auth level.', bot.info)
    elif isinstance(error, discord.ext.commands.errors.BadArgument):
        await ctx.send("Improper command. Check help [command] to help you formulate this command correctly.",
                       delete_after=deltime)
        return log(f'BadArgument error in {ctx.command} for {ctx.author}', bot.info)
    elif isinstance(error, json.JSONDecodeError):
        await ctx.send(f'{ctx.author}, that api appears to be down at the moment.')
        return log(f'{ctx.author} tried to use {ctx.command} but got a JSONDecodeError.', bot.error)
    elif isinstance(error, asyncio.TimeoutError):
        await ctx.send(f"{ctx.author}, you took too long. Please re-run the command to continue when you're ready.",
                       delete_after=5)
        return log(f'{ctx.author} tried to use {ctx.command} but got a TimeoutError.', bot.info)
    elif isinstance(error, discord.ext.commands.errors.CommandOnCooldown):
        await ctx.send(f"{ctx.author.name}, {error}.")
    elif isinstance(error, OSError):
        log(f'OSError in command {ctx.command}, restart recommended: {error.__traceback__}', bot.critical)
    elif isinstance(error, discord.ext.commands.errors.CommandInvokeError):
        log(f"CommandInvokeError contained a CommandInvokeError. This shouldn't be possible. "
            f"Submit a github issue with the following info:"
            f" Command: {ctx.command}, Author: {ctx.author}, Error: {error.__traceback__}")
    else:
        # get data from exception
        etype = type(error)
        trace = error.__traceback__
        # 'traceback' is the stdlib module, `import traceback`.
        lines = traceback.format_exception(etype, error, trace)
        # format_exception returns a list with line breaks embedded in the lines, so let's just stitch the elements
        # together
        traceback_text = '```py\n'
        traceback_text += ''.join(lines)
        traceback_text += '\n```'
        try:
            await ctx.send(
                f"Hmm, something went wrong with {ctx.command}. "
                f"I have let the developer know, and they will take a look.")
            await bot.get_user(owner_id).send(
                f'Hey Vyryn, there was an error in the command {ctx.command}: {error}.\n '
                f'It was used by {ctx.author} in {ctx.guild}, {ctx.channel}.')
            await bot.get_user(owner_id).send(traceback_text)
        except:
            log(f"Something terrible occured and I was unable to send the error log for debugging.", bot.critical)
        log(f'Error triggered: {error} in command {ctx.command}, {lines}',
            bot.critical)
        return


# Global checks
# Checks that a command is not being run in an ignored channel
@bot.check_once
def channel_check(ctx):
    async def channel_perm_check():
        no_command_channels = get_ignored_channels()
        for channel in no_command_channels:
            if int(channel) == ctx.channel.id:
                return False
        return True

    return channel_perm_check()


# Commands
@bot.command(name='load', description='Load a cog')
@commands.check(auth(4))
async def load(ctx, extension):
    """
    The command to load a cog
    Requires: Auth level 4
    Extension: the cog to load
    """
    bot.load_extension(f'cogs.{extension}')
    log(f'Loaded {extension}.')
    await ctx.send(f'Loaded {extension}.', delete_after=deltime)
    await ctx.message.delete(delay=deltime)  # delete the command


@bot.command(name='ignorech', description='Make the bot ignore commands in the channel this is used in.')
@commands.check(auth(4))
async def ignorech(ctx):
    """
    Makes the bot ignore commands in the channel this is used in.
    """
    ch_id = str(ctx.channel.id)
    no_command_channels = get_ignored_channels()
    no_command_channels.append(ch_id)
    with open('ignored_channels.json', 'w', encoding='utf-8') as f:
        json.dump(no_command_channels, f, indent=4)
    set_ignored_channels()
    await ctx.send("Adding channel to ignore list.", delete_after=deltime)


@bot.command(name='restart', description='Restart the bot')
@commands.check(auth(5))
async def restart():
    """
    The command to restart the bot
    Requires: Auth level 5
    """
    await bot.change_presence(status=discord.Status.idle, activity=discord.Game("Restarting..."))
    for file_name in os.listdir(f'./{cogs_dir}'):
        if file_name.endswith('.py'):
            # try:
            bot.unload_extension(f'cogs.{file_name[:-3]}')  # unload each extension gracefully before restart
            # except:
            #     log(f'Error unloading extension {file_name[:-3].title()}.', bot.warn)
    os.execv(sys.executable, ['python'] + sys.argv)


# load all cogs in cogs folder at launch
# for filename in os.listdir('./cogs'):
#    if filename.endswith('.py'):
#        bot.load_extension(f'cogs.{filename[:-3]}')  # load up each extension


bot.load_extension(f'cogs.logging')
bot.load_extension(f'cogs.dev')
bot.load_extension(f'cogs.management')
bot.load_extension(f'cogs.database')
bot.load_extension(f'cogs.googleapi')
bot.load_extension(f'cogs.basics')
bot.load_extension(f'cogs.moderation')
bot.load_extension(f'cogs.mechanics')
bot.load_extension(f'cogs.economy')

# run bot
bot.run(TOKEN)
