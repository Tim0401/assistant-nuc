#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import argparse
import os.path
import json
import sys
import re
import subprocess
import datetime
import random

from time import sleep
from subprocess import Popen
from pathlib import Path
from enum import Enum
import xml.etree.ElementTree as ET
from gmusicapi import Mobileclient
from unicodedata import normalize
import alsaaudio
import threading
import dbus

HOME_DIR = str(Path.home())
MY_MODULE_DIR = HOME_DIR + "/assistant-nuc/modules"
RESOURCE_DIR = HOME_DIR + "/assistant-nuc/resources"
SCRIPT_DIR = HOME_DIR + "/assistant-nuc/scripts"

LAUNCH_VLC_CMD = "vlc -A alsa -I dummy --fullscreen --control dbus"
QDBUS_VLC_CMD = "qdbus org.mpris.MediaPlayer2.vlc /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player"

# dbus関連
SERVICE_NAME 		= 'org.mpris.MediaPlayer2.vlc'
OBJECT_PATH 		= '/org/mpris/MediaPlayer2'

MAIN_INTERFACE 		= 'org.mpris.MediaPlayer2'
PLAYER_INTERFACE 	= 'org.mpris.MediaPlayer2.Player'
PROP_INTERFACE		= 'org.freedesktop.DBus.Properties'

# my module
sys.path.append(MY_MODULE_DIR)
import word_and_class
import jtalk
from playscroll import Player
from playscroll import Repeat
from alert_timer import AlertTimer

import convert_jnto_romaji as cir

# config
import configparser
config_ini = configparser.ConfigParser()
config_ini.read(MY_MODULE_DIR + '/config.ini', encoding='utf-8')

# SE
START_SE = RESOURCE_DIR + "/start.wav"
END_SE = RESOURCE_DIR + "/end.wav"

# Play Music用プレイヤー
player = None
is_player_playing = False
PLAY_MUSIC_DEVICE_ID = config_ini['gmusicapi']['DeviceId']

# アラーム用
ALERT_FILE_PATH = RESOURCE_DIR + "/alert.mp3"
alert_timer = None

# コマンドタイマー用 (task_id,thread)
tasks = []

# ラジオチャンネル定数
RADIO_CHANNEL = {
    "abc": "ABC",
    "mbs": "MBS",
    "obc": "OBC",
    "cocolo": "CCL",
    "802": "802",
    "fmoh": "FMO",
    "日経": "RN1",
    "日経2": "RN2",
    "kiss": "KISSFMKOBE",
    "housou-daigaku": "HOUSOU-DAIGAKU"
}

RADIO_CHANNEL_NAME = {
    "ABC": "ABCラジオ",
    "MBS": "MBSラジオ",
    "OBC": "OBCラジオ",
    "CCL": "FM こころ",
    "802": "FMはちまるに",
    "FMO": "FM OSAKA",
    "RN1": "ラジオ日経第一",
    "RN2": "ラジオ日経第二",
    "KISSFMKOBE": "きす FM 神戸",
    "HOUSOU-DAIGAKU": "放送大学"
}


def power_off_pi():
    print('Good bye!')
    subprocess.call('sudo shutdown now', shell=True)


def reboot_pi():
    print('See you in a bit!')
    subprocess.call('sudo reboot', shell=True)


def say_ip():
    ip_address = subprocess.check_output(
        "hostname -I | cut -d' ' -f1", shell=True)
    print('My IP address is %s' % ip_address.decode('utf-8'))


def init_player():
    global player
    global alert_timer
    print("init...")
    player = Player(PLAY_MUSIC_DEVICE_ID)
    alert_timer = AlertTimer(ALERT_FILE_PATH)
    launch_vlc()
    t = threading.Timer(1, prevent_duplicate)
    t.start()


# playmusicの再生とその他の重複防止
def prevent_duplicate():
    global player
    if player.playing:
        try:
            bus = dbus.SessionBus()
            vlc_media_player_obj = bus.get_object(SERVICE_NAME, OBJECT_PATH)
            props_iface = dbus.Interface(vlc_media_player_obj, PROP_INTERFACE)
            pb_stat = props_iface.Get(PLAYER_INTERFACE, 'PlaybackStatus')
            if pb_stat == "Playing":
                player.stop()
        except:
            pass
    t = threading.Timer(1, prevent_duplicate)
    t.start()


