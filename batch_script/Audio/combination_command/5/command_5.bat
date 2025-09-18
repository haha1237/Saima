@echo off

adb wait-for-device root

adb wait-for-device pull /data/debuglogger/mobilelog/ .\
adb wait-for-device pull /data/debuglogger/audio_dump/ .\
adb wait-for-device pull /data/vendor/audiohal/audio_dump/ .\
rem pull from /sdcard
rem adb wait-for-device pull /sdcard/debuglogger/audio_dump/ .\