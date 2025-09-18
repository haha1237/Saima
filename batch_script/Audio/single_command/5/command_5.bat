@echo off
adb wait-for-device root
adb shell dumpsys media.metrics