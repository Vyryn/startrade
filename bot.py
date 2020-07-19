import json
from json import JSONDecodeError
import traceback
import discord
import os
import random
import sys
import asyncio
from discord.ext import commands
from functions import get_prefix, global_prefix, get_ignored_channels, set_ignored_channels, confirmed_ids, auth
from privatevars import TOKEN

# The id of the bot creator
owner_id = 125449182663278592
# Default number of seconds to wait before deleting many bot responses and player commands
deltime = 10
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
bot = commands.Bot(command_prefix=get_prefix, case_insensitive=True)


# Events
@bot.event
async def on_ready():
    # Pick a random current status on startup
    await bot.change_presence(status=discord.Status.online, activity=discord.Game(random.choice(statuses)))
    bot.server = bot.get_guild(407481043856261120)
    bot.log_channel = bot.get_channel(408254707388383232)
    bot.global_prefix = global_prefix
    bot.deltime = deltime
    bot.confirmed_ids = confirmed_ids
    await asyncio.sleep(2)
    print(f'{bot.server.name} bot is fully ready.')


# ================================= Error Handler =================================
@bot.event
async def on_command_error(ctx, error):
    if hasattr(ctx.command, 'on_error'):
        print('An error occurred, but was handled command-locally.')
        return
    if isinstance(error, commands.NoPrivateMessage):
        try:
            await ctx.send(f'The {ctx.command} command can not be used in private messages.', delete_after=deltime)
        except:
            pass
        return print(f'Error, NoPrivateMessage in command {ctx.command}: {error.args}')
    elif isinstance(error, commands.CommandNotFound):
        print(f'Error, {ctx.author} triggered CommandNotFound in command {ctx.command}: {error.args[0]}')
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        try:
            await ctx.send("Incomplete command.", delete_after=deltime)
        except:
            pass
        return print(f'Error, MissingRequiredArgument in command {ctx.command}: {error.args[0]}')
    elif isinstance(error, OSError):
        return print(f'OSError in command {ctx.command}. Restart the server soon.')
    elif isinstance(error, commands.errors.CommandInvokeError):
        return print(error)
    elif isinstance(error, discord.ext.commands.errors.BadArgument):
        try:
            await ctx.send("Improper command. Check ,help [command] to help you formulate this command correctly.",
                           delete_after=deltime)
        except:
            pass
        return print(f'BadArgument error in {ctx.command} for {ctx.author}')
    elif isinstance(error, commands.MissingPermissions):
        try:
            await ctx.send(f'{ctx.author}, {error}', delete_after=deltime)
        except:
            pass
        return print(f'{ctx.author} tried to use {ctx.command} without sufficient permissions.')
    elif isinstance(error, commands.CheckFailure):
        try:
            await ctx.send(f'{ctx.author}, you are not authorized to perform this command in this channel. If you '
                           f'think this is a mistake, try using it in a channel where bot commands are not disabled.',
                           delete_after=deltime)
        except:
            pass
        return print(f'{ctx.author} tried to use {ctx.command} without sufficient auth level.')
    elif isinstance(error, JSONDecodeError):
        try:
            await ctx.send(f'{ctx.author}, that api appears to be down at the moment.', delete_after=deltime)
        except:
            pass
        return print(f'{ctx.author} tried to use {ctx.command} but got a JSONDecodeError.')
    elif isinstance(error, asyncio.TimeoutError):
        try:
            await ctx.send(f"{ctx.author}, you took too long. Please re-run the command to continue"
                           f" when you're ready.", delete_after=deltime)
        except:
            pass
        return print(f'{ctx.author} tried to use {ctx.command} but got a JSONDecodeError.')
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
                f"Hmm, something went wrong with {ctx.command}."
                f" I have let the developer know, and they will take a look.")
            await bot.get_user(owner_id).send(
                f'Hey Vyryn, there was an error in the command {ctx.command}: {error}.\n '
                f'It was used by {ctx.author} in {ctx.guild}, {ctx.channel}.')
            await bot.get_user(owner_id).send(traceback_text)
        except:
            print(f"I was unable to send the error log for debugging.")
        print(traceback_text)
        # print(f'Error triggered: {error} in command {ctx.command}, {traceback.print_tb(error.__traceback__)}')
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
    print(f'Loaded {extension}.')
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
            #     print(f'Error unloading extension {file_name[:-3].title()}.')
    os.execv(sys.executable, ['python'] + sys.argv)


bot.load_extension(f'cogs.basics')
bot.load_extension(f'cogs.dev')
bot.load_extension(f'cogs.moderation')
bot.load_extension(f'cogs.mechanics')
bot.load_extension(f'cogs.management')
bot.load_extension(f'cogs.database')
bot.load_extension(f'cogs.economy')
# load all cogs in cogs folder at launch
#for filename in os.listdir('./cogs'):
#    if filename.endswith('.py'):
#        bot.load_extension(f'cogs.{filename[:-3]}')  # load up each extension

# run bot
bot.run(TOKEN)
