# -*- coding: utf-8 -*-
from vlc import EventType, Instance, MediaPlayer


class VLCPlayer(object):
    def __init__(self, path=None):
        options = ["--aout=alsa", "-I dummy", "--fullscreen"]
        self.vlc = Instance(options)
        self.player = None
        self.path = path
        self.repeat = False
        self.volume = 100

    def end_callback(self, event):
        if self.repeat:
            self.play()
        else:
            self.stop()

    def set_repeat(self, flag):
        self.repeat = flag

    def play(self):
        self.player = self.vlc.media_player_new()
        #volume = self.player.audio_get_volume()
        self.player.audio_set_volume(self.volume)
        media = self.vlc.media_new(self.path)
        self.player.set_media(media)
        self.player.play()

        em = self.player.event_manager()
        em.event_attach(EventType.MediaPlayerEndReached, self.end_callback)

    def stop(self):
        if self.player != None:
            self.player.stop()
            self.player = None

    def pause(self):
        if self.player != None:
            self.player.set_pause(1)

    def resume(self):
        if self.player != None:
            self.player.set_pause(0)