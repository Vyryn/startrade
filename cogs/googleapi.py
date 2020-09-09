import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from discord.ext import commands
from bot import log, logready


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
        result = sheet.values().get(spreadsheetId=self.bot.SHEET_ID, range=self.bot.RANGE).execute()
        values = result.get('values', [])
        bot.commodities_sell_prices = []
        bot.commodities_buy_prices = []
        if not values:
            log('No data found.', self.bot.warn)
            return
        reference_row = values[1]
        log(reference_row, self.bot.debug)
        row_count = -3  # Start at -3 because this simplifies indexing below; we don't want the first two rows.
        for row in values:
            row_count += 1
            if row_count >= 0:
                bot.commodities_buy_prices.append((int(row[2]), row[0], {}))
                bot.commodities_sell_prices.append((int(row[2]), row[0], {}))
                counter = 4
                row = row[4:]
                for entry in row:
                    if entry == '':
                        pass
                    else:
                        reference_val = reference_row[counter]
                        if counter % 2:  # Odd, buy price
                            bot.commodities_buy_prices[row_count][2][reference_val] = \
                                float(entry.replace(',', '').replace('$', ''))
                        else:  # Even, sell price
                            bot.commodities_sell_prices[row_count][2][reference_val] = \
                                float(entry.replace(',', '').replace('$', ''))
                            # even, therefore sell price
                    counter += 1
            # print(row)
            # print([row[2], row[0], row[3:]])
        log(f'Commodities Buy Prices: {bot.commodities_buy_prices}')
        log(f'Commodities Sell Prices: {bot.commodities_sell_prices}')

    # Events
    @commands.Cog.listener()
    async def on_ready(self):
        logready(self)


def setup(bot):
    bot.add_cog(Googleapi(bot))
