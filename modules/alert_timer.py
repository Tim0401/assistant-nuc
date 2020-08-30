# -*- coding: utf-8 -*-
import threading
from time import sleep
from vlc_player import VLCPlayer

class AlertTimer(object):
    def __init__(self,
                 filepath,
                 repeat=True,
                 waittime=120,
                 endtime=1200):
        self.vlc = VLCPlayer(filepath)
        self.vlc.set_repeat(repeat)

        self.waittime = waittime
        self.endtime = endtime
        self.isPlaying = False
        self.isPause = False
        self.waitCounter = 0
        self.endCounter = 0

        t = threading.Timer(1, self.controller)
        t.start()

    def controller(self):
        if self.isPlaying:
            if self.isPause:
                self.waitCounter += 1
            else:
                self.waitCounter = 0
            self.endCounter += 1
        else:
            self.endCounter = 0

        if self.endCounter > self.endtime or self.waitCounter > self.waittime:
            self.stop()
            self.waitCounter = 0
            self.endCounter = 0

        t = threading.Timer(1, self.controller)
        t.start()

    def start(self):
        if self.isPause:
            self.resume()
        elif not self.isPlaying:
            self.vlc.play()
            self.isPlaying = True
            self.isPause = False

    def stop(self):
        self.vlc.stop()
        self.isPlaying = False
        self.isPause = False

    def resume(self):
        if self.isPlaying:
            self.vlc.resume()
            self.isPause = False

    def pause(self):
        if self.isPlaying:
            self.vlc.pause()
            self.isPause = True


if __name__ == '__main__':
    a = AlertTimer(r"../resources/alert.mp3")
    a.start()
    input()
    a.pause()
    input()
    a.resume()
    input()
    a.stop()
