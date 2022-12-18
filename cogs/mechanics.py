import math
import typing
from random import randrange
import random
from collections import Counter

import discord
from discord.ext import commands

from cogs.database import update_location
from functions import auth
from bot import log, logready, quiet_fail
from utils.hit_calculator import hit_chance

bonuses = {"vet": 10, "ace": 15, "hon": 20, "evad": 20, "jam": 20}


def hit_determine(
    distance: float,
    effective_range: float,
    ship_length: float,
    bonus: float = 0,
    missile=False,
    prow=False,
):
    if distance < 1:
        if effective_range >= distance:
            return True, bonus, 100, 100, 50
        else:
            distance = 1
    length_modifier = math.log(distance / (ship_length * 2)) - 1.4
    # length_modifier = ship_length / distance * 100
    if length_modifier < 1:
        length_modifier = 1
    elif length_modifier > 10:
        length_modifier = 10
    hit_chance = 1 / length_modifier
    r = distance / effective_range
    if distance > 2 * effective_range:
        hit_chance = 0
    elif distance > effective_range:
        hit_chance = hit_chance / r**3
    elif distance < effective_range and not missile:
        hit_chance = hit_chance * r
        if hit_chance < 0.2:
            hit_chance = 0.2
    if distance <= effective_range and prow:
        return True, bonus, 100, 100, 50
    if hit_chance < 0:
        hit_chance = 0
    hit_chance *= 100
    result = max(0.0, hit_chance - (bonus / 7.5))  # + length_modifier
    # round
    hit_chance = int(hit_chance * 100) / 100
    result = int(result * 1000) / 1000
    roll = randrange(1, 100)
    if roll < result:
        hit = True
    else:
        hit = False
    log([hit, bonus, length_modifier, hit_chance, result, roll], "DBUG")
    # http://prntscr.com/tgo2e3
    # http://prntscr.com/xcagno
    return hit, bonus, hit_chance, result, roll


def not_in_invalid_channels():
    async def inner(ctx, *args):
        if ctx.author.id == 125449182663278592:
            return True
        if ctx.channel.id not in [
            977038528364027986,
            977038528842186782,
            977038528364027985,
            977038529068683265,
            977038528842186791,
        ]:
            return False
        return True

    return inner


def damage_determine(
    hull: float,
    shields: float,
    weap_damage_shields: float,
    weap_damage_hull: float,
    pierce: float,
) -> (float, float):
    """Does damage with the provided weapon stats to the target hull and shields in absolute values *not* %s."""
    potential_shield_dmg = weap_damage_shields * (1 - pierce)
    hull_dmg = weap_damage_hull * pierce
    log(f"DMG: {hull_dmg},  {potential_shield_dmg}", "DBUG")
    if shields > 0 or pierce == 1:
        hull -= hull_dmg
    if shields > potential_shield_dmg:
        shields -= potential_shield_dmg
    else:  # If shields overkill
        undealt_shield_dmg = potential_shield_dmg - shields
        shields = 0
        # Need to convert this portion of damage to the hull-doing rate instead of the shields-doing rate
        portion_shield_overkill = undealt_shield_dmg / (potential_shield_dmg + 0.00001)
        extra_hull_dmg = portion_shield_overkill * weap_damage_hull
        hull -= extra_hull_dmg
    new_hull = max(hull, 0)
    new_shields = max(shields, 0)
    log([hull, shields, new_hull, new_shields], "DBUG")
    return new_hull, new_shields


