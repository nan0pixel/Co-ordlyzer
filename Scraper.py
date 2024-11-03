import discord
import re

TOKEN = ''
CHANNEL_ID = 0
COORDLE = 0
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
def color(embed):
    color = embed.color
    if str(color) == '#78b159': # str(color) returns the hex
        return 'g'
    elif str(color) == '#dd2e44':
        return 'r'
    return None

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$get'):
        solutions = []
        # Discord might limit rate
        async for msg in message.channel.history(limit=None): 

            # find messages with embeds
            if msg.embeds:  
                embed = msg.embeds[0]

                # green embeds - solved
                if color(embed) == 'g':
                    content = embed.description if embed.description else ""
                    line = content.strip().split('\n')[-1] # get answer from "keyboard"
                    word = getWord(line)
                    solutions.append(word)
                
                # red embeds - unsolved
                elif color(embed) == 'r':
                    # look for "The solution was" message in fields for red embeds
                    for f in embed.fields:
                        match = re.search(r'The solution was `(\w+)`', str(f))
                        if match:
                            solutions.append(match.group(1))
        solutions = [s.upper() for s in solutions]
        if solutions:
            await message.channel.send("Found solutions: " + ', '.join(solutions))
        else:
            await message.channel.send("No solutions found with green or red embeds.")

client.run(TOKEN)