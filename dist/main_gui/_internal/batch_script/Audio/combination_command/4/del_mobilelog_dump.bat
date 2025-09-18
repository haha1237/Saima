@echo off

adb wait-for-device root

echo delete /data/debuglogger/mobilelog
adb shell rm -rf /data/debuglogger/mobilelog

echo delete /data/debuglogger/audio_dump
adb shell rm -rf /data/debuglogger/audio_dump

echo delete /data/vendor/audiohal/audio_dump
adb shell rm -rf /data/vendor/audiohal/audio_dump

echo delete /sdcard/debuglogger/audio_dump/
adb shell rm -rf /sdcard/debuglogger/audio_dump/
