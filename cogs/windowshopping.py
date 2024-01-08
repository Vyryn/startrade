from datetime import datetime
import random

import discord  # pylint: disable=import-error
from discord.ext import commands, tasks  # pylint: disable=import-error

from bot import log, logready
from functions import auth

weapon_shop: dict[str, int] = {
    "CDEF Blaster Pistol Common": 150,
    "Snub-Blaster Common": 190,
    "Weequay Blaster Pistol Common": 200,
    "CA-87 Common": 490,
    "EE-4 Common": 600,
    "HK-8 Sawtooth Common": 655,
    "RG-4D Common": 685,
    "CC-420 Uncommon": 700,
    "Coronet Arms Dueling Pistol Rare": 750,
    "SS-410 Police Special Uncommon": 800,
    "Westar-34 Uncommon": 900,
    "SE-14C Uncommon": 1000,
    "SE-14R Uncommon": 1000,
    "RK-3 Common": 1250,
    "K-16 Bryar Uncommon": 1350,
    "DE-10 Uncommon": 1400,
    "VT-33D Uncommon": 1400,
    "E-11D Rare": 1400,
    "E-22 Uncommon": 1500,
    "HC-01 Gambit Legendary": 16100,
    "CDEF Blaster Rifle Common": 450,
    "E-5 Uncommon": 600,
    "DT-57 Annihilator Common": 850,
    "E-10 Uncommon": 890,
    "AB-75 Bo-Rifle Uncommon": 900,
    "VES-700 Pulse Rifle Very Rare": 950,
    "CJ-9 Bo-Rifle Uncommon": 1100,
    "Galaar-15 Uncommon": 1100,
    "H-7 Equalizer Blaster Pistol Very Rare": 1200,
    "DC-15A Carbine Uncommon": 1500,
    "HB-9 Uncommon": 1600,
    "L-60 Uncommon": 2100,
    "A-300 Uncommon": 2100,
    "DC-15LE Rare": 2800,
    "TER-02 Starweird Legendary": 36000,
    "Blackscale Hall Sweeper Common": 1000,
    "OK-98 Common": 1100,
    "E-11D Rare": 1400,
    "DH-X Common": 1000,
    "DLT-18 Uncommon": 1300,
    "RT-97C Rare": 2000,
    "DC-15X Rare": 2800,
    "DLT-19D Uncommon": 3100,
    "E-5S Rare": 1550,
    "Valken-38X Uncommon": 2480,
    "ACP Array Gun Common": 4100,
    "ACP Repeater Gun Uncommon": 4100,
    "ASP-9 Vrelt Auto-Pistol Common": 150,
    "Black-Powder Pistol Common": 200,
    "Cycler Rifle Common": 400,
    "Scatter Gun Common": 275,
    "Sub Machine Gun Common": 540,
    "Model 38 Sharpshooter's Rifle Uncommon": 3000,
    "Thermal Detonator Uncommon": 2000,
    "Concussion Grenade Common": 100,
    "Fragmentation Grenade Common": 50,
    "Ion Grenade Common": 65,
    "Smoke Grenade Common": 100,
    "Sonic Grenade Rare": 2000,
    "Ion Blaster Common": 250,
    "Thermal Detonator Uncommon": 2000,
}


def prep_windowshop_update(items: dict[str, int], n: int = 5) -> dict[str, float]:
    """Prepares a list of n items to be presented as available shop stock."""
    assert n > 0 and n <= len(
        items
    ), "N must be greater than 0 and less than or equal to the number of items"
    selected: list[tuple[str, int]] = random.sample(list(items.items()), n)
    results: dict[str, float] = {}
    for key, value in selected:
        new_value = value / 2 + value * (0.1 + random.random())
        results[key] = new_value
    return results


async def windowshop_update(bot) -> None:
    """Updates the windowshop"""
    shops: dict[int, dict[str, int]] = {
        1193320352512753684: weapon_shop,
    }
    for ch, _shop in shops.items():
        shop = prep_windowshop_update(_shop)
        channel = await bot.fetch_channel(ch)
        if channel is None:
            log(f"Unable to find channel {ch}")
            continue
        # Prepare shop
        embed = discord.Embed(
            title="Welcome to the Adventure Shop!",
            description="Here are the items I have in stock today:",
            color=discord.Color.blue(),
        )
        embed.set_footer(
            text="Place an order with a GM if you wish to buy something. "
            "Automated transactions are not currently supported."
        )
        for item, price in shop.items():
            embed.add_field(
                name=item, value=f"{bot.credit_emoji}{price:,.0f}", inline=False
            )
        # Update message
        async for message in channel.history(limit=100):
            if message.author == bot.user:
                await message.edit(embed=embed)
                break
        else:
            await channel.send(embed=embed)


class Windowshopping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        global payout_frequency
        payout_frequency = self.bot.PAYOUT_FREQUENCY
        self.update_windowshop.start()  # pylint: disable=no-member
        log("Started the windowshop task (1).", self.bot.debug)

    def cog_unload(self):
        self.update_windowshop.cancel()  # pylint: disable=no-member
        log("Ended the winodwshop task.")

    # Events
    @commands.Cog.listener()
    async def on_ready(self):
        logready(self)

    # Commands

    @commands.command(description="Manually update the payout cycle. Staff only.")
    @commands.check(auth(1))
    async def update_shop(self, ctx):
        """
        Staff override to update the window shop
        Requires Commander role
        """
        await windowshop_update(self.bot)
        message = f"Updated the shop by request of {ctx.author.name}."
        embed = discord.Embed(
            title="Shop", description=message, timestamp=datetime.now()
        )
        await ctx.send(embed=embed)

    @tasks.loop(seconds=60 * 60 * 24)
    async def update_windowshop(self):
        await windowshop_update(self.bot)
        log("Shop updated.")


async def setup(bot):
    await bot.add_cog(Windowshopping(bot))
