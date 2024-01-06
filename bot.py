import json
import traceback
from json import JSONDecodeError
from typing import Dict

import discord  # pylint: disable=import-error
import os
import random
import sys
import asyncio
from discord.ext import commands  # pylint: disable=import-error
from functions import (
    get_prefix,
    global_prefix,
    get_ignored_channels,
    set_ignored_channels,
    auth,
    now,
)
from privatevars import TOKEN  # pylint: disable=import-error

intents = discord.Intents.all()
intents.typing = False


class Bot(commands.Bot):
    """Initializes and manages a discord bot."""

    def __init__(self, *args, **kwargs):
        self.owner_id = None
        super().__init__(
            command_prefix=get_prefix,  # type: ignore[arg-type]
            case_insensitive=True,
            intents=intents,
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False),
            activity=discord.Game("Starting up..."),
            status=discord.Status.do_not_disturb,
        )

    async def setup_hook(self):
        # asyncio.get_running_loop().set_exception_handler(self.handler)

        self.appinfo = await self.application_info()
        # self.owner_id = self.appinfo.owner.id
        self.owner_id = 125449182663278592
        await self.load_extension("cogs.dev")
        await self.load_extension("cogs.management")
        await self.load_extension("cogs.googleapi")
        await self.load_extension("cogs.mechanics")


bot = Bot()
# ========================== Easily Configurable Values ========================
# Default number of seconds to wait before deleting many bot responses and player commands
deltime = 10
# The id of the primary guild the bot is operating in
bot.serverid = 977038517588885545  # 718893913976340561 for startrade
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
bot.log_channel_id = (
    977038528842186783  # The channel set up for logging message edits and the like.
)
# bot.verified_role_id = 718949160170291203  # The verification role id
# bot.literate_role_id = 728796399692677160  # The certified literate role id
# bot.verification_message_id = 718980234380181534  # The startrade verification message id
bot.DISBOARD = 302050872383242240  # Disboard uid
bot.credit_emoji = "<:Credits:977356871759462440>"
# Constants to do with the goolge sheet pulls the bot makes.
bot.SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
bot.SHEET_ID = "1ZU6pTfdIGkQ9zzOH6lW0zkEQuF7-xFsyxgwSgGz4WcM"
bot.RANGE_SHIPS = "AllShips!A1:T1750"
bot.RANGE_WEAPONS = "Weapons!A1:L250"
# Don't log or do any other on_message action in the following guilds
bot.ignored_guilds = [336642139381301249]  # (this one is d.py)
bot.ACTIVITY_COOLDOWN = 7  # Minimum number of seconds after last activity to have a message count as activity
bot.MOVE_ACTIVITY_THRESHOLD = (
    100  # Number of activity score that must be gained when moving to a new location
)
bot.DEFUALT_DIE_SIDES = 20  # Default number of sides to assume a rolled die has
bot.MAX_DIE_SIDES = 100  # Max number of sides each die may have
bot.MAX_DIE_ROLES = (
    100000  # Max number of dice that can be rolled with one ,roll command
)
bot.ITEMS_PER_TOP_PAGE = 10  # Number of items to show per page in ,top
bot.AUTH_LOCKDOWN = 1  # The base level for commands from this cog; set to 0 to enable public use, 1 to disable it
bot.MAX_PURGE = (
    100  # Max number of messages that can be purged with ,forcepurge command at once
)

