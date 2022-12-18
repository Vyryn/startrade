import asyncio
import random
import time
from decimal import Decimal

import aiohttp
from io import BytesIO

import asyncpg
import discord
from discord.ext import commands
from bot import log, logready
import asyncpg as conn
from functions import auth, now, level
from privatevars import DBUSER, DBPASS

global db
# These parameters need to be in this scope due to constraints of the library.
# I set them based on the bot attributes of the same names in init and on_ready.
# These are just "default default values" so to speak, and are never actually used.
starting_balance = 50000000
wealth_factor = 0
items_per_top_page = 10
refund_portion = 0.9
move_activity_threshold = 100
actweight = 10000
AUTH_LOCKDOWN = 1
COMMODITIES = {}


async def connect():
    global db
    try:
        if not db.is_closed():
            return
    except NameError:
        log('Creating DB Object.', "DBUG")
        pass
    db = await conn.connect(
        host='localhost',
        user=DBUSER,
        password=DBPASS,
        database='gfw'
    )


async def disconnect():
    try:
        await db.commit()
    except AttributeError:
        pass  # There was no need to commit
    # await db.close()


async def new_user(user: discord.User):
    uid = user.id
    name = user.name
    messages = 0
    balance = starting_balance
    last_pay = time.time() - 31536000  # Set last payout time to a year ago to allow immediate paycheck
    invested = 0
    await connect()
    check = await db.fetchrow(f"SELECT * FROM users WHERE id = $1", uid)
    print(f'Moving on: {check}')
    if check is not None:
        await disconnect()
        return f'User {name} Already Exists in database.'
    try:
        await db.execute(
            "INSERT INTO users VALUES($1, $2, $3, $4, $5, $6)", uid, name, messages, balance, last_pay, invested)
        result = f'User {name} added to database at {now()}.'
    except conn.UniqueViolationError:
        await db.execute("UPDATE users SET name = $1 WHERE id = $2", name, uid)
        result = f'User {name} name updated in database at {now()}.'
    await disconnect()
    return result


async def add_invest(member: discord.Member, amount: float):
    uid = member.id
    await connect()
    check = await db.fetchrow(f"SELECT * FROM users WHERE id = $1", uid)
    invested = check[5]
    balance = check[3]
    if check is None:
        return -1, 0, 0
    log(f'{invested}, {amount}', "DBUG")
    if float(amount) > float(balance):
        return -2, 0, 0
    await db.execute(f"UPDATE users SET invested = $1 where id = $2", float(invested) + float(amount), uid)
    await db.execute(f"UPDATE users SET balance = $1 where id = $2", float(balance) - float(amount), uid)
    await disconnect()
    return amount, float(invested) + float(amount), float(balance) - float(amount)


async def transfer_funds(from_user: discord.User, to_user: discord.User, amount: float):
    uid_from = from_user.id
    uid_to = to_user.id
    await connect()
    from_balance = (await db.fetchrow(f"SELECT balance FROM users WHERE id = $1", uid_from))[0]
    to_balance = (await db.fetchrow(f"SELECT balance FROM users WHERE id = $1", uid_to))[0]
    log(f'Transferring {amount} from {from_user} to {to_user}.')
    to_balance = float(to_balance) + float(amount)
    from_balance = float(from_balance) - float(amount)
    if float(from_balance) < 0:
        return -1, 0
    await db.execute(f"UPDATE users SET balance = $1 where id = $2", from_balance, uid_from)
    await db.execute(f"UPDATE users SET balance = $1 where id = $2", to_balance, uid_to)
    await disconnect()
    return from_balance, to_balance


async def update_activity(member: discord.Member, amount: int):
    uid = member.id
    await connect()
    activity = None
    try:
        activity = (await db.fetchval(f"SELECT activity FROM users WHERE id = $1", uid))
    except asyncpg.exceptions.InternalClientError:
        log('Asyncpg is being stupid, but I did my best.', "WARN")
    except asyncpg.exceptions.InterfaceError:
        log('Asyncpg is being stupid, but I did my best (2).', "WARN")
    if activity is None:
        activity = amount
    else:
        activity += amount
    log(f'Activity before: {activity - amount}, activity after: {activity}', "DBUG")
    level_before = level(activity - amount)
    level_after = level(activity)
    if level_after > level_before:
        # await channel.send(f"Congratulations {member} on reaching activity level {level_after}!")
        log(f'{member} ranked up their activity from level {level_before} to {level_after}', 'RKUP')
    try:
        recent_activity = (await db.fetchval(f"SELECT recent_activity FROM users WHERE id = $1", uid)) + amount
    except TypeError:
        recent_activity = amount
    log(f'Adding {amount} activity score to {member}. New activity score: {activity}. '
        f'New recent activity score: {recent_activity}', "DBUG")
    await db.execute(f"UPDATE users SET activity = $1 where id = $2", activity, uid)
    await db.execute(f"UPDATE users SET recent_activity = $1 where id = $2", recent_activity, uid)
    await disconnect()


