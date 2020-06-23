import asyncio
import random
import time
import aiohttp
from io import BytesIO

import discord
from discord.ext import commands
# import psycopg2 as conn
import asyncpg as conn
from functions import auth, now
from privatevars import DBUSER, DBPASS

global db

commodities = ['hydrogen', 'deuterium', 'tritium', 'helium', 'nitrogen', 'phosphorous', 'iodine', 'lithium',
               'magnesium', 'aluminum', 'silicon', 'titanium', 'vanadium', 'chromium',
               'cobalt', 'nickel', 'copper', 'neodymium', 'tungsten',
               'rhodium', 'silver', 'osmium', 'iridium', 'platinum', 'gold',
               'plutonium', 'americium',
               'methane', 'ammonia', 'water',
               'methamphetamine', 'heroin', 'cocaine', 'lsd',
               'painite', 'diamond', 'ruby', 'emerald', 'taaffeite',
               'processors_50a', 'processors_14a', 'processors_10a', 'processors_7a',
               'cotton', 'grain', 'milk', 'cocoa', 'salt', 'sugar', 'rubber',
               'steel', 'carbon_fiber', 'plastic', 'biosamples', 'wood',
               'saffron', 'coffee', 'pepper', 'cinnamon',
               'graphene', 'aerogel', 'cermets', 'm_glass', 'mol_glue', 'nanofibers', 'fullerenes', 'nanotubes',
               'h_fuel', 'antimatter']

# carbon-carbon bond average length is 1.54 a = 0.154 nm. Molecular superglue is mol-glue.
# aluminum oxynitride is m-glass. Metallic hydrogen is h-fuel.

async def connect():
    global db
    try:
        db = await conn.connect(
            host='localhost',
            user=DBUSER,
            password=DBPASS,
            database='startrade'
        )
        # print('Connected to database.')
    except:
        print(f'An unexpected error occurred when trying to connect to the database for connect() at {now()}.')
        pass


async def disconnect():
    try:
        await db.commit()
    except AttributeError:
        pass  # There was no need to commit
    await db.close()


async def new_user(user: discord.User):
    uid = user.id
    name = user.name
    messages = 0
    balance = 30000
    last_pay = time.time() - 1800
    invested = 0
    await connect()
    check = await db.fetchrow(f"SELECT * FROM users WHERE id = $1", uid)
    if check is not None:
        return f'User {name} Already Exists in database.'
    try:
        await db.execute(
            "INSERT INTO users VALUES($1, $2, $3, $4, $5, $6)", uid, name, messages, balance, last_pay, invested)
    except conn.errors.UniqueViolation:
        await db.commit()
        await connect()
        await db.execute("UPDATE users SET name = $1 WHERE id = $2", name, uid)
    await disconnect()
    return f'User {name} added to database at {now()}.'


async def add_invest(user: discord.User, amount: int):
    uid = user.id
    await connect()
    check = await db.fetchrow(f"SELECT * FROM users WHERE id = $1", uid)
    invested = check[5]
    balance = check[3]
    if check is None:
        return -1, 0, 0
    print(f'{invested}, {amount}')
    if int(amount) > int(balance):
        return -2, 0, 0
    await db.execute(f"UPDATE users SET invested = $1 where id = $2", int(invested) + int(amount), uid)
    await db.execute(f"UPDATE users SET balance = $1 where id = $2", int(balance) - int(amount), uid)
    await disconnect()
    return amount, int(invested) + int(amount), int(balance) - int(amount)


async def transfer_funds(from_user: discord.User, to_user: discord.User, amount: int):
    uid_from = from_user.id
    uid_to = to_user.id
    await connect()
    from_balance = (await db.fetchrow(f"SELECT balance FROM users WHERE id = $1", uid_from))[0]
    to_balance = (await db.fetchrow(f"SELECT balance FROM users WHERE id = $1", uid_to))[0]
    print(f'Transferring {amount} from {from_user} to {to_user} at {now()}.')
    to_balance = int(to_balance) + int(amount)
    from_balance = int(from_balance) - int(amount)
    if int(from_balance) < 0:
        return -1, 0
    await db.execute(f"UPDATE users SET balance = $1 where id = $2", from_balance, uid_from)
    await db.execute(f"UPDATE users SET balance = $1 where id = $2", to_balance, uid_to)
    await disconnect()
    return from_balance, to_balance


