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
from utils.hit_calculator import hit_chance, hit_determine, calc_dmg, calc_dmg_multi

bonuses = {"vet": 10, "ace": 15, "hon": 20, "jam": 20, "bh": 25}


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
    @commands.check(not_in_invalid_channels())
    async def calcdamage_old(
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
        for upgrade, val in bonuses.items():
            if upgrade in params:
                evade_bonus += val
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
        for _ in range(repeats):
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
        _bonus = 0
        params = params.lower()
        for upgrade, val in bonuses.items():
            if upgrade in params:
                _bonus += val
        evading: bool = False
        if "evad" in params:
            evading = True
        # Single ship, quick result
        if "-x" not in params:
            new_hull, new_shields, hit_perc, num_shots = calc_dmg(
                hull,
                shields,
                n_weaps,
                dist,
                _bonus,
                ship_info,
                weap_info,
                evading=evading,
                do_attenuation=True,
            )
            return await ctx.send(
                f"[{new_hull}] [{new_shields}] {name.title()}.\n({hit_perc}% of {num_shots}"
                f" total shots hit)"
            )
        # Number of ships specified as -x30 or similar
        repeats = int(params.split("-x")[1].split(" ")[0])
        ships = list()
        for _ in range(repeats):
            ships.append((hull, shields, ship_info))
        new_ships, hit_perc, num_shots = calc_dmg_multi(
            ships,
            n_weaps,
            dist,
            _bonus,
            weap_info,
            evading=evading,
            do_attenuation=True,
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
        aliases=["mglt", "distance"],
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
                "Oops, you were too ambitious. This ship was lost in hyperspace attempting "
                "fancy maneuvers, with all hands lost. Remove it from your UC, and any characters "
                "aboard are dead."
            )
        return await ctx.send(
            f"Targetting a range of {target}km, with an inaccuracy of +-{inaccuracy}km, "
            f"you come out at {target + random_}km."
        )

    @commands.command(description="Returns the hit % for a given weapon circumstances")
    @commands.check(not_in_invalid_channels())
    async def calcchance(
        self,
        ctx,
        distance: float,
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
            ship_length,
            weapon_accuracy,
            weapon_turn_rate,
            ship_speed,
            bonus=bonus,
        )
        await ctx.send(f"{res:.2f}%")

    @commands.command(
        description=f"Calculates how many missiles hit when defended by a given number of PDC"
    )
    @commands.check(not_in_invalid_channels())
    async def missiles(self, ctx, num_missiles: int, num_pdc: int, num_lc: int):
        """Calculate how many missiles **hit** when 20 missiles are launched at something defended by 10 PDC and 15 LC:
        $missiles 20 10 15
        """
        affected = min(num_missiles, num_pdc + num_lc)
        if num_pdc >= affected:
            blocked = affected * 0.9
        else:
            blocked = num_pdc * 0.9 + (affected - num_pdc) * 0.8
        await ctx.send(
            f"{num_missiles - blocked} missiles hit the target ({blocked} missiles were blocked)"
        )


def setup(bot):
    bot.add_cog(Mechanics(bot))
