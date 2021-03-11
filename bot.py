import json
import traceback
from json import JSONDecodeError

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
                          185496547436396545, 486271502107279391]
# allow settings to be modified by Vyryn, Xiant, Xifi and Brom
bot.BUMP_PAYMENT = 0  # Payment for disboard bumps
bot.PAYCHECK_AMOUNT_MIN = 4_000_000  # Minimum paycheck payout
bot.PAYCHECK_AMOUNT_MAX = 4_000_000  # Maximum paycheck payout
bot.PAYCHECK_INTERVAL = 3600  # Time between paychecks, in seconds
bot.REFUND_PORTION = 0.9  # Portion of buy price to refund when selling an item
bot.WEALTH_FACTOR = 0  # 0.0005  # Currently set to 0.05-0.1% payout per hour
bot.STARTING_BALANCE = 50_000_000  # New user starting balance
bot.PAYOUT_FREQUENCY = 60 * 60  # How frequently to send out investments, in seconds
bot.ACTIVITY_WEIGHT = 10000  # How many credits to award per activity point
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
# List of channels *to* count activity messages from
bot.activity_channels = [551189075646742579, 554390029976207378, 410451747547381760, 430796747552325632,
                         700944078128545842, 413462663767654412, 663819723263180844, 413461922260713494,
                         478004634624065551, 628713383746863144, 429055112615297035, 634940994361622548,
                         668016052709621760, 605201389739835393, 610736558839955456, 612339125034418240,
                         700134203278360596, 700339223038918706, 693235112871067678, 564230001369546767,
                         411255191816503318, 431833724993142794, 442348767790891009, 680443304202076186,
                         577909101552467971, 417164107431542785, 442810244855365632, 418585167670542366,
                         535196221531226135, 411660990246158336, 429783265772175370, 618573053697327126,
                         410128926183129088, 447429297859461120, 407497944846041088, 415619187507986452,
                         410128996978917397, 430011280183525417, 605507449767591937, 691379493293522994,
                         411255260447768597, 605507674997784607, 588081623526932493, 532437922545139723,
                         691381953227653120, 438041515491721216, 623018626571567104, 689851369351544899,
                         437089100575539201, 456645475429253121, 437041126399279104, 438042073921486857,
                         605507721483124747, 605507740403499028, 691383794430640129, 691382196463861882,
                         691381208608800989, 691381267945619559, 735127448869404785, 691379683434168410,
                         605507769453510656, 424280099773349888, 605508391858864173, 666706798534852627,
                         691383826777374720, 427861326166228992, 409815227140669452, 605508509299113995,
                         663287101256892427, 436965563974025236, 409814945673510923, 411255738825179146,
                         484566956775833601, 411256099241459722, 618573531629879310, 595304734240276490,
                         660696780484116500, 411255879040630795, 565026646797844500, 629536618172383258,
                         605507810763079695, 567128122332413962, 660750516569112597, 660692049787486219,
                         660692197175328788, 434494368108380160, 476401110588981259, 408819386808533022,
                         618573231816835092, 407497893205901313, 605507312962109467, 435453839978790912,
                         698854430677794846, 424281983104057345, 605507686754418688, 700323671167729684,
                         412097032485076992, 698855151531982857, 605508416387022869, 700323330561146950,
                         562803999011635220, 620404194679193613, 596110544298049546, 605508484670160919,
                         429050103962009601, 483797474037727257, 605507476489502760, 439914822524600330,
                         439914737497800714, 449139808993017866, 415619008428244992, 413009235463634954,
                         605508439862673455, 438041892869898250, 457234506441818133, 618573813831041037,
                         411256138991009793, 618573873524375584, 623023280147791874, 700322454421110804,
                         519386089186787329, 605507751803617310, 668407916440715333, 700322280001241138,
                         660692356407754752, 700322515159089182, 700322391347167292, 700322574365622352,
                         412008569404129280, 583095716734435346, 412008608964935710, 460940122830012427,
                         407497995790057473, 605508455247249558, 804717622847471646, 807791723995725854,
                         807794026937974784, 807794807052828713, 807795470742061086]
# Array to contain ids of each database-registered user to check for inclusion without database query
bot.list_of_users = []
OWNER_ID = owner_id
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


# ==================== Helper Utils ==============
async def quiet_send(ctx, message, delete_after=None) -> None:
    """Send a message. Should sending fail, log the error at the debug level but otherwise fail silently."""
    try:
        if delete_after:
            await ctx.send(message, delete_after=delete_after)
        else:
            await ctx.send(message)
    except discord.Forbidden:
        log(f'Insufficient permissions to send {message}', bot.debug)
    except discord.HTTPException:
        log(f'Failed to send {message} due to a discord HTTPException.', bot.debug)
    except discord.InvalidArgument:
        log(f'Failed to send {message} because files list is of the wrong size, reference is not a Message or '
            f'MessageReference, or both file and files parameters are specified.', bot.debug)


