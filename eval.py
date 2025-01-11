'''
eval.py

--- FUNCTION ---
For each guess in Co-ordle, this part of the bot will analyze its...
1. SKILL - a score from 0-100 which is determined primarily by how much of the "solution space"
   that guess eliminates ON AVERAGE
2. LUCK - a designation of 'GOOD', 'AVERAGE', or 'BAD', determined by how much of the "solution space"
   that guess ACTUALLY eliminated, given the answer to the Co-ordle
        (For example, 'COCCYX' would usually return a low SKILL score, which is intuitive since it contains 
        some pretty uncommon letter combinations. However, if the answer to that Co-ordle just happens to be 
        'COCCYX', the LUCK would evaluate to 'GOOD' - i.e. "this guess is not very strategic, but in this 
        particular case, we got lucky.)
3. TOP 5 ALTERNATIVE GUESSES - what the bot determines as the best guesses at this step

Additionally, the program can generate a full pattern between list of allowed guesses and a "solution wordlist",
which is saved as a file for quicker reference.
    This solution wordlist is a combination of a list of the ~5000 most common 6-letter words according
    to Wiktionary, and a list of seen Co-ordle solutions put together from thousands of plays.

--- CREDIT ---
- The math behind all the pattern determination & generation and  entropy calculations uses original work by 
  3Blue1Brown (see readme for source), under CC BY-NC-SA 4.0 License. Modifications to original code include:
    - updated ternary representation of pattern with np.int64 (was np.uint8)
        - handles larger integers for 6-letter version of Wordle
    - modified code which was hardcoded to 5 letters to LENGTH letters (global const)
    - set word length as global constant (6) instead of determining length from first word of list
    - renamed functions/variables for clarity and preference
        - words_to_int_arrays -> wordsToInts
        - generate_pattern_matrix -> generatePatterns
        - pattern_to_int_list -> intToPattern
        - etc.
- The list of the ~5000 most common 6-letter words according to Wiktionary was put together and kindly shared 
  with me by another Co-ordle enthusiast. 

ADDITIONAL NOTES:
- Currently, the ?eval function can only be called as a reply to the Co-ordle you wish to analyze
  I hope to update it so that if called on its own, it simply analyzes the last completed Co-ordle
'''

import os
import re
import numpy as np
import itertools as it
import discord
import math
from discord.ext import commands
from discord.ui import Button, View
from scipy.stats import entropy
from dotenv import load_dotenv

LENGTH = 6

MISS = np.uint8(0)
MISPLACED = np.uint8(1)
EXACT = np.uint8(2)

BAD = -1
AVERAGE = 0
GOOD = 1

PROJECT_FOLDER = os.path.dirname(__file__)
STORAGE_FOLDER = os.path.join(PROJECT_FOLDER, 'storage')
COORDLE_WORDLIST = os.path.join(STORAGE_FOLDER, 'CoordleWordlist.txt')
COMMON_WL = os.path.join(STORAGE_FOLDER, 'Common6.txt')
SCRABBLE_WORDLIST = os.path.join(STORAGE_FOLDER, 'ScrabbleWordlist.txt')
PATTERNS_FILE = os.path.join(STORAGE_FOLDER, 'patterns.npy')

PATTERN_GRID = dict()

# --------- COORDLE CONSTANTS --------- #
EMBED_GREEN = '#78b159' # solved Co-ordle
EMBED_RED = '#dd2e44' # unsolved Co-ordle
COORDLE = 1071892566158614608

# BOT STUFF
load_dotenv()
TOKEN = os.getenv('TOKEN')


def wordsToInts(words): # credit: 3B1B
    return np.array([[ord(c)for c in w] for w in words], dtype=np.uint8)

def getWordlist(file):
    wordlist = []
    with open(file) as f:
        wordlist.extend([word.strip() for word in f.readlines()])
    return wordlist

def getPriors(solutions): # credit: 3B1B
    # returns dict of all guess words with 1s correponding to answer words
    guessWords = getWordlist(SCRABBLE_WORDLIST)
    return dict(
        (w, int(w in solutions))
        for w in guessWords
    )

