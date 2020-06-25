import random
from collections import Counter

import discord
import typing

from discord.ext import commands


class Mechanics(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

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
        if content is not None:
            content = content.lower().split(' ')
            args = content[0].lower().split('d')
            try:
                num_dice = int(args[0])
            except ValueError:
                num_dice = 1
            try:
                num_sides = int(args[1])
            except ValueError:
                num_sides = 20
            except IndexError:
                num_sides = 20

        else:
            num_dice, num_sides = 1, 20
        if num_sides < 2:
            num_sides = 2
        elif num_sides > 50:
            num_sides = 100
        if num_dice < 1:
            num_dice = 1
        elif num_dice > 5:
            if num_dice > 100000:
                num_dice = 100000
            results = Counter([random.choice(range(1, num_sides + 1)) for die in range(1, num_dice + 1)])
            to_send = f"I've rolled {num_dice}x {num_sides} sided dice and grouped them by roll:\n```\n"
            iterator = sorted(results.items(), key=lambda x: x[1])
            i = 0
            for roll, amount in iterator:
                i += 1
                if i % 10 == 0:
                    composed = f'{amount}x {roll}'
                else:
                    composed = f'{amount}x {roll}'
                to_send += composed + ','
                to_send += ' ' * (11 - len(composed))
            to_send = to_send.rstrip()[:-1] + '```'  # Remove the last comma and close codeblock
            return await ctx.send(to_send)
        if num_dice == 1:
            return await ctx.send(random.choice(range(1, num_sides + 1)))
        result = f'Rolled {num_dice}x {num_sides} sided dice:\n'
        for die in range(1, num_dice+1):
            val = random.choice(range(1, num_sides + 1))
            try:
                flavor = content[die].title() + ':'
            except IndexError:
                flavor = 'You rolled a'
            result += f'> {flavor.replace("_", " ")} {val}.\n'
        await ctx.send(result)


def setup(bot):
    bot.add_cog(Mechanics(bot))
