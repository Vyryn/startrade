import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from discord.ext import commands
from bot import log, logready


def clean(s: str) -> float:
    """Cleans a google cell containing a float into a float"""
    return float(s.replace(',', '').replace('$', ''))


class Googleapi(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        creds = None
        log(f'Loading data from spreadsheet...')
        # Find the authorizations file
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, update creds with login
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.bot.SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        service = build('sheets', 'v4', credentials=creds)
        # Load in buy and sell prices from google sheets using sheets api
        sheet = service.spreadsheets()
        result_ships = sheet.values().get(spreadsheetId=self.bot.SHEET_ID, range=self.bot.RANGE_SHIPS).execute()
        result_weapons = sheet.values().get(spreadsheetId=self.bot.SHEET_ID, range=self.bot.RANGE_WEAPONS).execute()
        values_ships = result_ships.get('values', [])
        values_weapons = result_weapons.get('values', [])
        if not values_ships or not values_weapons:
            log('No data found.', self.bot.warn)
            return
        bot.values_ships = {}
        bot.values_weapons = {}
        values_weapons = values_weapons[1:]
        values_ships = values_ships[1:]
        for line in values_weapons:
            if '' in line[:7]:
                continue
            try:
                int(line[9][0])
            except TypeError:
                continue
            except IndexError:
                continue
            acronym = line[1]
            bot.values_weapons[acronym.lower()] = {'points_per': clean(line[2]),
                                                   'hull_dmg': clean(line[3]),
                                                   'shield_dmg': clean(line[4]),
                                                   'pierce': clean(line[5]),
                                                   'rate': clean(line[6]),
                                                   'range': clean(line[7]),
                                                   'note': line[8],
                                                   'name': line[0]
                                                   }
        for line in values_ships:
            if 'Incomplete' in line or 'Enter Missing Values' in line:
                continue
            bot.values_ships[line[0].lower()] = {'price': clean(line[1]),
                                                 'points': clean(line[2]),
                                                 'len': clean(line[13]),
                                                 'shield': clean(line[8]),
                                                 'hull': clean(line[9]),
                                                 'speed': clean(line[10]),
                                                 'fac': line[11],
                                                 'class': line[16],
                                                 'arm': line[3],
                                                 'armp': clean(line[4]),
                                                 'spec': line[5],
                                                 'specp': clean(line[6]),
                                                 'lar': clean(line[7]),
                                                 'source': line[12]
                                                 }
        log(f'Loaded {len(bot.values_ships.keys())} ready ships: {list(bot.values_ships.keys())}')
        log(f'Loaded {len(bot.values_weapons.keys())} weapons: {list(bot.values_weapons.keys())}')

    # Events
    @commands.Cog.listener()
    async def on_ready(self):
        logready(self)


def setup(bot):
    bot.add_cog(Googleapi(bot))
