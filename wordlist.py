'''
STRUCTURE

Data Storage:
- wordlist.txt: stores the unique words seen so far
- lastRetrieval.json: stores the Unix timestamp in the Co-ordle title of the last co-ordle retrieved.

Functions:
- getWordlist: loads wordlist.txt
- getNewWords: gets all words since the last retrieval using Unix timestamp.
    - getTimestamp: gets timestamp (encoded in message ID) of last Co-ordle retrieved
    - getCoordles: list of all solved and unsolved Co-ordles from channel since timestamp
    - loop message list, isSolvedCoordle(message)
        - if True -> getFound()
        - if False -> getSolution()
        - if None -> skip (not a Co-ordle)
- updateWordlist: compares the list of new words and the existing wordlist, 
                  adds new unique words to wordlist.txt
- updateTimestamp: updates timestamp to that of the most recent Co-ordle retrieved

Execution Flow:
?wordlist
    - getWordlist()
    - getNewWords()
        - getTimestamp()
    - updateWordlist()
    - updateLastRetrieval()

Calls:
- ?wordlist

To-dos:
- create /storage, wordlist.txt, lastRetrieval.json if doesn't exist
'''

import os
import json
import discord
from discord.ext import commands
from dotenv import load_dotenv

# --------- DIRECTORY --------- #
# folder paths
STORAGE_FOLDER = os.path.dirname(__file__)
STORAGE_FOLDER = os.path.join(STORAGE_FOLDER, "storage")

# file paths
WORDLIST_FILE = os.path.join(STORAGE_FOLDER, "wordlist.txt")
LAST_RETRIEVAL_FILE = os.path.join(STORAGE_FOLDER, "lastRetrieval.json")

# Create storage folder if it doesn't exist
os.makedirs(STORAGE_FOLDER, exist_ok=True)

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
# CURRENT WORDLIST
def getWordlist():
    '''
    Loads wordlist.txt from storage folder
    '''
    try:
        with open(WORDLIST_FILE, "r") as f:
            # read wordlist, strip newline characters -> return as set
            return set(f.read().splitlines())
    except FileNotFoundError:
        print("wordlist.txt not found")
        return set()

# NEW WORDS RETRIEVED
def isSolvedCoordle(message):
    '''
    Determines if a message is a Co-ordle and whether it is solved or unsolved

    Returns:
    True -> solved
    False -> unsolved
    None -> not a Co-ordle
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

    Parameters:
        channel: Discord channel to fetch messages from
        timestamp: starting timestamp from which to filter messages

    Returns:
        list of Co-ordles
    '''
    coordles = []
    async for message in channel.history(after=discord.Object(id=timestamp), limit = None):
        if isSolvedCoordle(message) is not None:
            coordles.append(message)
            #print(f"Found Co-ordle: ID {message.id}, Title: {message.embeds[0].title}") # for debugging
    print(str(len(coordles))) # for debugging
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

    Parameter:
        path: JSON file path
        data: data to save
    '''
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving JSON file: {e}")

def getTimestamp(channel):
    '''
    Gets timestamp (encoded in message ID) of last Co-ordle retrieval in the channel
    '''
    channelID = channel.id
    lastRetrieval = loadJson(LAST_RETRIEVAL_FILE)
    return lastRetrieval.get(str(channelID), 0) # return 0 if no timestamp found

def updateTimestamp(channel, coordles):
    '''
    Updates timestamp (encoded in message ID) of last Co-ordle retrieval in the channel
    '''
    if coordles:
        newest = coordles[-1].id  # message ID of most recent Co-ordle
        channelID = channel.id
        retrievals = loadJson(LAST_RETRIEVAL_FILE)
        retrievals[str(channelID)] = newest
        saveJson(LAST_RETRIEVAL_FILE, retrievals)
    else:
        print("No new Co-ordles retrieved")

async def getNewWords(channel):
    words = []
    timestamp = getTimestamp(channel)
    coordles = await getCoordles(channel, timestamp)
    updateTimestamp(channel, coordles)

# --------- EXECUTION --------- #
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('---------')
'''
@bot.command(name='wordlist')
async def wordlist(ctx):
    channel = ctx.channel
    wordlist = getWordlist()

    #updateWordlist(new_words)
    #updateLastRetrieval(lastRetrieval)
'''
# --------- TEST --------- #
'''
@bot.command(name='test')
async def test(ctx):
    channel = ctx.channel
    await getNewWords(channel)
'''

bot.run(TOKEN)