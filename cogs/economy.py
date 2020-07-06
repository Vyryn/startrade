import time
import random
from datetime import datetime
import discord
import typing
from discord.ext import commands, tasks
from cogs.database import add_invest, check_bal, transfer_funds, add_funds, distribute_payouts, check_last_paycheck, \
    set_last_paycheck_now, get_top, check_bal_str, transact_possession, add_possession, view_items, sell_possession
from functions import auth, now

PAYOUT_FREQUENCY = 60 * 60  # How frequently to send out investments, in seconds

class Economy(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.send_payouts.start()
        self.BUMP_PAYMENT = 100  # Payment for disboard bumps
        self.DISBOARD = 302050872383242240  # Disboard uid
        self.PAYCHECK_AMOUNT_MIN = 20  # Minimum paycheck payout
        self.PAYCHECK_AMOUNT_MAX = 30  # Maximum paycheck payout
        self.PAYCHECK_INTERVAL = 180  # Time between paychecks, in seconds
        print('Started the payouts task (1).')

    def cog_unload(self):
        self.send_payouts.cancel()
        print('Ended the investment payout task.')

    def cog_load(self):
        self.send_payouts.start()
        print('Started the payouts task (2).')

    # Events
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'Cog {self.qualified_name} is ready.')

    # =============================This rewards for disboard bumps=========================
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id == self.DISBOARD and len(message.embeds) > 0:  # From disboard and has an embed
            embed_content = message.embeds[0].to_dict()['description']
            if 'Bump Done' in embed_content:
                bumper_id = int(embed_content[3:21])
                bumper = await self.bot.fetch_user(bumper_id)
                balance = await add_funds(bumper, self.BUMP_PAYMENT)
                await message.channel.send(f"Thank you for bumping Startrade on Disboard, {bumper.mention()}. I've "
                                           f"added ${self.BUMP_PAYMENT} to your balance. "
                                           f"Your new balance is {balance}.")

    # Commands

    @commands.command(description='Invest some money into your business.')
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
        print(result)

    @commands.command(aliases=['bal', 'cash'], description='Check your balance.')
    async def balance(self, ctx, user: typing.Union[discord.Member, str] = None):
        """
        Check your balance and invested amount.
        """
        try:
            if user is None:
                user = ctx.author
            if isinstance(user, discord.Member):
                balance, invested = await check_bal(user)
            else:
                balance, invested, user = await check_bal_str(user)
            await ctx.send(f'Balance for {user}: \n> ${balance} in account.\n> ${invested} invested.')
        except TypeError:
            await ctx.send("User not found.")

    @commands.command(aliases=['send'], description='Send someone else money.')
    async def pay(self, ctx, user: discord.User, transfer):
        """
        Send someone else some money.
        """
        try:
            amount = float(transfer)
        except ValueError:
            return await ctx.send("You need to enter a number.")
        if user.id == ctx.author.id:
            return await ctx.send("You can't send money to yourself!")
        if amount < 0:
            return await ctx.send("You can't send negative amounts of money.")
        elif amount == 0:
            return await ctx.send("You can't send nothing!")
        from_balance, to_balance = await transfer_funds(ctx.author, user, amount)
        if from_balance == -1:
            await ctx.send(f"You can not send more money than you have.")
        else:
            await ctx.send(f'Successfully transferred {amount} to {user}. Your new balance is {from_balance}, '
                           f'their new balance is {to_balance}.')

    @commands.command(name='buy', description='Buy an item from the browse listings.')
    async def buyitem(self, ctx, amount: typing.Optional[int] = 1, *, item: str):
        """
        Buy an item from the browse listings. You can specify an amount of the item to buy before the
         name of the item to buy multiple. Exact name is required to prevent accidental matching.
        """
        # TODO: Add price determination depending on context
        print(f'{ctx.author} is attempting to purchase {amount} {item}s at {now()}.')
        await transact_possession(ctx, ctx.author, item.title(), amount=amount)

    @commands.command(name='sell', description='Sell an item from your possessions for 60% of its purchase value.')
    async def sellitem(self, ctx, amount: typing.Optional[int] = 1, *, item: str):
        """
        Sell an item from your possessions for 60% of its purchase value. You can specify the amount of the
         item to buy before the name of the item to buy multiple. Exact name is required to prevent accidental matching.
        """
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

    @commands.command(name='top', aliases=['topbank'], description='List the top people in the specified category.')
    async def topstat(self, ctx, look_type: typing.Optional[str] = 'balance', page: int = 1):
        # This method queries the database and returns a list of ten tuples of (name, stat) which is one page of results
        try:
            lines, num_pages, rank = await get_top(look_type, page, ctx.author)
        except NameError:
            return await ctx.send('Invalid category. Try balance, invested or activity.')
        message = f'**Top {look_type.title()} Page {page}/{num_pages}**\n\n'
        count = 1
        for line in lines:
            message += f'{count}) {line[0]} - {line[1]}\n'
            count += 1
        embed = discord.Embed(title='',
                              description=message,
                              timestamp=datetime.now())
        embed.set_footer(text=f'Your rank: {rank}')
        await ctx.send(embed=embed)

    @commands.command(description='Give someone money from nowhere. Staff only.')
    @commands.check(auth(2))
    async def cheat_money(self, ctx, member: discord.Member, amount: int):
        """
        Staff override to give people money. Can also take money away with negative amount.
        Requires Auth 2
        """
        new_balance = await add_funds(member, amount)
        print(f'Added {amount} credits to {member} by authority of {ctx.author}. Their new balance is {new_balance}')
        await ctx.send(
            f'Added {amount} credits to {member} by authority of {ctx.author}. Their new balance is {new_balance}')

    @commands.command(description='Distribute payouts based on investments.')
    @commands.check(auth(2))
    async def payout(self, ctx):
        """
        Staff command to distribute investment payout money.
        Requires Auth 2
        """
        await distribute_payouts()
        print(f'Bonus investment payouts sent by {ctx.author}, enjoy!')
        channel = self.bot.get_channel(718949686412705862)
        await channel.send(f'Bonus investment payouts sent by {ctx.author}, enjoy!')

    @commands.command(description='Get some free money!')
    async def paycheck(self, ctx):
        """
        Get some free money. Only gives a little bit, though; you can get much more money from actually RPing.
        """
        last_paycheck = await check_last_paycheck(ctx.author)
        if time.time() - last_paycheck < self.PAYCHECK_INTERVAL:
            seconds_remaining = last_paycheck + self.PAYCHECK_INTERVAL - time.time()
            return await ctx.send(f"You aren't ready for a paycheck yet. Try again in {int(seconds_remaining + 1)}"
                                  f" seconds.")
        paycheck_amount = random.randrange(self.PAYCHECK_AMOUNT_MIN, self.PAYCHECK_AMOUNT_MAX)
        await set_last_paycheck_now(ctx.author)
        balance = await add_funds(ctx.author, paycheck_amount)
        await ctx.send(f"{ctx.author} has found an odd job and earned {paycheck_amount} cool cash. "
                       f"It's not much, but their balance is now {balance} credits.\n\nTip: You can earn substantially "
                       f"more money from trading commodities. Check out ,buys [channel] and ,sells [channel]")

    @commands.command(aliases=['mine', 'backpack', 'items', 'inventory'], description='See what items you own.')
    async def possessions(self, ctx, member: discord.Member = None):
        if member is None:
            member = ctx.author
        items = await view_items(member)
        print(items)
        to_send = f'**You have {sum(item for item, _ in items)} items of {len(items)} different types:**\n'
        for item in items:
            to_send += f'{item[0]}x {item[1]}\n'
        to_send += "\n\n*Don't need an item anymore? you can sell it at any time for 60% of the price you bought it " \
                   "for with the sell command.*"
        await ctx.send(to_send)

    @commands.command()
    @commands.check(auth(2))
    async def econ_printout(self, ctx):
        print(self.bot.commodities_sell_prices)
        print(self.bot.commodities_buy_prices)
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
        for location_sell in self.bot.commodities_sell_prices:
            if location_sell[0] == ch_id:
                to_send = f'Sell prices at {location_sell[1]}:\n```\n'
                for item, price in sorted(location_sell[2].items(), key=lambda x: x[1]):
                    if price < threshold or threshold < 0:
                        spaces = ' ' * (17 - len(item))
                        random_modifier = random.random() * 0.001 + 1 - 0.0005
                        print(random_modifier)
                        to_send += f'{item}:{spaces} ~${price * random_modifier:,.2f}\n'
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
        for location_buy in self.bot.commodities_buy_prices:
            if location_buy[0] == ch_id:
                to_send = f'\nBuy prices at {location_buy[1]}:\n```\n'
                for item, price in sorted(location_buy[2].items(), key=lambda x: x[1]):
                    if price < threshold or threshold < 0:
                        spaces = ' ' * (17 - len(item))
                        random_modifier = random.random() * 0.001 + 1 - 0.0005
                        print(random_modifier)
                        to_send += f'{item}:{spaces} ~${price * random_modifier:,.2f}\n'
                append = '```'
                while len(to_send) > 1990:
                    await ctx.send(to_send[:1990] + append)
                    to_send = append + to_send[1990:]
                to_send += append
                await ctx.send(to_send)
                return
            count += 1

    @tasks.loop(seconds=PAYOUT_FREQUENCY)
    async def send_payouts(self):
        await distribute_payouts()
        print('Investment payouts sent.')
        channel = self.bot.get_channel(718949686412705862)
        if channel is not None:
            await channel.send('Investment payouts sent.')


def setup(bot):
    bot.add_cog(Economy(bot))
