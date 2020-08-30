# -*- coding: utf-8 -*-
import sys
import MeCab
from pathlib import Path

IPADIC_DIR = str(Path.home()) + r"/assistant-nuc/resources/dictionaries/ipadic-utf8"

def word_and_class(text):
    """
    Get word and class tuples list.
    """
    # Execute class analysis
    tagger = MeCab.Tagger('-Ochasen -d ' + IPADIC_DIR)
    tagger.parse('')
    result = tagger.parse(text)

    # Extract word and class
    word_class = []

    for chunk in result.splitlines()[:-1]:
        contents = chunk.split('\t')
        word_class.append((contents[0], contents[1], contents[2], contents[3]))

    return word_class


if __name__ == '__main__':
    result = word_and_class(sys.argv[1])
    print(result)