async def update_activity(member: discord.Member, amount: int):
    uid = member.id
    await connect()
    activity = (await db.fetchrow(f"SELECT activity FROM users WHERE id = $1", uid))[0] + amount
    print(f'Adding {amount} activity score to {member} at {now()}. New activity score: {activity}')
    await db.execute(f"UPDATE users SET activity = $1 where id = $2", activity, uid)
    await disconnect()


async def add_funds(user: discord.User, amount: int):
    uid = user.id
    await connect()
    result = await db.fetchrow(f"SELECT balance FROM users WHERE id = $1", uid)
    balance = result[0]
    print(f'Adding {amount} to {user} with Staff authority at {now()}.')
    balance += amount
    await db.execute(f"UPDATE users SET balance = $1 where id = $2", balance, uid)
    await disconnect()
    return balance


async def check_bal(user: discord.User):
    uid = user.id
    await connect()
    check = await db.fetchrow(f"SELECT * FROM users WHERE id = $1", uid)
    print(type(check))
    balance = check[3]
    invested = check[5]
    return balance, invested


async def check_bal_str(username: str):
    fuzzy_username = f'%{username}%'
    await connect()
    check = await db.fetchrow(f"SELECT * FROM users WHERE name LIKE $1", fuzzy_username)
    print(check)
    balance = check[3]
    invested = check[5]
    username = check[1]
    await disconnect()
    return balance, invested, username


async def distribute_payouts():
    WEALTH_FACTOR = 0.0005
    await connect()
    users = await db.fetch("SELECT * FROM users")
    for user in users:
        payout_generosity = random.random() / 2000  # Normalizes it to give between 0.05% and 0.1% payout each time
        payout = int(user[5] * (payout_generosity + WEALTH_FACTOR))
        new_user_balance = int(user[3]) + payout
        # print(f'User {user[1]}: investment: {user[5]}, payout_generosity: {payout_generosity * 1000}, payout:'
        #       f' {payout}, new bal: {user[3]}')
        await db.execute(f"UPDATE users SET balance = $1 where id = $2", new_user_balance, user[0])
    await disconnect()


async def check_last_paycheck(user: discord.User):
    uid = user.id
    await connect()
    check = await db.fetchrow(f"SELECT * FROM users WHERE id = $1", uid)
    last_paycheck = check[4]
    return last_paycheck


async def set_last_paycheck_now(user: discord.User):
    uid = user.id
    await connect()
    time_now = time.time()
    await db.execute(f"UPDATE users SET last_pay = $1 WHERE id = $2", time_now, uid)
    await disconnect()
    return time_now


async def get_top(cat: str, page: int):
    await connect()
    offset = 10 * (1 - page)
    if cat not in ['balance', 'invested', 'activity']:
        raise NameError(f'Category {cat} not found.')
    else:
        if cat == 'balance':
            ind = 3
        elif cat == 'invested':
            ind = 5
        elif cat == 'activity':
            ind = 2
    result = await db.fetchrow(f"SELECT COUNT(id) FROM users")
    num_users = result[0]
    if num_users < page * 10:
        offset = 0
    result = await db.fetch(f"""SELECT * FROM users ORDER BY {cat} DESC LIMIT 10 OFFSET $1""", offset)
    tops = []
    for line in result:
        tops.append((line[1], line[ind]))
    await disconnect()
    return tops


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
    for kwarg in kwargs:
        counter += 1
        query += f'${counter}, '
    query = query.rstrip()[:-1] + ')'
    print(query)
    parameters = [name, channel_id, is_buy]
    for value in kwargs.values():
        parameters.append(value)
    print(parameters)
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
    print(f'Exact :{result}')
    if result is None:
        result = await db.fetchrow(f"SELECT * FROM items WHERE name LIKE $1", query)
        print(f'Fuzzy: {result}')
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
    has_amount = await db.fetchval(f"SELECT id FROM possessions WHERE owner = $1 AND name = $2", uid, item)
    if has_amount is None:
        print([i_name, i_category, i_picture, i_min_cost, i_max_cost, i_description, i_faction])
        await db.execute(f"INSERT INTO possessions VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
                         unique_key, i_name, uid, amount, i_category, i_picture, cost, i_faction)
    else:
        print([i_name, i_category, i_picture, i_min_cost, i_max_cost, i_description, i_faction])
        await db.execute(f"UPDATE possessions SET amount = $1 WHERE owner = $2 AND name = $3",
                         amount + has_amount, uid, i_name)
    await disconnect()


