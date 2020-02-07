import sys
from collections import defaultdict
from string import ascii_lowercase
import math
import random
import ast



# replace all non lowercase or non alphabet characters with spaces
def removeNonLowerAlphaChar(inputString):
    outputString = ""
    for char in inputString:
        if char in ascii_lowercase:
            outputString += char
        else:
            outputString += " "
    return outputString

def normalizeDictionary(myDict):
    sumOfValues = sum(myDict.values())
    returnDict = defaultdict(float)
    for key in myDict.keys():
        returnDict[key] = myDict[key] / sumOfValues
    return returnDict

def getWordCountFromBook(filename):
#     print("reading " + filename)
    word_to_count = defaultdict(float)
    with open(filename, 'r') as bookFile:
        # the first two lines are read and interpreted as a dict
        firstTwoLines = bookFile.readline() + bookFile.readline()
        #slice off characters until we get to the opening curly bracket
        while firstTwoLines[0] != '{':
            firstTwoLines = firstTwoLines[1:]
#         print("decoding: " + firstTwoLines)
        metadata = ast.literal_eval(firstTwoLines)
        
        for line in bookFile.readlines():
            line = removeNonLowerAlphaChar(line.lower())
            words = line.split()
            for word in words:
                word_to_count[word] += 1
    return word_to_count, metadata
    
def getDistributions(bookFilenames, epsilon, takeLog):
    booknum_to_word_to_prob = [None]*len(bookFilenames)
    booknum_to_metadata = [None]*len(bookFilenames)
    word_set = set()
    for booknum in range(len(bookFilenames)):
        booknum_to_word_to_prob[booknum], booknum_to_metadata[booknum] = getWordCountFromBook(bookFilenames[booknum])
        for word in booknum_to_word_to_prob[booknum].keys():
            word_set.add(word)
    for booknum in range(len(bookFilenames)):
#         booknum_to_word_to_prob[booknum] = normalizeDictionary(booknum_to_word_to_prob[booknum])
        for word in word_set:
            booknum_to_word_to_prob[booknum][word] += epsilon
            if(takeLog):
                booknum_to_word_to_prob[booknum][word] = math.log(booknum_to_word_to_prob[booknum][word])
        booknum_to_word_to_prob[booknum] = normalizeDictionary(booknum_to_word_to_prob[booknum])
    return booknum_to_word_to_prob, booknum_to_metadata, word_set
            

def KullbackLeiblerDivergence(word_dist_p, word_dist_q, word_set):
    total = 0.0
        
    for word in word_set:
        prob_p = word_dist_p[word]
        prob_q = word_dist_q[word]
        if(prob_p > 0):
            total += prob_p * math.log(prob_p / prob_q)
    return total

def SymmetricKLDivergence(word_dist_1, word_dist_2, word_set):
    return (KullbackLeiblerDivergence(word_dist_1, word_dist_2, word_set) + 
            KullbackLeiblerDivergence(word_dist_2, word_dist_1, word_set) ) / 2

def randomGaussian(word_set):
    x = {}
#     print(x)
    for word in word_set:
        x[word] = random.gauss(0,1)
    return x

def normalizeVector(v):
    sumOfLengths = 0
    for val in v:
        sumOfLengths += val
    returnVector = [None] * len(v)
    for i in range(len(v)):
        v[i] /= sumOfLengths
    return v

def gaussian(x):
    return math.exp(-x^2)

def dotProduct(x, y):
    if len(x) != len(y):
        raise NameError("dotProduct encountered two vectors of different length")
    numberDimensions = len(x)
    returnValue = 0
    for word in x.keys():
        returnValue += x[word] * y[word]
    return returnValue

def readBookList(listFilename, pathname = ""):
    with open(listFilename, 'r') as bookFile:
        lines = bookFile.readlines()
    #remove newline characters, and add the pathname
    for i in range(len(lines)):
        lines[i] = pathname + lines[i].replace("\n","")
    return lines

def runFullComparison(booknum_to_word_to_prob, word_set, bookTitles):
    numBooks = len(booknum_to_word_to_prob)
    distances = [[0.0 for i in range(numBooks)] for j in range(numBooks)]
    for i in range(numBooks):
        for j in range(i,numBooks):
            distances[i][j] = KullbackLeiblerDivergence(booknum_to_word_to_prob[i], booknum_to_word_to_prob[j], word_set)
