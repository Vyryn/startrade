import json
from datetime import datetime, timezone, date
from typing import List

import aiohttp  # pylint: disable=import-error
import discord  # pylint: disable=import-error
from discord.ext import commands  # pylint: disable=import-error
from attr import dataclass  # pylint: disable=import-error

# The bot commanders (imported from a file)
bot_commanders = {}  # {125449182663278592: 10}
# Authorization level of someone not in bot_commanders. Think carefully before changing this.
DEFAULT_AUTH = 0
# No command channels: A list of channels the bot will not respond to messages in.
no_command_channels: List[int] = []
# The default global bot prefix
global_prefix = ","

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


# activity = floor( (5 / 6 * rank ) * (2 * rank ** 2 + 27 * rank + 91 ) )
def level(a):
    if a < 100:
        return 1
    else:
        return int(a ** (1 / 3) * 5 / 6 - 4)


activity_ranks = dict(zip(range(0, 1000), [level(a) for a in range(0, 1000)]))


def utcnow() -> datetime:
    """
    Returns the current time as a timezone aware utc datetime object.
    :return: the current time as a timezone aware utc datetime object.
    :rtype:
    """
    return datetime.now(tz=timezone.utc)


# Helper method for opening a json
def load_json_var(name):
    with open(f"{name}.json", "r") as f:
        return json.load(f)


# Helper method for writing a json
def write_json_var(name, obj):
    with open(f"{name}.json", "w") as f:
        json.dump(obj, f, indent=4)


# Update the memory bot_commanders dict by reading from file
def set_commanders():
    global bot_commanders
    bot_commanders = load_json_var("auths")
    bot_commanders["125449182663278592"] = 10
    return


def get_ignored_channels():
    global no_command_channels
    return no_command_channels


# Update the memory ignored_channels list by reading from file
def set_ignored_channels():
    global no_command_channels
    no_command_channels = load_json_var("ignored_channels")
    return


# Return the bot_commanders dict
def get_commanders():
    global bot_commanders
    return bot_commanders


# Save bot_commanders to file
def save_commanders():
    global bot_commanders
    write_json_var("auths", bot_commanders)
    return


# Checks if a user has the requested authorization level or not, is a coroutine for async operation
def auth(auth_level):
    async def user_auth_check(ctx, *args):
        for uid in bot_commanders.keys():
            if (
                int(uid) == ctx.author.id
                and bot_commanders.get(uid, DEFAULT_AUTH) >= auth_level
            ):
                return True
        # ('User not found to be auth\'d')
        return False

    return user_auth_check


# Checks if a user has the requested authorization level or not, is a coroutine for async operation
def channel_check(ctx):
    async def channel_perm_check(*args):
        for channel in no_command_channels:
            if int(channel) == ctx.channel.id:
                return True
        return False

    return channel_perm_check()


# Returns the bot prefix for the guild the message is within, or the global default prefix
def get_prefix(bot, message):
    global no_command_channels
    with open("ignored_channels.json", "r") as f:
        no_command_channels = json.load(f)
    # outside a guild
    if not message.guild:
        return global_prefix
    else:
        # Get guild custom prefixes from file
        with open("prefixes.json", "r") as f:
            prefixes = json.load(f)
        return prefixes.get(str(message.guild.id), global_prefix)


# Returns current timestamp in the desired format, in this case MM/DD/YYYY HH:MM:SS
def now():
    try:
        return datetime.now().strftime("%m/%d/%y %H:%M:%S")
    except commands.CommandInvokeError as e:
        return f"(Could not get timestamp)"
    except aiohttp.ClientOSError:
        return f"(Could not get timestamp #2)"


# Returns current datestamp as YYYY-MM-DD
def today():
    try:
        return date.today().strftime("%Y-%m-%d")
    except commands.CommandInvokeError as e:
        return f"(Could not get date)"


# Log a message.
def log(message, mm):
    print(message)
    try:
        if mm.guild is not None:
            guild = mm.guild.name
            channel = mm.channel.name
        else:
            guild = "DMs"
            channel = mm.channel.recipient
    except AttributeError:
        guild = "no_guild"
        channel = "no_channel"
    # logmsg = 'MSG@{}:  {}:{}'.format(now(), message['guild']['name'],message['channel']['name'])
    try:
        with open(
            f"./logs/{guild}/{channel}_{today()}_log.log", "a+", encoding="utf-8"
        ) as f:
            try:
                f.write(str(message) + "\n")
            except UnicodeEncodeError:
                f.write(
                    f"WRN@{now()}: A UnicodeEncodeError occurred trying to write a message log.\n"
                )
    except FileNotFoundError:
        try:
            with open(f"./logs/{guild}_{today()}_log.log", "a+", encoding="utf-8") as f:
                try:
                    f.write(str(message) + "\n")
                except UnicodeEncodeError:
                    f.write(
                        f"WRN@{now()}: A UnicodeEncodeError occurred trying to write a message log.\n"
                    )
        except:
            print("Something went very wrong trying to log a message.")
    return


def order(x, count=0):
    """Returns the base 10 order of magnitude of a number"""
    if x / 10 >= 1:
        count += order(x / 10, count) + 1
    return count


def get_item(iterable_or_dict, index, default=None):
    """Return iterable[index] or default if IndexError is raised."""
    try:
        return iterable_or_dict[index]
    except (IndexError, KeyError):
        return default


# For user info
@dataclass
class UserInfo:
    id: int
    name: str = "null"
    count: int = 0
