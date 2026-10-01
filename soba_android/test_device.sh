#!/usr/bin/env bash
set -u
cd "$(dirname "$0")"
mkdir -p build/device-evidence
result=0
gradle --no-daemon connectedDebugAndroidTest || result=$?
adb logcat -d > build/device-evidence/logcat.txt
adb pull /sdcard/Android/data/vn.dovanphi.quanmicuatoi.androidbeta/files/android-game.png build/device-evidence/android-game.png || true
exit "$result"
