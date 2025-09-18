@echo off

adb wait-for-device root

adb shell am broadcast -a com.debug.loggerui.ADB_CMD -e cmd_name start --ei cmd_target 1 -n com.debug.loggerui/.framework.LogReceiver

rem logTypes = 1 + 2 + 4 + 16 + 32 + 64
rem MobileLog : 1, ModemLog : 2, NetworkLog : 4, GPSLog : 16, ConnsysFWLog : 32, BTHostLog : 64

echo press any key to stop log

pause

adb shell am broadcast -a com.debug.loggerui.ADB_CMD -e cmd_name stop --ei cmd_target 1 -n com.debug.loggerui/.framework.LogReceiver

echo stop log over

@timeout /t 2 /nobreak > nul

adb wait-for-device pull /data/debuglogger/mobilelog/ .\