# -*- coding: utf-8 -*-
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from time import sleep
import random

Voice_TYPE = [
    "/usr/share/hts-voice/mei/mei_normal.htsvoice",
    "/usr/share/hts-voice/mei/mei_angry.htsvoice",
    "/usr/share/hts-voice/mei/mei_sad.htsvoice",
    "/usr/share/hts-voice/mei/mei_bashful.htsvoice",
    "/usr/share/hts-voice/mei/mei_happy.htsvoice"
]

MEI_NORMAL = 0
MEI_ANGRY = 1
MEI_SAD = 2
MEI_BASHFUL = 3
MEI_HAPPY = 4

def jtalk_create_wave(t, type=0):
    if 0 > type or type > len(Voice_TYPE) - 1:
        type = 0
    open_jtalk = 'open_jtalk'
    mech = '-x /var/lib/mecab/dic/open-jtalk/naist-jdic'
    htsvoice = '-m ' + Voice_TYPE[type]
    speed = '-r 1.0'
    outwav = '-ow'
    hash = random.randint(0, sys.maxsize)
    cache_dir = str(Path.home()) + '/.cache/open_jtalk'

    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    path = cache_dir + "/" + str(hash) + '.wav'
    cmd = open_jtalk + " " + mech + " " + htsvoice + " " + speed + " " + outwav + " " + path
    c = subprocess.Popen(cmd.strip().split(" "), stdin=subprocess.PIPE)
    c.communicate(t.encode("utf-8"))[0]
    c.wait()
    print(path)
    return path


def google_tts_create_wave(t, lang):
    hash = random.randint(0, sys.maxsize)
    cache_dir = str(Path.home()) + '/.cache/google_tts'
    t = t.replace(" ", "%20")
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    filepath = cache_dir + "/" + str(hash) + '.mp3'
    outpath = cache_dir + "/" + str(hash) + '.wav'
    cmd = 'wget -q -U Mozilla -O ' + filepath
    url = "http://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&q="
    url += t + '&tl=' + lang
    cmd += " " + url
    try:
        subprocess.Popen(cmd.strip().split(" ")).wait(timeout=5)
    except subprocess.TimeoutExpired:
        return None

    cmd = "ffmpeg -i " + filepath + " -loglevel warning -vn -ac 1 -ar 44100 -acodec pcm_s16le -f wav " + outpath
    subprocess.Popen(cmd.strip().split(" ")).wait()
    print(outpath)
    return outpath


def google_tts(t, wait=False, lang="ja-JP"):
    result = google_tts_create_wave(t, lang)
    if result:
        c = subprocess.Popen(
            ['aplay', result],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
        if wait:
            c.wait()
        return True
    return False


def jtalk(t, type=0, wait=False):
    c = subprocess.Popen(
        ['aplay', jtalk_create_wave(t, type)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)
    if wait:
        c.wait()


def say_datetime():
    d = datetime.now()
    text = '%s月%s日、%s時%s分%s秒' % (d.month, d.day, d.hour, d.minute, d.second)
    jtalk(text)
    sleep(10)
    google_tts(text)


if __name__ == '__main__':
    args = sys.argv
    if len(args) > 1:
        jtalk(args[1], MEI_NORMAL, True)
        google_tts(args[1], True)
    else:
        say_datetime()
