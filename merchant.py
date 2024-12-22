import os
import re
import json
import discord
from collections import Counter
from discord.ext import commands
from dotenv import load_dotenv

# --------- DIRECTORY --------- #
# folder paths
PROJECT_FOLDER = os.path.dirname(__file__)
STORAGE_FOLDER = os.path.join(PROJECT_FOLDER, 'storage')
MERCHANT_FOLDER = os.path.join(STORAGE_FOLDER, 'merchant')

# file paths
TS_FILE = os.path.join(MERCHANT_FOLDER, 'merchantTS.json')

# Create folders if they don't exist
os.makedirs(STORAGE_FOLDER, exist_ok=True)
os.makedirs(MERCHANT_FOLDER, exist_ok=True)

# --------- CONSTANTS --------- #
EMBED_GREEN = '#78b159' # solved Co-ordle
EMBED_RED = '#dd2e44' # unsolved Co-ordle
COORDLE = 1071892566158614608

# load token
load_dotenv()
TOKEN = os.getenv('TOKEN')

# --------- BOT SETUP --------- #
description = 'Analyzes user guesses for the Discord Co-ordle bot'
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='?', description=description, intents=intents)

# --------- FUNCTIONS --------- #
# NEW WORDS RETRIEVED
def isSolvedCoordle(message):
    '''
    Determines if a message is a Co-ordle and whether it is solved or unsolved
    
    Parameter
        message: Discord message
    Returns
        True: is Co-ordle, solved
        False: is Co-ordle, unsolved
        None: not a Co-ordle
    '''
    if message.author.id == COORDLE and message.embeds:
        embed = message.embeds[0]
        if str(embed.color) == EMBED_GREEN:
            return True
        elif str(embed.color) == EMBED_RED:
            return False
    return None

async def getCoordles(channel, timestamp):
    coordles = []
    async for message in channel.history(after=discord.Object(id=timestamp), limit = None):
        if isSolvedCoordle(message) is not None:
            coordles.append(message)
    return coordles


def getSolvedCoordles(coordles):
    solved = [coordle for coordle in coordles if isSolvedCoordle(coordle)]
    return solved

def loadJson(path):
    '''
    Loads JSON file

    Parameter
        path: JSON file path
    Return
        Loaded JSON data (empty dictionary if file not found or empty)
    '''
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def saveJson(path, data):
    '''
    Saves JSON file

    Parameter
        path: JSON file path
        data: data to save
    '''
    with open(path, 'w+') as f:
        json.dump(data, f, indent=4)

def getTimestamp(channel):
    '''
    Gets timestamp (encoded in message ID) of last Co-ordle retrieval in the channel

    Parameter
        channel: Discord channel   
    Return
        Channel-specific timestamp
    '''
    channelID = channel.id
    timestamp = loadJson(TS_FILE)
    return timestamp.get(str(channelID), 0)

def updateTimestamp(channel, coordles):
    '''
    Updates timestamp (encoded in message ID) of last Co-ordle retrieval in channel

    Parameters
        channel: Discord channel
        coordles: list of coordles
    '''
    if coordles:
        newest = coordles[-1].id  # message ID of most recent Co-ordle
        channelID = channel.id
        retrievals = loadJson(TS_FILE)
        retrievals[str(channelID)] = newest
        saveJson(TS_FILE, retrievals)
    else:
        print('No new Co-ordles retrieved')

def getMerchant(coordle):
    embed = coordle.embeds[0]
    guesses = embed.description or ''
    guessers = re.findall(r'<@!(\d+)>', guesses)
    guesserIDs = list(map(int, guessers))
    
    possibleMerchant = guesserIDs[-1] # first guess = answer

    if possibleMerchant in guesserIDs[:-1]:
        return None  # not a merchant, made guesses earlier
    
    return possibleMerchant

def updateStats(saved, gamesPlayed, merchantings):
    for user in set(gamesPlayed.keys()).union(merchantings.keys()):
        if str(user) not in saved:
            saved[str(user)] = {'gamesPlayed': 0, 'merchantings': 0}
        
        saved[str(user)]['gamesPlayed'] += gamesPlayed.get(user, 0)
        saved[str(user)]['merchantings'] += merchantings.get(user, 0)
    
    return saved

def loadStatsFile(channel):
    channelID = channel.id
    path = os.path.join(MERCHANT_FOLDER, f'{channelID}.json')
    file = loadJson(path)
    return file

def saveStatsFile(channel, stats):
    channelID = channel.id
    path = os.path.join(MERCHANT_FOLDER, f'{channelID}.json')
    saveJson(path, stats)

def getGamesPlayed(coordles):
    gamesPlayed = Counter()
    for coordle in coordles:
        embed = coordle.embeds[0] 
        description = embed.description or ''
        
        participants = set(re.findall(r'<@!(\d+)>', description))
        
        for participant in participants:
            gamesPlayed[participant] += 1
    return gamesPlayed

def getMerchantings(coordles):
    solvedCoordles = getSolvedCoordles(coordles)
    merchants = [getMerchant(coordle) for coordle in solvedCoordles]
    merchants = [merc for merc in merchants if merc is not None]
    merchantings = Counter(merchants)
    return merchantings

def getMercPercs(allStats):
    mercPercs = {}
    for user, stats in allStats.items():
        games = stats.get('gamesPlayed', 0)
        merchantings_count = stats.get('merchantings', 0)
        if games > 0:
            percentage = (merchantings_count / games) * 100
            mercPercs[user] = percentage
        else:
            mercPercs[user] = 0  # no games played

    sortedMercPercs = sorted(
        mercPercs.items(), key=lambda x: x[1], reverse=True
    )
    return sortedMercPercs

# --------- EXECUTION --------- #
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('---------')

@bot.command(name='merchants')
async def merchants(ctx):
    channel = ctx.channel
    timestamp = getTimestamp(channel)
    coordles = await getCoordles(channel, timestamp)
    updateTimestamp(channel, coordles)

    # GAMES PLAYED
    gamesPlayed = getGamesPlayed(coordles)

    # GAMES MERCHANTED
    merchantings = getMerchantings(coordles)
    savedStats = loadStatsFile(channel)
    updatedStats = updateStats(savedStats, gamesPlayed, merchantings)
    mercPercs = getMercPercs(updatedStats)

    # OUTPUT
    rankings = '\n'.join(
        f"{i+1}. <@!{user}>: `{percentage:.1f}%` of '{updatedStats[user]['gamesPlayed']}' played"
        for i, (user, percentage) in enumerate(mercPercs)
    )

    embed = discord.Embed(
        title=f'Biggest Merchants in `{ctx.guild.name}`',
        description=(
            'Times merchanted / Co-ordles played\n\n' + rankings
        ),
        color=discord.Color.purple()
    )
    await ctx.send(embed=embed)

    # SAVE STATS
    saveStatsFile(channel, updatedStats)

bot.run(TOKEN)