def calc_dmg(
    i_hull: float,
    i_shield: float,
    n_weaps: int,
    dist: float,
    bonus: int,
    ship_info: dict,
    weap_info: dict,
) -> (float, float):
    """Determines whether a weapon hits and if so calculates damage. Returns the new hull and shields."""
    # Look up values
    weap_damage_shields = weap_info["shield_dmg"]
    weap_damage_hull = weap_info["hull_dmg"]
    weap_rate = int(weap_info["rate"])
    pierce = weap_info["pierce"]
    missile = "missile" in weap_info["note"].lower()
    prow = "prow" in weap_info["note"].lower()

    ship_length = ship_info["len"]
    max_hull = ship_info["hull"]
    max_shield = ship_info["shield"]
    effective_range = weap_info["range"] * 1000
    dist *= 1000
    # Values need to be in absolutes for damage_determine
    hull = perc_to_val(i_hull, max_hull)
    shield = perc_to_val(i_shield, max_shield)
    num_hits = 0
    # For each weapon, determine if it hits. If so, subtract the damage dealt by it.
    for i in range(n_weaps):
        for j in range(weap_rate):
            weap_hits = hit_determine(
                dist, effective_range, ship_length, bonus, missile=missile, prow=prow
            )[0]
            log(
                [dist, effective_range, ship_length, bonus, hull, shield, weap_hits],
                "DBUG",
            )
            if weap_hits:
                num_hits += 1
                (hull, shield) = damage_determine(
                    hull, shield, weap_damage_shields, weap_damage_hull, pierce
                )

    hit_perc = val_to_perc(num_hits, n_weaps * weap_rate)
    num_shots = n_weaps * weap_rate

    return (
        val_to_perc(hull, max_hull),
        val_to_perc(shield, max_shield),
        hit_perc,
        num_shots,
    )


def calc_dmg_multi(ships, n_weaps, dist, bonus, weap_info):
    """Randomly scatters damage between a bunch of different ships of the same type. Returns a list of hull and
    shields and amounts."""
    weap_damage_shields = weap_info["shield_dmg"]
    weap_damage_hull = weap_info["hull_dmg"]
    weap_rate = int(weap_info["rate"])
    pierce = weap_info["pierce"]
    missile = "missile" in weap_info["note"].lower()
    prow = "prow" in weap_info["note"].lower()
    total_hits = 0
    total_shots = 0

    for i in range(n_weaps):
        selected_ship = random.randrange(len(ships))
        i_hull, i_shield, ship_info = ships[selected_ship]
        new_hull, new_shields, hit_perc, num_shots = calc_dmg(
            i_hull, i_shield, 1, dist, bonus, ship_info, weap_info
        )
        ships[selected_ship] = (new_hull, new_shields, ship_info)
        total_hits += round(hit_perc / 100 * num_shots)
        total_shots += num_shots
    final_hit_perc = val_to_perc(total_hits, total_shots)
    log(ships, "DBUG")
    new_ships = Counter([(hull, shields) for hull, shields, _ in ships])
    return new_ships, final_hit_perc, total_shots


