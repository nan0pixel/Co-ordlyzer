'''
eval.py

Complete:
- generates full pattern between list of allowed guesses and Co-ordle wordlist

Next:
- determining skillfulness of a guess via amount of information obtained

Uses original work by 3Blue1Brown (see readme for source), under CC BY-NC-SA 4.0 License.
Modifications to original code include:
- updated ternary representation of pattern with np.int64 (was np.uint8)
    - handles larger integers for 6-letter version of Wordle
- set word length as global constant (6) instead of determining length from first word of list
- renamed functions for clarity and preference
    - words_to_int_arrays -> wordsToInts
    - generate_pattern_matrix -> generatePatterns
    - pattern_to_int_list -> intToPattern
    - pattern_to_string -> patternToString
'''

import os
import numpy as np
import itertools as it

LENGTH = 6

MISS = np.uint8(0)
MISPLACED = np.uint8(1)
EXACT = np.uint8(2)

PROJECT_FOLDER = os.path.dirname(__file__)
STORAGE_FOLDER = os.path.join(PROJECT_FOLDER, 'storage')
COORDLE_WORDLIST = os.path.join(STORAGE_FOLDER, 'CoordleWordlist.txt')
SCRABBLE_WORDLIST = os.path.join(STORAGE_FOLDER, 'ScrabbleWordlist.txt')
PATTERNS_FILE = os.path.join(STORAGE_FOLDER, 'patterns.npy')

def wordsToInts(words):
    return np.array([[ord(c)for c in w] for w in words], dtype=np.uint8)

def getWordlist(file):
    wordlist = []
    with open(file) as f:
        wordlist.extend([word.strip() for word in f.readlines()])
    return wordlist

def generatePatterns(guesses, answers):
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
    guesses = getWordlist(SCRABBLE_WORDLIST)
    answers = getWordlist(COORDLE_WORDLIST)
    patterns = generatePatterns(guesses, answers)
    np.save(PATTERNS_FILE, patterns)

def intToPattern(pattern):
    result = []
    curr = pattern
    for x in range(LENGTH):
        result.append(curr % 3)
        curr = curr // 3
    return result

def patternToString(pattern):
    color = {MISS: '⬛', MISPLACED: '🟨', EXACT: '🟩'}
    return ''.join(color[letter] for letter in intToPattern(pattern))