async def sell_possession(ctx, user: discord.Member, item: str, amount: int = 1):
    REFUND_PORTION = 0.6
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
        print(f'Removing: has_amount = {has_amount}, amount = {amount}.')
        balance = await db.fetchval(f"SELECT balance FROM users WHERE id = $1", uid)
        new_balance = balance + (amount * i_cost) * REFUND_PORTION
        await db.execute(f"UPDATE users SET balance = $1 WHERE id = $2", new_balance, uid)
        await db.execute(f"DELETE FROM possessions WHERE owner = $1 AND name = $2", uid, item)
    else:
        print(f'Updating: has_amount = {has_amount}, amount = {amount}.')
        balance = await db.fetchval(f"SELECT balance FROM users WHERE id = $1", uid)
        new_balance = balance + (amount * i_cost) * REFUND_PORTION
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
        print(f'Cost not in valid range. Using max_cost instead.')
    new_balance = balance - (cost * amount)
    if new_balance < 0:
        await disconnect()
        return await ctx.send(f'Transaction aborted. You do not have sufficient funds. {item} costs {cost} but you '
                              f'only have {balance}. You can use the paycheck command to earn a small amount of money '
                              f'or earn more money through roleplay.')
    await add_possession(user, item, cost, amount)
    await connect()  # Because add_possession automatically disconnects
    await db.execute(f"UPDATE users SET balance = $1 where id = $2", new_balance, uid)
    await disconnect()
    plural = 's' if amount != 1 else ''
    await ctx.send(f"{user} has successfully purchased {amount} {item}{plural} for {cost * amount} credits.")
    pass


async def view_items(member: discord.Member):
    await connect()
    items = await db.fetch(f"SELECT amount, name FROM possessions WHERE owner = $1", member.id)
    await disconnect()
    print(items)
    return set(items)


async def send_formatted_browse(ctx, result, i_type):
    if i_type == 'all':
        send = 'The following items are available. You can browse specific ones to see more details:\n```\n'
    else:
        send = f'Items in category {i_type}:\n```\n'
    count = 0
    print(result)
    items = sorted(result, key=lambda x: x['min_cost'])
    print(items)
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