# ============================ Less Easily Configured Values =======================
# The bot randomly selects one of these statuses at startup
statuses = [
    "Being an adult is just walking around wondering what you're forgetting.",
    "A clean house is the sign of a broken computer.",
    "I have as much authority as the Pope, i just don't have as many people who believe it.",
    "A conclusion is the part where you got tired of thinking.",
    "To the mathematicians who thought of the idea of zero, thanks for nothing!",
    "My job is secure. No one else wants it.",
    "If at first you don't succeed, we have a lot in common.",
    "I think we should get rid of democracy. All in favor raise your hand.",
]
# Which discord perms are consider basic/important
basicperms = [
    "administrator",
    "manage_guild",
    "ban_members",
    "manage_roles",
    "manage_messages",
]
# Which discord perms are consider significant/notable
sigperms = [
    "deafen_members",
    "kick_members",
    "manage_channels",
    "manage_emojis",
    "manage_nicknames",
    "manage_webhooks",
    "mention_everyone",
    "move_members",
    "mute_members",
    "priority_speaker",
    "view_audit_log",
]
# The directory for cogs
cogs_dir = "cogs"
bot.global_prefix = global_prefix
bot.deltime = deltime
bot.confirmed_ids: Dict[int, int] = {}
bot.content_max = 1970  # The maximum number of characters that can safely be fit into a logged message
bot.time_options = {
    "s": 1,
    "m": 60,
    "h": 60 * 60,
    "d": 60 * 60 * 24,
    "w": 60 * 60 * 24 * 7,
    "y": 60 * 60 * 24 * 365,
}
bot.number_reactions = [
    "1\u20e3",
    "2\u20e3",
    "3\u20e3",
    "4\u20e3",
    "5\u20e3",
    "6\u20e3",
    "7\u20e3",
    "8\u20e3",
    "9\u20e3",
]
bot.reactions_to_nums = {
    "1⃣": 1,
    "2⃣": 2,
    "3⃣": 3,
    "4⃣": 4,
    "5⃣": 5,
    "6⃣": 6,
    "7⃣": 7,
    "8⃣": 8,
    "9⃣": 9,
}
# Bot commanders levels
bot.PERMS_INFO = {
    0: "(No other dev perms)",
    1: "Can use echo and auth check",
    2: "Can make bot send DMs",
    3: "Can reload cogs",
    4: "Can load and unload cogs",
    5: "Can update bot status",
    6: "Can see the list of all bot commanders",
    7: "Can set other people's auth levels",
    8: "Trusted for dangerous dev commands",
    9: "Can use eval",
    10: "Created me",
}
# List of channels *to* count activity messages from
bot.activity_channels = [
    977038522500382751,
    977038522500382752,
    977038522500382753,
    977038522500382754,
    977038522500382755,
    977038522500382756,
    977038522500382757,
    977038522500382758,
    977038522500382759,
    977038522785628201,
    977038522785628202,
    977038522785628203,
    977038522785628204,
    977038522785628205,
    977038523158908989,
    977038523158908990,
    977038523158908992,
    977038523158908991,
    977038523645456384,
    977038523158908993,
    977038523158908994,
    977038523158908995,
    977038523645456385,
    977038523645456387,
    977038523645456388,
    977038523645456389,
    977038523645456390,
    977038523645456391,
    977038523645456392,
    977038523905474570,
    977038523645456393,
    977038523905474571,
    977038523905474572,
    977038523905474573,
    977038523905474574,
    977038523905474576,
    977038523905474577,
    977038523905474578,
    977038524148752424,
    977038523905474579,
    977038524148752425,
    977038524148752428,
    977038524148752429,
    977038524148752430,
    977038524148752431,
    977038524694028338,
    977038524148752432,
    977038524694028339,
    977038524694028340,
    977038524694028341,
    977038524694028342,
    977038524694028346,
    977038524874387536,
    977038524694028347,
    977038524874387538,
    977038524874387539,
    977038524874387540,
    977038525180555304,
    977038524874387541,
    977038524874387542,
    977038524874387543,
    977038524874387544,
    977038524874387545,
    977038525180555305,
    977038525180555307,
    977038525180555306,
    977038525180555309,
    977038525180555310,
    977038525499310130,
    977038525180555311,
    977038525180555312,
    977038525180555313,
    977038525499310131,
    977038525499310132,
    977038525499310133,
    977038525499310134,
    977038525851664394,
    977038525499310135,
    977038525499310136,
    977038525499310138,
    977038525499310139,
    977038526203973669,
    977038525851664395,
    977038526203973671,
    977038526443032576,
    977038526443032577,
    977038525851664396,
    977038526203973668,
    977038526715658331,
    977038525851664399,
    977038525851664400,
    977038525851664401,
    977038525851664402,
    977038525851664403,
    977038526203973662,
    977038526203973663,
    977038526443032584,
    977038526203973664,
    977038526443032579,
    977038526443032583,
    977038526443032585,
    977038526715658330,
    977038526715658332,
    977038526443032578,
    977038527068012586,
    977038526443032582,
    977038526715658336,
    1045779522114568302,
    977038527068012584,
    1045779992639975504,
    977038527068012585,
    977038527068012587,
    977038527068012588,
    1045779353990070302,
    977038527068012589,
    977038527068012590,
    1045779146430763068,
    977038527625842716,
    977038527068012593,
    977038526715658335,
    977038527395160095,
    977038527395160096,
    977038527395160097,
    977038527395160098,
    977038527395160099,
    977038527395160100,
    977038527625842708,
    977038527395160102,
    977038527395160101,
    977038527395160104,
    977038527625842709,
    977038527625842717,
    977038527625842710,
    977038527625842714,
    977038527625842713,
    977038527625842711,
    977038527625842712,
    977038526715658333,
    977038527986544710,
    977038527625842715,
    977038527986544711,
    977038526443032580,
    977038526443032581,
    977038523645456386,
    977038527068012591,
    977038525180555308,
    977038527068012592,
    1045784201531752570,
    1045784301964374067,
    977038522051620921,
    977038522051620920,
    1059169009007869972,
    977038527986544718,
    977038527986544717,
    977038527986544716,
    977038527986544714,
    977038525499310138,
    977038524874387537,
    1136474005394694204,
    1136474090715226143,
    1136474090715226143,
    1136474159497613463,
    1157406621480267887,
    1073061987216535662,
    1143402970625626112,
]