def generatePatternsGrid(guesses, answers): # adapted from 3B1B
    numGuesses = len(guesses)
    numAnswers = len(answers)

    guessInts, answerInts = map(wordsToInts, (guesses, answers))
    matchGrid = np.zeros((numGuesses, numAnswers, LENGTH, LENGTH), dtype=bool)
    for i, j in it.product(range(LENGTH), range(LENGTH)):
        matchGrid[:, :, i, j] = np.equal.outer(guessInts[:, i], answerInts[:, j])
    
    patterns = np.zeros((numGuesses, numAnswers, LENGTH), dtype=np.uint8)
    for i in range(LENGTH):
        matches = matchGrid[:, :, i, i].flatten()
        patterns[:, :, i].flat[matches] = EXACT

        for k in range(LENGTH):
            matchGrid[:, :, k, i].flat[matches] = False
            matchGrid[:, :, i, k].flat[matches] = False
    
    for i, j in it.product(range(LENGTH), range(LENGTH)):
        matches = matchGrid[:, :, i, j].flatten()
        patterns[:, :, i].flat[matches] = MISPLACED
        for k in range(LENGTH):
            matchGrid[:, :, k, j].flat[matches] = False
            matchGrid[:, :, i, k].flat[matches] = False
    
    patternsToInt = np.dot(
        patterns,
        (3**np.arange(LENGTH)).astype(np.int64) # changed uint8 -> int64
    )

    return patternsToInt

def savePatterns():
    wordlist = getWordlist(SCRABBLE_WORDLIST)
    patterns = generatePatternsGrid(wordlist, wordlist)
    np.save(PATTERNS_FILE, patterns)

def intToPattern(pattern): # adapted from 3B1B
    result = []
    curr = pattern
    for x in range(LENGTH):
        result.append(curr % 3)
        curr = curr // 3
    return result

def patternToString(pattern): # adapted from 3B1B
    color = {MISS: '⬛', MISPLACED: '🟨', EXACT: '🟩'}
    return ''.join(color[letter] for letter in intToPattern(pattern))

def getPatterns(guesses, answers): # adapted from 3B1B
    PATTERN_GRID['grid'] = np.load(PATTERNS_FILE)
    PATTERN_GRID['index'] = dict(zip(
        getWordlist(SCRABBLE_WORDLIST), it.count()
    ))

    grid = PATTERN_GRID['grid']
    index = PATTERN_GRID['index']

    indexGuesses = [index[word] for word in guesses]
    indexAnswers = [index[word] for word in answers]

    return grid[np.ix_(indexGuesses, indexAnswers)]

def getPattern(guess, answer): # adapted from 3B1B
    index = PATTERN_GRID['index']
    if guess in index and answer in index:
        return getPatterns([guess], [answer])[0, 0]
    return None

def getRemainingWords(guess, pattern, solutions): # adapted from 3B1B
    allPatterns = getPatterns([guess], solutions).flatten()
    return list(np.array(solutions)[allPatterns == pattern])

def patternArrayToInt(array): # adapted from 3B1B
    return np.dot(array, 3**np.arange(LENGTH).astype(np.int64))

def getPatternBuckets(guess, possibleWords): # adapted from 3B1B
    '''
    For each guess, there are 3^LENGTH (in this case, 3^6) possible pattern results.
    This function groups a set of possible solutions by the pattern that the guess would generate
    '''
    buckets = [[] for x in range(3**LENGTH)] # number of possible patterns
    hashes = getPatterns([guess], possibleWords).flatten()
    for index, word in zip(hashes, possibleWords):
        buckets[index].append(word)
    return buckets

def getWeights(words, priors): # adapted from 3B1B
    # returns relative weights of a set of answer words (really, all equal
    # since the Co-ordle wordlist has equal chance of being answers)
    frequencies = np.array([priors[word] for word in words])
    total = frequencies.sum()
    if total == 0:
        return np.zeros(frequencies.shape)
    return frequencies / total

