# Quán Mì Của Tôi — Android

Nhà phát hành **Đỗ Văn Phi**. Bản thử **1.8.0-beta.3**, gameplay Python 1.7.3 không thay đổi. iPhone được giữ trên nhánh `iphone-native` để tiếp tục khi chủ game có Apple Developer Program.

Ứng dụng Android riêng, đóng gói CPython/pygame WebAssembly và toàn bộ mã game, font, âm thanh trong APK. Chạy bằng Android System WebView; không mở website công khai, không tải game từ Internet. Yêu cầu Android 8.0 trở lên và WebView cập nhật có hỗ trợ WebAssembly. Cần thử trên điện thoại thật trước khi phát hành chính thức.

- Giữ tên game và icon bát mì, chơi ngang, chạm/kéo/giữ, phóng to và di chuyển vùng nhìn.
- Tiến trình lưu nguyên tử trong bộ nhớ riêng của ứng dụng; WebView cache không giữ bản lưu. Khi khôi phục bản lưu lỗi, dữ liệu gốc được bảo vệ theo gameplay chung. Gỡ ứng dụng hoặc xóa dữ liệu ứng dụng sẽ mất tiến trình.
- Bàn phím Android để nhập tên món, giá, ca làm; giọng Việt dùng TextToSpeech hệ thống nếu đã cài giọng tiếng Việt.
- Nhân viên không được đảm bảo hoạt động khi Android đình chỉ/đóng ứng dụng nền. Khôi phục lần lưu gần nhất.
- Chỉ phục vụ tài nguyên đóng gói qua WebViewAssetLoader; chặn các tài nguyên/màn hình bên ngoài, không có quyền đọc tệp của điện thoại.

## Dựng và kiểm tra

Dùng workflow `.github/workflows/build-android.yml`. Nó xác minh runtime theo khóa SHA-256 của bản iOS, biên dịch APK, chạy emulator Android 36 và kiểm tra khởi động Python offline, chạm bắt đầu, lưu/đọc lại khi tạo Activity mới, dữ liệu lỗi và đường dẫn bản sao lưu.

Dựng thủ công với Java 17, Android SDK 36, Gradle 8.11.1:

```sh
pip install pygame-ce==2.5.7 pygbag==0.9.3 holidays==0.105 pillow==11.3.0 soundfile==0.13.1 python-dateutil==2.9.0.post0 six==1.17.0
python soba_manual/build_brand_assets.py
python soba_manual/build_audio.py
python soba_android/build.py
cd soba_android
gradle assembleDebug
```

## APK thử và bản chính thức

Từ beta.3, APK phát hành được ký bằng khóa ổn định do chủ game giữ, với application ID `vn.dovanphi.quanmicuatoi.androidbeta`. Mỗi APK sau phải giữ khóa này để cập nhật tại chỗ. APK debug do CI tạo chỉ để kiểm tra, không được phát hành trực tiếp. Workflow phát hành áp dụng bản vá chữ ký công khai lên đúng APK đã kiểm tra, xác minh SHA-256 và chứng chỉ; khóa riêng không xuất hiện trong repo hoặc CI.

Beta.1 và beta.2 dùng khóa debug khác; Android không cho cài đè beta.3 lên hai bản đó. Không hướng dẫn gỡ bản cũ nếu người chơi còn cần tiến trình. Cần sao lưu/chuyển dữ liệu trước khi chuyển bản; thao tác gỡ ứng dụng sẽ mất dữ liệu.

## Thông báo phiên bản mới

Khi game sẵn sàng và khi quay lại ứng dụng sau ít nhất 6 giờ, Android kiểm tra danh sách GitHub Releases công khai trong luồng riêng. Chỉ nhận bản có tag `android-X.Y.Z` hoặc `android-X.Y.Z-beta.N`, APK đúng tên và ghi chú chứa `[android-apk-channel:androidbeta]`; không nhầm bản Windows/iPhone/Google Play. Chọn phiên bản cao nhất tương thích, kể cả prerelease beta, bỏ qua draft/bản bằng hoặc cũ/thiếu APK/URL lạ. Hiện thông báo tiếng Việt có bản đang chơi và nút **Tải bản mới**, **Để sau**. Nút tải mở APK của đúng bản trong trình duyệt; Android vẫn yêu cầu người chơi xác nhận cài đặt. Mất mạng, lỗi GitHub hoặc timeout không chặn game. Không gửi bản lưu hay thông tin cá nhân.

Mỗi lần phát hành APK sau phải giữ application ID, khóa ký và marker kênh trên; tăng versionCode và versionName. Yêu cầu thông báo cập nhật áp dụng cho mọi nền tảng theo AGENTS.md.

Cài trực tiếp APK có thể yêu cầu cho phép trình duyệt cài ứng dụng từ nguồn đó và vẫn có thể xuất hiện cảnh báo của Android/Play Protect. Không cam kết APK bên ngoài cửa hàng sẽ không có cảnh báo.

## Google Play

Gói AAB release dùng application ID ổn định `vn.dovanphi.quanmicuatoi`, target API 36 theo yêu cầu Google Play từ 31/08/2026. .androidbeta APK vẫn dùng hậu tố `.androidbeta` để tách dữ liệu thử. Workflow tạo AAB chưa ký, chỉ sau khi kiểm tra game trên Android thành công. AAB phải được ký bằng upload key riêng trước khi tải lên Play Console; không gửi bản UNSIGNED lên cửa hàng. Khóa upload phải được lưu riêng, không commit lên repo. Với Play App Signing, Google giữ khóa ký phân phối; upload key của chủ game dùng cho các cập nhật tiếp theo.

Tài khoản cá nhân mới có thể phải hoàn thành xác minh tài khoản/thiết bị và thử nghiệm kín ít nhất 12 người tham gia liên tục 14 ngày trước khi xin quyền phát hành công khai. Bản dựng đạt kiểm tra không có nghĩa đã được Google duyệt.

Nguồn chính thức: https://developer.android.com/google/play/requirements/target-sdk ; https://support.google.com/googleplay/android-developer/answer/9842756 ; https://support.google.com/googleplay/android-developer/answer/14151465 .
