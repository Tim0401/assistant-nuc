# -*- coding: utf-8 -*-
from gmusicapi import Mobileclient
from playscroll import Player
from playscroll import Repeat
from time import sleep
from subprocess import Popen

import convert_jnto_romaji as cir

# config
import configparser
config_ini = configparser.ConfigParser()
config_ini.read('config.ini', encoding='utf-8')
DEVICE_ID = config_ini['gmusicapi']['DeviceId']

def main():
    search_word = "アイビートーン"
    converted_word = cir.convert_into_romaji(search_word)

    player = Player(DEVICE_ID)
    # auth = player.api.is_subscribed
    # クラウド上のみの検索
    # search = player.api.search(playlist)

    # player.reload_library()

    if player.load_playlist(converted_word) is None:
        if player.load_song(converted_word) is None:
            if player.load_album(converted_word) is None:
                return

    player.start_playlist()

    while True:
        command = input()
        if command == 'stop':
            player.stop()
        elif command == 'next':
            player.next()
        elif command == 'prev':
            player.prev()
        elif command == 'pause':
            player.pause()
        elif command == 'resume':
            player.resume()
        elif command == 'reload':
            player.reload_library()
        elif command == 'random':
            if player.random == True:
                player.random = False
            else:
                player.random = True
            print("random:", player.random)
        elif command == 'repeat':
            if player.repeat == Repeat.none:
                player.repeat = Repeat.playlist
            elif player.repeat == Repeat.playlist:
                player.repeat = Repeat.song
            elif player.repeat == Repeat.song:
                player.repeat = Repeat.none
            print("repeat:", player.repeat)


if __name__ == "__main__":
    main()