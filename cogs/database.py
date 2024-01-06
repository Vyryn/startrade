import asyncio
import random
import time
from typing import Optional
from functools import wraps

import aiohttp  # pylint: disable=import-error
from io import BytesIO

import discord  # pylint: disable=import-error
from discord.ext import commands  # pylint: disable=import-error
from bot import log, logready
import asyncpg as conn  # pylint: disable=import-error
from asyncpg.exceptions import (  # pylint: disable=import-error
    InternalClientError,
    InterfaceError,
    StringDataRightTruncationError,
    PostgresError,
)
from functions import auth, now, level
from privatevars import DBUSER, DBPASS  # pylint: disable=import-error

# Lazily scoped
# These globals are based on the bot attributes of the same names in init and on_ready.
# These are just "default default values", and normally aren't used.
starting_balance = 50000000
wealth_factor = 0
items_per_top_page = 10
refund_portion = 0.9
move_activity_threshold = 100
actweight = 10000
AUTH_LOCKDOWN = 1
COMMODITIES = {}


# Handle database connection pool with dependency injection====
global pool
pool = None


async def create_db_pool():
    global pool
    pool = await conn.create_pool(
        host="localhost", user=DBUSER, password=DBPASS, database="gnk"
    )
    return pool


def with_db(func):
    """Decorator for database functions that injects a pool connection object and automatically commits if the function didn't, or rolls back if the function raises an exception."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        global pool
        if not pool:
            pool = await create_db_pool()
        async with pool.acquire() as db:
            transaction = db.transaction()
            await transaction.start()
            try:
                result = await func(db, *args, **kwargs)
                await transaction.commit()
                return result
            except:
                await transaction.rollback()
                raise

    return wrapper


@with_db
async def new_user(db, user: discord.User):
    uid = user.id
    name = user.name
    activity = 0
    balance = starting_balance
    last_pay = (
        time.time() - 31536000
    )  # Set last payout time to a year ago to allow immediate paycheck
    invested = 0
    networth = balance
    check = await db.fetchrow("SELECT * FROM users WHERE id = $1", uid)
    print(f"Moving on: {check}")
    if check is not None:
        return f"User {name} Already Exists in database."
    try:
        await db.execute(
            "INSERT INTO users VALUES($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)",
            uid,
            name,
            activity,
            balance,
            last_pay,
            invested,
            0,
            0,
            networth,
            0,
            0,
        )
        result = f"User {name} added to database at {now()}."
    except conn.UniqueViolationError:
        await db.execute("UPDATE users SET name = $1 WHERE id = $2", name, uid)
        result = f"User {name} name updated in database at {now()}."
    return result


@with_db
async def add_invest(db, user: discord.User, amount: float):
    uid = user.id
    check = await db.fetchrow("SELECT * FROM users WHERE id = $1", uid)
    try:
        invested = check[5]
    except AttributeError:
        invested = 0
    balance = check[3]
    if check is None:
        return -1, 0, 0
    log(f"{invested}, {amount}", "DBUG")
    if float(amount) > float(balance):
        return -2, 0, 0
    await db.execute(
        "UPDATE users SET invested = $1, balance = $2 where id = $3",
        float(invested) + float(amount),
        float(balance) - float(amount),
        uid,
    )
    return amount, float(invested) + float(amount), float(balance) - float(amount)


@with_db
async def transfer_funds(
    db, from_user: discord.User, to_user: discord.User, amount: float
):
    uid_from = from_user.id
    uid_to = to_user.id
    tr = db.transaction()
    await tr.start()
    try:
        query = """
        UPDATE users 
        SET 
            balance = CASE 
                        WHEN id = $1 THEN balance + $3
                        WHEN id = $2 THEN balance - $3
                      END,
            networth = CASE 
                        WHEN id = $1 THEN networth + $3
                        WHEN id = $2 THEN networth - $3
                       END
        WHERE id IN ($1, $2)
        """

        await db.execute(query, uid_to, uid_from, amount)

        await tr.commit()

        from_balance = (
            await db.fetchrow("SELECT balance FROM users WHERE id = $1", uid_from)
        )[0]
        to_balance = (
            await db.fetchrow("SELECT balance FROM users WHERE id = $1", uid_to)
        )[0]
    except (PostgresError, InterfaceError):
        await tr.rollback()
        raise
    return from_balance, to_balance


@with_db
async def update_activity(db, user: discord.User, amount: int):
    uid = user.id
    activity = None
    try:
        activity = await db.fetchval("SELECT activity FROM users WHERE id = $1", uid)
    except InternalClientError:
        log("Asyncpg is being stupid, but I did my best.", "WARN")
    except InterfaceError:
        log("Asyncpg is being stupid, but I did my best (2).", "WARN")
    if activity is None:
        activity = amount
    else:
        activity += amount
    log(f"Activity before: {activity - amount}, activity after: {activity}", "DBUG")
    level_before = level(activity - amount)
    level_after = level(activity)
    if level_after > level_before:
        # await channel.send(f"Congratulations {user} on reaching activity level {level_after}!")
        log(
            f"{user} ranked up their activity from level {level_before} to {level_after}",
            "RKUP",
        )
    try:
        recent_activity = (
            await db.fetchval("SELECT recent_activity FROM users WHERE id = $1", uid)
        ) + amount
    except TypeError:
        recent_activity = amount
    log(
        f"Adding {amount} activity score to {user}. New activity score: {activity}. "
        f"New recent activity score: {recent_activity}",
        "DBUG",
    )
    await db.execute("UPDATE users SET activity = $1 where id = $2", activity, uid)
    await db.execute(
        "UPDATE users SET recent_activity = $1 where id = $2", recent_activity, uid
    )


@with_db
async def add_funds(db, user: discord.User, amount: int, reduce_networth: bool = True):
    uid = user.id
    log(f"Adding {amount} credits to {user}.")
    if reduce_networth:
        await db.execute(
            "UPDATE users SET balance = balance + $1, networth = networth + $1 where id = $2",
            amount,
            uid,
        )
    else:
        await db.execute(
            "UPDATE users set balance = balance + $1 where id = $2", amount, uid
        )
    balance = await db.fetchval("SELECT balance FROM users WHERE id = $1", uid)
    return balance


@with_db
async def add_networth(db, user: discord.User, amount: int):
    uid = user.id
    log(f"Adding {amount} networth to {user}.")
    await db.execute(
        "UPDATE users SET networth = networth + $1 where id = $2",
        amount,
        uid,
    )
    networth = await db.fetchval("SELECT networth FROM users WHERE id = $1", uid)
    return networth


@with_db
async def check_bal(db, user: discord.User):
    uid = user.id
    check = await db.fetchrow("SELECT * FROM users WHERE id = $1", uid)
    log(type(check), "DBUG")
    balance = check[3]
    invested = check[5]
    networth = check[8] or balance
    return balance, invested, networth


@with_db
async def check_bal_str(db, username: str):
    fuzzy_username = f"%{username}%"
    check = await db.fetchrow("SELECT * FROM users WHERE name LIKE $1", fuzzy_username)
    log(check, "DBUG")
    balance = check[3]
    invested = check[5]
    networth = check[8] or balance
    username = check[1]
    passive = check[9] or 0
    bonus = check[10] or 0
    return balance, invested, networth, passive, bonus, username


def activity_multiplier(networth: float):
    if not networth or networth < 0:
        networth = 0
    if networth < 100_000_000:
        return 5.0
    if networth < 250_000_000:
        return 4.0
    if networth < 400_000_000:
        return 3.0
    if networth < 650_000_000:
        return 2.5
    if networth < 1_000_000_000:
        return 2.0
    if networth < 1_200_000_000:
        return 1.8
    if networth < 1_400_000_000:
        return 1.6
    if networth < 1_600_000_000:
        return 1.4
    if networth < 1_800_000_000:
        return 1.2
    if networth < 2_000_000_000:
        return 1.1
    return 1


@with_db
async def activity_multiplier_for_user(db, user_id: int) -> float:
    networth = await db.fetchval("SELECT networth FROM users where id = $1", user_id)
    return activity_multiplier(networth)


def calc_disp_delta(amount: float) -> str:
    disp_delta = str(int(amount))
    digits = len(str(amount))
    if digits > 6:
        disp_delta = f"{disp_delta[:-6]}.{disp_delta[-6:-4]}m"
    elif digits > 3:
        disp_delta = f"{disp_delta[:-3]}.{disp_delta[-3:-1]}k"
    return disp_delta


@with_db
async def distribute_payouts(db, bot=None):
    await ensure_tables_are_configured(bot)
    channel = None
    if bot is not None:
        channel = bot.get_channel(1055577521795641398)
        if channel is not None:
            await channel.send("Payouts distributed.")
    users = await db.fetch("SELECT * FROM users")
    for user in users:
        invested = user[5]
        if not invested:
            invested = 0
        balance = user[3]
        networth = user[8]
        remaining_bonus = user[10]
        if not networth:
            networth = balance
        recent_activity = user[6]
        if not recent_activity:
            recent_activity = 0
        if not remaining_bonus:
            remaining_bonus = 0
        # If wealth factor is zero, this bit doesn't give anything.
        payout_generosity = (
            random.random() * wealth_factor
        )  # Normalizes it to give between wf and 2* wf per hour
        investment_payout = int(invested * (payout_generosity + wealth_factor))
        # Distribute activity payouts too
        activity_payout = 0
        act_mult = activity_multiplier(networth)
        if user[6] is not None:
            # activity_payout = int(recent_activity) * actweight # Un-scaled
            activity_payout = int(recent_activity) * actweight * act_mult
            bonus_payout = min(activity_payout * 2, remaining_bonus)
        new_user_balance = (
            int(balance) + investment_payout + activity_payout + bonus_payout
        )
        new_user_networth = (
            int(networth) + investment_payout + activity_payout + bonus_payout
        )
        if new_user_balance > balance:
            log(
                f"User {user[1]}: {recent_activity=}, "
                f"{activity_payout=}, {invested=}, "
                f"{investment_payout=}, "
                f"{bonus_payout=}"
                f"old bal: {user[3]}, new bal: {new_user_balance}",
                "INFO",
            )
        if channel is not None and new_user_balance > user[3] + 20 * actweight:
            delta = new_user_balance - user[3]
            disp_delta = calc_disp_delta(delta)
            disp_networth = calc_disp_delta(networth)
            disp_bonus = calc_disp_delta(bonus_payout)
            to_send = (
                f"{user[1]}: **+{disp_delta}** credits for activity in the past hour."
            )
            to_send += f"\n\t*(x{act_mult} due to their net worth of {disp_networth})*"
            if bonus_payout > 0:
                to_send += f"""\n\t*(Bonus payout of {disp_bonus} is part of this)*"""
            await channel.send(to_send)

        await db.execute(
            "UPDATE users SET balance = $1, networth = $2, recent_activity = $3, bonus = $4 where id = $5",
            new_user_balance,
            new_user_networth,
            0,
            remaining_bonus - bonus_payout,
            user[0],
        )


@with_db
async def check_last_paycheck(db, user: discord.User, do_not_reinvoke: bool = False):
    uid = user.id
    check = await db.fetchrow("SELECT * FROM users WHERE id = $1", uid)
    try:
        last_paycheck = check[4]
    except IndexError:
        return 0
    except TypeError:
        if do_not_reinvoke:
            return 0
        # First ever message, need to initialize user first
        await new_user(user)
        return await check_last_paycheck(user, do_not_reinvoke=True)
    return last_paycheck


@with_db
async def set_last_paycheck_now(db, user: discord.User):
    uid = user.id
    time_now = time.time()
    await db.execute("UPDATE users SET last_pay = $1 WHERE id = $2", time_now, uid)
    return time_now


@with_db
async def set_passive_income(db, user: discord.User, amount: int):
    uid = user.id
    await db.execute("UPDATE users SET passive_income = $1 WHERE id = $2", amount, uid)


@with_db
async def get_passive_and_bonus_for_user(db, user: discord.User) -> (int, int):
    uid = user.id
    result = await db.fetchrow("SELECT * from users where id = $1", uid)
    return result[9] or 0, result[10] or 0


@with_db
async def reset_bonus_for_all_users(db):
    await db.execute("UPDATE users SET bonus = passive_income")


@with_db
async def get_top(db, cat: str, page: int, user: discord.User):
    offset = items_per_top_page * (1 - page)
    offset *= -1
    ind = 3
    mult = 1
    if cat not in [
        "balance",
        "invested",
        "activity",
        "earned",
        "networth",
        "bonus",
        "passive",
    ]:
        raise NameError(f"Category {cat} not found.")
    else:
        if cat == "invested":
            ind = 5
        elif cat == "activity":
            ind = 2
        elif cat == "networth":
            ind = 8
        elif cat == "earned":
            ind = 2
            mult = actweight
            cat = "activity"
        elif cat == "passive":
            ind = 9
            cat = "passive_income"
        elif cat == "bonus":
            ind = 10
        num_users = await db.fetchval(
            f"SELECT COUNT(id) FROM users WHERE {cat} IS NOT NULL"
        )
    if num_users < (page - 1) * items_per_top_page:
        offset = 0
    result = await db.fetch(
        f"SELECT * FROM users WHERE {cat} IS NOT NULL ORDER BY {cat} DESC LIMIT "
        f"{items_per_top_page} OFFSET $1",
        offset,
    )
    tops = []
    num_pages = num_users // items_per_top_page + 1
    for line in result:
        if line[ind] is None:
            line[ind] = 0
        tops.append((line[1], line[ind] * mult))
    subjects_bal = await db.fetchval(f"SELECT {cat} FROM users WHERE id = $1", user.id)
    rank = (
        await db.fetchval(
            f"SELECT COUNT({cat}) FROM users WHERE {cat} > $1", subjects_bal
        )
        + 1
    )
    return tops, num_pages, rank


@with_db
async def add_item(
    db,
    name: str,
    category: str,
    picture: str,
    min_cost: float,
    max_cost: float,
    description: str,
    faction: str,
):
    await db.execute(
        "INSERT INTO items VALUES ($1, $2, $3, $4, $5, $6, $7)",
        name,
        category,
        picture,
        min_cost,
        max_cost,
        description,
        faction,
    )


@with_db
async def add_custom_item(
    db,
    name: str,
    user: discord.User,
    amount: int = 1,
    description: str = "",
    picture: str = "",
):
    uid = user.id
    try:
        unique_key = await db.fetchval("SELECT MAX(id) from custom_items") + 1
    except TypeError:
        unique_key = 1
    # Check if player already owns some of that item
    has_amount = await db.fetchval(
        "SELECT amount FROM custom_items WHERE owner = $1 AND name = $2", uid, name
    )
    # log(f'{user} currently has {has_amount}x {item}.')
    if has_amount is None:
        # log('has_amount was None.', "DBUG"")
        await db.execute(
            "INSERT INTO custom_items VALUES ($1, $2, $3, $4, $5, $6)",
            unique_key,
            name,
            uid,
            amount,
            description,
            picture,
        )
    else:
        await db.execute(
            "UPDATE custom_items SET amount = $1 WHERE owner = $2 AND name = $3",
            amount + has_amount,
            uid,
            name,
        )


@with_db
async def get_custom_items(db, user: discord.User) -> [(str, str)]:
    """
    Returns a list of name, desc tuples for each custom item owned by the specified user
    """
    uid = user.id
    results = await db.fetch("SELECT * FROM custom_items WHERE owner = $1", uid)
    return [(result["name"], result["amount"]) for result in results]


@with_db
async def add_commodity_location(
    db, name: str, channel_id: int, is_buy: bool, **kwargs
):
    query = "INSERT INTO commodities_locations VALUES ($1, $2, $3)"
    counter = 3
    for _ in kwargs:
        counter += 1
        query += f"${counter}, "
    query = query.rstrip()[:-1] + ")"
    log(query, "DBUG")
    parameters = [name, channel_id, is_buy]
    for value in kwargs.values():
        parameters.append(value)
    log(parameters, "DBUG")
    await db.execute(query, *parameters)


@with_db
async def edit_item(db, item: str, category: str, new_value: str):
    categories = [
        "name",
        "category",
        "picture",
        "min_cost",
        "max_cost",
        "description",
        "faction",
    ]
    if category not in categories:
        raise NameError(f"Category {category} not found.")
    if category in ["min_cost", "max_cost"]:
        new_value = float(new_value)
    result = await db.fetchrow("SELECT * FROM items WHERE name = $1", item)
    if result is None:
        raise NameError(f"Item {item} not in database.")
    await db.execute(
        f"UPDATE items SET {category} = $1 WHERE name = $2", new_value, item
    )


@with_db
async def find_item(db, item: str):
    result = await db.fetchrow("SELECT * FROM items WHERE name = $1", item)
    query = f"%{item}%"
    log(f"Exact :{result}", "DBUG")
    if result is None:
        result = await db.fetchrow("SELECT * FROM items WHERE name LIKE $1", query)
        log(f"Fuzzy: {result}", "DBUG")
    return result


@with_db
async def find_items_in_cat(db, item: str):
    query = f"%{item}%"
    result = await db.fetch("SELECT * FROM items WHERE category LIKE $1", query)
    return result


@with_db
async def remove_item(db, item: str):
    result = await db.fetch("SELECT * FROM items WHERE name LIKE $1", item)
    print(result)
    if len(result) > 2:
        return "Too many matching items found."
    matching_possessions = await db.fetch(
        "SELECT * FROM possessions WHERE name like $1", item
    )
    for possession in matching_possessions:
        cost = possession["cost"] * possession["amount"]
        owner = possession["owner"]
        temp_result = await db.fetchrow(
            "SELECT balance, networth FROM users WHERE id = $1", owner
        )
        balance = float(temp_result[0])
        networth = float(temp_result[1])
        log(f"Adding {cost} credits to {owner} for refund of {possession['name']}.")
        balance += cost
        networth += cost
        await db.execute(
            "UPDATE users SET balance = $1, networth = $2 where id = $3",
            balance,
            networth,
            owner,
        )
    await db.execute("DELETE FROM possessions WHERE name LIKE $1", item)
    await db.execute("DELETE FROM items WHERE name LIKE $1", item)


def flatten(flatten_list):  # Just a one layer flatten
    new_list = []
    for item in flatten_list:
        for entry in item:
            new_list.append(entry)
    return new_list


@with_db
async def add_possession(
    db,
    user: discord.User,
    item: str,
    cost: Optional[float] = 0,
    amount: Optional[float] = 1,
):
    if not cost:
        cost = 0
    if not amount:
        amount = 1
    uid = user.id
    try:
        unique_key = await db.fetchval("SELECT MAX(id) from possessions") + 1
    except TypeError:
        unique_key = 1
    full_item = await db.fetchrow("SELECT * FROM items WHERE name = $1", item)
    # Check if player already owns some of that item
    (
        i_name,
        i_category,
        i_picture,
        i_min_cost,
        i_max_cost,
        i_description,
        i_faction,
    ) = full_item
    has_amount = await db.fetchval(
        "SELECT amount FROM possessions WHERE owner = $1 AND name = $2", uid, item
    )
    # log(f'{user} currently has {has_amount}x {item}.')
    if has_amount is None:
        await db.execute(
            "INSERT INTO possessions VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
            unique_key,
            i_name,
            uid,
            amount,
            i_category,
            i_picture,
            cost,
            i_faction,
        )
    else:
        await db.execute(
            "UPDATE possessions SET amount = $1 WHERE owner = $2 AND name = $3",
            amount + has_amount,
            uid,
            i_name,
        )


@with_db
async def add_ships_commodities(
    db, user: discord.User, commodity: str, amount: float = 1
):
    # TODO: NOT IMPLEMENTED YET, MAY NOT WORK AS EXPECTED
    uid = user.id
    # unique_key = await db.fetchval(f"SELECT MAX(id) FROM ships_commodities") + 1
    capacity = await db.fetchval(
        "SELECT capacity FROM ships_commodities WHERE owner = $1", uid
    )
    has_amount = await db.fetchval(
        "SELECT $1 FROM ships_commodities WHERE owner = $2", commodity, uid
    )
    if amount < 1:
        amount = 0
    if amount > capacity:
        raise ValueError
    await db.execute(
        "UPDATE ships_commodities SET capacity = $1 WHERE owner = $2",
        capacity - amount,
        uid,
    )
    await db.execute(
        "UPDATE ships_commodities SET $1 = $2 WHERE owner = $3",
        commodity,
        has_amount + amount,
        uid,
    )


@with_db
async def sell_possession(db, ctx, user: discord.User, item: str, amount: int = 1):
    uid = user.id
    full_item = await db.fetchrow("SELECT * FROM items WHERE name = $1", item)
    # Check if player already owns some of that item
    (
        i_name,
        i_category,
        i_picture,
        i_min_cost,
        i_max_cost,
        i_description,
        i_faction,
    ) = full_item
    has_amount = await db.fetchval(
        "SELECT amount FROM possessions WHERE owner = $1 AND name = $2", uid, item
    )
    i_cost = await db.fetchval(
        "SELECT cost FROM possessions WHERE owner = $1 AND name = $2", uid, item
    )
    if has_amount is None:
        return await ctx.send(
            f"You can not sell {item} because you do not have any of them."
        )
    elif has_amount < amount:
        return await ctx.send(
            f"You do not have enough {item}. You are trying to sell {amount}"
            f" but only have {has_amount}."
        )
    elif has_amount == amount:
        log(f"Removing: has_amount = {has_amount}, amount = {amount}.")
        balance = await db.fetchval("SELECT balance FROM users WHERE id = $1", uid)
        new_balance = balance + (amount * i_cost) * refund_portion
        await db.execute(
            "UPDATE users SET balance = $1 WHERE id = $2", new_balance, uid
        )
        await db.execute(
            "DELETE FROM possessions WHERE owner = $1 AND name = $2", uid, item
        )
    else:
        log(f"Updating: has_amount = {has_amount}, amount = {amount}.")
        balance = await db.fetchval("SELECT balance FROM users WHERE id = $1", uid)
        new_balance = balance + (amount * i_cost) * refund_portion
        await db.execute(
            "UPDATE users SET balance = $1 WHERE id = $2", new_balance, uid
        )
        await db.execute(
            "UPDATE possessions SET amount = $1 WHERE owner = $2 AND name = $3",
            has_amount - amount,
            uid,
            i_name,
        )
    await ctx.send(
        f"{ctx.author} has successfully sold {amount}x {item}, their balance is now {new_balance} credits."
    )


@with_db
async def transact_possession(
    db,
    ctx,
    user: discord.User,
    item: str,
    cost: float = 0,
    amount: Optional[int] = 1,
    credit: str = "credits",
) -> str:
    uid = user.id
    if cost < 0:
        raise ValueError("Cost can't be negative.")
    balance = await db.fetchval("SELECT balance FROM users WHERE id = $1", uid)
    max_cost = await db.fetchval("SELECT max_cost FROM items WHERE name = $1", item)
    min_cost = await db.fetchval("SELECT min_cost FROM items WHERE name = $1", item)
    if max_cost is None:
        raise ValueError(
            "Item not found. Remember, you must use the full item name and if you buy more than one "
            "the amount goes before the item name."
        )
    if cost == 0:
        cost = int((max_cost + min_cost) / 2 * 100) / 100
    if not (min_cost <= cost <= max_cost):
        cost = max_cost
        log("Cost not in valid range. Using max_cost instead.", "DBUG")
    new_balance = balance - (cost * amount)
    if new_balance < 0:
        return await ctx.send(
            f"Transaction aborted. You do not have sufficient funds. {amount}x {item} costs"
            f" {cost * amount} but you only have {balance}. You can use the paycheck command to "
            "earn a small amount of money or earn more money through roleplay."
        )
    log(
        f"Adding {amount}x {item} to {user} for {cost * amount}, their balance is currently"
        f" {balance} and will be {new_balance} after."
    )
    await add_possession(user, item, cost, amount)
    await db.execute("UPDATE users SET balance = $1 where id = $2", new_balance, uid)
    plural = "s" if amount != 1 else ""
    return f"{user} has successfully purchased {amount} {item}{plural} for {cost * amount} {credit}."


@with_db
async def view_items(db, user: discord.User):
    items = await db.fetch(
        "SELECT amount, name FROM possessions WHERE owner = $1", user.id
    )
    log(items, "DBUG")
    return set(items)


@with_db
async def update_location(db, user: discord.User, channel: discord.TextChannel):
    # old_location = await db.fetchval(f"SELECT location FROM users WHERE id = $1", user.id)
    new_location = channel.id
    recent_activity = await db.fetchval(
        "SELECT recent_activity FROM users WHERE id = $1", user.id
    )
    if recent_activity < move_activity_threshold:
        raise ValueError
    # await pay_recent_activity(user)
    await db.execute(
        "UPDATE users SET location = $1 where id = $2", new_location, user.id
    )


async def send_formatted_browse(ctx, result, i_type):
    if i_type == "all":
        send = "The following items are available. You can browse specific ones to see more details:\n```\n"
    else:
        send = f"Items in category {i_type}:\n```\n"
    count = 0
    log(result, "DBUG")
    items = sorted(result, key=lambda x: x["min_cost"])
    log(items, "DBUG")
    max_len = 35
    for item in items:
        item_price = int((float(item[3]) + float(item[4])) / 2 * 100) / 100
        if count < 25:
            send += (
                f'{item[0]}{(max_len - len(item[0])) * " "} ( ~ {item_price} credits)\n'
            )
            count += 1
        else:
            send += "```"
            await ctx.send(send)
            send = f'```{item[0]}{(max_len - len(item[0])) * " "} ( ~ {item_price} credits\n'
            count = 1
    send += "```"
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


@with_db
async def ensure_tables_are_configured(db, bot):
    # cursor.execute("SHOW DATABASES")
    # databases = cursor.fetchall()
    # log(f"Databases: {databases}", self.bot.debug)
    # cursor.execute("DROP TABLE users")
    tables = str(
        await db.fetch(
            """SELECT * FROM pg_catalog.pg_tables 
            WHERE schemaname != 'pg_catalog' 
            AND schemaname !='information_schema'"""
        )
    )
    log(f"I have the following tables:\n{tables}", bot.debug)
    if "settings" not in tables:
        log("Settings table not found. Creating a new one...")
        await db.execute(
            "CREATE TABLE settings( "
            "id BIGINT NOT NULL PRIMARY KEY, "
            "cooldown INT,"
            "amount DOUBLE PRECISION,"
            "starting DOUBLE PRECISION,"
            "actweight DOUBLE PRECISION)"
        )
        await db.execute(
            "INSERT INTO settings VALUES($1, $2, $3, $4, $5)",
            1,
            bot.PAYCHECK_INTERVAL,
            bot.PAYCHECK_AMOUNT_MAX,
            bot.STARTING_BALANCE,
            bot.ACTIVITY_WEIGHT,
        )
        log("Saved default settings to database.")
    else:
        settings = await db.fetchrow("SELECT * FROM settings WHERE id = 1")
        log(settings, bot.debug)
        bot.PAYCHECK_INTERVAL = settings[1]
        bot.PAYCHECK_AMOUNT_MAX = settings[2]
        bot.PAYCHECK_AMOUNT_MIN = settings[2]
        bot.STARTING_BALANCE = settings[3]
        bot.ACTIVITY_WEIGHT = settings[4]
        copy_bot_vars_to_local(bot)
        log(f"Loaded settings from database: {settings}", bot.debug)
    if "users" not in tables:
        log("Users table not found. Creating a new one...")
        await db.execute(
            "CREATE TABLE users( "
            "id BIGINT NOT NULL PRIMARY KEY, "
            "name VARCHAR (255), "
            "activity BIGINT, "
            "balance DOUBLE PRECISION, "
            "last_pay BIGINT,"
            "invested DOUBLE PRECISION,"
            "recent_activity BIGINT,"
            "location BIGINT,"
            "networth DOUBLE PRECISION,"
            "passive_income DOUBLE PRECISION,"
            "bonus DOUBLE PRECISION)"
        )
    if "items" not in tables:
        log("Items table not found. Creating a new one...")
        await db.execute(
            "CREATE TABLE items( "
            "name VARCHAR (127) NOT NULL PRIMARY KEY, "
            "category VARCHAR (127), "
            "picture VARCHAR (255), "
            "min_cost DOUBLE PRECISION, "
            "max_cost DOUBLE PRECISION, "
            "description VARCHAR (2048), "
            "faction VARCHAR (127))"
        )
    if "possessions" not in tables:
        log("Possessions table not found. Creating a new one...")
        await db.execute(
            "CREATE TABLE possessions("
            "id INT NOT NULL PRIMARY KEY, "
            "name VARCHAR (127) REFERENCES items(name), "
            "owner BIGINT REFERENCES users(id), "
            "amount INT, "
            "category VARCHAR (127), "
            "picture VARCHAR (127), "
            "cost DOUBLE PRECISION, "
            "faction VARCHAR (127))"
        )
    users_config = await db.fetch(
        "SELECT COLUMN_NAME from information_schema.COLUMNS WHERE TABLE_NAME = 'users' "
    )
    log(f"My Users table is configured thusly: {users_config}", bot.debug)
    users = await db.fetch("SELECT * FROM users")
    log(f"Users: {users}", bot.debug)
    bot.list_of_users = [user["id"] for user in users]
    log(repr(bot.list_of_users), bot.debug)


@with_db
async def get_users(db):
    return await db.fetch("SELECT * FROM users")


@with_db
async def execute_arbitrary_query(db, query):
    if query.strip().lower().startswith("select"):
        result = await db.fetch(query)
    else:
        result = await db.execute(query)
    return result


@with_db
async def set_setting_value(db, setting, value):
    return await db.execute(f"UPDATE settings SET {setting} = $1 WHERE id = 1", value)


@with_db
async def wipe_the_whole_economy(db, starting_balance):
    await db.execute(
        "UPDATE users SET balance = $1, activity = 0, last_pay = 0, invested = 0,"
        " recent_activity= 0",
        starting_balance,
    )


@with_db
async def do_browse(db, bot, ctx, item):
    if item is None:
        result = await db.fetch("SELECT DISTINCT category from items")
        categories = sorted(
            list(set(flatten([item[0].split(", ") for item in result])))
        )
        log(repr(categories), bot.debug)
        send = (
            "Here are the categories of items available. You can browse each category (case sensitive) to "
            "list the items in it, or you can browse all to see every item in the shop.\n "
        )
        send += "=" * 20 + "\n"
        for category in categories:
            send += f"{category}\n"
        await ctx.send(send)
        log(repr(categories), bot.debug)
        return
        pass
    elif item == "all":
        result = await db.fetch("SELECT * FROM items")
        await send_formatted_browse(ctx, result, "all")
        return
    item = item.title()
    # See if the keyword is a category
    results_in_category = await find_items_in_cat(item)
    if len(results_in_category) > 0:  # If it is a category, display category
        return await send_formatted_browse(ctx, results_in_category, item)
    # No we know its a specific item, find it
    result = await find_item(item)
    if result is None:
        return await ctx.send("Item not found.")
    log(result, bot.debug)
    av_cost = int((float(result[3]) + float(result[4])) / 2 * 100) / 100
    async with aiohttp.ClientSession() as session:  # Load image from link. TODO: Download and save image instead
        async with session.get(result[2]) as resp:
            buffer = BytesIO(await resp.read())
        await session.close()
    await ctx.send(
        f"__**{result[0]}**__ ({result[1]})"
        f"\n**Cost:** {av_cost} credits:"
        f"\n> {result[5]}",
        file=discord.File(fp=buffer, filename="file.jpg"),
    )


class Database(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = None
        copy_bot_vars_to_local(bot)

    # Events
    @commands.Cog.listener()
    async def on_ready(self):
        log(f"Loading {self.qualified_name}...", self.bot.debug)
        self.session = aiohttp.ClientSession(loop=self.bot.loop)
        await create_db_pool()
        await ensure_tables_are_configured(self.bot)
        logready(self)

    def cog_unload(self):
        global pool
        log(f"Closing {self.qualified_name} cog.", self.bot.prio)
        try:
            flag = False
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                flag = True
            loop.run_until_complete(pool.close())
            if flag:
                loop.close()
        except NameError:
            pass
        try:
            self.session.close()
        except AttributeError:
            log(
                f"AttributeError trying to close aiohttp session at {now()}",
                self.bot.warn,
            )

    @commands.command(description="Prints the list of users to the console.")
    @commands.check(auth(max(4, AUTH_LOCKDOWN)))
    async def listusers(self, ctx):
        users = await get_users()
        log(
            f"The list of users was requested by a command. Here it is: {users}",
            self.bot.prio,
        )
        names = [user[1] for user in users]
        num_users = len(users)
        await ctx.send(
            f"The list of {num_users} users has been printed to the console. "
            f"Here are their names only:\n{str(names)[0:1800]}"
        )
        log(f"The users command was used by {ctx.author}.", self.bot.cmd)

    @commands.command(description="Does a direct database query.")
    @commands.check(auth(max(8, AUTH_LOCKDOWN)))
    async def directq(self, ctx, *, query):
        """
        Does a direct database query. Not quite as dangerous as eval, but still restricted to Auth 8.
        """
        add_text = ""
        try:
            result = await execute_arbitrary_query(query)
            await ctx.send(result)
            add_text = f"Result was:\n{result}"
        except conn.InterfaceError:
            await ctx.send("Okay. There's no result from that query.")
        log(
            f"{ctx.author} executed a direct database query:\n{query}\n{add_text}",
            self.bot.cmd,
        )

    @commands.command(description="add new user to database")
    @commands.check(auth(max(2, AUTH_LOCKDOWN)))
    async def newuser(self, ctx, user: discord.User):
        """
        Add a new user to the database.
        """
        result = await new_user(user)
        log(result, self.bot.debug)
        await ctx.send(result)
        log(f"{ctx.author} added new user {user} to the database.", self.bot.cmd)

    @commands.command(aliases=["additem"], description="add a new item to the database")
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
        item = content.split("\n")
        log(f"Adding item {item[0]} by request of {ctx.author}: {item}", self.bot.cmd)
        try:
            await add_item(
                item[0],
                item[1],
                item[2],
                float(item[3]),
                float(item[4]),
                item[5],
                item[6],
            )
        except ValueError:
            return await ctx.send(
                "Incorrect format. Remember each item must be on its own line, and the minimum "
                "and maximum prices must be numbers. Check your formatting and try again."
            )
        except IndexError:
            return await ctx.send(
                "Incorrect format. Remember each item must be on its own line, and the minimum "
                "and maximum prices must be numbers. Check your formatting and try again."
            )
        except StringDataRightTruncationError:
            return await ctx.send(
                "One of your values is too long. Here are the max lengths of each value in "
                "characters:\n"
                "Name 127\n"
                "Category 127\n"
                "Picture 255\n"
                "Description 300\n"
            )
        # return await ctx.send('An item with that name is already in the database.')
        await ctx.send(f"Added {item[0]} to the database.")

    @commands.command(
        aliases=["addlocation"],
        description=f"Add a new location to the database. \nChannel is a "
        f"channel mention for this shop, and is_buy is TRUE for"
        f" purchase costs, FALSE for sell costs. Each value must"
        f" be a kwarg from: {COMMODITIES}",
    )
    @commands.check(auth(3))
    async def newlocation(
        self,
        ctx,
        name: str,
        channel: discord.TextChannel,
        is_buy: bool,
        *,
        in_values: str,
    ):
        values = in_values.split(" ")
        kwargs = {}
        for tic in values:
            item, value = tic.split("=")
            kwargs[item] = float(value)
        log(
            f"Adding location {name} by request of {ctx.author}: {kwargs}", self.bot.cmd
        )
        try:
            await add_commodity_location(name, channel.id, is_buy, **kwargs)
        except ValueError:
            return await ctx.send("Incorrect format. (1)")
        except IndexError:
            return await ctx.send("Incorrect format. (2)")
        # return await ctx.send('A location with that name is already in the database.')
        await ctx.send(f"Added {name} to the database.")

    @commands.command(
        aliases=["removeitem"], description="Remove an item from the database"
    )
    @commands.check(auth(max(4, AUTH_LOCKDOWN)))
    async def deleteitem(self, ctx, *, item: str):
        """
        Remove an item from the database. Requires Auth 4.
        """
        await ctx.send(
            f"Are you sure you want to remove {item} from the database? Respond with 'y' within 20 seconds to confirm."
        )
        try:
            response = await self.bot.wait_for(
                "message", check=lambda x: x.author == ctx.author, timeout=20
            )
        except asyncio.TimeoutError:
            return await ctx.send("Delete cancelled.")
        if response.content != "y":
            return await ctx.send("Delete cancelled.")
        log(f"Removing item {item} by request of {ctx.author}.", self.bot.cmd)
        await remove_item(item)
        await ctx.send(
            f"Successfully removed {item} from the database and refunded any owners 100%."
        )

    @commands.command(
        aliases=["updateitem"], description="Edit a value of an item in the database."
    )
    @commands.check(auth(max(4, AUTH_LOCKDOWN)))
    async def edititem(self, ctx, item: str, field: str, value: str):
        """Edit a value of an item in the database."""
        try:
            await edit_item(item, field, value)
            await ctx.send(f"Updated {item}.")
            log(
                f"Updated item {item} field {field} to value {value} by request of {ctx.author}.",
                self.bot.cmd,
            )
        except NameError:
            await ctx.send(
                "Category not found. Categories are case sensitive, double check!"
            )
            log(
                f"Failed to update item {item} field {field} to value {value} for {ctx.author}.",
                self.bot.cmd,
            )

    @commands.command(description="Adjust bot settings")
    @commands.has_permissions(administrator=True)
    async def settings(self, ctx, setting: str, value: str):
        """Adjust bot settings.
        Setting must be one of: 'cooldown', 'amount', 'starting', 'actweight'
        Cooldown: the number of seconds between paychecks
        Amount: the amount of credits per paycheck
        Starting: the amount of credits a brand new player starts with
        Actweight: The number of credits to pay out per internal bot "activity point"
        """
        config_opts = ["cooldown", "amount", "starting", "actweight"]
        if setting not in config_opts:
            return await ctx.send(
                f"Sorry, that isn't a configurable setting. Try one of {config_opts}."
            )
        if setting == "cooldown":
            value = int(value)
            self.bot.PAYCHECK_INTERVAL = value
        elif setting == "amount":
            value = round(float(value), 2)
            self.bot.PAYCHECK_AMOUNT_MAX = value
            self.bot.PAYCHECK_AMOUNT_MIN = value
        elif setting == "starting":
            value = round(float(value), 2)
            self.bot.STARTING_BALANCE = value
        elif setting == "actweight":
            value = round(float(value), 2)
            self.bot.ACTIVITY_WEIGHT = value
        await set_setting_value(setting, value)
        await ctx.send(f"Okay, {setting} set to {value}.")
        log(f"Updated {setting} to {value} for {ctx.author}.", self.bot.cmd)

    @commands.command(description="Reset the economy entirely.")
    @commands.has_permissions(administrator=True)
    async def wipe_the_whole_fucking_economy_like_seriously(self, ctx):
        """Set everyone's balance to the configured starting balance and activity to 0. Several safeguards are in
        place."""
        confirmation_phrase = "I understand I am wiping the whole economy"
        await ctx.send(
            f"This will reset **everyone's** balance to {self.bot.STARTING_BALANCE} and activity to 0. "
            f"This is not reversible. If you are sure, type "
            f"`{confirmation_phrase}`\nTo be safe, it must match exactly. You have 30 seconds,"
            f" or this command will cancel without running."
        )
        try:
            confirmation = await self.bot.wait_for(
                "message", check=check_author(ctx.author), timeout=30
            )
        except asyncio.TimeoutError:
            return await ctx.send(
                "Cancelled operation: Took longer than 30 seconds to respond."
            )
        if confirmation.content != confirmation_phrase:
            return await ctx.send(
                "Cancelled operation: Phrase did not match `{confirmation_phrase}`."
            )
        await wipe_the_whole_economy(self.bot.STARTING_BALANCE)
        await ctx.send(
            f"Successfully reset everyone's balance to {self.bot.STARTING_BALANCE}"
        )
        log(
            f"Reset all balances to {self.bot.STARTING_BALANCE} by request of {ctx.author}.",
            self.bot.cmd,
        )
        log(
            f"Reset all balances to {self.bot.STARTING_BALANCE} by request of {ctx.author}.",
            self.bot.prio,
        )

    @commands.command(description="browse the shop")
    @commands.check(auth(AUTH_LOCKDOWN))
    async def browse(self, ctx, *, item: str = None):
        """
        Browse the items available for sale.
        You can also specify a category to list the items of that type, or a specific item to see more details
         on that item, including a picture.
        """
        log(f"{ctx.author} used the browse command for {item}.")
        await do_browse(self.bot, ctx, item)


async def setup(bot_o):
    await bot_o.add_cog(Database(bot_o))