def val_to_perc(value, max_) -> int:
    """Converts a value as a portion of max to a percentage"""
    if max_ <= 0:
        return 0
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
    @commands.command(aliases=["die", "dice"], description="Roll some dice.")
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
        log(
            f"{ctx.author} used the roll command with content: {content}.", self.bot.cmd
        )
        summ = 0
        if content is not None:
            content = content.lower().split(" ")
            #            args_pre = content[0].lower().split('>')
            args = content[0].lower().split("d")
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
            results = Counter(
                [
                    random.choice(range(1, num_sides + 1))
                    for __ in range(1, num_dice + 1)
                ]
            )
            to_send = f"I've rolled {num_dice}x {num_sides} sided dice and grouped them by roll:\n```\n"
            iterator = sorted(results.items(), key=lambda x: x[1], reverse=True)
            i = 0
            for roll, amount in iterator:
                summ += roll * amount
                i += 1
                if i % 10 == 0:
                    composed = f"{amount}x {roll}"
                else:
                    composed = f"{amount}x {roll}"
                to_send += composed + ","
                to_send += " " * (11 - len(composed))
            to_send = (
                to_send.rstrip()[:-1] + "```"
            )  # Remove the last comma and close codeblock
            to_send += f"Total: {summ}"
            return await ctx.send(to_send)
        if num_dice == 1:
            return await ctx.send(random.choice(range(1, num_sides + 1)))
        result = f"Rolled {num_dice}x {num_sides} sided dice:\n"
        for die in range(1, num_dice + 1):
            val = random.choice(range(1, num_sides + 1))
            summ += val
            try:
                flavor = content[die].title() + ":"
            except IndexError:
                flavor = "You rolled a"
            result += f'> {flavor.replace("_", " ")} {val}.\n'
        result += f"Total: {summ}"
        await ctx.send(result)

    @commands.command()
    @commands.check(auth(1))
    async def travel(self, ctx, channel: discord.TextChannel):
        log(f"{ctx.author} attempted to travel to {channel}.")
        try:
            await update_location(ctx.author, channel)
            await ctx.send(f"*{ctx.author} traveled to {channel.mention}.*")
            # TODO: Send in a dedicated travel channel instead
        except ValueError:
            await ctx.send(
                f"{ctx.author}, you haven't done enough at your current location to be able to move to"
                f" travel to a new location yet. Try RPing a bit first.",
                delete_after=30,
            )

    @commands.command()
    async def calchit(
        self, ctx, distance: float, effective_range: float, ship_length: float
    ):
        """Determine how a weapon hit goes.
        This allows you to simulate a weapon firing. Specify distance to the target, effective range of the weapon,
        and size of the target and it will do the rest: ,calchit 10000 8000 500 will tell you how it goes when a
        weapon with effective range 8000m fires from 10000m at a 500m long target.
        """
        hit, luck, hit_chance, result, roll = hit_determine(
            distance, effective_range, ship_length
        )
        await ctx.send(
            f"Luck roll: {luck}. Hit chance: {hit_chance} Result: {result} For hit, rolled a {roll}. Hit? {hit}"
        )
        log(
            f"{ctx.author} used the calchit command with [distance: {distance}, effective_range: {effective_range},"
            f" ship_length: {ship_length}]. Their result was [luck: {luck}, hit_chance: {hit_chance},"
            f" result:{result}, roll: {roll}, hit: {hit}]."
        )

    @commands.command()
    async def calchits(
        self,
        ctx,
        distance: float,
        effective_range: float,
        ship_length: float,
        num_guns: int,
        attacker_upgrade="norm",
        weap_type: str = "TC",
    ):
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
        if weap_type.casefold() == "lc":
            num_guns *= 30
        elif weap_type.casefold() == "pdc":
            num_guns *= 100
        if attacker_upgrade.casefold() == "vet":
            bonus = 10
        elif attacker_upgrade.casefold() == "ace":
            bonus = 15
        elif attacker_upgrade.casefold() == "hon":
            bonus = 20
        elif attacker_upgrade.casefold() == "vetace":
            bonus = 25
        elif attacker_upgrade.casefold() == "vethon":
            bonus = 30
        else:
            bonus = 0
        hits = 0
        for i in range(0, num_guns):
            hit, _, _, _, _ = hit_determine(
                distance, effective_range, ship_length, bonus=bonus
            )
            if hit:
                hits += 1
        await ctx.send(f"{hits} out of {num_guns} weapons hit their target.")
        log(
            f"{ctx.author} used the calchits command with [distance: {distance}, effective_range: {effective_range},"
            f" ship_length: {ship_length}, num_guns: {num_guns}, attacker_upgrade: {attacker_upgrade}]. Their result"
            f" was: {hits} out of {num_guns} hit their target."
        )

    @commands.command()
    @commands.check(not_in_invalid_channels())
    async def calcdamage(
        self,
        ctx,
        hull: typing.Optional[int] = 100,
        shields: typing.Optional[int] = 100,
        name: str = "",
        dist: int = 10,
        n_weaps: int = 1,
        weap: str = "TC",
        *,
        params="",
    ):
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
            if upgrade in params:
                evade_bonus += bonuses[upgrade]
        # Single ship, quick result
        if "-x" not in params:
            new_hull, new_shields, hit_perc, num_shots = calc_dmg(
                hull, shields, n_weaps, dist, evade_bonus, ship_info, weap_info
            )
            return await ctx.send(
                f"[{new_hull}] [{new_shields}] {name.title()}.\n({hit_perc}% of {num_shots}"
                f" total shots hit)"
            )
        # Number of ships specified as -x30 or similar
        repeats = int(params.split("-x")[1].split(" ")[0])
        ships = list()
        for i in range(repeats):
            ships.append((hull, shields, ship_info))
        new_ships, hit_perc, num_shots = calc_dmg_multi(
            ships, n_weaps, dist, evade_bonus, weap_info
        )
        to_send = ""
        for (hull, shields), num in new_ships.most_common():
            to_send += f"{num}x [{hull}] [{shields}] {name.title()}.\n"
        to_send += f"({hit_perc}% of {num_shots} total shots hit)"
        if len(to_send) > 1980:
            to_send = to_send[:1940] + "\nWarning: too many lines, cut off some."
        await ctx.send(to_send)

    @commands.command(
        description="Calculate points from shield (sbd), hull (ru), speed (mglt), length(m)"
        " and armament (pts)"
    )
    @commands.check(not_in_invalid_channels())
    async def points(self, ctx, shield, hull, mglt, length, armament):
        """Calculate points from shield (sbd), hull (ru), speed (mglt), length(m) and armament (pts)"""
        await ctx.send(((shield + hull) / 3) + (mglt * length / 100) + armament)
        log(f"{ctx.author} used the points command.")

    @commands.command(
        description="Calculate time to get from starting distance to target distance",
        aliases=["mglt"],
    )
    @commands.check(not_in_invalid_channels())
    async def timespeed(
        self, ctx, mglt: float, current: float = None, target: float = None
    ):
        """Display how many turns until you're at the target distance.
        MGLT is the MGLT your're approaching at (subtract the two ship speeds if one ship is running away from another)
        Current is the current distance between the ships.
        Target is the target distance between the ships.
        If you don't put a target, this will instead display the distance gained per turn.
        If you only specify a MGLT, it will simply convert to km/turn
        """
        if mglt < 1:
            return await quiet_fail(ctx, "speed must be at least 1 MGLT.")
        elif current is not None and current < 0:
            return await quiet_fail(ctx, "you can't be a negative distance away.")

        rate = round(mglt * 0.432)
        if current is None:
            return await ctx.send(f"{mglt} MGLT = {rate} km/turn.")
        if target is not None:
            turns = math.ceil(math.fabs(current - target) / rate)
            return await ctx.send(
                f"Closing at a rate of {rate} km/turn, it will take {turns} turns to reach "
                f"{target}km."
            )
        else:
            return await ctx.send(
                f"Closing at a rate of {rate} km/turn, next turn distance will be "
                f"{round(current - rate)}km if headed toward the target or {round(current + rate)}km "
                f"if headed away."
            )

    @commands.command(description="Calculate a range coming out of hyperspace")
    @commands.check(not_in_invalid_channels())
    async def range(self, ctx, target: float, inaccuracy: float = -1):
        """range target inaccuracy, where target is the desired starting range in km and inaccuracy is the
        inaccuracy. Default inaccuracy scales inversely to target."""
        if target <= 0:
            return await ctx.send("Range must be greater than 0.")
        if inaccuracy < 0:
            inaccuracy = int(2 * 100 / target) + 10
        if target >= 200:
            inaccuracy = 10
        random_ = randrange(-1 * inaccuracy, inaccuracy)
        result = target + random_
        if result < 0:
            return await ctx.send(
                f"Oops, you were too ambitious. This ship was lost in hyperspace attempting "
                f"fancy maneuvers, with all hands lost. Remove it from your UC, and any characters "
                f"aboard are dead."
            )
        return await ctx.send(
            f"Targetting a range of {target}km, with an inaccuracy of +-{inaccuracy}km, "
            f"you come out at {target + random_}km."
        )

    @commands.command(description=f"Returns the hit % for a given weapon circumstances")
    @commands.check(not_in_invalid_channels())
    async def calcchance(
        self,
        ctx,
        distance: float,
        effective_range: float,
        ship_length: float,
        weapon_accuracy: float,
        weapon_turn_rate: float,
        ship_speed: float,
        bonus: float = 0,
    ):
        """Calculates the % chance a shot under the given circumstances hits.
        distance: in km
        ship_length: in meters
        weapon_accuracy: 1-100
        weapon_turn_rate: 1-100
        ship_speed: in MGLT

        bonus: A flat % subtracted from the hit chance after all other modifiers are applied
        """
        res = hit_chance(
            distance,
            effective_range,
            ship_length,
            weapon_accuracy,
            weapon_turn_rate,
            ship_speed,
            bonus=bonus,
        )
        await ctx.send(f"{res:.2f}%")


def setup(bot):
    bot.add_cog(Mechanics(bot))
