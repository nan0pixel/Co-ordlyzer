import discord
import re
import asyncio
import logging
import time

TOKEN = ''
TEMP = ''
COORDLE = 0
MESSAGE = 'Co-ordle for'

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
Determines the color of the embed
'''
def color(embed):
    color = embed.color
    if str(color) == '#78b159': # str(color) returns the hex
        return 'g'
    elif str(color) == '#dd2e44':
        return 'r'
    return None

async def update(channel, solutions):
    # progress tracker (via message edits)
    progress = await channel.send("Solutions found: 0")

    while True:
        # Update the message with the current count
        await progress.edit(content=f"Solutions found: {len(solutions)}")
        await asyncio.sleep(1)  # updates every ___ seconds

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$get'):
        startTime = time.time()
        solutions = set()
        channel = message.channel
        totalCoordles = 0

        updateTask = asyncio.create_task(update(channel, solutions))

        # Discord might limit rate
        async for msg in channel.history(limit=None): 
            if msg.embeds:  
                embed = msg.embeds[0]

                # green embeds - solved
                if color(embed) == 'g':
                    content = embed.description if embed.description else ""
                    line = content.strip().split('\n')[-1]
                    word = getWord(line)
                    solutions.add(word)

                    totalCoordles += 1

                # red embeds - unsolved
                elif color(embed) == 'r':
                    for f in embed.fields:
                        match = re.search(r'The solution was `(\w+)`', str(f))
                        if match:
                            solutions.add(match.group(1))

                    totalCoordles += 1

        runtime = time.time() - startTime
        updateTask.cancel()

        # send final results
        solutions = [s.upper() for s in solutions]
        if solutions:
            # printing first and last 3 of the set
            if len(solutions) > 6:
                display_solutions = ', '.join(solutions[:3]) + " ... " + ', '.join(solutions[-3:])
            else:
                display_solutions = ', '.join(solutions)
            await channel.send(display_solutions)

            await channel.send(f"Found {len(solutions)} unique solutions in {totalCoordles} total Co-ordles.")
            await channel.send(f"Runtime: {runtime:.2f}s")
            
            # write solutions to txt file
            with open("solutions.txt", "w") as f:
                for solution in solutions:
                    f.write(solution + "\n")
        else:
            await channel.send("No solutions found with green or red embeds.")

@client.event
async def on_error(event, *args, **kwargs):
    if isinstance(args[0], discord.errors.HTTPException) and args[0].status == 429:
        channel = kwargs.get('channel')
        if channel:
            await channel.send("Rate limited")
        logging.warning("Rate limit hit")

client.run(TOKEN)