def play_music(wordlist):
    global player
    global is_player_playing
    start = 0
    start_options = []
    end = 0

    isLocal = True
    isCloud = True

    isPlaylist = True
    isAlbum = True
    isSong = True
    isArtist = False
    isRepeat = False
    isRandom = False

    # 検索ワード抽出
    for index, word in enumerate(wordlist):
        for target in ComList.play.value:
            if word == target:
                end = index
        for target in ["プレイリスト"]:
            if word == target:
                start = index + 1
                isAlbum = False
                isSong = False
        for target in ["アルバム"]:
            if word == target:
                start = index + 1
                isPlaylist = False
                isSong = False
        for target in ["アーティスト"]:
            if word == target:
                start = index + 1
                isArtist = True
                isPlaylist = False
                isSong = False
                isAlbum = False
        for target in ["ネット", "インターネット"]:
            if word == target:
                start = index + 1
                isLocal = False
        for target in ["ローカル"]:
            if word == target:
                start = index + 1
                isCloud = False
        for target in ["の", "で", "から"]:
            if word == target:
                start_options.append(index + 1)
    # ランダム・リピート指定
    for index, word in enumerate(wordlist):
        for target in ["ランダム"]:
            if word == target:
                end = index
                isRandom = True
        for target in ["リピート"]:
            if word == target:
                end = index
                isRepeat = True
        if isRandom or isRepeat:
            break
    # ーの曲、ーの歌の場合、アーティスト検索もする
    for index, word in enumerate(wordlist[:-1]):
        if word == "の":
            if wordlist[index + 1] == "曲" or wordlist[index + 1] == "歌":
                end = index
                isArtist = True
                wordlist[index] = ""
                wordlist[index + 1] = ""
                break

    # 検索ワード作成
    title = None
    search_word = wordlist
    # 助詞削除
    if search_word[end - 1] == 'を':
        end -= 1
    # 検索バリエーション作成
    start_options.insert(0, start)
    # ローカル検索
    for st in start_options:
        if not isLocal:
            break
        title = ""
        for i in range(st, end):
            title += search_word[i]
        if not title:
            title = None
            continue

        converted_word = cir.convert_into_romaji(title)
        print(converted_word)

        if isArtist:
            title = player.load_artist(converted_word)
            if title is not None:
                isPlaylist = False
                isSong = False
                isAlbum = False
                break
        if isPlaylist:
            title = player.load_playlist(converted_word)
            if title is not None:
                isSong = False
                isAlbum = False
                isArtist = False
                break
        if isSong:
            title = player.load_song(converted_word)
            if title is not None:
                isPlaylist = False
                isAlbum = False
                isArtist = False
                break
        if isAlbum:
            title = player.load_album(converted_word)
            if title is not None:
                isPlaylist = False
                isSong = False
                isArtist = False
                break

    # ローカルになかったらクラウド曲検索
    # 課金やめたのでコメントアウト
    '''
    if title is None:
        for index, st in enumerate(start_options):
            if not isCloud or index > 1:
                break
            title = ""
            for target in ["の", "で", "から"]:
                if target == search_word[st]:
                    st += 1
                    break
            for i in range(st, end):
                title += search_word[i] + " "
            if not title:
                title = None
                continue

            print(title)
            title = player.load_cloud(title, isArtist, isSong, isAlbum)
            if title is not None:
                isAlbum = False
                isPlaylist = False
                isSong = False
                isArtist = False
                break

    '''
    # どこにもなかったら終了
    if title is None:
        return False

    stop_all_and_launch()

    # title = cir.convert_into_pronunciation(title)
    print(title)
    if isPlaylist:
        voice = "プレイリスト、" + title
    elif isAlbum:
        voice = "アルバム、" + title
    elif isArtist:
        voice = "アーティスト、" + title
    elif isSong:
        voice = title
    else:
        voice = "プレイミュージックから、" + title

    if isRandom:
        player.random = True
        voice += " をランダム再生します。"
    elif isRepeat:
        player.repeat = Repeat.playlist
        voice += " をリピート再生します。"
    else:
        voice += " を流します。"

    if not jtalk.google_tts(voice, True):
        jtalk.jtalk(voice, jtalk.MEI_NORMAL, True)
    player.start_playlist()
    is_player_playing = True

    return True


def play_random(wordlist):
    global player
    global is_player_playing
    if is_player_playing:
        if is_includes(wordlist, ComList.stop.value):
            player.random = False
            jtalk.jtalk("ランダム再生はオフです。", jtalk.MEI_NORMAL, True)
        else:
            player.random = True
            jtalk.jtalk("ランダム再生はオンです。", jtalk.MEI_NORMAL, True)
        return True

    return False


