@echo off
adb wait-for-device root
adb shell tinypcminfo -D /proc/asound/cards