async def update_n_word(member: discord.Member, amount: int):
    uid = member.id
    await connect()
    n_word = None
    n_word = (await db.fetchval(f"SELECT n_word FROM users WHERE id = $1", uid))
    if n_word is None:
        n_word = amount
    else:
        n_word += amount
    await db.execute(f"UPDATE users SET n_word = $1 where id = $2", n_word, uid)
    await disconnect()


async def add_funds(member: discord.Member, amount: int):
    uid = member.id
    await connect()
    result = await db.fetchrow(f"SELECT balance FROM users WHERE id = $1", uid)
    balance = result[0]
    log(f'Adding {amount} credits to {member}.')
    balance += amount
    await db.execute(f"UPDATE users SET balance = $1 where id = $2", balance, uid)
    await disconnect()
    return balance


async def check_bal(member: discord.Member):
    uid = member.id
    await connect()
    check = await db.fetchrow(f"SELECT * FROM users WHERE id = $1", uid)
    log(type(check), "DBUG")
    balance = check[3]
    invested = check[5]
    return balance, invested


async def check_bal_str(username: str):
    fuzzy_username = f'%{username}%'
    await connect()
    check = await db.fetchrow(f"SELECT * FROM users WHERE name LIKE $1", fuzzy_username)
    log(check, "DBUG")
    balance = check[3]
    invested = check[5]
    username = check[1]
    await disconnect()
    return balance, invested, username


async def distribute_payouts(bot=None):
    await connect()
    channel = None
    if bot is not None:
        channel = bot.get_channel(731726249868656720)
        if channel is not None:
            await channel.send('Payouts distributed.')
    users = await db.fetch("SELECT * FROM users")
    for user in users:
        # If wealth factor is zero, this bit doesn't give anything.
        payout_generosity = random.random() * wealth_factor  # Normalizes it to give between wf and 2* wf per hour
        investment_payout = int(user[5] * (payout_generosity + wealth_factor))
        # Distribute activity payouts too
        activity_payout = 0
        if user[6] is not None:
            activity_payout = int(user[6]) * actweight
        new_user_balance = int(user[3]) + investment_payout + activity_payout
        if new_user_balance > user[3]:
            log(f'User {user[1]}: activity: {user[6]}, activity_payout: {activity_payout}, investment: {user[5]}, '
                f'investment_payout:'
                f' {investment_payout}, old bal: {user[3]}, new bal: {new_user_balance}', "INFO")
        if channel is not None and new_user_balance > user[3] + 20 * actweight:
            delta = new_user_balance - user[3]
            disp_delta = str(int(delta))
            digits = len(str(delta))
            if digits > 6:
                disp_delta = f'{disp_delta[:-6]}.{disp_delta[-6:-4]}m'
            elif digits > 3:
                disp_delta = f'{disp_delta[:-3]}.{disp_delta[-3:-1]}k'
            await channel.send(f'{user[1]}: +{disp_delta} credits for activity in the past hour.')

        await db.execute(f"UPDATE users SET balance = $1, recent_activity = $2 where id = $3", new_user_balance, 0,
                         user[0])
    await disconnect()


async def check_last_paycheck(user: discord.User):
    uid = user.id
    await connect()
    check = await db.fetchrow(f"SELECT * FROM users WHERE id = $1", uid)
    try:
        last_paycheck = check[4]
    except IndexError:
        return 0
    return last_paycheck


async def set_last_paycheck_now(user: discord.User):
    uid = user.id
    await connect()
    time_now = time.time()
    await db.execute(f"UPDATE users SET last_pay = $1 WHERE id = $2", time_now, uid)
    await disconnect()
    return time_now