async def quiet_x(ctx) -> None:
    """React to a message with an :x: reaction. Should reaction, fail, log the error at the debug level but
    otherwise fail silently."""
    if not ctx.message:
        log(f'Failed to react to {ctx} because it has no message parameter.', bot.debug)
    try:
        await ctx.message.add_reaction('❌')
    except discord.Forbidden:
        log(f'Insufficient permissions to react to {ctx.message} with an x.', bot.debug)
    except discord.NotFound:
        log(f'Did not find {ctx.message} to react to with an x.')
    except discord.HTTPException:
        log(f'Failed to react to {ctx.message} with an x due to a discord HTTPException', bot.debug)
    except discord.InvalidArgument:
        log(f'Failed to react to {ctx.message} because the X reaction is not recognized by discord.')


async def quiet_fail(ctx, message: str) -> None:
    """React with an x and send the user an explanatory failure message. Should anything fail, log at the debug level
     but otherwise fail silently. Delete own response after 30 seconds."""
    resp = f'{ctx.author.name}, {message}'
    await quiet_x(ctx)
    await quiet_send(ctx, resp, delete_after=30)



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
async def on_command_error(ctx, error) -> None:
    """
    General bot error handler. The main thing here is if something goes very wrong, dm the bot owner the full
    error directly.
    :param ctx: Invoking context
    :param error: The error
    """
    # Ignore local command error handlers
    if hasattr(ctx.command, 'on_error'):
        return

    # Strip CommandInvokeError and ignore errors that require no reaction whatsoever.
    error = getattr(error, 'original', error)
    ignored = (commands.CommandNotFound, commands.DisabledCommand, commands.NotOwner)
    if isinstance(error, ignored):
        return
    bad_quotes = (commands.UnexpectedQuoteError, commands.InvalidEndOfQuotedStringError,
                  commands.ExpectedClosingQuoteError, commands.ArgumentParsingError)
    # Log anything not totally ignored
    log(f'{ctx.author} triggered {error} in command {ctx.command}: {error.args[0]} ({error.args})', bot.debug)
    # Several common errors that do require handling
    # Wrong place or no perms errors:
    if isinstance(error, commands.NoPrivateMessage):
        return await quiet_fail(ctx, f'the {ctx.command} command can not be used in private messages.')
    elif isinstance(error, commands.PrivateMessageOnly):
        return await quiet_fail(ctx, f'{ctx.command} command can only be used in private messages.')
    elif isinstance(error, commands.BotMissingPermissions) or isinstance(error, commands.BotMissingRole) or \
            isinstance(error, commands.BotMissingAnyRole):
        return await quiet_fail(ctx, f'{error}')
    elif isinstance(error, commands.MissingRole) or isinstance(error, commands.MissingAnyRole) or \
            isinstance(error, commands.MissingPermissions):
        return await quiet_fail(ctx, f'{error}')
    elif isinstance(error, commands.NSFWChannelRequired):
        return await quiet_fail(ctx, f'the {ctx.command} command must be used in an NSFW-marked channel.')
    elif isinstance(error, discord.ext.commands.errors.CommandOnCooldown):
        return await quiet_fail(ctx, f'you are on cooldown for that command. Try again in a little'
                                     f' while.')
    elif isinstance(error, commands.MaxConcurrencyReached):
        return await quiet_fail(ctx, f'too many instances of this command are being run at the moment.')
    elif isinstance(error, commands.CheckFailure):
        return await quiet_fail(ctx, f'you are not authorized to perform this command.')
    # User misformulated command errors
    elif isinstance(error, commands.BadBoolArgument):
        return await quiet_fail(ctx, 'boolean arguments must be "yes"/"no", "y"/"n", "true"/"false", "t"/"f", '
                                     '"1"/"0", "enable"/"disable" or "on"/"off".')
    elif isinstance(error, commands.PartialEmojiConversionFailure):
        return await quiet_fail(ctx, 'that is not an emoji.')
    elif isinstance(error, commands.EmojiNotFound):
        return await quiet_fail(ctx, "I didn't find that emoji.")
    elif isinstance(error, commands.BadInviteArgument):
        return await quiet_fail(ctx, 'that invite is invalid or expired.')
    elif isinstance(error, commands.RoleNotFound):
        return await quiet_fail(ctx, "I didn't find that role.")
    elif isinstance(error, commands.BadColourArgument):
        return await quiet_fail(ctx, "that's not a valid color")
    elif isinstance(error, commands.ChannelNotReadable):
        return await quiet_fail(ctx, "I don't have permission to read messages in that channel.")
    elif isinstance(error, commands.ChannelNotFound):
        return await quiet_fail(ctx, "I didn't find that channel.")
    elif isinstance(error, commands.MemberNotFound):
        return await quiet_fail(ctx, "I didn't find that member.")
    elif isinstance(error, commands.UserNotFound):
        return await quiet_fail(ctx, "I didn't find that user.")
    elif isinstance(error, commands.UserNotFound):
        return await quiet_fail(ctx, "I didn't find that message.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send_help(ctx.command)
        return await quiet_fail(ctx, f'incomplete command.')
    elif isinstance(error, commands.TooManyArguments):
        await ctx.send_help(ctx.command)
        return await quiet_fail(ctx, f'too many values passed to this command.')
    elif isinstance(error, bad_quotes):  # User messed up quotes
        return await quiet_fail(ctx, f'quotation marks do not balance. Make sure you close every quote you open.')
    elif isinstance(error, commands.ConversionError):
        return await quiet_fail(ctx, f"I couldn't convert a parameter to the correct format. Check help {ctx.command}"
                                     f" to help you formulate this command correctly.")
    elif isinstance(error, commands.BadArgument) or isinstance(error, commands.BadUnionArgument) or \
            isinstance(error, commands.UserInputError):
        return await quiet_fail(ctx, f'improper command. Check help {ctx.command} to help you '
                                     f'formulate this command correctly.')
    # Extension and command registration errors
    elif isinstance(error, commands.ExtensionAlreadyLoaded):
        return await quiet_fail(ctx, f'that extension is already loaded.')
    elif isinstance(error, commands.ExtensionNotLoaded):
        return await quiet_fail(ctx, f'that extension is not loaded.')
    elif isinstance(error, commands.NoEntryPointError):
        return await quiet_fail(ctx, f'that extension does not have a setup function.')
    elif isinstance(error, commands.ExtensionNotFound):
        return await quiet_fail(ctx, f'I see no such extension.')
    elif isinstance(error, commands.ExtensionFailed):
        return await quiet_fail(ctx, f'that exception refused to load.')
    elif isinstance(error, commands.ExtensionError):
        return await quiet_fail(ctx, f'uncaught ExtensionError.')
    elif isinstance(error, commands.CommandRegistrationError):
        return await quiet_fail(ctx, f'failed to register a duplicate command name: {error}')
    elif isinstance(error, discord.ClientException):
        return await quiet_fail(ctx, f'hmm, something went wrong. Try that command again.')
    # Other
    elif isinstance(error, discord.HTTPException):
        return await quiet_fail(ctx, f'the result was longer than I expected. Discord only supports 2000 '
                                     f'characters.')
    elif isinstance(error, JSONDecodeError):
        return await quiet_fail(ctx, f'the api for {ctx.command} appears to be down at the moment.'
                                     f' Try again later.')
    elif isinstance(error, asyncio.TimeoutError):
        return await quiet_fail(ctx, f"you took too long. Please re-run the command to continue when "
                                     f"you're ready.")
    else:
        # Get data from exception and format
        e_type = type(error)
        trace = error.__traceback__
        lines = traceback.format_exception(e_type, error, trace)
        traceback_text = '```py\n'
        traceback_text += ''.join(lines)
        traceback_text += '\n```'
        # If something goes wrong with sending the dev these errors it's a bit of a yikes so take some special
        # care here.
        try:
            await ctx.send(
                f"Hmm, something went wrong with {ctx.command}. I have let the developer know, and they will "
                f"take a look.")
            owner = bot.get_user(OWNER_ID)
            await owner.send(
                f'Hey {owner}, there was an error in the command {ctx.command}: {error}.\n It was used by '
                f'{ctx.author} in {ctx.guild}, {ctx.channel}.')
            try:
                await bot.get_user(OWNER_ID).send(traceback_text)
            except discord.errors.HTTPException:
                await bot.get_user(OWNER_ID).send(traceback_text[0:1995] + '\n```')
                await bot.get_user(OWNER_ID).send('```py\n' + traceback_text[1995:3994])
        except discord.errors.Forbidden:
            await ctx.message.add_reaction('❌')
            log(f"{ctx.command} invoked in a channel I do not have write perms in.", bot.info)
        log(f'Error triggered in command {ctx.command}: {error}, {lines}', bot.critical)
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
async def restart(ctx):
    """
    The command to restart the bot
    Requires: Auth level 5
    """
    await ctx.send("Restarting. Take a look at my status for when I'm back up.")
    await bot.change_presence(status=discord.Status.idle, activity=discord.Game("Restarting..."))
    for file_name in os.listdir(f'./{cogs_dir}'):
        if file_name.endswith('.py'):
            try:
                bot.unload_extension(f'cogs.{file_name[:-3]}')  # unload each extension gracefully before restart
            except commands.ExtensionError:
                log(f'Error unloading extension {file_name[:-3].title()}.', bot.warn)
    os.execv(sys.executable, ['python'] + sys.argv)


# load all cogs in cogs folder at launch
# for filename in os.listdir('./cogs'):
#    if filename.endswith('.py'):
#        bot.load_extension(f'cogs.{filename[:-3]}')  # load up each extension


bot.load_extension(f'cogs.logging')
bot.load_extension(f'cogs.dev')
bot.load_extension(f'cogs.management')
bot.load_extension('cogs.welcome')
bot.load_extension(f'cogs.database')
bot.load_extension(f'cogs.googleapi')
bot.load_extension(f'cogs.basics')
bot.load_extension(f'cogs.moderation')
bot.load_extension(f'cogs.mechanics')
bot.load_extension(f'cogs.economy')

# run bot
bot.run(TOKEN)
