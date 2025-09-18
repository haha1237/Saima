@echo off

md audio_param

ren default.audio_param default.audio_param.zip

rem use the port of Bandizip, it need to be configured through the actual location
"C:\Program Files\Bandizip\bc.exe" x default.audio_param.zip audio_param

ren default.audio_param.zip default.audio_param

adb wait-for-device root
adb wait-for-device remount
adb wait-for-device push audio_param /vendor/etc/

rmdir /s /q audio_param