# Array to contain ids of each database-registered user to check for inclusion without database query
bot.list_of_users = []
# Set debug display values
bot.debug = "DBUG"
bot.info = "INFO"
bot.warn = "WARN"
bot.error = "EROR"
bot.critical = "CRIT"
bot.cmd = "CMMD"
bot.tofix = "TOFX"
bot.prio = "PRIO"
bot.rankup = "RKUP"
bot.msg = "MESG"

bot.logging_status = [
    bot.debug,
    bot.msg,
]  # Any logging levels here will be *excluded* from being logged


def botget(arg: str):
    return bot.__dict__[arg]


def log(message: str, severity="INFO"):
    if severity in bot.logging_status:
        return
    print(f"[{severity}] {message}  |  {now()}")


def logready(item):
    try:
        log(f"{item.qualified_name} is ready.")
    except AttributeError:
        log(f"{item} is ready.")


# ==================== Helper Utils ==============
async def quiet_send(ctx, message, delete_after=None) -> None:
    """Send a message. Should sending fail, log the error at the debug level but otherwise fail silently."""
    try:
        if delete_after:
            await ctx.send(message, delete_after=delete_after)
        else:
            await ctx.send(message)
    except discord.Forbidden:
        log(f"Insufficient permissions to send {message}", bot.debug)
    except discord.HTTPException:
        log(f"Failed to send {message} due to a discord HTTPException.", bot.debug)
    except (TypeError, ValueError):
        log(
            f"Failed to send {message} because files list is of the wrong size, reference is not a Message or "
            f"MessageReference, or both file and files parameters are specified.",
            bot.debug,
        )


async def quiet_x(ctx) -> None:
    """React to a message with an :x: reaction. Should reaction, fail, log the error at the debug level but
    otherwise fail silently."""
    if not ctx.message:
        log(f"Failed to react to {ctx} because it has no message parameter.", bot.debug)
    try:
        await ctx.message.add_reaction("❌")
    except discord.Forbidden:
        log(f"Insufficient permissions to react to {ctx.message} with an x.", bot.debug)
    except discord.NotFound:
        log(f"Did not find {ctx.message} to react to with an x.")
    except discord.HTTPException:
        log(
            f"Failed to react to {ctx.message} with an x due to a discord HTTPException",
            bot.debug,
        )
    except (TypeError, ValueError):
        log(
            f"Failed to react to {ctx.message} because the X reaction is not recognized by discord."
        )


async def quiet_fail(ctx, message: str) -> None:
    """React with an x and send the user an explanatory failure message. Should anything fail, log at the debug level
    but otherwise fail silently. Delete own response after 30 seconds."""
    resp = f"{ctx.author.name}, {message}"
    await quiet_x(ctx)
    await quiet_send(ctx, resp, delete_after=30)