def play_repeat(wordlist):
    global player
    global is_player_playing
    if is_player_playing:
        if is_includes(wordlist, ComList.stop.value):
            player.repeat = Repeat.none
            jtalk.jtalk("リピート再生はオフです。", jtalk.MEI_NORMAL, True)
        elif is_includes(wordlist, ComList.playlist.value):
            player.random = Repeat.playlist
            jtalk.jtalk("プレイリストをリピート再生します。", jtalk.MEI_NORMAL, True)
        else:
            player.random = Repeat.song
            jtalk.jtalk("この曲をリピート再生します。", jtalk.MEI_NORMAL, True)
        return True

    return False


def reply_song_detail():

    global player
    global is_player_playing
    if is_player_playing:
        voice = ""
        if player.now_playing_playlist:
            voice += player.now_playing_playlist + " から、"
        if player.now_playing_artist:
            voice += player.now_playing_artist + " の "
        if player.now_playing_title:
            voice += player.now_playing_title + " です。"

        if not jtalk.google_tts(voice, True):
            jtalk.jtalk(voice, jtalk.MEI_NORMAL, True)
        return True

    return False


def play_radio(wordlist):
    print("Play radio!")
    channel = ""
    for word in wordlist:
        if (word in RADIO_CHANNEL.keys()):
            channel = RADIO_CHANNEL[word]
            break
    print("channel:" + channel)
    if channel == "":
        return False

    stop_all()
    voice = RADIO_CHANNEL_NAME[channel] + "をかけますね！"
    print(voice)
    jtalk.jtalk(voice, jtalk.MEI_HAPPY)

    cmd = SCRIPT_DIR + "/play_radiko.sh" + " " + channel
    Popen(cmd.strip().split(" "))

    return True


def play_news(wordlist):

    voice = "最新のニュースを流しますね。"
    print(voice)
    jtalk.jtalk(voice, jtalk.MEI_NORMAL)

    path = HOME_DIR + "/.cache/news.xml"
    mp3path = HOME_DIR + "/.cache/news.mp3"
    cmd = "wget https://www.nhk.or.jp/r-news/podcast/nhkradionews.xml -O " + path
    c = Popen(cmd.strip().split(" "))
    c.wait()

    tree = ET.parse(path)
    root = tree.getroot()
    mp3 = root[0][10][1].attrib['url']
    cmd = "wget " + mp3 + " -O " + mp3path
    c = Popen(cmd.strip().split(" "))
    c.wait()

    stop_all()
    cmd = LAUNCH_VLC_CMD + " " + mp3path
    Popen(cmd.strip().split(" "))

    return True


def control_volume(wordlist):

    global player
    isMedia = is_includes(wordlist, ComList.media.value)
    VOL_DEFAULT = 4
    if isMedia:
        try:
            bus = dbus.SessionBus()
            vlc_media_player_obj = bus.get_object(SERVICE_NAME, OBJECT_PATH)
            props_iface = dbus.Interface(vlc_media_player_obj, PROP_INTERFACE)
            currentvol = round(props_iface.Get(PLAYER_INTERFACE, 'Volume') * 100)
        except:
            return
    else:
        try:
            m = alsaaudio.Mixer(control='Speaker')
        except:
            m = alsaaudio.Mixer()
        currentvol = m.getvolume()
        currentvol = int(currentvol[0])

    voice = ""
    for index, word in enumerate(wordlist):
        if word == "上げ" or word == "大きく":
            if (wordlist[index - 1].isdigit()):
                volnum = int(wordlist[index - 1])
            else:
                volnum = VOL_DEFAULT
            voice = "音量を" + str(volnum) + "上げます。"
            break

        elif word == "下げ" or word == "小さく":
            if (wordlist[index - 1].isdigit()):
                volnum = -int(wordlist[index - 1])
            else:
                volnum = -VOL_DEFAULT
            voice = "音量を" + str(volnum*-1) + "下げます。"
            break

    if not voice:
        # 現在の音量
        voice = "音量は" + str(currentvol) + "です。"
    else:
        # ボリューム変更
        volume = currentvol + volnum
        if volume > 100:
            volume = 100
        if volume < 0:
            volume = 0

        if isMedia:
            player.set_volume(volume)
            props_iface.Set(PLAYER_INTERFACE, 'Volume', volume / 100)
        else:
            m.setvolume(volume)


    if isMedia:
        voice = "メディアの" + voice
    print(voice)
    jtalk.jtalk(voice, jtalk.MEI_NORMAL, True)

    return True


