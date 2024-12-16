import os

PROJECT_FOLDER = os.path.dirname(__file__)
STORAGE_FOLDER = os.path.join(PROJECT_FOLDER, 'storage')
WORDLIST_FOLDER = os.path.join(STORAGE_FOLDER, 'wordlists')
COORDLE_WORDLIST = os.path.join(STORAGE_FOLDER, 'CoordleWordlist.txt')


def getTotalWordlist(folder):
    wordlist = set()

    # loops through all files in wordlists folder
    for filename in os.listdir(folder):
        if filename.endswith('.txt'):
            filePath = os.path.join(folder, filename)

            with open(filePath, 'r') as file:
                words = file.read().splitlines()
                wordlist.update(words)

    return sorted(wordlist) # alphabetical

def saveTotalWordlist(directory, outputFile):
    wordlist = getTotalWordlist(directory)

    with open(outputFile, 'w+') as file:
        for word in wordlist:
            file.write(word + '\n')

saveTotalWordlist(WORDLIST_FOLDER, COORDLE_WORDLIST)