# Events
@bot.event
async def on_ready():
    bot.server = bot.get_guild(bot.serverid)
    bot.log_channel = bot.get_channel(bot.log_channel_id)
    # Pick a random current status on startup
    await bot.change_presence(
        status=discord.Status.online, activity=discord.Game(random.choice(statuses))
    )
    await asyncio.sleep(2)
    if hasattr(bot, "server") and hasattr(bot.server, "name"):
        log(f"{bot.server.name} bot is fully ready.", bot.prio)
    else:
        log("Bot is fully ready.", bot.prio)


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
    if hasattr(ctx.command, "on_error"):
        return

    # Strip CommandInvokeError and ignore errors that require no reaction whatsoever.
    error = getattr(error, "original", error)
    ignored = (commands.CommandNotFound, commands.DisabledCommand, commands.NotOwner)
    if isinstance(error, ignored):
        return
    bad_quotes = (
        commands.UnexpectedQuoteError,
        commands.InvalidEndOfQuotedStringError,
        commands.ExpectedClosingQuoteError,
        commands.ArgumentParsingError,
    )
    # Log anything not totally ignored
    log(
        f"{ctx.author} triggered {error} in command {ctx.command}: {error.args[0]} ({error.args})",
        bot.debug,
    )
    # Several common errors that do require handling
    # Wrong place or no perms errors:
    if isinstance(error, commands.NoPrivateMessage):
        return await quiet_fail(
            ctx, f"the {ctx.command} command can not be used in private messages."
        )
    elif isinstance(error, commands.PrivateMessageOnly):
        return await quiet_fail(
            ctx, f"{ctx.command} command can only be used in private messages."
        )
    elif (
        isinstance(error, commands.BotMissingPermissions)
        or isinstance(error, commands.BotMissingRole)
        or isinstance(error, commands.BotMissingAnyRole)
    ):
        return await quiet_fail(ctx, f"{error}")
    elif (
        isinstance(error, commands.MissingRole)
        or isinstance(error, commands.MissingAnyRole)
        or isinstance(error, commands.MissingPermissions)
    ):
        return await quiet_fail(ctx, f"{error}")
    elif isinstance(error, commands.NSFWChannelRequired):
        return await quiet_fail(
            ctx, f"the {ctx.command} command must be used in an NSFW-marked channel."
        )
    elif isinstance(error, discord.ext.commands.errors.CommandOnCooldown):
        return await quiet_fail(
            ctx,
            f"you are on cooldown for that command. Try again in a little" f" while.",
        )
    elif isinstance(error, commands.MaxConcurrencyReached):
        return await quiet_fail(
            ctx, f"too many instances of this command are being run at the moment."
        )
    elif isinstance(error, commands.CheckFailure):
        return await quiet_fail(ctx, f"you are not authorized to perform this command.")
    # User misformulated command errors
    elif isinstance(error, commands.BadBoolArgument):
        return await quiet_fail(
            ctx,
            'boolean arguments must be "yes"/"no", "y"/"n", "true"/"false", "t"/"f", '
            '"1"/"0", "enable"/"disable" or "on"/"off".',
        )
    elif isinstance(error, commands.PartialEmojiConversionFailure):
        return await quiet_fail(ctx, "that is not an emoji.")
    elif isinstance(error, commands.EmojiNotFound):
        return await quiet_fail(ctx, "I didn't find that emoji.")
    elif isinstance(error, commands.BadInviteArgument):
        return await quiet_fail(ctx, "that invite is invalid or expired.")
    elif isinstance(error, commands.RoleNotFound):
        return await quiet_fail(ctx, "I didn't find that role.")
    elif isinstance(error, commands.BadColourArgument):
        return await quiet_fail(ctx, "that's not a valid color")
    elif isinstance(error, commands.ChannelNotReadable):
        return await quiet_fail(
            ctx, "I don't have permission to read messages in that channel."
        )
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
        return await quiet_fail(ctx, f"incomplete command.")
    elif isinstance(error, commands.TooManyArguments):
        await ctx.send_help(ctx.command)
        return await quiet_fail(ctx, f"too many values passed to this command.")
    elif isinstance(error, bad_quotes):  # User messed up quotes
        return await quiet_fail(
            ctx,
            f"quotation marks do not balance. Make sure you close every quote you open.",
        )
    elif isinstance(error, commands.ConversionError):
        return await quiet_fail(
            ctx,
            f"I couldn't convert a parameter to the correct format. Check help {ctx.command}"
            f" to help you formulate this command correctly.",
        )
    elif (
        isinstance(error, commands.BadArgument)
        or isinstance(error, commands.BadUnionArgument)
        or isinstance(error, commands.UserInputError)
    ):
        return await quiet_fail(
            ctx,
            f"improper command. Check help {ctx.command} to help you "
            f"formulate this command correctly.",
        )
    # Extension and command registration errors
    elif isinstance(error, commands.ExtensionAlreadyLoaded):
        return await quiet_fail(ctx, f"that extension is already loaded.")
    elif isinstance(error, commands.ExtensionNotLoaded):
        return await quiet_fail(ctx, f"that extension is not loaded.")
    elif isinstance(error, commands.NoEntryPointError):
        return await quiet_fail(ctx, f"that extension does not have a setup function.")
    elif isinstance(error, commands.ExtensionNotFound):
        return await quiet_fail(ctx, f"I see no such extension.")
    elif isinstance(error, commands.ExtensionFailed):
        return await quiet_fail(ctx, f"that exception refused to load.")
    elif isinstance(error, commands.ExtensionError):
        return await quiet_fail(ctx, f"uncaught ExtensionError.")
    elif isinstance(error, commands.CommandRegistrationError):
        return await quiet_fail(
            ctx, f"failed to register a duplicate command name: {error}"
        )
    elif isinstance(error, discord.ClientException):
        return await quiet_fail(
            ctx, f"hmm, something went wrong. Try that command again."
        )
    # Other
    elif isinstance(error, discord.HTTPException):
        return await quiet_fail(
            ctx,
            "the result was longer than I expected. Discord only supports 2000 "
            "characters.",
        )
    elif isinstance(error, JSONDecodeError):
        return await quiet_fail(
            ctx,
            f"the api for {ctx.command} appears to be down at the moment."
            f" Try again later.",
        )
    elif isinstance(error, asyncio.TimeoutError):
        return await quiet_fail(
            ctx,
            "you took too long. Please re-run the command to continue when "
            "you're ready.",
        )
    else:
        # Get data from exception and format
        e_type = type(error)
        trace = error.__traceback__
        lines = traceback.format_exception(e_type, error, trace)
        traceback_text = "```py\n"
        traceback_text += "".join(lines)
        traceback_text += "\n```"
        # If something goes wrong with sending the dev these errors it's a bit of a yikes so take some special
        # care here.
        try:
            await ctx.send(
                f"Hmm, something went wrong with {ctx.command}. I have let the developer know, and they will "
                f"take a look."
            )
            owner = bot.get_user(bot.owner_id)
            await owner.send(
                f"Hey {owner}, there was an error in the command {ctx.command}: {error}.\n It was used by "
                f"{ctx.author} in {ctx.guild}, {ctx.channel}."
            )
            try:
                await bot.get_user(bot.owner_id).send(traceback_text)
            except discord.errors.HTTPException:
                await bot.get_user(bot.owner_id).send(traceback_text[0:1995] + "\n```")
                await bot.get_user(bot.owner_id).send(
                    "```py\n" + traceback_text[1995:3994]
                )
        except discord.errors.Forbidden:
            await ctx.message.add_reaction("❌")
            log(
                f"{ctx.command} invoked in a channel I do not have write perms in.",
                bot.info,
            )
        log(f"Error triggered in command {ctx.command}: {error}, {lines}", bot.critical)
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
@bot.command(name="load", description="Load a cog")
@commands.check(auth(4))
async def load(ctx, extension):
    """
    The command to load a cog
    Requires: Auth level 4
    Extension: the cog to load
    """
    await bot.load_extension(f"cogs.{extension}")
    log(f"Loaded {extension}.")
    await ctx.send(f"Loaded {extension}.", delete_after=deltime)
    await ctx.message.delete(delay=deltime)  # delete the command


