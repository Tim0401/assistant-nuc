#!/bin/bash
vlcCall="vlc -A alsa -I dummy --fullscreen --control dbus"
function cleanup(){
    for pid in $(pgrep -f "$vlcCall"); do
        kill -9 $pid 
    done
    killall rygel
}
function waitCpuDecrease(){
    pid=$1
    lastCpu="0.0"
    while true; do
        cpu=$(ps S -p $pid -o pcpu=)
        sleep 0.2
        [ $( bc <<< "$cpu < $lastCpu") == 1 ] && break
        lastCpu=$cpu
    done
}
# killall rygel and vlc
cleanup
# launch vlc in background
export DISPLAY=:0.0
$vlcCall &
# wait until vlc has done most stuff
# waitCpuDecrease $!
sleep 5
# start rygel
rygel -c /etc/rygel.conf

