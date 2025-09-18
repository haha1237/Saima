adb wait-for-device root

adb shell setprop vendor.af.track.log 4
adb shell setprop vendor.af.audioflinger.log 4
adb shell setprop vendor.af.policy.debug 4
adb shell setprop log.tag.APM_AudioPolicyManager V
adb shell pkill audioserver