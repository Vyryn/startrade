import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import discord
from discord.ext import commands

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SHEET_ID = '1p8mtlGzJHeu_ta0ZoowJhBB1t5xM5QRGbRSHCgkyjYg'
RANGE = 'Sheet1!A1:Z'


class Googleapi(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        creds = None
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
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        service = build('sheets', 'v4', credentials=creds)
        # Load in buy and sell prices from google sheets using sheets api
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SHEET_ID, range=RANGE).execute()
        values = result.get('values', [])
        bot.commodities_prices = values
        if not values:
            print('No data found.')
        else:
            print('Data:')
            for row in values:
                print(row)

    @commands.command(name='test')
    async def test(self, ctx):
        send = '\n'.join([str(line) for line in self.bot.commodities_prices])
        counter = 0
        to_send = ''
        for i in send:
            counter += 1
            to_send += i
            if counter > 1999:
                await ctx.send(to_send)
                to_send = ''
                counter = 0
        await ctx.send(to_send)


def setup(bot):
    bot.add_cog(Googleapi(bot))
