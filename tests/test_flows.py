import tempfile
import unittest
from contextlib import chdir
from types import SimpleNamespace as Obj
from unittest.mock import AsyncMock, MagicMock, patch

import functions
from tests.support import app, basics, googleapi, inert_credentials, mechanics
from utils import hit_calculator as combat


class Configuration(unittest.IsolatedAsyncioTestCase):
    async def test_guild_prefix_refreshes_channel_restrictions(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            chdir(tmp),
            patch.object(functions, "no_command_channels", []),
        ):
            functions.write_json_var("prefixes", {"42": "!"})
            functions.write_json_var("ignored_channels", ["101"])
            for guild, prefix in [(Obj(id=42), "!"), (Obj(id=43), ","), (None, ",")]:
                self.assertEqual(functions.get_prefix(None, Obj(guild=guild)), prefix)
            self.assertTrue(await functions.channel_check(Obj(channel=Obj(id=101))))
            functions.write_json_var("ignored_channels", [])
            functions.get_prefix(None, Obj(guild=None))
            self.assertFalse(await functions.channel_check(Obj(channel=Obj(id=101))))

    async def test_saved_commanders_enforce_thresholds_after_reload(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            chdir(tmp),
            patch.object(functions, "bot_commanders", {}),
        ):
            functions.write_json_var("auths", {"17": 3})
            functions.set_commanders()
            ctx = Obj(author=Obj(id=17))
            self.assertTrue(await functions.auth(3)(ctx))
            self.assertFalse(await functions.auth(4)(ctx))
            functions.get_commanders()["17"] = 4
            functions.save_commanders()
            functions.set_commanders()
            self.assertTrue(await functions.auth(4)(ctx))
            self.assertFalse(await functions.auth(1)(Obj(author=Obj(id=88))))


class DiscordFlows(unittest.IsolatedAsyncioTestCase):
    async def test_dice_alias_and_command_replies(self):
        bot = app.bot
        await mechanics.setup(bot)
        self.addAsyncCleanup(bot.remove_cog, "Mechanics")
        command = bot.get_command("DICE")
        self.assertIs(command, bot.get_command("roll"))
        with patch.object(
            mechanics.random, "choice", side_effect=lambda sides: sides[-1]
        ):
            for content, reply in [
                ("", 20),
                ("d999", 100),
                ("0d1", 2),
                (
                    "6d4",
                    "I've rolled 6x 4 sided dice and grouped them by roll:\n```\n6x 4```Total: 24",
                ),
            ]:
                ctx = Obj(author="Pilot", send=AsyncMock())
                await command(ctx, content=content)
                ctx.send.assert_awaited_once_with(reply)

    async def test_activity_credit_and_cooldown(self):
        bot = Obj(activity_channels=[10], recent_actives={}, ACTIVITY_COOLDOWN=7)
        pilot = Obj(id=1, bot=False)
        with patch.object(basics, "update_activity", new_callable=AsyncMock) as credit:
            for channel, author in [
                (11, pilot),
                (10, Obj(id=2, bot=True)),
                (10, pilot),
                (10, pilot),
            ]:
                await basics.do_activity_update(
                    bot, Obj(id=channel), author, "blue moon rises"
                )
            credit.assert_awaited_once_with(pilot, 1)


class SheetCombat(unittest.TestCase):
    def test_catalog_rows_feed_a_salvo(self):
        ship = [
            "Cruiser",
            "$1,000",
            "1",
            "",
            "0",
            "",
            "0",
            "0",
            "100",
            "200",
            "10",
            "Alliance",
            "source",
            "100",
            "",
            "",
            "capital",
            "heavy",
        ]
        weapon = ["Laser", "LS", "1", "10", "20", "0", "2", "20", "60", "100", "", "1"]
        bot = Obj(
            api_service=MagicMock(),
            SHEET_ID="test",
            RANGE_SHIPS="ships",
            RANGE_WEAPONS="weapons",
            warn="WARN",
        )
        get = bot.api_service.spreadsheets.return_value.values.return_value.get
        get.side_effect = lambda spreadsheetId, range: MagicMock(
            execute=lambda: {
                "values": [["header"], ["Incomplete"], ship]
                if range == "ships"
                else [["header"], ["short"], weapon]
            }
        )
        googleapi.load_from_sheet(bot)
        self.assertEqual(set(bot.values_ships), {"cruiser"})
        self.assertEqual(set(bot.values_weapons), {"ls"})
        with patch.object(combat.random, "random", side_effect=[0, 1, 0, 1]):
            self.assertEqual(
                combat.calc_dmg(
                    100,
                    100,
                    2,
                    100,
                    0,
                    bot.values_ships["cruiser"],
                    bot.values_weapons["ls"],
                    do_attenuation=True,
                ),
                (100, 80, 50, 4),
            )


class Startup(unittest.IsolatedAsyncioTestCase):
    async def test_setup_hook_registers_extensions_and_commands(self):

        bot = app.bot
        self.enterContext(patch.object(bot, "application_info", new_callable=AsyncMock))
        self.enterContext(
            patch("googleapiclient.discovery.build", return_value=MagicMock())
        )
        tempdir = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(chdir(tempdir))
        functions.write_json_var("auths", {})
        with inert_credentials():
            try:
                await bot.setup_hook()
                self.assertEqual(
                    set(bot.extensions),
                    {
                        "cogs.logging",
                        "cogs.dev",
                        "cogs.management",
                        "cogs.welcome",
                        "cogs.database",
                        "cogs.googleapi",
                        "cogs.basics",
                        "cogs.moderation",
                        "cogs.mechanics",
                        "cogs.economy",
                    },
                )
                for command in [
                    "prefix set",
                    "dice",
                    "refresh_data",
                    "newuser",
                    "ping",
                ]:
                    self.assertIsNotNone(bot.get_command(command), command)
            finally:
                for extension in reversed(tuple(bot.extensions)):
                    await bot.unload_extension(extension)