class Database(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.bot.commodities = commodities
        self.session = aiohttp.ClientSession(loop=bot.loop)

    # Events
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'Loading Cog {self.qualified_name}...')
        await connect()
        # cursor.execute("SHOW DATABASES")
        # databases = cursor.fetchall()
        # print(f"Databases: {databases}")
        # cursor.execute("DROP TABLE users")
        tables = str(
            await db.fetch("SELECT * FROM pg_catalog.pg_tables WHERE schemaname != 'pg_catalog' AND schemaname "
                           "!='information_schema'"))
        # print(f'I have the following tables:\n{tables}')
        if 'users' not in tables:
            print('Users table not found. Creating a new one...')
            await db.execute("CREATE TABLE users( "
                             "id BIGINT NOT NULL PRIMARY KEY, "
                             "name VARCHAR (255), "
                             "activity BIGINT, "
                             "balance DOUBLE PRECISION, "
                             "last_pay BIGINT,"
                             "invested DOUBLE PRECISION)"
                             )
            await disconnect()
            await connect()
        if 'items' not in tables:
            print('Items table not found. Creating a new one...')
            await db.execute("CREATE TABLE items( "
                             "name VARCHAR (127) NOT NULL PRIMARY KEY, "
                             "category VARCHAR (127), "
                             "picture VARCHAR (255), "
                             "min_cost DOUBLE PRECISION, "
                             "max_cost DOUBLE PRECISION, "
                             "description VARCHAR (2048), "
                             "faction VARCHAR (127))"
                             )
            await disconnect()
            await connect()
        if 'possessions' not in tables:
            print('Possessions table not found. Creating a new one...')
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
        await disconnect()
        await connect()
        if 'commodities' not in tables:
            print('Commodities table not found. Creating a new one...')
            commodities_creation_command = "CREATE TABLE commodities_locations(name VARCHAR(127) NOT NULL" \
                                           " PRIMARY KEY, channel_id BIGINT, type BOOL, "
            for commodity in commodities:
                commodities_creation_command += f'{commodity} DOUBLE PRECISION, '
            commodities_creation_command = commodities_creation_command.rstrip()[:-1] + ')'  # Get rid of final comma
            # and add closing bracket
            await db.execute(commodities_creation_command)
        users_config = await db.fetch("SELECT COLUMN_NAME from information_schema.COLUMNS WHERE TABLE_NAME = 'users' ")
        print(f'My Users table is configured thusly:\n{users_config}')
        # users = await db.fetch("SELECT * FROM users")
        # print(f'Users:\n{users}')
        await disconnect()
        print(f'Cog {self.qualified_name} is ready.')

    def cog_unload(self):
        print(f"Closing {self.qualified_name} cog.")
        try:
            db.terminate()
        except NameError:
            pass
        try:
            self.session.terminate()
        except AttributeError:
            pass

    @commands.command(description='Prints the list of users to the console.')
    @commands.check(auth(4))
    async def listusers(self, ctx):
        await connect()
        users = await db.fetch("SELECT * FROM users")
        await disconnect()
        print(f'Users: {users}')
        names = [user[1] for user in users]
        num_users = len(users)
        await ctx.send(
            f'The list of {num_users} users has been printed to the console. Here are their names only:\n{names}')

    @commands.command(description='Does a direct database query.')
    @commands.check(auth(8))
    async def directq(self, ctx, *, query):
        """
        Does a direct database query. Not quite as dangerous as eval, but still restricted to Auth 8.
        """
        await connect()
        try:
            result = await db.fetch(query)
        except conn.InterfaceError:
            await ctx.send("Okay. There's no result from that query.")
        await disconnect()
        await ctx.send(result)
        print(f'{ctx.author} executed a direct database query at {now()}:\n{query}\nResult was:\n{result}')

    @commands.command(description='add new user to database')
    @commands.check(auth(2))
    async def newuser(self, ctx, user: discord.User):
        """
        Add a new user to the database.
        """
        result = await new_user(user)
        print(result)
        await ctx.send(result)

    @commands.command(aliases=['additem'], description='add a new item to the database')
    @commands.check(auth(3))
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
        print(f"Adding item {item[0]} by request of {ctx.author}: {item}")
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
                                                           f' be a kwarg from: {commodities}')
    @commands.check(auth(3))
    async def newlocation(self, ctx, name: str, channel: discord.TextChannel, is_buy: bool, *, in_values: str):
        values = in_values.split(' ')
        kwargs = {}
        for tic in values:
            item, value = tic.split('=')
            kwargs[item] = float(value)
        print(f"Adding location {name} by request of {ctx.author}: {kwargs}")
        try:
            await add_commodity_location(name, channel.id, is_buy, **kwargs)
        except ValueError:
            return await ctx.send(f'Incorrect format. (1)')
        except IndexError:
            return await ctx.send(f'Incorrect format. (2)')
        # return await ctx.send('A location with that name is already in the database.')
        await ctx.send(f'Added {name} to the database.')

    @commands.command(aliases=['removeitem'], description='Remove an item from the database')
    @commands.check(auth(4))
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
        print(f"Removing item {item} by request of {ctx.author}.")
        await remove_item(item)
        await ctx.send(f'Successfully removed {item} from the database.')

    @commands.command(aliases=['updateitem'], description='Edit a value of an item in the database.')
    @commands.check(auth(4))
    async def edititem(self, ctx, item: str, field: str, value: str):
        """Edit a value of an item in the database.
        """
        print(f"Updating item {item} field {field} to value {value} by request of {ctx.author}.")
        await connect()
        try:
            await edit_item(item, field, value)
            await ctx.send(f'Updated {item}.')
        except NameError:
            await ctx.send(f'Category not found. Categories are case sensitive, double check!')

    @commands.command(description='browse the shop')
    async def browse(self, ctx, *, item: str = None):
        """
        Browse the items available for sale.
        You can also specify a category to list the items of that type, or a specific item to see more details
         on that item, including a picture.
        """
        await connect()
        if item is None:
            result = await db.fetch("SELECT DISTINCT category from items")
            categories = sorted(list(set(flatten([item[0].split(', ') for item in result]))))
            print(categories)
            send = f'Here are the categories of items available. You can browse each category (case sensitive) to ' \
                   f'list the items in it, or you can browse all to see every item in the shop.\n '
            send += '=' * 20 + '\n'
            for category in categories:
                send += f'{category}\n'
            await ctx.send(send)
            print(categories)
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
        print(result)
        av_cost = int((float(result[3]) + float(result[4])) / 2 * 100) / 100
        async with aiohttp.ClientSession() as session:  # Load image from link. TODO: Download and save image instead
            async with session.get(result[2]) as resp:
                buffer = BytesIO(await resp.read())
            await session.close()
        await ctx.send(f"__**{result[0]}**__ ({result[1]})"
                       f"\n**Cost:** {av_cost} credits:"
                       f"\n> {result[5]}", file=discord.File(fp=buffer, filename='file.jpg'))


def setup(bot):
    bot.add_cog(Database(bot))
