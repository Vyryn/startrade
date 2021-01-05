import typing
from random import randrange
import random
from collections import Counter
import discord
from discord.ext import commands
from cogs.database import update_location
from functions import auth
from bot import log, logready

bonuses = {'vet': 10,
           'ace': 15,
           'hon': 20,
           'vetace': 25,
           'vethon': 30,
           'evading': 30}


def hit_determine(distance: float, effective_range: float, ship_length: float, bonus: float = 0, missile=False):
    hit_chance = 1
    if distance < 1:
        distance = 1
    r = distance / effective_range
    if distance > effective_range:
        hit_chance = 2 - r
    elif distance < effective_range and not missile:
        hit_chance = r
    if hit_chance < 0:
        hit_chance = 0
    length_modifier = ship_length / distance * 100
    if length_modifier < 0:
        length_modifier = 0
    elif length_modifier > 10:
        length_modifier = 10
    hit_chance *= 100
    result = hit_chance + (bonus / 10) + length_modifier
    # round
    hit_chance = int(hit_chance * 100) / 100
    result = int(result * 1000) / 1000
    roll = randrange(1, 100)
    if roll < result:
        hit = True
    else:
        hit = False
    # print([hit, bonus, length_modifier, hit_chance, result, roll])
    # http://prntscr.com/tgo2e3
    return hit, bonus, hit_chance, result, roll


def damage_determine(hull: float, shields: float, weap_damage_shields: float, weap_damage_hull: float,
                     pierce: float) -> (float, float):
    """Does damage with the provided weapon stats to the target hull and shields in absolute values *not* %s."""
    potential_shield_dmg = weap_damage_shields * (1 - pierce)
    hull_dmg = weap_damage_hull * pierce
    # print(f'DMG: {hull_dmg},  {potential_shield_dmg}')
    hull -= hull_dmg
    if shields > potential_shield_dmg:
        shields -= potential_shield_dmg
    else:  # If shields overkill
        undealt_shield_dmg = potential_shield_dmg - shields
        shields = 0
        # Need to convert this portion of damage to the hull-doing rate instead of the shields-doing rate
        extra_hull_dmg = undealt_shield_dmg / (weap_damage_shields+0.00001) * weap_damage_hull
        hull -= extra_hull_dmg
    new_hull = max(hull, 0)
    new_shields = max(shields, 0)
    # print([hull, shields, new_hull, new_shields])
    return new_hull, new_shields


def calc_dmg(i_hull: float, i_shield: float, n_weaps: int, dist: float, bonus: int, ship_info: dict,
             weap_info: dict) -> (float, float):
    """Determines whether a weapon hits and if so calculates damage. Returns the new hull and shields."""
    # Look up values
    ship_length = ship_info['len']
    max_hull = ship_info['hull']
    max_shield = ship_info['shield']
    effective_range = weap_info['range'] * 1000
    dist *= 1000
    weap_damage_shields = weap_info['shield_dmg']
    weap_damage_hull = weap_info['hull_dmg']
    weap_rate = int(weap_info['rate'])
    pierce = weap_info['pierce']
    missile = 'missile' in weap_info['note'].lower()
    # Values need to be in absolutes for damage_determine
    hull = perc_to_val(i_hull, max_hull)
    shield = perc_to_val(i_shield, max_shield)
    num_hits = 0
    # For each weapon, determine if it hits. If so, subtract the damage dealt by it.
    for i in range(n_weaps):
        for j in range(weap_rate):
            weap_hits = hit_determine(dist, effective_range, ship_length, bonus, missile=missile)[0]
            # print([dist, effective_range, ship_length, bonus, hull, shield, weap_hits])
            if weap_hits:
                num_hits += 1
                (hull, shield) = damage_determine(hull, shield, weap_damage_shields, weap_damage_hull, pierce)

    hit_perc = val_to_perc(num_hits, n_weaps * weap_rate)
    num_shots = n_weaps * weap_rate

    return val_to_perc(hull, max_hull), val_to_perc(shield, max_shield), hit_perc, num_shots


def val_to_perc(value, max_):
    """Converts a value as a portion of max to a percentage"""
    return round(value / max_ * 100)


def perc_to_val(perc, max_):
    """Converts a percentage of max to a value"""
    return perc / 100.0 * max_


class Mechanics(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        # TODO: Initialize Travel Channel

    # Events
    @commands.Cog.listener()
    async def on_ready(self):
        logready(self)

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
        log(f'{ctx.author} used the roll command with content: {content}.', self.bot.cmd)
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
        log(f'{ctx.author} attempted to travel to {channel}.')
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
        log(f'{ctx.author} used the calchit command with [distance: {distance}, effective_range: {effective_range},'
            f' ship_length: {ship_length}]. Their result was [luck: {luck}, hit_chance: {hit_chance},'
            f' result:{result}, roll: {roll}, hit: {hit}].')

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
        log(f'{ctx.author} used the calchits command with [distance: {distance}, effective_range: {effective_range},'
            f' ship_length: {ship_length}, num_guns: {num_guns}, attacker_upgrade: {attacker_upgrade}]. Their result'
            f' was: {hits} out of {num_guns} hit their target.')

    @commands.command()
    async def calcdamage(self, ctx, hull: typing.Optional[int] = 100, shields: typing.Optional[int] = 100,
                         name: str = '', dist: int = 10, n_weaps: int = 1, weap: str = 'TC', *, params=''):
        """
        Calculates damage.
        $calcdamage  (target hull) (target shields) "[target ship name]" [distance in km] [number of weapons] [weapon
        type] (-ace/-vet/-hon/-evading)
        """
        name = name.lower()
        weap = weap.lower()
        ship_info = self.bot.values_ships.get(name, [])
        weap_info = self.bot.values_weapons.get(weap, [])
        if not ship_info:
            return await ctx.send("Incomplete command. I didn't find that ship.")
        if not weap_info:
            return await ctx.send("Incomplete command. I didn't find that weapon.")
        # Apply evasion bonus for -ace, -evading etc
        evade_bonus = 0
        params = params.lower()
        for upgrade in bonuses:
            if upgrade[1:] in params:
                evade_bonus += bonuses[upgrade]
        new_hull, new_shields, hit_perc, num_shots = calc_dmg(hull, shields, n_weaps, dist, evade_bonus, ship_info,
                                                              weap_info)
        return await ctx.send(f'[{new_hull}] [{new_shields}] {name.title()}.\n({hit_perc}% of {num_shots} total shots '
                              f'hit)')

    @commands.command(description='Calculate points from shield (sbd), hull (ru), speed (mglt), length(m)'
                                  ' and armament (pts)')
    async def points(self, ctx, shield, hull, mglt, length, armament):
        """Calculate points from shield (sbd), hull (ru), speed (mglt), length(m) and armament (pts)"""
        await ctx.send(((shield + hull) / 3) + (mglt * length / 100) + armament)
        log(f'{ctx.author} used the points command.')


def setup(bot):
    bot.add_cog(Mechanics(bot))
