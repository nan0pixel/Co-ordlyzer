import discord
import re
from discord.ext import commands

TOKEN = ''
CHANNEL_ID = 0
MESSAGE = ''

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

'''
Gets word from co-ordle embed
'''
def getWord(line):
    letters = re.findall(r':green_([a-zA-Z]):', line)
    return ''.join(letters)

'''
Determines whether a co-ordle was solved from the color of the embed
'''
def solved(embed):
    color = embed.color
    if str(color) == '#78b159': # str(color) returns the hex
        return True
    else:
        return False
    
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$get'):
        if message.reference:
            reference = await message.channel.fetch_message(message.reference.message_id)
            if reference.embeds:
                embed = reference.embeds[0]  # Get the first embed
                content = embed.description if embed.description else "No description available."
                line = content.strip().split('\n')[-1]  # Split by lines and take the last one
                if solved(embed):
                    # return word
                    word = getWord(line)
                    await message.channel.send('The word is: ' + word)
                else:
                    await message.channel.send('This co-ordle was not solved')
            else:
                await message.channel.send('The referenced message does not contain any embeds')
        else:
            await message.channel.send('This command is not a reply to any message')
        

client.run(TOKEN)