#             print("distance from {} to {} is {:.5f}".format(i,j,distances[i][j]) )
#     print("sending to csv printer: " + str(distances))
    printAsCSV(bookTitles, bookTitles, distances)

def runLSHComparison(booknum_to_word_to_prob, word_set, numReps, stringLength, verbose, bookTitles, transitiveClustering, numClasses):
    numBooks = len(booknum_to_word_to_prob)
    booknum_to_similarBooks = [set() for x in range(numBooks)]

    equivalencyClasses = [None] * numBooks

    rep = 0
    while rep < numReps and (len(equivalencyClasses) > numClasses):
        rep += 1
        booknum_strings = [""] * numBooks

        for stringIndex in range(stringLength):
            randomVector = randomGaussian(word_set)
            for booknum in range(numBooks):
                if(dotProduct(randomVector, booknum_to_word_to_prob[booknum]) > 0):
                    booknum_strings[booknum] += '1'
                else:
                    booknum_strings[booknum] += '0'
#         print(booknum_strings)
        reverseDictionary = defaultdict(set)
        for booknum in range(numBooks):
            reverseDictionary[booknum_strings[booknum]].add(booknum)
#         print(reverseDictionary)
        if(rep % 5 == 0 and verbose):
            print("Rep {}".format(rep))
        for bookset in reverseDictionary.values():
#             print("bookset: " + str(bookset))
            for booknum in bookset:
#                 print("for " + str(booknum) + " in " + str(bookset))
                newLikeBooks = bookset.difference(booknum_to_similarBooks[booknum])
                if(verbose and bool(newLikeBooks)):
#                     print(newLikeBooks)
                    for newBook in newLikeBooks:
                        if booknum < newBook:
                            print("{} is similar to {}".format(bookTitles[booknum],bookTitles[newBook]))
                booknum_to_similarBooks[booknum].update(bookset)
        #convert like books into equivalency classes
        equivalencyClasses = mergeSetsWithCommonElements(booknum_to_similarBooks)
                
            
                
    print("Final results:")
    if(transitiveClustering):
        equivalencyClassesWithNames = []
        equivalencyClassNum = 1
        for equivalencyClass in sorted(list(equivalencyClasses)):
            currentClassNames = []
            for booknum in equivalencyClass:
                currentClassNames.append(bookTitles[booknum])
#             equivalencyClassesWithNames.append(currentClassNames)
            print("Equivalency Class {}: {}".format(equivalencyClassNum, str(currentClassNames)))
            equivalencyClassNum += 1
    else:
        for booknum in range(numBooks):
            likeBooks = set()
    #         print(booknum_to_similarBooks[booknum])
    #         print(booknum_to_similarBooks[booknum].difference({booknum}))
            for likeBookNum in booknum_to_similarBooks[booknum].difference({booknum}):
                likeBooks.add(bookTitles[likeBookNum])
            print("{} is like {}".format(bookTitles[booknum],",".join(likeBooks)))
            
def mergeSetsWithCommonElements(listOfSets):
    changeMade = True
    listOfSets = list(listOfSets)
    while changeMade:
        changeMade = False
        setsToAdd = []
        setIndicesToRemove = []
        for i in range(len(listOfSets)):
            for j in range(i+1,len(listOfSets)):
                if(not changeMade and bool(set.intersection(listOfSets[i], listOfSets[j]))):
                    #the intersection is nonempty
                    setsToAdd.append(set.union(listOfSets[i], listOfSets[j]))
                    setIndicesToRemove += [i]
                    setIndicesToRemove += [j]
                    changeMade = True
#                     print("marked {} and {} as indices to be removed".format(i,j))
        setIndicesToRemove = sorted(list(set(setIndicesToRemove)))
        for i in reversed(range(len(setIndicesToRemove))):
            listOfSets.pop(setIndicesToRemove[i])
        for setToAdd in setsToAdd:
            listOfSets += [setToAdd]
    return listOfSets

def shiftOriginToMedian(booknum_to_word_to_prob, word_set, numBooks):
    for word in word_set:
        probs = [booknum_to_word_to_prob[booknum][word] for booknum in range(numBooks)]
        dimensionMedian = median(probs)
        for booknum in range(numBooks):
            booknum_to_word_to_prob[booknum][word] -= dimensionMedian
    return booknum_to_word_to_prob
        
    
