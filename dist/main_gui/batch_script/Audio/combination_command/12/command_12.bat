@echo off

adb wait-for-device root

echo copy framework audio_dump to sdcard/audio_dump
adb shell audiotest copyAudioDump

echo pull /data/debuglogger to Desktop
rem HAL层的dump
adb wait-for-device pull sdcard/debuglogger/audio_dump .\

echo pull /sdcard/audio_dump/
adb wait-for-device pull sdcard/audio_dump .\