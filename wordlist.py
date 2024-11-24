'''
STRUCTURE

Data Storage:
- wordlist.txt: stores the unique words seen so far
- lastRetrieval.json: stores the Unix timestamp in the Co-ordle title of the last co-ordle retrieved.

Functions:
- getWordlist: reads and loads wordlist.txt
- getNewWords: gets all words since the last retrieval using Unix timestamp.
    - getTimestamp - specialized function, gets unix timestamp from embed
    - getCoordles(timestamp) - specialized function
        isCoordle(): True if contains embed AND embed.color = red or = green
        solved(): True if embed.color = red, False if = green
        - get all messages from coordleBot (using user ID) -> message list
        - loop message list
            - if isCoordle() = True
                - if solved() = True -> getFound() else getSolution()
- updateWordlist: compares the list of new words and the existing wordlist, 
                  adds new unique words to wordlist.txt
- updateLastRetrieval: updates the last retrieved Unix timestamp

Execution Flow:
- getWordlist()
- getNewWords()
    - getTimestamp()
- updateWordlist()
- updateLastRetrieval()
'''

import os
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
EMBED_GREEN = '#78b159'
EMBED_RED = '#dd2e44'

# load token
load_dotenv()
TOKEN = os.getenv('TOKEN')

# --------- BOT SETUP --------- #
description = 'Analyzes user guesses for the Discord Co-ordle bot'
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='?', description=description, intents=intents)

# --------- FUNCTIONS --------- #
def isCoordle(message):
    '''
    Determines whether a message is a Co-ordle game by the inclusion of an embed and embed color
    '''
    if message.embeds:
        embed = message.embeds[0] # message.embeds returns a list
        if str(embed.color) == EMBED_GREEN or str(embed.color) == EMBED_RED:
            return True
    return False

def getWordlist():
    """
    Reads and loads wordlist.txt from the storage folder.
    """
    try:
        with open(WORDLIST_FILE, "r") as f:
            # read wordlist, strip newline characters -> return as set
            return set(f.read().splitlines())
    except FileNotFoundError:
        print("wordlist.txt not found")
        return set()

#def getTimestamp(message):
    #if isCoordle:

# MAIN
#wordlist = getWordlist()

# --------- EXECUTION --------- #
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('---------')

# --- TEST --- #

bot.run(TOKEN)