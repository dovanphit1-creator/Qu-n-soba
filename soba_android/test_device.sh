#!/usr/bin/env bash
set -u
cd "$(dirname "$0")"
mkdir -p build/device-evidence
adb shell settings put secure immersive_mode_confirmations confirmed
result=0
gradle --no-daemon connectedDebugAndroidTest || result=$?
adb logcat -d > build/device-evidence/logcat.txt
adb pull /data/local/tmp/android-game.png build/device-evidence/android-game.png || true
adb pull /data/local/tmp/android-welcome.png build/device-evidence/android-welcome.png || true
adb pull /data/local/tmp/android-management.png build/device-evidence/android-management.png || true
adb pull /data/local/tmp/android-market.png build/device-evidence/android-market.png || true
exit "$result"