async def get_top(cat: str, page: int, user: discord.Member):
    await connect()
    offset = items_per_top_page * (1 - page)
    offset *= -1
    ind = 3
    if cat not in ['balance', 'invested', 'activity', 'n']:
        raise NameError(f'Category {cat} not found.')
    else:
        if cat == 'invested':
            ind = 5
        elif cat == 'activity':
            ind = 2
        elif cat == 'n':
            cat = 'n_word'
            ind = 10
    num_users = await db.fetchval(f"SELECT COUNT(id) FROM users WHERE {cat} IS NOT NULL")
    if num_users < page * items_per_top_page:
        offset = 0
    result = await db.fetch(
        f"""SELECT * FROM users WHERE {cat} IS NOT NULL ORDER BY {cat} DESC LIMIT {items_per_top_page} OFFSET $1""",
        offset)
    tops = []
    num_pages = num_users // items_per_top_page + 1
    for line in result:
        if line[ind] is None:
            line[ind] = 0
        tops.append((line[1], line[ind]))
    subjects_bal = await db.fetchval(f"SELECT {cat} FROM users WHERE id = $1", user.id)
    rank = await db.fetchval(f"SELECT COUNT({cat}) FROM users WHERE {cat} > $1", subjects_bal) + 1
    await disconnect()
    return tops, num_pages, rank


async def add_item(name: str, category: str, picture: str, min_cost: float, max_cost: float, description: str,
                   faction: str):
    await connect()
    await db.execute(f"INSERT INTO items VALUES ($1, $2, $3, $4, $5, $6, $7)",
                     name, category, picture, min_cost, max_cost, description, faction)
    await disconnect()


async def add_commodity_location(name: str, channel_id: int, is_buy: bool, **kwargs):
    await connect()
    query = f"INSERT INTO commodities_locations VALUES ($1, $2, $3 "
    counter = 3
    for _ in kwargs:
        counter += 1
        query += f'${counter}, '
    query = query.rstrip()[:-1] + ')'
    log(query, "DBUG")
    parameters = [name, channel_id, is_buy]
    for value in kwargs.values():
        parameters.append(value)
    log(parameters, "DBUG")
    await db.execute(query, *parameters)
    await disconnect()


async def edit_item(item: str, category: str, new_value: str):
    categories = ['name', 'category', 'picture', 'min_cost', 'max_cost', 'description', 'faction']
    if category not in categories:
        raise NameError(f'Category {category} not found.')
    await connect()
    if category in ['min_cost', 'max_cost']:
        new_value = float(new_value)
    result = await db.fetchrow(f"SELECT * FROM items WHERE name = $1", item)
    if result is None:
        raise NameError(f'Item {item} not in database.')
    await db.execute(f"UPDATE items SET {category} = $1 WHERE name = $2", new_value, item)
    await disconnect()


async def find_item(item: str):
    await connect()
    result = await db.fetchrow(f"SELECT * FROM items WHERE name = $1", item)
    query = f'%{item}%'
    log(f'Exact :{result}', "DBUG")
    if result is None:
        result = await db.fetchrow(f"SELECT * FROM items WHERE name LIKE $1", query)
        log(f'Fuzzy: {result}', "DBUG")
    await disconnect()
    return result


async def find_items_in_cat(item: str):
    await connect()
    query = f'%{item}%'
    result = await db.fetch(f"SELECT * FROM items WHERE category LIKE $1", query)
    await disconnect()
    return result


async def remove_item(item: str):
    await connect()
    await db.execute(f"DELETE FROM items WHERE name = $1", item)
    await disconnect()


def flatten(flatten_list):  # Just a one layer flatten
    new_list = []
    for item in flatten_list:
        for entry in item:
            new_list.append(entry)
    return new_list


async def add_possession(user: discord.Member, item: str, cost: float = 0, amount: float = 1):
    uid = user.id
    await connect()
    unique_key = await db.fetchval(f"SELECT MAX(id) from possessions") + 1
    full_item = await db.fetchrow(f"SELECT * FROM items WHERE name = $1", item)
    # Check if player already owns some of that item
    i_name, i_category, i_picture, i_min_cost, i_max_cost, i_description, i_faction = full_item
    has_amount = await db.fetchval(f"SELECT amount FROM possessions WHERE owner = $1 AND name = $2", uid, item)
    # log(f'{user} currently has {has_amount}x {item}.')
    if has_amount is None:
        # log('has_amount was None.', "DBUG"")
        # log([i_name, i_category, i_picture, i_min_cost, i_max_cost, i_description, i_faction], "DBUG")
        await db.execute(f"INSERT INTO possessions VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
                         unique_key, i_name, uid, amount, i_category, i_picture, cost, i_faction)
    else:
        # log([i_name, i_category, i_picture, i_min_cost, i_max_cost, i_description, i_faction], "DBUG")
        await db.execute(f"UPDATE possessions SET amount = $1 WHERE owner = $2 AND name = $3",
                         amount + has_amount, uid, i_name)
    # log(f'{user} now has {amount + has_amount}x {item}.', "DBUG")
    await disconnect()


