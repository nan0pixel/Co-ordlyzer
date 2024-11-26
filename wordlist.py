'''
--- DIRECTORY STRUCTURE ---
wordlist.py
/storage (created if doesn't exist)
    timestamps.json: (created if doesn't exist) stores the timestamp (encoded in message ID) 
    of the last Co-ordle retrieved by channel
    /wordlists (created if doesn't exist)
        {channel1ID}.txt
        {channel2ID}.txt
        (stores unique words seen so far by channel)

--- EXECUTION FLOW ---
?wordlist
    1. getTimestamp() - gets channel-specific timestamp of last Co-ordle retrieved
    2. getCoordles() - gets all Co-ordles from channel history since timestamp
    3. getSolutions() - gets solutions from Co-ordles (both solved and unsolved)
    4. updateWordlist() - updates channel-specific wordlist file with any new solutions
    5. updateTimestamp() - updates channel-specific timestamp to that of the most recent Co-ordle
    6. output - sends embed summarizing number of new Co-ordles and unique solutions found
'''

import os
import re
import json
import discord
from discord.ext import commands
from dotenv import load_dotenv

# --------- DIRECTORY --------- #
# folder paths
PROJECT_FOLDER = os.path.dirname(__file__)
STORAGE_FOLDER = os.path.join(PROJECT_FOLDER, 'storage')
WORDLISTS_FOLDER = os.path.join(STORAGE_FOLDER, "wordlists")

# file paths
LAST_RETRIEVAL_FILE = os.path.join(STORAGE_FOLDER, 'timestamps.json')

# Create folders if they don't exist
os.makedirs(STORAGE_FOLDER, exist_ok=True)
os.makedirs(WORDLISTS_FOLDER, exist_ok=True)

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
        embed = message.embeds[0] # message.embeds returns a list
        if str(embed.color) == EMBED_GREEN:
            return True
        elif str(embed.color) == EMBED_RED:
            return False
    return None

async def getCoordles(channel, timestamp):
    '''
    Gets all Co-ordles from specified timestamp (usu. since last retrieval)

    Parameters
        channel: Discord channel to fetch messages from
        timestamp: starting timestamp from which to filter messages
    Return
        coordles: list of Co-ordles
    '''
    coordles = []
    async for message in channel.history(after=discord.Object(id=timestamp), limit = None):
        if isSolvedCoordle(message) is not None:
            coordles.append(message)
            #print(f"Found Co-ordle: ID {message.id}, Title: {message.embeds[0].title}") # for debugging
    return coordles

def loadJson(path):
    '''
    Loads JSON file

    Parameter
        path: JSON file path
    Return
        Loaded JSON data (empty dictionary if file not found or empty)
    '''
    try:
        with open(path, "r") as f:
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
    with open(path, "w+") as f:
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
    timestamp = loadJson(LAST_RETRIEVAL_FILE)
    return timestamp.get(str(channelID), 0) # return 0 if no timestamp found

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
        retrievals = loadJson(LAST_RETRIEVAL_FILE)
        retrievals[str(channelID)] = newest
        saveJson(LAST_RETRIEVAL_FILE, retrievals)
    else:
        print("No new Co-ordles retrieved")

def getSolved(coordle):
    '''
    Gets solution from solved Co-ordle

    Parameter
        coordle: message containing solved Co-ordle 
    Return
        word: solution
    '''
    embed = coordle.embeds[0]
    description = embed.description or ""
    found = description.strip().split('\n')[-1] # i.e. last guess
    letters = re.findall(r':\w+_([a-zA-Z]):', found) # gets letters from emotes
    word = ''.join(letters)
    return word

def getUnsolved(coordle):
    '''
    Gets solution from unsolved Co-ordle

    Parameter
        coordle: message containing unsolved Co-ordle
    Return
        Solution
    '''
    embed = coordle.embeds[0]
    solution = embed.fields[-2].value # custom to Co-ordle structure
    word = re.search(r'`(\w+)`', solution)
    if word:
        return word.group(1)
    raise ValueError("Solution not found")

def getWordlist(channelID):
    '''
    Loads channel-specific wordlist file from storage folder

    Parameter
        channelID: channel ID
    Return
        Wordlist as list
    '''
    wordlistFile = os.path.join(WORDLISTS_FOLDER, f"{channelID}.txt")
    try:
        with open(wordlistFile, "r") as f:
            # strip newline characters -> return as list
            return [line.strip() for line in f]
    except FileNotFoundError:
        print(f"{channelID} has no existing wordlist")
        return []
    
def updateWordlist(channel, words):
    '''
    Updates channel-specific wordlist file with any unique solutions found

    Parameters
        channel: Discord channel
        words: list of words from new Co-ordles (not necessarily unique)
    Return
        numUnique: number of unique solutions found in new batch of Co-ordles
    '''
    channelID = channel.id
    wordlist = getWordlist(channelID)
    combined = set(wordlist + words)  # add new words
    numUnique = len(combined) - len(wordlist)

    wordlistFile = os.path.join(WORDLISTS_FOLDER, f"{channelID}.txt")
    with open(wordlistFile, 'w+') as f:
        f.write("\n".join(sorted(combined))) 
    return numUnique

def getSolutions(coordles):
    '''
    Gets solutions from solved and unsolved Co-ordles

    Parameter
        coordles: list of Co-ordle embeds
    Return
        solutions: list of solutions
    '''
    solutions = []
    for coordle in coordles:
        if isSolvedCoordle(coordle):
            solutions.append(getSolved(coordle))
        else:
            solutions.append(getUnsolved(coordle))
    solutions = [word.upper() for word in solutions]
    return solutions

# --------- EXECUTION --------- #
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('---------')

@bot.command(name='wordlist')
async def wordlist(ctx):
    channel = ctx.channel
    timestamp = getTimestamp(channel)
    coordles = await getCoordles(channel, timestamp)
    solutions = getSolutions(coordles)
    updateTimestamp(channel, coordles)
    numUnique = updateWordlist(channel, solutions)

    # OUTPUT
    embed = discord.Embed(
        title = "Wordlist Summary",
        description = (
            f"Found `{len(coordles)}` Co-ordle(s) since the last `?wordlist` call, "
            f"`{numUnique}` of which contained a yet unseen solution."
        ),
        color=discord.Color.purple()
    )
    embed.timestamp = ctx.message.created_at
    await ctx.send(embed=embed)

bot.run(TOKEN)