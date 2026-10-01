# Third-party components

Quán Mì Của Tôi — Android. Publisher: Đỗ Văn Phi.

The APK includes CPython 3.12.12 (PSF License and historical notices), pygbag 0.9.3 (MIT), pygame-ce 2.5.7 (LGPL 2.1), holidays 0.105 (MIT), python-dateutil 2.9.0.post0 (Apache 2.0/BSD), six 1.17.0 (MIT), DejaVu Fonts 2.37 (Bitstream Vera/DejaVu) and AndroidX WebKit 1.12.1 (Apache 2.0, Android Open Source Project). License texts are in the bundled game/licenses folder; DejaVu's full license also appears inside the game archive. Apache 2.0 license text is included with python-dateutil.

Upstream source and notices:
- CPython: https://github.com/python/cpython/tree/v3.12.12
- pygbag and WebAssembly build infrastructure: https://github.com/pygame-web/pygbag/tree/0.9.3 ; https://github.com/pygame-web/python-wasm-sdk
- pygame-ce: https://github.com/pygame-community/pygame-ce/tree/2.5.7
- holidays: https://github.com/vacanza/holidays
- python-dateutil: https://github.com/dateutil/dateutil
- six: https://github.com/benjaminp/six
- DejaVu: https://github.com/dejavu-fonts/dejavu-fonts/tree/version_2_37
- AndroidX WebKit: https://android.googlesource.com/platform/frameworks/support/+/androidx-main/webkit/

The Python game source, mobile wrapper, build instructions and pinned runtime URLs/checksums are available at https://github.com/dovanphit1-creator/Qu-n-soba/tree/android-native . Users can rebuild the APK with a modified/replaced pygame-ce runtime and their own signing key. Android System WebView and its system TextToSpeech engine are installed by the Android platform and are not redistributed in this APK.
