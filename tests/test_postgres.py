"""Run the economy against a new local cluster, using only a private Unix socket."""

import os
import shutil
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import asyncpg

from tests.support import app, database


@unittest.skipUnless(
    shutil.which("initdb") and shutil.which("pg_ctl"),
    "PostgreSQL server tools required",
)
class Economy(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        cls.socket = tmp.name
        data = os.path.join(tmp.name, "data")
        subprocess.run(
            ["initdb", "-D", data, "-U", "tester", "-A", "trust", "--no-locale"],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                "pg_ctl",
                "-D",
                data,
                "-l",
                os.path.join(tmp.name, "server.log"),
                "-o",
                f"-c listen_addresses='' -k {tmp.name}",
                "-w",
                "start",
            ],
            check=True,
        )
        cls.addClassCleanup(
            subprocess.run,
            ["pg_ctl", "-D", data, "-m", "fast", "-w", "stop"],
            check=True,
        )

    async def asyncSetUp(self):
        pool = await asyncpg.create_pool(
            host=self.socket, database="postgres", user="tester", min_size=1
        )
        self.addAsyncCleanup(pool.close)
        self.enterContext(patch.object(database, "pool", pool))
        await database.ensure_tables_are_configured(app.bot)
        self.pilot = SimpleNamespace(id=1, name="Pilot")
        await pool.execute("TRUNCATE users CASCADE")
        await database.new_user(self.pilot)

    async def test_registration_is_idempotent(self):
        self.assertIn("Already Exists", await database.new_user(self.pilot))
        self.assertEqual(
            await database.check_bal(self.pilot), (50_000_000, 0, 50_000_000)
        )

    async def test_investment_and_insufficient_funds(self):
        self.assertEqual(
            await database.add_invest(self.pilot, 100), (100, 100, 49_999_900)
        )
        self.assertEqual(await database.add_invest(self.pilot, 50_000_000), (-2, 0, 0))
        self.assertEqual(
            await database.check_bal(self.pilot), (49_999_900, 100, 50_000_000)
        )

    async def test_transfer_updates_both_net_worths(self):
        recipient = SimpleNamespace(id=99, name="Merchant")
        await database.new_user(recipient)
        self.assertEqual(
            await database.transfer_funds(self.pilot, recipient, 500),
            (49_999_500, 50_000_500),
        )
        self.assertEqual(
            await database.check_bal(self.pilot), (49_999_500, 0, 49_999_500)
        )
        self.assertEqual(
            await database.check_bal_str("erch"),
            (50_000_500, 0, 50_000_500, 0, 0, "Merchant"),
        )

    async def test_duplicate_item_rolls_back_and_leaves_catalog_usable(self):
        item = ("ore", "mineral", "", 10, 20, "raw", "neutral")
        await database.add_item(*item)
        with self.assertRaises(asyncpg.UniqueViolationError):
            await database.add_item(*item)
        self.assertEqual(tuple(await database.find_item("or")), item)
        self.assertEqual(
            [row["name"] for row in await database.find_items_in_cat("min")], ["ore"]
        )
        await database.remove_item("ore")
        self.assertIsNone(await database.find_item("ore"))

    async def test_passive_income_applies_at_bonus_reset(self):
        await database.set_passive_income(self.pilot, 250)
        self.assertEqual(
            await database.get_passive_and_bonus_for_user(self.pilot), (250, 0)
        )
        await database.reset_bonus_for_all_users()
        self.assertEqual(
            await database.get_passive_and_bonus_for_user(self.pilot), (250, 250)
        )

    async def test_first_paycheck_eligible_then_timestamp_persists(self):
        newcomer = SimpleNamespace(id=10, name="Newcomer")
        with patch.object(database.time, "time", return_value=2_000_000_000):
            self.assertEqual(
                await database.check_last_paycheck(newcomer), 1_968_464_000
            )
            await database.set_last_paycheck_now(newcomer)
            self.assertEqual(
                await database.check_last_paycheck(newcomer), 2_000_000_000
            )

    async def test_catalog_removal_refunds_owned_units(self):
        await database.add_item("fuel", "supply", "", 10, 10, "", "")
        await database.add_possession(self.pilot, "fuel", 10, 2)
        await database.add_possession(self.pilot, "fuel", 10, 1)
        self.assertEqual(
            [tuple(row) for row in await database.view_items(self.pilot)], [(3, "fuel")]
        )
        await database.remove_item("fuel")
        self.assertFalse(await database.view_items(self.pilot))
        self.assertEqual(
            await database.check_bal(self.pilot), (50_000_030, 0, 50_000_030)
        )

    async def test_travel_requires_recent_activity(self):
        channel = SimpleNamespace(id=42)
        await database.update_activity(self.pilot, 99)
        with self.assertRaises(ValueError):
            await database.update_location(self.pilot, channel)
        await database.update_activity(self.pilot, 1)
        await database.update_location(self.pilot, channel)
        (user,) = await database.get_users()
        self.assertEqual((user["activity"], user["location"]), (100, 42))
