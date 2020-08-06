from random import randrange
import random
from collections import Counter
import discord
from discord.ext import commands
from cogs.database import update_location
from functions import auth


def hit_determine(distance: float, effective_range: float, ship_length: float, bonus: float = 0):
    hit_chance = 1
    luck = float(randrange(1, 100)) + bonus
    if distance > effective_range:
        hit_chance = - (0.1111 * (distance / effective_range - 1) ** 2) + 1
    elif distance < effective_range * 0.3:
        hit_chance = -100 * ((distance / effective_range) - 0.32) ** 4 + 1
    if hit_chance < 0:
        hit_chance = 0
    intermediate_step = (101.0 * ship_length / distance) ** 2
    result = hit_chance * (intermediate_step + luck / 10)
    hit_chance = int(hit_chance * 100) / 100
    result = int(result * 1000) / 1000
    roll = randrange(1, 100)
    if roll < result:
        hit = True
    else:
        hit = False
    # http://prntscr.com/tgo2e3
    return hit, luck, hit_chance, result, roll


class Mechanics(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        # TODO: Initialize Travel Channel

    # Events
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'Cog {self.qualified_name} is ready.')

    # Commands
    @commands.command(aliases=['die', 'dice'], description='Roll some dice.')
    async def roll(self, ctx, *, content: str = None):
        """Roll some dice.
        Roll x d y dice, where x is the number of dice and y is the number of sides. Defaults to 1D20.
        If you only specify one number, this will be the number of D20s to roll. If you only specify dy,
        it will roll one die with the specified number of sides.
        If you roll more than 5 dice at once, it will group up your dice by roll to conserve channel space.
        If you roll less than five dice, you can specify single-word names for each roll by putting these names
         with spaces between after your roll. For example,
         "roll 2d20 constitution strength" will give you two d20s, one labeled Constitution and one labeled Strength.
        """
        summ = 0
        if content is not None:
            content = content.lower().split(' ')
            #            args_pre = content[0].lower().split('>')
            args = content[0].lower().split('d')
            try:
                num_dice = int(args[0])
            except ValueError:
                num_dice = 1
            try:
                num_sides = int(args[1])
            except ValueError:
                num_sides = self.bot.DEFUALT_DIE_SIDES
            except IndexError:
                num_sides = self.bot.DEFUALT_DIE_SIDES
        else:
            num_dice, num_sides = 1, self.bot.DEFUALT_DIE_SIDES
        if num_sides < 2:
            num_sides = 2
        elif num_sides > self.bot.MAX_DIE_SIDES:
            num_sides = self.bot.MAX_DIE_SIDES
        if num_dice < 1:
            num_dice = 1
        elif num_dice > 5:
            if num_dice > self.bot.MAX_DIE_ROLES:
                num_dice = self.bot.MAX_DIE_ROLES
            results = Counter([random.choice(range(1, num_sides + 1)) for __ in range(1, num_dice + 1)])
            to_send = f"I've rolled {num_dice}x {num_sides} sided dice and grouped them by roll:\n```\n"
            iterator = sorted(results.items(), key=lambda x: x[1], reverse=True)
            i = 0
            for roll, amount in iterator:
                summ += roll * amount
                i += 1
                if i % 10 == 0:
                    composed = f'{amount}x {roll}'
                else:
                    composed = f'{amount}x {roll}'
                to_send += composed + ','
                to_send += ' ' * (11 - len(composed))
            to_send = to_send.rstrip()[:-1] + '```'  # Remove the last comma and close codeblock
            to_send += f'Total: {summ}'
            return await ctx.send(to_send)
        if num_dice == 1:
            return await ctx.send(random.choice(range(1, num_sides + 1)))
        result = f'Rolled {num_dice}x {num_sides} sided dice:\n'
        for die in range(1, num_dice + 1):
            val = random.choice(range(1, num_sides + 1))
            summ += val
            try:
                flavor = content[die].title() + ':'
            except IndexError:
                flavor = 'You rolled a'
            result += f'> {flavor.replace("_", " ")} {val}.\n'
        result += f'Total: {summ}'
        await ctx.send(result)

    @commands.command()
    @commands.check(auth(1))
    async def travel(self, ctx, channel: discord.TextChannel):
        try:
            await update_location(ctx.author, channel)
            await ctx.send(f"*{ctx.author} traveled to {channel.mention}.*")
            # TODO: Send in a dedicated travel channel instead
        except ValueError:
            await ctx.send(f"{ctx.author}, you haven't done enough at your current location to be able to move to"
                           f" travel to a new location yet. Try RPing a bit first.", delete_after=30)

    @commands.command()
    async def calchit(self, ctx, distance: float, effective_range: float, ship_length: float):
        """Determine how a weapon hit goes.
        This allows you to simulate a weapon firing. Specify distance to the target, effective range of the weapon,
        and size of the target and it will do the rest: ,calchit 10000 8000 500 will tell you how it goes when a
        weapon with effective range 8000m fires from 10000m at a 500m long target.
        """
        hit, luck, hit_chance, result, roll = hit_determine(distance, effective_range, ship_length)
        await ctx.send(
            f'Luck roll: {luck}. Hit chance: {hit_chance} Result: {result} For hit, rolled a {roll}. Hit? {hit}')

    @commands.command()
    async def calchits(self, ctx, distance: float, effective_range: float, ship_length: float, num_guns: int,
                       attacker_upgrade='norm',
                       weap_type: str = 'TC'):
        """This allows you to simulate many weapons firing - rather more useful for combat. Specify distance to
        the target, effective range of the weapon, size of the target, and number of weapons, and it will tell you
        how many hits are successful. ,calchits 10000 8000 500 20 will tell you how many hits are successful when 20
        of the weapon from example 2 above are fired.
        You can also add a bonus for the attacker's luck chance if they are veteran, ace, etc, as follows:
        vet: +10
        ace: +15
        hon: +20
        vetace: +25
        vethon: +30
        These are used as: ,calchits 10000 8000 500 20 ace
        """
        if weap_type.casefold() == 'lc':
            num_guns *= 30
        elif weap_type.casefold() == 'pdc':
            num_guns *= 100
        if attacker_upgrade.casefold() == 'vet':
            bonus = 10
        elif attacker_upgrade.casefold() == 'ace':
            bonus = 15
        elif attacker_upgrade.casefold() == 'hon':
            bonus = 20
        elif attacker_upgrade.casefold() == 'vetace':
            bonus = 25
        elif attacker_upgrade.casefold() == 'vethon':
            bonus = 30
        else:
            bonus = 0
        hits = 0
        for i in range(0, num_guns):
            hit, _, _, _, _ = hit_determine(distance, effective_range, ship_length, bonus=bonus)
            if hit:
                hits += 1
        await ctx.send(f'{hits} out of {num_guns} weapons hit their target.')

    @commands.command(description='Calculate points from shield (sbd), hull (ru), speed (mglt), length(m) and armament (pts)')
    async def points(self, ctx, shield, hull, mglt, length, armament):
        """Calculate points from shield (sbd), hull (ru), speed (mglt), length(m) and armament (pts)"""
        await ctx.send(((shield + hull)/3) + (mglt*length/100) + armament)


def setup(bot):
    bot.add_cog(Mechanics(bot))
