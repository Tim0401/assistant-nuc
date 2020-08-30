# -*- coding: utf-8 -*-
from gmusicapi import Mobileclient
from gmusicapi.utils import utils
from vlc import EventType, Instance
import json
import os.path
import time
import random
import difflib
import threading
import logging
from enum import Enum
from pathlib import Path
import convert_jnto_romaji as cir

DIFF_ARGS = 0.67
JSON_DIR = str(Path.home()) + "/.cache/"
CREDENTIAL_FILE = str(Path.home()) + '/mobileclient.cred'
RELOAD_LIB_TIME = 24 * 60 * 60
MAX_TRACK = 128


class Repeat(Enum):
    none = 0
    song = 1
    playlist = 2


class Player(object):
    def __init__(self, device_id):
        self.api = Mobileclient()
        self.api.logger.setLevel(logging.INFO)
        #print(utils.log_filepath)

        options = ["--aout=alsa", "-I dummy", "--fullscreen"]
        self.vlc = Instance(options)
        self.player = None

        self.loaded_tracks = []

        self.playing = False
        self.repeat = Repeat.none
        self.random = False
        self.song_index = 0
        self.now_playing_title = ""
        self.now_playing_artist = ""
        self.now_playing_playlist = ""

        # 取得したjsonの生データ
        self.song_library = []
        self.playlist_library = []
        # 整頓した楽曲ライブラリ
        self.songs = []
        self.albums = []
        self.playlists = []
        self.artists = []

        # play musicログイン
        if not os.path.exists(CREDENTIAL_FILE):
            self.api.perform_oauth(CREDENTIAL_FILE)
        self.api.oauth_login(device_id, CREDENTIAL_FILE)
        # 曲一覧読み込み
        if os.path.isfile(JSON_DIR + "songs.json"):
            # Load from file
            print("Found songs data.")
            with open(JSON_DIR + 'songs.json') as input_file:
                self.song_library = json.load(input_file)
        else:
            self.song_library = self.api.get_all_songs()
            # Save to file
            with open(JSON_DIR + 'songs.json', 'w') as output_file:
                json.dump(self.song_library, output_file)

        self.create_songs()
        self.create_albums()
        self.create_artists()

        # プレイリスト読み込み
        if os.path.isfile(JSON_DIR + "playlists.json"):
            # Load from file
            print("Found playlist data.")
            with open(JSON_DIR + 'playlists.json') as input_file:
                self.playlist_library = json.load(input_file)
        else:
            self.playlist_library = self.api.get_all_user_playlist_contents()
            # Save to file
            with open(JSON_DIR + 'playlists.json', 'w') as output_file:
                json.dump(self.playlist_library, output_file)
        #プレイリスト名編集
        self.create_playlists()

        # 定時ライブラリ更新処理
        t = threading.Timer(RELOAD_LIB_TIME, self.auto_reload)
        t.start()

    def auto_reload(self):
        while True:
            if not self.playing:
                break
            time.sleep(60)
        self.reload_library()
        print("[ music list auto reloaded ]")
        t = threading.Timer(RELOAD_LIB_TIME, self.auto_reload)
        t.start()

    def reload_library(self):
        # 曲一覧読み込み
        self.song_library = self.api.get_all_songs()
        # Save to file
        with open(JSON_DIR + 'songs.json', 'w') as output_file:
            json.dump(self.song_library, output_file)

        self.create_songs()
        self.create_albums()
        self.create_artists()
        # プレイリスト読み込み
        self.playlist_library = self.api.get_all_user_playlist_contents()
        # Save to file
        with open(JSON_DIR + 'playlists.json', 'w') as output_file:
            json.dump(self.playlist_library, output_file)
        #プレイリスト名編集
        self.create_playlists()

    def create_songs(self):
        self.songs = []
        # 曲名編集
        for index, song in enumerate(self.song_library):
            self.songs.append({})
            self.songs[index].update({"original_name": song['title']})
            self.songs[index].update({
                "name":
                cir.convert_into_romaji(song['title'])
            })
            self.songs[index].update({"artist": song['artist']})
            self.songs[index].update({"trackId": song['id']})
            self.songs[index].update({"source": 1})
            #print(self.songs[index])
            #sleep(0.1)
        print("[ create_songs finished ]")

    def create_playlists(self):
        self.playlists = []
        #プレイリスト名編集
        for index, playlist in enumerate(self.playlist_library):
            self.playlists.append({})
            self.playlists[index].update({"original_name": playlist['name']})
            self.playlists[index].update({
                "name":
                cir.convert_into_romaji(playlist['name'])
            })
            self.playlists[index].update({"tracks": playlist['tracks']})
            print(self.playlists[index]['name'])
        print("[ create_playlists finished ]")

    def create_albums(self):
        self.albums = []
        # アルバムリスト作成
        for song in self.song_library:
            album_found = False
            track = {}
            for index, album in enumerate(self.albums):
                # アルバムがすでに登録されていた場合
                if album['original_name'] == song['album']:
                    album_found = True
                    track.update({"trackId": song['id']})
                    track.update({"source": 1})
                    track.update({"trackNumber": song['trackNumber']})
                    self.albums[index]['tracks'].append(track)
                    #print(self.albums[index])
                    break
            if album_found:
                continue

            #新規アルバム作成
            albums_len = len(self.albums)
            self.albums.append({})
            self.albums[albums_len].update({"original_name": song['album']})
            self.albums[albums_len].update({
                "name":
                cir.convert_into_romaji(song['album'])
            })

            track.update({"trackId": song['id']})
            track.update({"source": 1})
            track.update({"trackNumber": song['trackNumber']})
            self.albums[albums_len].update({"tracks": [track]})
            #print(self.albums[albums_len])
        # tracknumberでソート
        for album in self.albums:
            album['tracks'] = sorted(
                album['tracks'], key=lambda x: x['trackNumber'])
            print(album["name"])

        print("[ create_albums finished ]")

    def create_artists(self):
        self.artists = []
        # アーティストリスト作成
        for song in self.song_library:
            artist_found = False
            track = {}
            for index, artist in enumerate(self.artists):
                # アーティストがすでに登録されていた場合
                if artist['original_name'] == song['artist']:
                    artist_found = True
                    track.update({"trackId": song['id']})
                    track.update({"source": 1})
                    track.update({"trackNumber": song['trackNumber']})
                    self.artists[index]['tracks'].append(track)
                    break
            if artist_found:
                continue

            #新規アルバム作成
            artists_len = len(self.artists)
            self.artists.append({})
            self.artists[artists_len].update({"original_name": song['artist']})
            self.artists[artists_len].update({
                "name":
                cir.convert_into_romaji(song['artist'])
            })

            track.update({"trackId": song['id']})
            track.update({"source": 1})
            track.update({"trackNumber": song['trackNumber']})
            self.artists[artists_len].update({"tracks": [track]})
            print(self.artists[artists_len]["name"])
        print("[ create_artists finished ]")

    def load_playlist(self, name):
        name = name.strip().lower()
        print("Looking for...", name)

        top_diff = 0.0
        top_playlist = {}
        # 検索
        for playlist_dict in self.playlists:
            playlist_name = playlist_dict['name'].strip().lower()
            diff = difflib.SequenceMatcher(None, playlist_name, name).ratio()

            if diff > top_diff:
                print("diff match...", playlist_dict['name'], ":", diff)
                top_playlist = playlist_dict
                top_diff = diff
            else:
                pass
                #print("Found...", playlist_dict['name'])
        # 一番マッチしたものを返す
        if top_diff > DIFF_ARGS:
            self.loaded_tracks = []
            print(top_diff)
            print("Found match...", top_playlist['name'])
            for track_dict in top_playlist['tracks']:
                self.loaded_tracks.append(track_dict)
            self.now_playing_playlist = top_playlist['original_name']
            return top_playlist['original_name']
        else:
            return None

    def load_song(self, name):
        name = name.strip().lower()
        print("Looking for...", name)

        top_diff = 0.0
        top_song = {}
        for song_dict in self.songs:
            song_name = song_dict['name'].strip().lower()
            diff = difflib.SequenceMatcher(None, song_name, name).ratio()
            #print(diff)
            if diff > top_diff:
                print("diff match...", song_dict['name'], ":", diff)
                top_song = song_dict
                top_diff = diff
            else:
                pass
                #print("Found...", song_dict['name'])
        # 一番マッチしたものを返す
        if top_diff > DIFF_ARGS:
            self.loaded_tracks = []
            print(top_diff)
            print("Found match...", top_song['name'])
            self.loaded_tracks.append(top_song)
            self.now_playing_playlist = ""
            return top_song['original_name']
        else:
            return None

    def load_album(self, name):
        name = name.strip().lower()
        print("Looking for...", name)

        top_diff = 0.0
        top_album = {}
        for album_dict in self.albums:
            album_name = album_dict['name'].strip().lower()
            diff = difflib.SequenceMatcher(None, album_name, name).ratio()
            #print(diff)
            if diff > top_diff:
                print("diff match...", album_dict['name'], ":", diff)
                top_album = album_dict
                top_diff = diff
            else:
                pass
                #print("Found...", album_dict['name'])
        # 一番マッチしたものを返す
        if top_diff > DIFF_ARGS:
            self.loaded_tracks = []
            print(top_diff)
            print("Found match...", top_album['name'])
            for track_dict in top_album['tracks']:
                self.loaded_tracks.append(track_dict)
            self.now_playing_playlist = top_album['original_name']
            return top_album['original_name']
        else:
            return None

    def load_artist(self, name):
        name = name.strip().lower()
        print("Looking for...", name)

        top_diff = 0.0
        top_artist = {}
        for artist_dict in self.artists:
            artist_name = artist_dict['name'].strip().lower()
            diff = difflib.SequenceMatcher(None, artist_name, name).ratio()
            #print(diff)
            if diff > top_diff:
                print("diff match...", artist_dict['name'], ":", diff)
                top_artist = artist_dict
                top_diff = diff
            else:
                pass
        # 一番マッチしたものを返す
        if top_diff > DIFF_ARGS:
            self.loaded_tracks = []
            print(top_diff)
            print("Found match...", top_artist['name'])
            for track_dict in top_artist['tracks']:
                self.loaded_tracks.append(track_dict)
            self.now_playing_playlist = top_artist['original_name']
            return top_artist['original_name']
        else:
            return None

    def load_cloud(self, name, isArtist=True, isSong=True, isAlbum=True):
        search = self.api.search(name)

        # アーティストのトップ曲を流す
        if search["artist_hits"] and isArtist:
            for index in range(len(search["artist_hits"])):
                artist_id = search["artist_hits"][index]["artist"]["artistId"]
                artist = self.api.get_artist_info(
                    artist_id,
                    max_top_tracks=MAX_TRACK,
                    include_albums=False,
                    max_rel_artist=0)
                if "topTracks" in artist.keys():
                    break
            if "topTracks" in artist.keys():
                self.loaded_tracks = []
                for track_dict in artist["topTracks"]:
                    track_dict.update({"track": track_dict})
                    track_dict.update({"trackId": track_dict["storeId"]})
                    track_dict.update({"source": "2"})
                    self.loaded_tracks.append(track_dict)
                self.now_playing_playlist = ""
                return artist["name"]

        # 単曲を流す（複数にしたほうがいいかも）
        elif search["song_hits"] and isSong:
            self.loaded_tracks = []
            for index, track_dict in enumerate(search["song_hits"]):
                if index >= MAX_TRACK: break
                track_dict.update({"trackId": track_dict["track"]["storeId"]})
                track_dict.update({"source": "2"})
                self.loaded_tracks.append(track_dict)
            self.now_playing_playlist = ""
            return self.loaded_tracks[0]["track"]["title"]

        # アルバムを流す（正確さに欠ける）
        elif search["album_hits"] and isAlbum:
            album_id = search["album_hits"][0]["album"]["albumId"]
            album = self.api.get_album_info(album_id)
            self.loaded_tracks = []
            for track_dict in album["tracks"]:
                track_dict.update({"track": track_dict})
                track_dict.update({"trackId": track_dict["storeId"]})
                track_dict.update({"source": "2"})
                self.loaded_tracks.append(track_dict)
            self.now_playing_playlist = album["name"]
            return album["name"]

        # ステーション（ここまで回ってこない気が・・・）
        elif search["station_hits"]:
            pass
        return None

    def end_callback(self, event, track_index):
        # ランダム再生時処理
        if self.random:
            self.song_index = random.randint(0, len(self.loaded_tracks) - 1)
            self.play_song(self.loaded_tracks[self.song_index])
            event_manager = self.player.event_manager()
            event_manager.event_attach(EventType.MediaPlayerEndReached,
                                       self.end_callback, self.song_index + 1)
            return
        # 一曲リピート
        if self.repeat == Repeat.song:
            self.play_song(self.loaded_tracks[track_index - 1])
            event_manager = self.player.event_manager()
            event_manager.event_attach(EventType.MediaPlayerEndReached,
                                       self.end_callback, track_index)
            return
        # 通常再生・プレイリストリピート
        if track_index < len(self.loaded_tracks):
            self.song_index = track_index
            self.play_song(self.loaded_tracks[track_index])
            event_manager = self.player.event_manager()
            event_manager.event_attach(EventType.MediaPlayerEndReached,
                                       self.end_callback, track_index + 1)
        else:
            if self.repeat == Repeat.playlist:
                self.start_playlist()
            else:
                self.playing = False
                self.song_index = 0

    def start_playlist(self):
        if len(self.loaded_tracks) > 0:
            # ランダム再生時処理
            if self.random:
                self.song_index = random.randint(0,
                                                 len(self.loaded_tracks) - 1)
            else:
                # 通常再生
                self.song_index = 0
            self.play_song(self.loaded_tracks[self.song_index])
            event_manager = self.player.event_manager()
            event_manager.event_attach(EventType.MediaPlayerEndReached,
                                       self.end_callback, self.song_index + 1)
            return True
        return False

    def play_song(self, song_dict):
        stream_url = self.api.get_stream_url(song_dict['trackId'])
        self.player = self.vlc.media_player_new()
        media = self.vlc.media_new(stream_url)
        self.player.set_media(media)
        self.player.play()
        self.playing = True

        if (song_dict['source'] == '2'):
            self.now_playing_artist, self.now_playing_title = self.get_song_details(
                song_dict)
        else:
            self.now_playing_artist, self.now_playing_title = self.get_local_song_details(
                song_dict['trackId'])

        print("Playing...", self.now_playing_artist, " - ",
              self.now_playing_title)

    def stop(self):
        if self.player != None:
            self.player.stop()
            self.player = None
        self.playing = False
        self.repeat = Repeat.none
        self.random = False
        self.song_index = 0
        self.now_playing_title = ""
        self.now_playing_artist = ""

    def pause(self):
        if self.player == None:
            return False
        if self.playing == True:
            self.player.set_pause(1)
            self.playing = False
            return True
        return False

    def resume(self):
        if self.player == None:
            return False
        if self.playing == False:
            self.player.set_pause(0)
            self.playing = True
            return True
        return False

    def next(self):
        if self.player == None:
            return False
        # ランダム
        if self.random:
            self.song_index = random.randint(0, len(self.loaded_tracks) - 1)
            self.player.stop()
            self.play_song(self.loaded_tracks[self.song_index])
            event_manager = self.player.event_manager()
            event_manager.event_detach(EventType.MediaPlayerEndReached)
            event_manager.event_attach(EventType.MediaPlayerEndReached,
                                       self.end_callback, self.song_index + 1)
            return True
        # 通常
        if self.song_index + 1 < len(self.loaded_tracks):
            self.song_index += 1
            self.player.stop()
            self.play_song(self.loaded_tracks[self.song_index])
            event_manager = self.player.event_manager()
            event_manager.event_detach(EventType.MediaPlayerEndReached)
            event_manager.event_attach(EventType.MediaPlayerEndReached,
                                       self.end_callback, self.song_index + 1)
            return True
        else:
            if self.repeat == Repeat.playlist:
                self.start_playlist()
                return True

        return False

    def prev(self):
        if self.player == None:
            return False
        if self.song_index - 1 <= 0:
            self.song_index -= 1
            self.player.stop()
            self.play_song(self.loaded_tracks[self.song_index])
            event_manager = self.player.event_manager()
            event_manager.event_detach(EventType.MediaPlayerEndReached)
            event_manager.event_attach(EventType.MediaPlayerEndReached,
                                       self.end_callback, self.song_index + 1)
            return True
        return False

    def get_local_song_details(self, track_id):
        for song_dict in self.song_library:
            if track_id == song_dict['id']:
                return song_dict['artist'], song_dict['title']

    def get_song_details(self, song_dict):
        return song_dict['track']['albumArtist'], song_dict['track']['title']

    def set_volume(self, volume):
        if self.player:
            self.player.audio_set_volume(volume)

