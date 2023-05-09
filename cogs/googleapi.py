import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from discord.ext import commands
from bot import log, logready
from functions import auth


def clean(s: str) -> float:
    """Cleans a google cell containing a float into a float"""
    try:
        return float(s.replace(",", "").replace("$", ""))
    except ValueError as e:
        return 0


def load_from_sheet(bot) -> None:
    log(f"Loading data from spreadsheet...")
    # Load in buy and sell prices from google sheets using sheets api
    sheet = bot.api_service.spreadsheets()
    result_ships = (
        sheet.values().get(spreadsheetId=bot.SHEET_ID, range=bot.RANGE_SHIPS).execute()
    )
    result_weapons = (
        sheet.values()
        .get(spreadsheetId=bot.SHEET_ID, range=bot.RANGE_WEAPONS)
        .execute()
    )
    values_ships = result_ships.get("values", [])
    values_weapons = result_weapons.get("values", [])
    if not values_ships or not values_weapons:
        log("No data found.", bot.warn)
        return
    bot.values_ships = {}
    bot.values_weapons = {}
    values_weapons = values_weapons[1:]
    values_ships = values_ships[1:]
    for line in values_weapons:
        if len(line) < 8:
            print(f"Skipping {line}")
            continue
        if "" in line[:8]:
            continue
        try:
            int(line[11][0])
        except TypeError:
            continue
        except IndexError:
            continue
        acronym = line[1]
        bot.values_weapons[acronym.lower()] = {
            "points_per": clean(line[2]),
            "hull_dmg": clean(line[3]),
            "shield_dmg": clean(line[4]),
            "pierce": clean(line[5]),
            "rate": clean(line[6]),
            "turn_speed": clean(line[7]),
            "accuracy": clean(line[8]),
            "attenuation": line[9],
            "note": line[10],
            "name": line[0],
            "range": 100,
        }
    for line in values_ships:
        if (
            "Incomplete" in line
            or "Enter Missing Values" in line
            or "Enter Length" in line
        ):
            continue
        bot.values_ships[line[0].lower()] = {
            "price": clean(line[1]),
            "points": clean(line[2]),
            "len": clean(line[13]),
            "shield": clean(line[8]),
            "hull": clean(line[9]),
            "speed": clean(line[10]),
            "fac": line[11],
            "class": line[16],
            "arm": line[3],
            "armp": clean(line[4]),
            "spec": line[5],
            "specp": clean(line[6]),
            "lar": clean(line[7]),
            "source": line[12],
        }
    log(
        f"Loaded {len(bot.values_ships.keys())} ready ships: {list(bot.values_ships.keys())}"
    )
    log(
        f"Loaded {len(bot.values_weapons.keys())} weapons: {list(bot.values_weapons.keys())}"
    )
    print("OVER HERE!!!! exiting load_from_sheet")


class GoogleAPI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        credentials = None
        log(f"Loading data from spreadsheet...")
        # Find the authorizations file
        if os.path.exists("token.pickle"):
            with open("token.pickle", "rb") as token:
                credentials = pickle.load(token)
        # If there are no (valid) credentials available, update credentials with login
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", bot.SCOPES
                )
                credentials = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open("token.pickle", "wb") as token:
                pickle.dump(credentials, token)
        bot.api_service = build("sheets", "v4", credentials=credentials)
        load_from_sheet(self.bot)
        print("OVER HERE!!!! exiting api init")

    # Events
    @commands.Cog.listener()
    async def on_ready(self):
        logready(self)

    @commands.command()
    @commands.check(auth(1))
    async def refresh_data(self, ctx):
        """Reloads data from the spreadsheet."""
        await ctx.send("Fetching data from spreadsheet...")
        load_from_sheet(self.bot)
        await ctx.send("Done.")


def setup(bot):
    bot.add_cog(GoogleAPI(bot))
