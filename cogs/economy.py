import time
import random
from datetime import datetime
import discord
import typing
from discord.ext import commands, tasks

from bot import log, logready
from cogs.database import add_invest, check_bal, transfer_funds, add_funds, distribute_payouts, check_last_paycheck, \
    set_last_paycheck_now, get_top, check_bal_str, transact_possession, add_possession, view_items, sell_possession, \
    items_per_top_page
from functions import auth

global payout_frequency
# These parameters need to be in this scope due to constraints of the library.
# I set them based on the bot attributes of the same names in init and on_ready.
# These are just "default default values" so to speak, and are never actually used.
payout_frequency = 10000000


class Economy(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        global payout_frequency
        payout_frequency = self.bot.PAYOUT_FREQUENCY
        # self.send_payouts.start()
        log('Started the investment payouts task (1).', self.bot.debug)

    def cog_unload(self):
        self.send_payouts.cancel()
        log('Ended the investment payout task.')

    def cog_load(self):
        self.send_payouts.start()
        log('Weirldy Started the investment payouts task (2).')

    # Events
    @commands.Cog.listener()
    async def on_ready(self):
        logready(self)

    # =============================This rewards for disboard bumps=========================
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id == self.bot.DISBOARD and len(message.embeds) > 0:  # From disboard and has an embed
            embed_content = message.embeds[0].to_dict()['description']
            if 'Bump done' in embed_content:
                bumper_id = int(embed_content[2:20])
                bumper = await self.bot.fetch_user(bumper_id)
                balance = await add_funds(bumper, self.bot.BUMP_PAYMENT)
                message = f"Thank you for bumping {self.bot.server.name} on Disboard, {bumper.mention}." \
                          f" I've added {self.bot.BUMP_PAYMENT}" \
                          f" {self.bot.credit_emoji} to your balance. Your new balance is {balance}."
                log(f'{bumper} bumpbed the server on Disboard. Gave them {self.bot.BUMP_PAYMENT}, '
                    f'new balance {balance}.')
                # await message.channel.send(message)

    # Commands

    @commands.command(description='Invest some money into your business.')
    @commands.check(auth(1))
    async def invest(self, ctx, transact):
        """
            Invest some money into your business in order to occasionally receive dividends in proportion
             to how much you have invested. Be warned, investments currently can not be withdrawn.
        """
        try:
            amount = float(transact)
        except ValueError:
            return await ctx.send("You need to enter a number.")
        if amount < 0:
            return await ctx.send("You can not invest a negative amount.")
        elif amount == 0:
            return await ctx.send("You can't invest nothing!")
        invested, total_invested, new_balance = await add_invest(ctx.author, amount)
        if invested == -1:
            result = 'User not found.'
        elif invested == -2:
            result = 'You do not have enough cash for that.'
        else:
            result = f"{ctx.author}, you have just invested {invested} for a total of invested of {total_invested}." \
                     f" You now have {new_balance} credits left."
        await ctx.send(result)
        log(f'{ctx.author} used invest command with result: {result}.', self.bot.cmd)

    @commands.command(aliases=['bal', 'cash'], description='Check your balance.')
    async def balance(self, ctx, user: typing.Union[discord.Member, str] = None):
        """
        Check your credit balance.
        """
        try:
            if user is None:
                user = ctx.author
            if isinstance(user, discord.Member):
                balance, invested = await check_bal(user)
            else:
                balance, invested, user = await check_bal_str(user)
            message = f"{user.name}'s balance is {int(balance)} {self.bot.credit_emoji}"
            embed = discord.Embed(title='Balance',
                                  description=message,
                                  timestamp=datetime.now())
            await ctx.send(embed=embed)
            log(f"{ctx.author} checked {user}'s balance, it was {balance}.", self.bot.cmd)
        except TypeError:
            await ctx.send("User not found.")
            log(f"{ctx.author} attempted to check {user}'s balance, but it was not found.", self.bot.cmd)

    @commands.command(aliases=['send'], description='Send someone else credits.')
    async def pay(self, ctx, user: discord.User, transfer):
        """
        Send someone else some credits.
        """
        log(f'{ctx.author} attempted to transfer {transfer} to {user}.', self.bot.cmd)
        try:
            amount = float(transfer)
        except ValueError:
            return await ctx.send("You need to enter a number.")
        if user.id == ctx.author.id:
            return await ctx.send("You can't send credits to yourself!")
        if amount < 0:
            return await ctx.send("You can't send negative amounts of credits.")
        elif amount == 0:
            return await ctx.send("You can't send nothing!")
        from_balance, to_balance = await transfer_funds(ctx.author, user, amount)
        if from_balance == -1:
            await ctx.send(f"You can not send more credits than you have.")
        else:
            await ctx.send(f'Successfully transferred {amount} to {user}. Your new balance is {from_balance}'
                           f' {self.bot.credit_emoji}, their new balance is {to_balance} {self.bot.credit_emoji}.')
            log(f'{ctx.author} transferred {amount} to {user}.')

    @commands.command(name='buy', description='Buy an item from the browse listings.')
    @commands.check(auth(1))
    async def buyitem(self, ctx, amount: typing.Optional[int] = 1, *, item: str):
        """
        Buy an item from the browse listings. You can specify an amount of the item to buy before the
         name of the item to buy multiple. Exact name is required to prevent accidental matching.
        """
        # TODO: Add price determination depending on context
        log(f'{ctx.author} is attempting to purchase {amount} {item}(s).', self.bot.cmd)
        await transact_possession(ctx, ctx.author, item.title(), amount=amount)

    @commands.command(name='sell', description='Sell an item from your possessions for 60% of its purchase value.')
    @commands.check(auth(1))
    async def sellitem(self, ctx, amount: typing.Optional[int] = 1, *, item: str):
        """
        Sell an item from your possessions for 60% of its purchase value. You can specify the amount of the
         item to buy before the name of the item to buy multiple. Exact name is required to prevent accidental matching.
        """
        log(f'{ctx.author} is attempting to sell {amount} {item}(s).', self.bot.cmd)
        if amount < 1:
            return await ctx.send('Invalid sell amount.')
        await sell_possession(ctx, ctx.author, item.title(), amount)

    @commands.command(description='Add an item to a users possessions without the need to buy it.')
    @commands.check(auth(2))
    async def cheat_item(self, ctx, user: discord.Member, amount: typing.Optional[int] = 1,
                         price: typing.Optional[float] = 0, *, item: str):
        """
        Add an item to a users possessions without the need to buy it.
        Meant for GMs to give rewards and the like.
        Optionally include an amount and or price after the username. The price will not take that money away from
        the target user, but will set the possession's base sell price.
        """
        await add_possession(user, item, cost=price, amount=amount)
        await ctx.send(f'I have given {user} {amount} {item}.')
        log(f'{ctx.author} added {amount} {item} to {user}.', self.bot.cmd)

    @commands.command(name='top', aliases=['topbank'], description='List the top people in the bank.')
    async def topbank(self, ctx, page: int = 1):
        # This method queries the database and returns a list of ten tuples of (name, stat) which is one page of results
        log(f'{ctx.author} used topbank {page}.', self.bot.cmd)
        try:
            lines, num_pages, rank = await get_top('balance', page, ctx.author)
        except NameError:
            return await ctx.send('Invalid category. Try balance, invested or activity.')
        message = f"**Top {'balance'.title()} Page {page}/{num_pages}**\n\n"
        count = (page - 1) * self.bot.ITEMS_PER_TOP_PAGE + 1
        for line in lines:
            message += f'{count}) {line[0]} - {line[1]}\n'
            count += 1
        embed = discord.Embed(title='',
                              description=message,
                              timestamp=datetime.now())
        embed.set_footer(text=f'Your rank: {rank}')
        await ctx.send(embed=embed)

    @commands.command(description='List the top people in the specified category.')
    async def topstat(self, ctx, look_type: typing.Optional[str] = 'balance', page: int = 1):
        # This method queries the database and returns a list of ten tuples of (name, stat) which is one page of results
        log(f'{ctx.author} used topbank {look_type} {page}.', self.bot.cmd)
        try:
            lines, num_pages, rank = await get_top(look_type, page, ctx.author)
        except NameError:
            return await ctx.send('Invalid category. Try balance, n or activity.')
        if page > num_pages:
            page %= num_pages
        message = f'**Top {look_type.title()} Page {page}/{num_pages}**\n\n'
        count = 1
        for line in lines:
            message += f'{count + (page - 1) * items_per_top_page}) {line[0]} - {line[1]}\n'
            count += 1
        embed = discord.Embed(title='',
                              description=message,
                              timestamp=datetime.now())
        embed.set_footer(text=f'Your rank: {rank}')
        await ctx.send(embed=embed)

    @commands.command(description='Give someone credits from nowhere. Staff only.')
    async def credadd(self, ctx, member: discord.Member, amount: int):
        """
        Staff override to give people credits. Can also take credits away with negative amount.
        Requires Commander role
        """
        log(f'{ctx.author} used credadd command with amount {amount} and member {member}.', self.bot.cmd)
        commander = ctx.guild.get_role(456506763139612695)
        if commander not in ctx.author.roles:
            return await ctx.send("You are not authoried to use this command.")
        new_balance = await add_funds(member, amount)
        log(f'Added {amount} credits to {member} by authority of {ctx.author}. Their new balance is {new_balance}')
        message = f"Added {int(amount)} {self.bot.credit_emoji} to {member.name}'s account by request of " \
                  f"{ctx.author.name}."
        embed = discord.Embed(title='Money',
                              description=message,
                              timestamp=datetime.now())
        await ctx.send(embed=embed)
        await ctx.send(
            f'Added {amount} credits to {member} by authority of {ctx.author}. Their new balance is {new_balance}')

    @commands.command(description='Take credits from someone. Staff only.')
    async def credremove(self, ctx, member: discord.Member, amount: int):
        """
        Staff override to give people credits. Can also take credits away with negative amount.
        Requires Commander role
        """
        log(f'{ctx.author} used credremove command with amount {amount} and member {member}.', self.bot.cmd)
        commander = ctx.guild.get_role(456506763139612695)
        if commander not in ctx.author.roles:
            return await ctx.send("You are not authoried to use this command.")
        new_balance = await add_funds(member, -1 * amount)
        log(f'Removed {amount} credits from {member} by authority of {ctx.author}. Their new balance is {new_balance}')
        message = f"Removed {int(amount)} {self.bot.credit_emoji} from {member.name}'s account by request" \
                  f" of {ctx.author.name}."
        embed = discord.Embed(title='Money',
                              description=message,
                              timestamp=datetime.now())
        await ctx.send(embed=embed)

    @commands.command(description='Distribute payouts based on investments.')
    @commands.check(auth(2))
    async def payout(self, ctx):
        """
        Staff command to distribute investment payout money.
        Requires Auth 2
        """
        log(f'{ctx.author} used the payout command.', self.bot.cmd)
        await distribute_payouts()
        log(f'Bonus investment payouts successfully distributed by {ctx.author}.')
        channel = self.bot.log_channel
        await channel.send(f'Bonus investment payouts sent by {ctx.author}, enjoy!')

    @commands.command(description='Get some free credits!')
    async def paycheck(self, ctx, *, params=''):
        """
        Get some free credits.
        """
        log(f'{ctx.author} used the paycheck command.', self.bot.cmd)
        # Debug blurb
        if ctx.author.id == 125449182663278592 and '-debug' in params:
            paycheck_amount = 1
            await add_funds(ctx.author, paycheck_amount)
            message = f'{ctx.author.name} has been paid a (debug) paycheck of {paycheck_amount} {self.bot.credit_emoji}'
            embed = discord.Embed(title='Paycheck',
                                  description=message,
                                  timestamp=datetime.now())
            return await ctx.send(embed=embed)
        last_paycheck = await check_last_paycheck(ctx.author)
        if time.time() - last_paycheck < self.bot.PAYCHECK_INTERVAL:
            seconds_remaining = int(last_paycheck + self.bot.PAYCHECK_INTERVAL - time.time() + 1)
            minutes_remaining = seconds_remaining // 60
            seconds_remaining = seconds_remaining % 60
            return await ctx.send(f"You aren't ready for a paycheck yet. Try again in {minutes_remaining} minutes"
                                  f" and {seconds_remaining} seconds.")

        if self.bot.PAYCHECK_AMOUNT_MAX == self.bot.PAYCHECK_AMOUNT_MIN:
            paycheck_amount = self.bot.PAYCHECK_AMOUNT_MAX
        else:
            paycheck_amount = random.randrange(self.bot.PAYCHECK_AMOUNT_MIN, self.bot.PAYCHECK_AMOUNT_MAX)
        balance = await add_funds(ctx.author, paycheck_amount)
        message = f'{ctx.author.name} has been paid {paycheck_amount} {self.bot.credit_emoji} [{int(balance)}]'
        await set_last_paycheck_now(ctx.author)
        embed = discord.Embed(title='Paycheck',
                              description=message,
                              timestamp=datetime.now())
        await ctx.send(embed=embed)
        log(f'Paycheck of {paycheck_amount} successfully distributed to {ctx.author}. New balance {balance}.')

    @commands.command(aliases=['mine', 'backpack', 'items', 'inventory'], description='See what items you own.')
    @commands.check(auth(1))
    async def possessions(self, ctx, member: discord.Member = None):
        if member is None:
            member = ctx.author
        log(f'{ctx.author} checked the inventory of {member}.', self.bot.cmd)
        items = await view_items(member)
        log(items, self.bot.debug)
        to_send = f'**You have {sum(item for item, _ in items)} items of {len(items)} different types:**\n'
        for item in items:
            to_send += f'{item[0]}x {item[1]}\n'
        to_send += "\n\n*Don't need an item anymore? you can sell it at any time for 60% of the price you bought it " \
                   "for with the sell command.*"
        await ctx.send(to_send)

    @commands.command()
    @commands.check(auth(2))
    async def econ_printout(self, ctx):
        log(f'{ctx.author} used the econ_printout command.', self.bot.cmd)
        log(self.bot.commodities_sell_prices, self.bot.debug)
        log(self.bot.commodities_buy_prices, self.bot.debug)
        send = '\n'.join([str(line) for line in self.bot.commodities_sell_prices if line[0] != ''])
        counter = 0
        to_send = ''
        for i in send:
            counter += 1
            to_send += i
            if counter > 1999:
                await ctx.send(to_send)
                to_send = ''
                counter = 0
        await ctx.send(to_send)

    @commands.command(aliases=['sells'])
    @commands.check(auth(2))
    async def sell_prices(self, ctx, channel: discord.TextChannel, threshold: float = 0):
        if threshold == 0:
            threshold = (await check_bal(ctx.author))[0]
        ch_id = channel.id
        count = 0
        log(f'{ctx.author} checked sell prices for {channel}, threshold {threshold}.', self.bot.cmd)
        for location_sell in self.bot.commodities_sell_prices:
            if location_sell[0] == ch_id:
                to_send = f'Sell prices at {location_sell[1]}:\n```\n'
                for item, price in sorted(location_sell[2].items(), key=lambda x: x[1]):
                    if price < threshold or threshold < 0:
                        spaces = ' ' * (17 - len(item))
                        random_modifier = random.random() * 0.001 + 1 - 0.0005
                        log(random_modifier, self.bot.debug)
                        to_send += f'{item}:{spaces} ~{price * random_modifier:,.2f}\n'
                append = '```'
                while len(to_send) > 1995:
                    await ctx.send(to_send[:1990] + append)
                    to_send = append + to_send[1990:]
                to_send += append
                await ctx.send(to_send)
                return
            count += 1

    @commands.command(aliases=['buys'])
    @commands.check(auth(2))
    async def buy_prices(self, ctx, channel: discord.TextChannel, threshold: float = 0):
        if threshold == 0:
            threshold = (await check_bal(ctx.author))[0]
        ch_id = channel.id
        count = 0
        log(f'{ctx.author} checked buy prices for {channel}, threshold {threshold}.', self.bot.cmd)
        for location_buy in self.bot.commodities_buy_prices:
            if location_buy[0] == ch_id:
                to_send = f'\nBuy prices at {location_buy[1]}:\n```\n'
                for item, price in sorted(location_buy[2].items(), key=lambda x: x[1]):
                    if price < threshold or threshold < 0:
                        spaces = ' ' * (17 - len(item))
                        random_modifier = random.random() * 0.001 + 1 - 0.0005
                        log(random_modifier, self.bot.debug)
                        to_send += f'{item}:{spaces} ~{price * random_modifier:,.2f}\n'
                append = '```'
                while len(to_send) > 1990:
                    await ctx.send(to_send[:1990] + append)
                    to_send = append + to_send[1990:]
                to_send += append
                await ctx.send(to_send)
                return
            count += 1

    @tasks.loop(seconds=payout_frequency)
    async def send_payouts(self):
        await distribute_payouts()
        log('Investment payouts sent.')
        channel = self.bot.get_channel(718949686412705862)
        if channel is not None:
            await channel.send('Investment payouts sent.')


def setup(bot):
    bot.add_cog(Economy(bot))