@bot.command(
    name="ignorech",
    description="Make the bot ignore commands in the channel this is used in.",
)
@commands.check(auth(4))
async def ignorech(ctx):
    """
    Makes the bot ignore commands in the channel this is used in.
    """
    ch_id = str(ctx.channel.id)
    no_command_channels = get_ignored_channels()
    if ch_id not in no_command_channels:
        no_command_channels.append(ch_id)
        await ctx.send("Adding channel to ignore list.", delete_after=deltime * 5)
    else:
        no_command_channels.remove(ch_id)
        await ctx.send("Removing channel from ignore list.", delete_after=deltime * 5)
    with open("ignored_channels.json", "w", encoding="utf-8") as f:
        json.dump(no_command_channels, f, indent=4)
    set_ignored_channels()


@bot.command(name="restart", description="Restart the bot")
@commands.check(auth(5))
async def restart(ctx):
    """
    The command to restart the bot
    Requires: Auth level 5
    """
    await ctx.send("Restarting. Take a look at my status for when I'm back up.")
    await bot.change_presence(
        status=discord.Status.idle, activity=discord.Game("Restarting...")
    )
    for file_name in os.listdir(f"./{cogs_dir}"):
        if file_name.endswith(".py"):
            try:
                await bot.unload_extension(
                    f"cogs.{file_name[:-3]}"
                )  # unload each extension gracefully before restart
            except commands.ExtensionError:
                log(f"Error unloading extension {file_name[:-3].title()}.", bot.warn)
    os.execv(sys.executable, ["python"] + sys.argv)


# load all cogs in cogs folder at launch
# for filename in os.listdir('./cogs'):
#    if filename.endswith('.py'):
#        bot.load_extension(f'cogs.{filename[:-3]}')  # load up each extension

if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except ConnectionResetError:
        print("Initially failed to connect. Retrying in five seconds.")
        time.sleep(5000)
        bot.run(TOKEN)