def set_task(wordlist):
    now = datetime.datetime.now()
    target = [0, 0, 0, 0, 0, 0]
    waittime = 0
    diff = False
    voice = ""
    comvoice = ""
    input_str = ""

    dellist = lambda items, indexes: [item for index, item in enumerate(items) if index not in indexes]
    delindex = []

    # タイマー実行するコマンド確認
    if is_includes(wordlist, ComList.radio.value, ComList.play.value):
        comvoice = "ラジオを流します。"
    elif is_includes(wordlist, ComList.news.value, ComList.play.value):
        comvoice = "ニュースを流します。"
    elif is_includes(wordlist, ComList.task.value):
        comvoice = "タイマーをセットします。"
    elif is_includes(wordlist, ComList.play.value):
        comvoice = "音楽を流します。"
    elif is_includes(wordlist, ComList.stop.value):
        comvoice = "停止します。"

    if not comvoice:
        return False

    # 時刻取得
    for index, word in enumerate(wordlist[:-1]):
        if word.isdigit():
            if wordlist[index + 1] == "年":
                target[0] = int(word)
                delindex.append(index)
                delindex.append(index + 1)
            elif wordlist[index
                                 + 1] == "月" or wordlist[index
                                                                + 1] == "ヶ月":
                target[1] = int(word)
                delindex.append(index)
                delindex.append(index + 1)
            elif wordlist[index + 1] == "日":
                target[2] = int(word)
                delindex.append(index)
                delindex.append(index + 1)
            elif wordlist[index
                                 + 1] == "時" or wordlist[index
                                                                + 1] == "時間":
                target[3] = int(word)
                delindex.append(index)
                delindex.append(index + 1)
            elif wordlist[index + 1] == "分":
                target[4] = int(word)
                delindex.append(index)
                delindex.append(index + 1)
            elif wordlist[index + 1] == "秒":
                target[5] = int(word)
                delindex.append(index)
                delindex.append(index + 1)

        elif word == "後":
            diff = True
            delindex.append(index)

    wordlist = dellist(wordlist, delindex)
    if wordlist[0] == "に":
        del wordlist[0]
    input_str = "".join(wordlist)
    print(input_str)

    # 待ち時間計算
    if diff:
        if target[0]:
            waittime += target[0] * 31536000
            voice += str(target[0]) + "年"
        if target[1]:
            waittime += target[1] * 2592000
            voice += str(target[1]) + "ヶ月"
        if target[2]:
            waittime += target[2] * 86400
            voice += str(target[2]) + "日"
        if target[3]:
            waittime += target[3] * 3600
            voice += str(target[3]) + "時間"
        if target[4]:
            waittime += target[4] * 60
            voice += str(target[4]) + "分"
        if target[5]:
            waittime += target[5]
            voice += str(target[5]) + "秒"
        voice += "後"
    else:
        if target[0]:
            waittime += (target[0] - now.year) * 31536000
            if waittime < 0:
                return False
            voice += str(target[0]) + "年"
        if target[1]:
            waittime += (target[1] - now.month) * 2592000
            if waittime < 0:
                waittime += 31536000
            voice += str(target[1]) + "月"
        if target[2]:
            waittime += (target[2] - now.day) * 86400
            if waittime < 0:
                waittime += 2592000
            voice += str(target[2]) + "日"
        if target[3]:
            waittime += (target[3] - now.hour) * 3600
            if waittime < 0:
                waittime += 86400
            voice += str(target[3]) + "時"
        if target[4]:
            waittime += (target[4] - now.minute) * 60
            if waittime < 0:
                waittime += 3600
            voice += str(target[4]) + "分"
        if target[5]:
            waittime += (target[5] - now.second)
            if waittime < 0:
                waittime += 60
            voice += str(target[5]) + "秒"

    print(str(waittime))

    if waittime > 0:
        global tasks
        task_id = random.randint(0, sys.maxsize)
        t = threading.Timer(
            waittime, run_task, args=(input_str, task_id))
        t.start()
        tasks.append((task_id, t))
        voice += "に" + comvoice
        jtalk.jtalk(voice, jtalk.MEI_NORMAL, True)
        return True

    return False


def run_task(input_str, task_id):
    global tasks
    for index, task in enumerate(tasks[:]):
        if task[0] == task_id:
            tasks.pop(index)
            command(input_str)
            return


def delete_task():
    global tasks
    if len(tasks) > 0:
        for task in tasks:
            task[1].cancel()
        tasks = []
        jtalk.jtalk("タスクを消去しました。", jtalk.MEI_NORMAL, True)
    else:
        jtalk.jtalk("タスクはありません。", jtalk.MEI_NORMAL, True)

    return True


