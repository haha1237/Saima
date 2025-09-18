@echo off

adb wait-for-device root
adb wait-for-device disable-verity
adb wait-for-device remount

adb wait-for-device push preset_music.bin /vendor/etc/audio_param/preset_music.bin
adb wait-for-device push preset_voip.bin /vendor/etc/audio_param/preset_voip.bin
adb wait-for-device push preset_ringtone.bin /vendor/etc/audio_param/preset_ringtone.bin
adb wait-for-device push preset_default.bin /vendor/etc/audio_param/preset_default.bin
adb wait-for-device push fs1599.fsm vendor/firmware/fs1599.fsm
adb wait-for-device push aurisys_config_fs.xml vendor/etc/aurisys_config_fs.xml

pause
adb shell pkill audioserver