async def add_ships_commodities(user: discord.Member, commodity: str, amount: float = 1):
    # TODO: NOT IMPLEMENTED YET, MAY NOT WORK AS EXPECTED
    uid = user.id
    await connect()
    # unique_key = await db.fetchval(f"SELECT MAX(id) FROM ships_commodities") + 1
    capacity = await db.fetchval(f"SELECT capacity FROM ships_commodities WHERE owner = $1", uid)
    has_amount = await db.fetchval(f"SELECT $1 FROM ships_commodities WHERE owner = $2", commodity, uid)
    if amount < 1:
        amount = 0
    if amount > capacity:
        await disconnect()
        raise ValueError
    await db.execute(f"UPDATE ships_commodities SET capacity = $1 WHERE owner = $2", capacity - amount, uid)
    await db.execute(f"UPDATE ships_commodities SET $1 = $2 WHERE owner = $3", commodity, has_amount + amount, uid)
    await disconnect()


async def sell_possession(ctx, user: discord.Member, item: str, amount: int = 1):
    uid = user.id
    await connect()
    full_item = await db.fetchrow(f"SELECT * FROM items WHERE name = $1", item)
    # Check if player already owns some of that item
    i_name, i_category, i_picture, i_min_cost, i_max_cost, i_description, i_faction = full_item
    has_amount = await db.fetchval(f"SELECT amount FROM possessions WHERE owner = $1 AND name = $2", uid, item)
    i_cost = await db.fetchval(f"SELECT cost FROM possessions WHERE owner = $1 AND name = $2", uid, item)
    if has_amount is None:
        await disconnect()
        return await ctx.send(f"You can not sell {item} because you do not have any of them.")
    elif has_amount < amount:
        await disconnect()
        return await ctx.send(
            f"You do not have enough {item}. You are trying to sell {amount} but only have {has_amount}.")
    elif has_amount == amount:
        log(f'Removing: has_amount = {has_amount}, amount = {amount}.')
        balance = await db.fetchval(f"SELECT balance FROM users WHERE id = $1", uid)
        new_balance = balance + (amount * i_cost) * refund_portion
        await db.execute(f"UPDATE users SET balance = $1 WHERE id = $2", new_balance, uid)
        await db.execute(f"DELETE FROM possessions WHERE owner = $1 AND name = $2", uid, item)
    else:
        log(f'Updating: has_amount = {has_amount}, amount = {amount}.')
        balance = await db.fetchval(f"SELECT balance FROM users WHERE id = $1", uid)
        new_balance = balance + (amount * i_cost) * refund_portion
        await db.execute(f"UPDATE users SET balance = $1 WHERE id = $2", new_balance, uid)
        await db.execute(f"UPDATE possessions SET amount = $1 WHERE owner = $2 AND name = $3",
                         has_amount - amount, uid, i_name)
    await disconnect()
    await ctx.send(
        f'{ctx.author} has successfully sold {amount}x {item}, their balance is now {new_balance} credits.')


async def transact_possession(ctx, user: discord.Member, item: str, cost: float = 0, amount: int = 1):
    uid = user.id
    if cost < 0:
        return await ctx.send("Transaction aborted. Cost can't be negative.")
    await connect()
    balance = await db.fetchval(f"SELECT balance FROM users WHERE id = $1", uid)
    max_cost = await db.fetchval(f"SELECT max_cost FROM items WHERE name = $1", item)
    min_cost = await db.fetchval(f"SELECT min_cost FROM items WHERE name = $1", item)
    if max_cost is None:
        await disconnect()
        return await ctx.send(f"Item not found. Remember, you must use the full item name, names are case sensitive, "
                              f"and if you buy more than one the amount goes before the item name.")
    if cost == 0:
        cost = int((max_cost + min_cost) / 2 * 100) / 100
    if not (min_cost <= cost <= max_cost):
        cost = max_cost
        log(f'Cost not in valid range. Using max_cost instead.', "DBUG")
    new_balance = balance - (cost * amount)
    if new_balance < 0:
        await disconnect()
        return await ctx.send(f'Transaction aborted. You do not have sufficient funds. {amount}x {item} costs'
                              f' {cost * amount} but you only have {balance}. You can use the paycheck command to '
                              f'earn a small amount of money or earn more money through roleplay.')
    log(f'Adding {amount}x {item} to {user} for {cost * amount}, their balance is currently {balance} and will'
        f' be {new_balance} after.')
    await add_possession(user, item, cost, amount)
    await connect()  # Because add_possession automatically disconnects
    await db.execute(f"UPDATE users SET balance = $1 where id = $2", new_balance, uid)
    await disconnect()
    plural = 's' if amount != 1 else ''
    await ctx.send(f"{user} has successfully purchased {amount} {item}{plural} for {cost * amount} credits.")
    pass


