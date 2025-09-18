@echo off



adb wait-for-device

adb reboot bootloader

echo wait for bootloader detect

fastboot oem tran_skip_confirm_key

fastboot flashing unlock

fastboot reboot

adb wait-for-device

adb root

adb disable-verity

adb reboot

adb wait-for-device

adb root

adb remount

timeout /t 30

adb shell settings put global device_provisioned 1

adb shell settings put secure user_setup_complete 1

adb reboot

adb wait-for-device shell settings put secure user_setup_complete 1

pause