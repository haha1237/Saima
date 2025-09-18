@echo off

adb wait-for-device root

echo opening audio_dump...

adb shell "AudioSetParam vendor.a2dp.streamout.pcm=1"
adb shell "AudioSetParam vendor.aaudio.pcm=1"
adb shell "AudioSetParam vendor.af.effect.pcm=1"
adb shell "AudioSetParam vendor.af.mixer.drc.pcm=1"
adb shell "AudioSetParam vendor.af.mixer.end.pcm=1"
adb shell "AudioSetParam vendor.af.mixer.pcm=1"
adb shell "AudioSetParam vendor.af.offload.write.raw=1"
adb shell "AudioSetParam vendor.af.record.dump.pcm=1"
adb shell "AudioSetParam vendor.af.resampler.pcm=1"
adb shell "AudioSetParam vendor.af.track.pcm=1"
adb shell "AudioSetParam vendor.streamin.dsp.dump=1"
adb shell "AudioSetParam vendor.streamin.pcm.dump=1"
adb shell "AudioSetParam vendor.streamout.dsp.dump=1"
adb shell "AudioSetParam vendor.streamout.pcm.dump=1"
adb shell "AudioSetParam persist.vendor.audiohal.aurisys.pcm_dump_on=1"

echo open over
echo press any key to stop audio_dump

pause

echo stoping audio_dump

adb shell setprop vendor.a2dp.streamout.pcm 0
adb shell setprop vendor.aaudio.pcm 0
adb shell setprop vendor.af.effect.pcm 0
adb shell setprop vendor.af.mixer.drc.pcm 0
adb shell setprop vendor.af.mixer.end.pcm 0
adb shell setprop vendor.af.mixer.pcm 0
adb shell setprop vendor.af.offload.write.raw 0
adb shell setprop vendor.af.record.dump.pcm 0
adb shell setprop vendor.af.resampler.pcm 0
adb shell setprop vendor.af.track.pcm 0
adb shell setprop vendor.streamin.dsp.dump 0
adb shell setprop vendor.streamin.pcm.dump 0
adb shell setprop vendor.streamout.dsp.dump 0
adb shell setprop vendor.streamout.pcm.dump 0
adb shell setprop persist.vendor.audiohal.aurisys.pcm_dump_on 0

echo stop audio_dump over

adb wait-for-device pull /data/debuglogger/audio_dump/ .\
adb wait-for-device pull /data/vendor/audiohal/audio_dump/ .\
rem from sdcard
rem adb wait-for-device pull /sdcard/debuglogger/audio_dump/ .\