async def view_items(member: discord.Member):
    await connect()
    items = await db.fetchrow(f"SELECT amount, name FROM possessions WHERE owner = $1", member.id)
    await disconnect()
    log(items, "DBUG")
    return set(items)


async def update_location(member: discord.Member, channel: discord.TextChannel):
    await connect()
    # old_location = await db.fetchval(f"SELECT location FROM users WHERE id = $1", member.id)
    new_location = channel.id
    recent_activity = await db.fetchval(f"SELECT recent_activity FROM users WHERE id = $1", member.id)
    if recent_activity < move_activity_threshold:
        raise ValueError
    await db.execute(f"UPDATE users SET recent_activity = 0 where id = $1", member.id)
    await db.execute(f"UPDATE users SET location = $1 where id = $2", new_location, member.id)


async def send_formatted_browse(ctx, result, i_type):
    if i_type == 'all':
        send = 'The following items are available. You can browse specific ones to see more details:\n```\n'
    else:
        send = f'Items in category {i_type}:\n```\n'
    count = 0
    log(result, "DBUG")
    items = sorted(result, key=lambda x: x['min_cost'])
    log(items, "DBUG")
    max_len = 35
    for item in items:
        item_price = int((float(item[3]) + float(item[4])) / 2 * 100) / 100
        if count < 30:
            send += f'{item[0]}{(max_len - len(item[0])) * " "} ( ~ {item_price} credits)\n'
            count += 1
        else:
            await ctx.send(send)
            send = f'{item[0]}{(max_len - len(item[0])) * " "} ( ~ {item_price} credits\n'
            count = 1
    send += '```'
    await ctx.send(send)


def check_author(author):
    def in_check(message):
        return message.author == author

    return in_check


def copy_bot_vars_to_local(bot):
    global starting_balance
    global wealth_factor
    global items_per_top_page
    global refund_portion
    global move_activity_threshold
    global AUTH_LOCKDOWN
    global actweight
    starting_balance = bot.STARTING_BALANCE
    wealth_factor = bot.WEALTH_FACTOR
    items_per_top_page = bot.ITEMS_PER_TOP_PAGE
    refund_portion = bot.REFUND_PORTION
    move_activity_threshold = bot.MOVE_ACTIVITY_THRESHOLD
    AUTH_LOCKDOWN = bot.AUTH_LOCKDOWN
    actweight = bot.ACTIVITY_WEIGHT


