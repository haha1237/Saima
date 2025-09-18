@echo off
adb wait-for-device root
adb shell dumpsys media.audio_policy
