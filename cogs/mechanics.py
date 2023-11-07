import math
import typing
from random import randrange
import random
from collections import Counter
import copy

import discord  # pylint: disable=import-error
from discord.ext import commands  # pylint: disable=import-error

from cogs.database import update_location
from functions import auth, utcnow
from bot import log, logready, quiet_fail
from utils.hit_calculator import hit_chance, hit_determine, calc_dmg, calc_dmg_multi


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
    async def roll(self, ctx, *, content: str = ""):
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
        if content != "":
            content = content.lower().replace(" ", "")
            args = content.split("d")
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
                f"{ctx.author}, you haven't done enough at your current location to be "
                f"able to move to travel to a new location yet. Try RPing a bit first.",
                delete_after=30,
            )

    @commands.command()
    async def statline(self, ctx, *, ship_name: str):
        """Displays the stats for a specified ship. Name must be exact.
        Do not include quotation marks unless they are part of the ship name."""
        gm_role = ctx.guild.get_role(977038517710495760)
        if gm_role not in ctx.author.roles:
            return await ctx.send("This command is for game masters.")
        info = self.bot.values_ships.get(ship_name.lower().strip(), [])
        if not info:
            return await ctx.send("I didn't find that ship. Spelling must be exact.")

        title = f"{info['fac']} {info['subclass']}\n"
        description = f"Armament: {info['arm']}\nSpecials: {info['spec']}\n"
        embed = discord.Embed(
            title=info["unclean_name"],
            description=description,
        )
        embed.add_field(name="Hull", value=f"{info['hull']} RU")
        embed.add_field(name="Shields", value=f"{info['shield']} SBD")
        embed.add_field(name="Speed", value=f"{info['speed']} MGLT")
        embed.add_field(name="Length", value=f"{info['len']}m")
        embed.add_field(name="Price", value=info["unclean_price"])
        embed.add_field(name="Points", value=f"{info['points']}")
        embed.color = discord.Color.darker_grey()
        embed.set_author(
            name=title,
            icon_url=self.bot.user.display_avatar.url,
            url=info["source"],
        )
        # description += f"Hull: {info['hull']}\n"
        # description += f"Shields: {info['shield']}\n"
        # description += f"Speed: {info['speed']} MGLT\n"
        # description += f"Length: {info['len']}m\n"
        # description += f"Price: {info['unclean_price']}\n"
        # description += f"Points: {info['points']}\n"
        embed.set_footer(text=f"Requested by {ctx.author}")
        embed.url = info["source"]
        embed.timestamp = utcnow()
        try:
            return await ctx.send(embed=embed)
        except discord.HTTPException:
            embed.set_author(name=title, icon_url=None, url=None)
            embed.url = None
            return await ctx.send(embed=embed)

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
        type] (-a/-v/-j/-bh/-t5/-aibh, etc)
        The following modifiers have objective criteria:
        -a (Ace): Used if the target has the Ace modifier. Applies a medium point bonus to dodge capability
        -v (Veteran): Used if the target has the Veteran modifier. Applies a medium point bonus to dodge capability.
            The combined bonus from a and v will not exceed the distance at which combat is taking place.
        -j (Jammed): Used if the firing ship is jammed. Applies a large point bonus to dodge capability.
        -bh (Bounty hunter): Always used if the target pilot is a bounty hunter. Applies a large point bonus to dodge capability.
        -tX (Tractor beam): Used if the target is tractor beamed. X indicates how many tractor beams are locked onto the target and defaults to 1.
            Each reduces target's speed by a moderate amount, to a minimum speed of 0 MGLT.
        -i (Immobile): Applied if the target ship is completely immobile, for example landed. Reduces target's speed to 0 MGLT.
        The following modifiers may be applied at GM discretion:
        -c (Clear advantage): Used for things like catching a vessel off guard. Doubles the hits landed.
        -u (Uncoordinated): Used for things like the attacker being a large fighter swarm. Reduces damage by a significant amount.
        -e (Evading): Used when the target is not firing weapons, is a relatively small or agile ship, and can plausibly evade.
            Applies a hit chance reduction that depends on the speed of the target ship.
        """
        if hull is None:
            hull = 100
        if shields is None:
            shields = 100
        params += " "
        name = name.lower()
        weap = weap.lower()
        ship_info = copy.deepcopy(self.bot.values_ships.get(name, []))
        weap_info = self.bot.values_weapons.get(weap, [])
        if not ship_info:
            return await ctx.send("Incomplete command. I didn't find that ship.")
        if not weap_info:
            return await ctx.send("Incomplete command. I didn't find that weapon.")
        # Apply evasion bonus for -ace, -evading etc
        _bonus = 0
        evading: bool = False
        uncoordinated: bool = False
        clear_advantage: bool = False

        params = params.lower().replace("-", "").replace(" ", "")
        if "v" in params:
            _bonus += 10
        if "a" in params:
            _bonus += 15
        _bonus = min(dist - 1, _bonus)
        if "j" in params:
            _bonus += 20
        if "bh" in params:
            _bonus += 25
        if "t" in params:
            # reduce speed by 10 MGLT times the parameter following t
            # default to 10 MGLT if parameter isn't included.
            try:
                tractors = int(params.split("t")[1].split(" ")[0])
            except (IndexError, ValueError):
                tractors = 1
            reduced_speed = ship_info["speed"] - 10 * tractors
            ship_info["speed"] = max(0, reduced_speed)
        if "i" in params:
            # Reduces speed to 0MGLT
            ship_info["speed"] = 0
        if "u" in params:
            # Reduces damage dealt by 30%
            uncoordinated = True
        if "c" in params:
            # Doubles # of hits landed
            clear_advantage = True
        if "e" in params:
            # reduces hit chance by a variable amount depneding on speed and size
            evading = True
        # Single ship, quick result

        if "x" not in params:
            new_hull, new_shields, hit_perc, num_shots = calc_dmg(
                hull,
                shields,
                n_weaps,
                dist,
                _bonus,
                ship_info,
                weap_info,
                evading=evading,
                clear_advantage=clear_advantage,
                uncoordinated=uncoordinated,
                do_attenuation=True,
            )
            return await ctx.send(
                f"[{new_hull}] [{new_shields}] {name.title()}.\n({hit_perc}% of {num_shots}"
                f" total shots hit)"
            )
        # Number of ships specified as -x30 or similar
        repeats = int(params.split("x")[1].split(" ")[0])
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
            clear_advantage=clear_advantage,
            uncoordinated=uncoordinated,
            do_attenuation=True,
        )
        to_send = ""
        for (_hull, _shields), num in new_ships.most_common():
            to_send += f"{num}x [{_hull}] [{_shields}] {name.title()}.\n"
        to_send += f"({hit_perc}% of {num_shots} total shots hit)"
        if len(to_send) > 1980:
            to_send = to_send[:1940] + "\nWarning: too many lines, cut off some."
        await ctx.send(to_send)
        # print("OVER HERE!!!! exiting calcdamage")

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
        self,
        ctx,
        mglt: float,
        current: typing.Optional[float] = None,
        target: typing.Optional[float] = None,
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
        """Range target inaccuracy, where target is the desired starting range in km and
        inaccuracy is the inaccuracy. Default inaccuracy scales inversely to target."""
        if target <= 0:
            return await ctx.send("Range must be greater than 0.")
        if inaccuracy < 0:
            inaccuracy = int(2 * 100 / target) + 10
        if target >= 200:
            inaccuracy = 10
        random_ = randrange(int(-1 * inaccuracy), int(inaccuracy))
        if target + random_ < 0:
            result = target - random_
        else:
            result = target + random_

        msg = f"Targetting a range of {target}km, with an inaccuracy of "
        msg += f"+-{inaccuracy}km, you come out at {result}km"
        if result < 0:
            msg += " **behind** your target."
        return await ctx.send(msg)

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
        description="Calculates how many missiles hit when defended by a given number of PDC"
    )
    @commands.check(not_in_invalid_channels())
    async def missiles(self, ctx, num_missiles: int, num_pdc: int, num_lc: int):
        """Calculate how many missiles **hit** when 20 missiles are launched at something
        defended by 10 PDC and 15 LC:
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


async def setup(bot):
    await bot.add_cog(Mechanics(bot))
