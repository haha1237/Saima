@echo off
adb wait-for-device root
adb shell settings put secure user_setup_complete 1