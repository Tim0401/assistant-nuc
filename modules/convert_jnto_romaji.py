from pykakasi import kakasi
from unicodedata import normalize
import MeCab
import re
from pathlib import Path

UNIDIC_DIR = str(Path.home()) + r"/assistant-nuc/resources/dictionaries/unidic-mecab"
IPADIC_DIR = str(Path.home()) + r"/assistant-nuc/resources/dictionaries/ipadic-utf8"

d = {
    '0': 'zero',
    '1': 'one',
    '2': 'two',
    '3': 'three',
    '4': 'four',
    '5': 'five',
    '6': 'six',
    '7': 'seven',
    '8': 'eight',
    '9': 'nine',
    '10': 'ten',
    '11': 'eleven',
    '12': 'twelve',
    '13': 'thirteen',
    '14': 'fourteen',
    '15': 'fifteen',
    '16': 'sixteen',
    '17': 'seventeen',
    '18': 'eighteen',
    '19': 'nineteen',
    '20': 'twenty'
}


def convert_into_romaji(text):
    _kakasi = kakasi()
    _kakasi.setMode('H', 'a')
    _kakasi.setMode('K', 'a')
    _kakasi.setMode('J', 'a')
    conv = _kakasi.getConverter()

    mecab = MeCab.Tagger(r'-Ochasen -d ' + IPADIC_DIR)
    eng = MeCab.Tagger(r'-d ' + UNIDIC_DIR)
    normalized_text = normalize('NFKC', text)
    filename_romaji = ""

    #ipa unidic併用
    results = mecab.parse(normalized_text)
    for chunk in results.splitlines()[:-1]:
        engFlag = False
        eng_work = ""
        original = chunk.split('\t')
        isEng = eng.parse(original[0])
        for word in isEng.splitlines()[:-1]:
            work = word.split('\t')[1]
            comma = work.split(',')
            if len(comma) > 12 and comma[12] == '外':
                engFlag = True
                engTrance = comma[7]
                hyphen = engTrance.split('-')
                if len(hyphen) < 2:
                    engFlag = False
                    break
                else:
                    eng_work += hyphen[1] + " "
        if not engFlag:
            #数字を英語にするべき？→1-20だけを処理する
            #変換対象を読み（ひらがな）にするべき？→英語判定は漢字、ローマ字変換はカタカナの文字を使う
            if original[0] in d.keys():
                filename_romaji += d[original[0]] + " "
            else:
                filename_romaji += conv.do(original[1]) + " "
        else:
            filename_romaji += eng_work
    """
    # unidicオンリー
    isEng = eng.parse(text)
    for word in isEng.splitlines()[:-1]:
        engFlag = False
        eng_work = ""
        original = word.split('\t')
        comma = original[1].split(',')
        if len(comma) > 12 and comma[12] == '外':
            engTrance = comma[7]
            hyphen = engTrance.split('-')
            if len(hyphen) > 1:
                engFlag = True
                eng_work += hyphen[1] + " "
        if not engFlag:
            #数字を英語にするべき？→1-20だけを処理する
            if original[0] in d.keys():
                filename_romaji += d[original[0]] + " "
            else:
                filename_romaji += conv.do(original[1]) + " "
        else:
            filename_romaji += eng_work
    """

    #ローマ字と数字以外を空白にするべき？→Yes75 No25
    filename_romaji = re.sub(r'[^a-zA-Z0-9_ ]*', "", filename_romaji)
    #小文字にするべき？→Yes
    return filename_romaji.lower()


def convert_into_pronunciation(text):
    mecab = MeCab.Tagger()
    results = mecab.parse(text)
    pronunciation = ""
    print(results)
    for chunk in results.splitlines()[:-1]:
        pronunciation += chunk.split('\t')[1].split(',')[0]

    return pronunciation