def printAsCSV(colTitles, rowTitles, array):
#     print("printing csv: " + str(array))
    numRows = len(rowTitles)
    numCols = len(colTitles)
    stringArray = [None] * numRows
    for row in range(numRows):
        stringArray[row] = [None] * numCols
        for col in range(numCols):
            stringArray[row][col] = "{:.5f}".format(array[row][col])
    print(",\""+ "\",\"".join(colTitles) + "\"")
    for i in range(len(rowTitles)):
        print( "\"" + rowTitles[i] + "\"," + ",".join(stringArray[i]))

def median(lst):
    n = len(lst)
    s = sorted(lst)
    return (sum(s[n//2-1:n//2+1])/2.0, s[n//2])[n % 2] if n else None

def main(args):
    
    i = 0
    argError = False
    verbose = False
    epsilon = 0.1
    numBooks = 0
    numReps = 1
    numClasses = -1
    stringLength = 5
    bookFileNames = []
    logOfProbabilities = False
    fullComparison = False  #when false use LSH, when true, find the KL-divergence between all pairs
    useMedian = False
    transitiveClustering = True
    while(i < len(args) and not argError):
        if(args[i] == '-b'):
            if(i + 1 < len(args)):
                i += 1
                numBooks = int(args[i])
                if(i + numBooks < len(args)):
                    i += 1
                    bookFileNames = [None] * numBooks
                    for j in range(numBooks):
                        bookFileNames[j] = args[i]
                        j += 1
                        i += 1
                else:
                    argError = True
            else:
                argError = True
        elif(args[i] == '-bl'):
            if(i + 2 < len(args)):
                listFilename = args[i+1]
                pathname = args[i+2]
                bookFileNames = readBookList(listFilename, pathname)
                numBooks = len(bookFileNames)
                i+= 2
            else:
                argError = True
        elif(args[i] == '-r'):
            if(i + 1 < len(args)):
                i += 1
                numReps = int(args[i])
            else:
                argError = True
        elif(args[i] == '-s'):
            if(i + 1 < len(args)):
                i += 1
                stringLength = int(args[i])
            else:
                argError
        elif(args[i] == '-e'):
            if(i + 1 < len(args)):
                i += 1
                epsilon = float(args[i])
            else:
                argError = True
        elif(args[i] == '-v'):
            verbose = True
        elif(args[i] == '--full'):
            fullComparison = True
        elif(args[i] == '--logs'):
            logOfProbabilities = True
        elif(args[i] == '--nontransitive'):
            transitiveClustering = False #if a=b and b=c, then is a=c is not necessarily true
        elif(args[i] == '--usemedian'):
            useMedian = True
        elif(args[i] == '--classes'):
            if(i + 1 < len(args)):
                i += 1
                numReps = 999
                numClasses = int(args[i])
            else:
                argError = True
        else:
            print("Encountered unknown argument: " + args[i])
            argError = True
        i += 1
    if(argError or numBooks == 0):
        print("invalid input")
        return

    if(verbose):
        print("Books: " + str(bookFileNames))


    booknum_to_word_to_prob, booknum_to_metadata, word_set = getDistributions(bookFileNames, epsilon, logOfProbabilities)
    
    bookTitles = [None] * numBooks
    for i in range(numBooks):
        bookTitles[i] = booknum_to_metadata[i]['title']

    if(useMedian):
        booknum_to_word_to_prob = shiftOriginToMedian(booknum_to_word_to_prob, word_set, numBooks)
#     if(verbose):
#         for i in range(numBooks):
#             print(bookTitles[i] + ": " + str(booknum_to_word_to_prob[i]))
#     if(logOfProbabilities):
#         for booknum in range(numBooks):
#             for word in word_set:
#                 booknum_to_word_to_prob[booknum][word] = math.log(booknum_to_word_to_prob[booknum][word])


    if(fullComparison):
        runFullComparison(booknum_to_word_to_prob, word_set, bookTitles)
    else:
        runLSHComparison(booknum_to_word_to_prob, word_set, numReps, stringLength, verbose, bookTitles, transitiveClustering, numClasses)

    
    return

if __name__ == '__main__':
    main(sys.argv[1:])
    