def pause_media():
    global is_player_playing
    global alert_timer
    global player
    print("Pause media")
    is_player_playing = player.playing
    cmd = QDBUS_VLC_CMD + ".Pause"
    Popen(cmd.strip().split(" "))
    player.pause()
    alert_timer.pause()

    return True


def play_media():
    global is_player_playing
    global alert_timer
    global player
    print("Play media")
    cmd = QDBUS_VLC_CMD + ".Play"
    Popen(cmd.strip().split(" "))
    if is_player_playing:
        player.resume()
    alert_timer.resume()

    return True


def stop_all_and_launch():
    stop_all()
    launch_vlc()
    return True

# 基本的に上のstop_all_and_launchを使用
# こっちを使った場合は手動でvlc立ち上げ必須
def stop_all():
    global alert_timer
    global player
    print("Killall vlc")
    cmd = "killall vlc"
    Popen(cmd.strip().split(" "))
    player.stop()
    alert_timer.stop()
    return True


def launch_vlc():
    print("launch vlc")
    cmd = LAUNCH_VLC_CMD
    Popen(
        cmd.strip().split(" "),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)
    return True


def is_includes(src, *targets):
    src_set = set(src)
    for target in targets:
        tag_set = set(target)
        matched_list = []
        matched_list = list(src_set & tag_set)
        if not matched_list:
            return False
    return True


# コマンドリスト
class ComList(Enum):
    radio = ["ラジオ", "fm"]
    news = ["ニュース"]
    volume = ["音量", "ボリューム"]
    stop = ["止め", "停止", "やめ"]
    play = ["再生", "流し", "かけ"]
    pause = ["ポーズ"]
    resume = ["再開"]
    teach = ["教え", "何", "情報", "詳細"]
    time = ["時間", "時", "分", "秒"]

    task = ["タイマー", "タスク", "アラーム"]
    kill = ["解除", "削除", "消し"]

    media = ["vlc", "メディア", "音楽", "動画", "ミュージック", "ムービー"]

    do_next = ["次"]
    do_prev = ["前"]
    playlist = ["プレイリスト", "アルバム"]
    random = ["ランダム"]
    repeat = ["リピート", "ループ"]
    song_detail = ["歌", "歌手", "アーティスト", "曲", "曲名"]

# 入力文をもとにカスタムコマンド実行
# Trueを返すとカスタムコマンドを実行したものとして以後のアシスタントに処理をさせない
def command(input_str):
    input_str = normalize('NFKC', input_str).lower()
    result = word_and_class.word_and_class(input_str)
    result_wordlist = []
    run = False
    print(result)

    for word in result:
        result_wordlist.append(word[0])

    global is_player_playing
    global player

    if is_includes(result_wordlist, ComList.time.value):
        if set_task(result_wordlist):
            return True
    if is_includes(result_wordlist, ComList.task.value, ComList.kill.value):
        if delete_task():
            return True
    elif is_includes(result_wordlist, ComList.task.value):
        alert_timer.start()
        return True

    if is_includes(result_wordlist, ComList.radio.value, ComList.play.value):
        if play_radio(result_wordlist):
            return True
    if is_includes(result_wordlist, ComList.news.value, ComList.play.value):
        if play_news(result_wordlist):
            return True
    if is_includes(result_wordlist, ComList.volume.value):
        if control_volume(result_wordlist):
            return True

    # 再生制御
    if is_includes(result_wordlist, ComList.do_next.value):
        if is_player_playing:
            if player.next():
                return True
    if is_includes(result_wordlist, ComList.do_prev.value):
        if is_player_playing:
            if player.prev():
                return True
    if is_includes(result_wordlist, ComList.random.value):
        if play_random(result_wordlist):
            return True
    if is_includes(result_wordlist, ComList.repeat.value):
        if play_repeat(result_wordlist):
            return True
    if is_includes(result_wordlist, ComList.pause.value):
        if is_player_playing:
            pause_media()
            is_player_playing = False
            return True
    if is_includes(result_wordlist, ComList.resume.value):
        if not is_player_playing:
            is_player_playing = True
            play_media()
            return True

    if is_includes(result_wordlist, ComList.song_detail.value,
                   ComList.teach.value):
        if reply_song_detail():
            return True

    if is_includes(result_wordlist, ComList.play.value):
        if play_music(result_wordlist):
            return True
    if is_includes(result_wordlist, ComList.stop.value):
        # 停止のみの場合アシスタントにも処理させたい
        stop_all_and_launch()

    return False

def start_ga():
    Popen(
        ['aplay', START_SE],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)

def end_ga():
    Popen(
        ['aplay', END_SE],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)