class Database(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.session = None
        copy_bot_vars_to_local(bot)

    # Events
    @commands.Cog.listener()
    async def on_ready(self):
        log(f'Loading {self.qualified_name}...', self.bot.debug)
        self.session = aiohttp.ClientSession(loop=self.bot.loop)
        await connect()
        # cursor.execute("SHOW DATABASES")
        # databases = cursor.fetchall()
        # log(f"Databases: {databases}", self.bot.debug)
        # cursor.execute("DROP TABLE users")
        tables = str(
            await db.fetch("SELECT * FROM pg_catalog.pg_tables WHERE schemaname != 'pg_catalog' AND schemaname "
                           "!='information_schema'"))
        log(f'I have the following tables:\n{tables}', self.bot.debug)
        if 'settings' not in tables:
            log('Settings table not found. Creating a new one...')
            await db.execute("CREATE TABLE settings( "
                             "id BIGINT NOT NULL PRIMARY KEY, "
                             "cooldown INT,"
                             "amount DOUBLE PRECISION,"
                             "starting DOUBLE PRECISION,"
                             "actweight DOUBLE PRECISION)")
            await db.execute("INSERT INTO settings VALUES($1, $2, $3, $4, $5)",
                             1, self.bot.PAYCHECK_INTERVAL, self.bot.PAYCHECK_AMOUNT_MAX, self.bot.STARTING_BALANCE,
                             self.bot.ACTIVITY_WEIGHT)
            log('Saved default settings to database.')
            await disconnect()
            await connect()
        else:
            settings = await db.fetchrow("SELECT * FROM settings WHERE id = 1")
            log(settings, self.bot.debug)
            self.bot.PAYCHECK_INTERVAL = settings[1]
            self.bot.PAYCHECK_AMOUNT_MAX = settings[2]
            self.bot.PAYCHECK_AMOUNT_MIN = settings[2]
            self.bot.STARTING_BALANCE = settings[3]
            self.bot.ACTIVITY_WEIGHT = settings[4]
            copy_bot_vars_to_local(self.bot)
            log(f'Loaded settings from database: {settings}', self.bot.debug)
        if 'users' not in tables:
            log('Users table not found. Creating a new one...')
            await db.execute("CREATE TABLE users( "
                             "id BIGINT NOT NULL PRIMARY KEY, "
                             "name VARCHAR (255), "
                             "activity BIGINT, "
                             "balance DOUBLE PRECISION, "
                             "last_pay BIGINT,"
                             "invested DOUBLE PRECISION,"
                             "recent_activity BIGINT,"
                             "location BIGINT,"
                             "cargo_kg_capacity DOUBLE PRECISION,"
                             "cargo_kg DOUBLE PRECISION,"
                             "n_word BIGINT)"
                             )
            # await disconnect()
            # await connect()
        if 'items' not in tables:
            log('Items table not found. Creating a new one...')
            await db.execute("CREATE TABLE items( "
                             "name VARCHAR (127) NOT NULL PRIMARY KEY, "
                             "category VARCHAR (127), "
                             "picture VARCHAR (255), "
                             "min_cost DOUBLE PRECISION, "
                             "max_cost DOUBLE PRECISION, "
                             "description VARCHAR (2048), "
                             "faction VARCHAR (127))"
                             )
            # await disconnect()
            # await connect()
        if 'possessions' not in tables:
            log('Possessions table not found. Creating a new one...')
            await db.execute("CREATE TABLE possessions("
                             "id INT NOT NULL PRIMARY KEY, "
                             "name VARCHAR (127) REFERENCES items(name), "
                             "owner BIGINT REFERENCES users(id), "
                             "amount INT, "
                             "category VARCHAR (127), "
                             "picture VARCHAR (127), "
                             "cost DOUBLE PRECISION, "
                             "faction VARCHAR (127))"
                             )
        # await disconnect()
        # await connect()
        users_config = await db.fetch("SELECT COLUMN_NAME from information_schema.COLUMNS WHERE TABLE_NAME = 'users' ")
        log(f'My Users table is configured thusly: {users_config}', self.bot.debug)
        users = await db.fetch("SELECT * FROM users")
        log(f'Users: {users}', self.bot.debug)
        self.bot.list_of_users = [user['id'] for user in users]
        log(repr(self.bot.list_of_users), self.bot.debug)
        await disconnect()
        logready(self)

    def cog_unload(self):
        log(f"Closing {self.qualified_name} cog.", self.bot.prio)
        try:
            db.terminate()
        except NameError:
            pass
        try:
            self.session.close()
        except AttributeError:
            log(f'AttributeError trying to close aiohttp session at {now()}', self.bot.warn)
            pass

    @commands.command(description='Prints the list of users to the console.')
    @commands.check(auth(max(4, AUTH_LOCKDOWN)))
    async def listusers(self, ctx):
        await connect()
        users = await db.fetch("SELECT * FROM users")
        await disconnect()
        log(f'The list of users was requested by a command. Here it is: {users}', self.bot.prio)
        names = [user[1] for user in users]
        num_users = len(users)
        await ctx.send(
            f'The list of {num_users} users has been printed to the console. Here are their names only:\n'
            f'{str(names)[0:1800]}')
        log(f'The users command was used by {ctx.author}.', self.bot.cmd)

    @commands.command(description='Does a direct database query.')
    @commands.check(auth(max(8, AUTH_LOCKDOWN)))
    async def directq(self, ctx, *, query):
        """
        Does a direct database query. Not quite as dangerous as eval, but still restricted to Auth 8.
        """
        await connect()
        add_text = ''
        try:
            result = await db.fetch(query)
            await disconnect()
            await ctx.send(result)
            add_text = f'Result was:\n{result}'
        except conn.InterfaceError:
            await ctx.send("Okay. There's no result from that query.")
        log(f'{ctx.author} executed a direct database query:\n{query}\n{add_text}', self.bot.cmd)

    @commands.command(description='add new user to database')
    @commands.check(auth(max(2, AUTH_LOCKDOWN)))
    async def newuser(self, ctx, user: discord.User):
        """
        Add a new user to the database.
        """
        result = await new_user(user)
        log(result, self.bot.debug)
        await ctx.send(result)
        log(f'{ctx.author} added new user {user} to the database.', self.bot.cmd)

    @commands.command(aliases=['additem'], description='add a new item to the database')
    @commands.check(auth(max(3, AUTH_LOCKDOWN)))
    async def newitem(self, ctx, *, content):
        """
        Add a new item to the database. Each property must be on a new line.
        Item Properties
        ID (internal, you need not add)
        Name (max length 127)
        Category (ship, weapon, etc, max length 127)
        Picture (direct link to the .png, max length 255)
        Min_cost (minimum reasonable cost for this item anywhere, whole number)
        Max_cost (maximum reasonable cost for this item anywhere, whole number)
        Description (One to five sentences or so, strive to be funny. max length 300)
        Faction (One of the faction names or NONE for available to all factions)
        """
        item = content.split('\n')
        log(f"Adding item {item[0]} by request of {ctx.author}: {item}", self.bot.cmd)
        try:
            await add_item(item[0], item[1], item[2], float(item[3]), float(item[4]), item[5], item[6])
        except ValueError:
            return await ctx.send(f'Incorrect format. Remember each item must be on its own line, and the minimum '
                                  f'and maximum prices must be numbers. Check your formatting and try again.')
        except IndexError:
            return await ctx.send(f'Incorrect format. Remember each item must be on its own line, and the minimum '
                                  f'and maximum prices must be numbers. Check your formatting and try again.')
        # return await ctx.send('An item with that name is already in the database.')
        await ctx.send(f'Added {item[0]} to the database.')

    @commands.command(aliases=['addlocation'], description=f'Add a new location to the database. \nChannel is a '
                                                           f'channel mention for this shop, and is_buy is TRUE for'
                                                           f' purchase costs, FALSE for sell costs. Each value must'
                                                           f' be a kwarg from: {COMMODITIES}')
    @commands.check(auth(3))
    async def newlocation(self, ctx, name: str, channel: discord.TextChannel, is_buy: bool, *, in_values: str):
        values = in_values.split(' ')
        kwargs = {}
        for tic in values:
            item, value = tic.split('=')
            kwargs[item] = float(value)
        log(f"Adding location {name} by request of {ctx.author}: {kwargs}", self.bot.cmd)
        try:
            await add_commodity_location(name, channel.id, is_buy, **kwargs)
        except ValueError:
            return await ctx.send(f'Incorrect format. (1)')
        except IndexError:
            return await ctx.send(f'Incorrect format. (2)')
        # return await ctx.send('A location with that name is already in the database.')
        await ctx.send(f'Added {name} to the database.')

    @commands.command(aliases=['removeitem'], description='Remove an item from the database')
    @commands.check(auth(max(4, AUTH_LOCKDOWN)))
    async def deleteitem(self, ctx, *, item: str):
        """
        Remove an item from the database. Requires Auth 4.
        """
        await ctx.send(
            f"Are you sure you want to remove {item} from the database? Respond with 'y' within 20 seconds to confirm.")
        try:
            response = await self.bot.wait_for('message', check=lambda x: x.author == ctx.author, timeout=20)
        except asyncio.TimeoutError:
            return await ctx.send('Delete cancelled.')
        if response.content is not 'y':
            return await ctx.send('Delete cancelled.')
        log(f"Removing item {item} by request of {ctx.author}.", self.bot.cmd)
        await remove_item(item)
        await ctx.send(f'Successfully removed {item} from the database.')

    @commands.command(aliases=['updateitem'], description='Edit a value of an item in the database.')
    @commands.check(auth(max(4, AUTH_LOCKDOWN)))
    async def edititem(self, ctx, item: str, field: str, value: str):
        """Edit a value of an item in the database.
        """
        await connect()
        try:
            await edit_item(item, field, value)
            await ctx.send(f'Updated {item}.')
            log(f'Updated item {item} field {field} to value {value} by request of {ctx.author}.', self.bot.cmd)
        except NameError:
            await ctx.send(f'Category not found. Categories are case sensitive, double check!')
            log(f'Failed to update item {item} field {field} to value {value} for {ctx.author}.', self.bot.cmd)

    @commands.command(description='Adjust bot settings')
    async def settings(self, ctx, setting: str, value: str):
        """Adjust bot settings.
        Setting must be one of: 'cooldown', 'amount', 'starting', 'actweight'
        Cooldown: the number of seconds between paychecks
        Amount: the amount of credits per paycheck
        Starting: the amount of credits a brand new player starts with
        Actweight: The number of credits to pay out per internal bot "activity point"
        """
        if ctx.author.id not in self.bot.settings_modifiers:
            return await ctx.send(f"You do not have permission to run this command.")
        config_opts = ['cooldown', 'amount', 'starting', 'actweight']
        if setting not in config_opts:
            return await ctx.send(f"Sorry, that isn't a configurable setting. Try one of {config_opts}.")
        if setting == 'cooldown':
            value = int(value)
            self.bot.PAYCHECK_INTERVAL = value
        elif setting == 'amount':
            value = round(float(value), 2)
            self.bot.PAYCHECK_AMOUNT_MAX = value
            self.bot.PAYCHECK_AMOUNT_MIN = value
        elif setting == 'starting':
            value = round(float(value), 2)
            self.bot.STARTING_BALANCE = value
        elif setting == 'actweight':
            value = round(float(value), 2)
            self.bot.ACTIVITY_WEIGHT = value
        await connect()
        await db.execute(f"UPDATE settings SET {setting} = $1 WHERE id = 1", value)
        await disconnect()
        await ctx.send(f'Okay, {setting} set to {value}.')
        log(f'Updated {setting} to {value} for {ctx.author}.', self.bot.cmd)

    @commands.command(description='Reset the economy entirely.')
    async def wipe_the_whole_fucking_economy_like_seriously(self, ctx):
        """Set everyone's balance to the configured starting balance and activity to 0. Several safeguards are in
        place."""
        if ctx.author.id not in self.bot.settings_modifiers:
            return await ctx.send(f"You do not have permission to run this command.")
        confirmation_phrase = "I understand I am wiping the whole economy"
        await ctx.send(f"This will reset **everyone's** balance to {self.bot.STARTING_BALANCE} and activity to 0. "
                       f"This is not reversible. If you are sure, type "
                       f"`{confirmation_phrase}`\nTo be safe, it must match exactly. You have 30 seconds,"
                       f" or this command will cancel without running.")
        try:
            confirmation = await self.bot.wait_for('message', check=check_author(ctx.author), timeout=30)
        except asyncio.TimeoutError:
            return await ctx.send(f"Cancelled operation: Took longer than 30 seconds to respond.")
        if confirmation.content != confirmation_phrase:
            return await ctx.send(f"Cancelled operation: Phrase did not match `{confirmation_phrase}`.")
        await connect()
        await db.execute(f"UPDATE users SET balance = $1, activity = 0, last_pay = 0, invested = 0,"
                         f" recent_activity= 0", self.bot.STARTING_BALANCE)
        await disconnect()
        await ctx.send(f"Successfully reset everyone's balance to {self.bot.STARTING_BALANCE}")
        log(f'Reset all balances to {self.bot.STARTING_BALANCE} by request of {ctx.author}.', self.bot.cmd)
        log(f'Reset all balances to {self.bot.STARTING_BALANCE} by request of {ctx.author}.', self.bot.prio)

    @commands.command(description='browse the shop')
    @commands.check(auth(AUTH_LOCKDOWN))
    async def browse(self, ctx, *, item: str = None):
        """
        Browse the items available for sale.
        You can also specify a category to list the items of that type, or a specific item to see more details
         on that item, including a picture.
        """
        log(f'{ctx.author} used the browse command for {item}.')
        await connect()
        if item is None:
            result = await db.fetch("SELECT DISTINCT category from items")
            categories = sorted(list(set(flatten([item[0].split(', ') for item in result]))))
            log(repr(categories), self.bot.debug)
            send = f'Here are the categories of items available. You can browse each category (case sensitive) to ' \
                   f'list the items in it, or you can browse all to see every item in the shop.\n '
            send += '=' * 20 + '\n'
            for category in categories:
                send += f'{category}\n'
            await ctx.send(send)
            log(repr(categories), self.bot.debug)
            return
            pass
        elif item == 'all':
            result = await db.fetch("SELECT * FROM items")
            await send_formatted_browse(ctx, result, 'all')
            await disconnect()
            return
        item = item.title()
        # See if the keyword is a category
        results_in_category = await(find_items_in_cat(item))
        if len(results_in_category) > 0:  # If it is a category, display category
            await disconnect()
            return await send_formatted_browse(ctx, results_in_category, item)
        # No we know its a specific item, find it
        result = await find_item(item)
        if result is None:
            return await ctx.send('Item not found.')
        log(result, self.bot.debug)
        av_cost = int((float(result[3]) + float(result[4])) / 2 * 100) / 100
        async with aiohttp.ClientSession() as session:  # Load image from link. TODO: Download and save image instead
            async with session.get(result[2]) as resp:
                buffer = BytesIO(await resp.read())
            await session.close()
        await ctx.send(f"__**{result[0]}**__ ({result[1]})"
                       f"\n**Cost:** {av_cost} credits:"
                       f"\n> {result[5]}", file=discord.File(fp=buffer, filename='file.jpg'))


def setup(bot_o):
    bot_o.add_cog(Database(bot_o))