def getPatternDistribution(allowedGuesses, answers, weights): # adapted from 3B1B
    '''
    Returns an array of arrays, one for each possible guess (Scrabble wordlist),
    with the % likelihood of seeing the patterns [0 1 ... 3^LENGTH]
    '''
    patternGrid = getPatterns(allowedGuesses, answers)

    n = len(allowedGuesses)
    distribution = np.zeros((n, 3**LENGTH))
    n_range = np.arange(n)
    for j, prob in enumerate(weights):
        distribution[n_range, patternGrid[:, j]] += prob
    return distribution

def entropyOfDistribution(distribution, atol=1e-12): # adapted from 3B1B
    axis = len(distribution.shape) - 1
    return entropy(distribution, base=2, axis=axis)

def getEntropies(allowed_words, possible_words, weights): # adapted from 3B1B
    if weights.sum() == 0:
        return np.zeros(len(allowed_words))
    distribution = getPatternDistribution(allowed_words, possible_words, weights)
    return entropyOfDistribution(distribution)

# --------- UTILS --------- # (to be moved to dedicated utils file)
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
    return word.upper()

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

def getSolution(coordle):
    '''
    Gets solutions from solved and unsolved Co-ordles

    Parameter
        coordles: list of Co-ordle embeds
    Return
        solutions: list of solutions
    '''
    if isSolvedCoordle(coordle):
        return getSolved(coordle)
    else:
        return getUnsolved(coordle)

def getGuesses(coordle):
    embed = coordle.embeds[0]
    description = embed.description or ""
    content = description.strip().split('\n')

    regexPattern = re.compile(r':\w+_([a-zA-Z]):')
    guesses = []
    
    for row in content:
        guess = ''.join(regexPattern.findall(row))
        guesses.append(guess.upper())
    
    return guesses

# --------- EVAL CALCULATIONS --------- #
def getSkillScore(guess, expectedEntropies, possibleSols):
    actual = expectedEntropies[guess]
    print("actual: " + str(actual))
    rankings = sorted(expectedEntropies.items(), key=lambda x: x[1], reverse=True)
    optimal = rankings[0][1]
    weighingFactor = 1
    if guess not in possibleSols:
        # this weighing factor penalizes guesses that could NOT POSSIBLY BE a solution, 
        # given the pattern information we already have. The extent of the penalty 
        # depends on how many possible solutions there are left - 
        # if there are many solutions left, guessing a word that is known not to be the
        # solution can still be very skillful if it helps cut down the solution space 
        # significantly, and will receive minimal penalty. However, if there are only
        # few solutions left, it is less strategic to make such a guess, so it would 
        # receive a greater penalty. 
        weighingFactor = 1-1/len(possibleSols)

    infoRatio = actual / optimal if optimal != 0 else 1

    return round(infoRatio * weighingFactor * 100)

def expectedEntropies(guesses, possibleAnswers, priors):
    weights = getWeights(possibleAnswers, priors)
    entropies = getEntropies(guesses, possibleAnswers, weights)
    expectedEntropies = dict(zip(guesses, entropies))

    return expectedEntropies

def actualEntropy(guess, answer, possibleSols):
    # shortcut method, since for Co-ordle we can assume uniformity of prior distribution
    # (i.e. I'm not taking into account likelihood of a word as an answer
    # based on its popularity.)
    remainingSols = getRemainingWords(guess, getPattern(guess, answer), possibleSols)

    return math.log2(len(possibleSols)/len(remainingSols))

def getLuckScore(guess, answer, rankings, possibleSols):
    expected = rankings[guess]
    actual = actualEntropy(guess, answer, possibleSols)

    diff = actual - expected

    if abs(diff) <= 1:  # within 1 bit
        return AVERAGE
    elif diff < -1:  # more than 1 bit below expected
        return BAD
    else:  # more than 1 bit above expected
        return GOOD

def explanation(skill, luck):
    if skill < 50:
        skillDesc = "WEAK"
    elif skill <= 80:
        skillDesc = "DECENT"
    else:
        skillDesc = "GREAT"

    if luck == 'BAD':
        luckDesc = "WORSE THAN"
    elif luck == 'AVERAGE':
        luckDesc = "ABOUT AS"
    else:
        luckDesc = "BETTER THAN"
    
    sentence = (
        f"This was a `{skillDesc}` guess, and it performed `{luckDesc}` expected."
    )
    return sentence

def getBestGuesses(guess, expectedEntropies, possibleSols, rankLength):
    inSols = [word for word in expectedEntropies if word in possibleSols and word != guess]
    rankings = sorted(((word, expectedEntropies[word]) for word in inSols), key=lambda x: x[1], reverse=True)

    bestGuesses = [w for w, _ in rankings[:rankLength]]
    return bestGuesses

# --------- BOT --------- #

description = 'Analyzes user guesses for the Discord Co-ordle bot'
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='?', description=description, intents=intents)

class EvalPages(discord.ui.View):
    def __init__(self, guesses, skills, lucks, bests):
        super().__init__(timeout=None)
        self.guesses = guesses
        self.skills = skills
        self.lucks = lucks
        self.bests = bests
        self.current_page = 0

    def update_embed(self):
        guess = self.guesses[self.current_page]
        skill = self.skills[self.current_page]
        luck = self.lucks[self.current_page]
        bestsByGuess = self.bests[self.current_page]

        expl = explanation(skill, luck)

        bestGuessesList = "\n".join([f"{i+1}. `{best}`" for i, best in enumerate(bestsByGuess)])

        embed = discord.Embed(
            title=f"Evaluation of `{self.current_page + 1}.` `{guess}`",
            color=discord.Color.purple()
        )

        embed.description = (
        f"Skill: `{skill}`\n"
        f"Luck: `{luck}`\n\n"
        f"{expl}\n\n"
        f"**Some other good guesses were:**\n{bestGuessesList}"
        )
        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.gray, disabled=True)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        if self.current_page == 0:
            self.previous_button.disabled = True
        self.next_button.disabled = False

        embed = self.update_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        if self.current_page == len(self.guesses) - 1:
            self.next_button.disabled = True
        self.previous_button.disabled = False

        embed = self.update_embed()
        await interaction.response.edit_message(embed=embed, view=self)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('---------')

@bot.command(name='eval')
async def eval(ctx):
    possibleSols = getWordlist(COMMON_WL)
    guesslist = getWordlist(SCRABBLE_WORDLIST)
    priors = getPriors(possibleSols)
    patterns = getPatterns(guesslist, possibleSols)

    guesses = []
    skillScores = []
    luckScores = []
    bests = []

    # GET REFERENCED MESSAGE
    if ctx.message.reference is not None:
        referenced = await ctx.fetch_message(ctx.message.reference.message_id)

        if isSolvedCoordle(referenced) is not None:
            guesses = getGuesses(referenced)
            solution = getSolution(referenced)

            for guess in guesses:
                pattern = getPattern(guess, solution)
                expEntrs = expectedEntropies(guesslist, possibleSols, priors)
                bestGuesses = getBestGuesses(guess, expEntrs, possibleSols, 5)
                bests.append(bestGuesses)

                print(bests)
                print()

                # skill score
                skill = getSkillScore(guess, expEntrs, possibleSols)
                skillScores.append(skill)

                # luck score
                luck = getLuckScore(guess, solution, expEntrs, possibleSols)
                if luck == GOOD:
                    luckScores.append('GOOD')
                elif luck == AVERAGE:
                    luckScores.append('AVERAGE')
                else:
                    luckScores.append('BAD')

                # CUT DOWN SOLUTION SPACE FOR NEXT GUESS
                possibleSols = getRemainingWords(guess, pattern, possibleSols)
                print(possibleSols)

        else:
            await ctx.send("The referenced message must be a completed Co-ordle game.")
            return
    else:
        await ctx.send("This command must be called as a reply to a Co-ordle.")
        return

    # OUTPUT
    if guesses:
        
        view = EvalPages(guesses, skillScores, luckScores, bests)
        embed = view.update_embed()

        await ctx.send(embed=embed, view=view)
    else:
        await ctx.send("No valid guesses to evaluate.")
bot.run(TOKEN)
