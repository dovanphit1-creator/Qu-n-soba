# Quán Mì Của Tôi — Android

Nhà phát hành **Đỗ Văn Phi**. Bản thử **1.8.0-beta.1**, gameplay Python 1.7.3 không thay đổi. iPhone được giữ trên nhánh `iphone-native` để tiếp tục khi chủ game có Apple Developer Program.

Ứng dụng Android riêng, đóng gói CPython/pygame WebAssembly và toàn bộ mã game, font, âm thanh trong APK. Chạy bằng Android System WebView; không mở website công khai, không tải game từ Internet. Yêu cầu Android 8.0 trở lên và WebView cập nhật có hỗ trợ WebAssembly. Cần thử trên điện thoại thật trước khi phát hành chính thức.

- Giữ tên game và icon bát mì, chơi ngang, chạm/kéo/giữ, phóng to và di chuyển vùng nhìn.
- Tiến trình lưu nguyên tử trong bộ nhớ riêng của ứng dụng; WebView cache không giữ bản lưu. Khi khôi phục bản lưu lỗi, dữ liệu gốc được bảo vệ theo gameplay chung. Gỡ ứng dụng hoặc xóa dữ liệu ứng dụng sẽ mất tiến trình.
- Bàn phím Android để nhập tên món, giá, ca làm; giọng Việt dùng TextToSpeech hệ thống nếu đã cài giọng tiếng Việt.
- Nhân viên không được đảm bảo hoạt động khi Android đình chỉ/đóng ứng dụng nền. Khôi phục lần lưu gần nhất.
- Chỉ phục vụ tài nguyên đóng gói qua WebViewAssetLoader; chặn các tài nguyên/màn hình bên ngoài, không có quyền đọc tệp của điện thoại.

## Dựng và kiểm tra

Dùng workflow `.github/workflows/build-android.yml`. Nó xác minh runtime theo khóa SHA-256 của bản iOS, biên dịch APK, chạy emulator Android 35 và kiểm tra khởi động Python offline, chạm bắt đầu, lưu/đọc lại khi tạo Activity mới, dữ liệu lỗi và đường dẫn bản sao lưu.

Dựng thủ công với Java 17, Android SDK 35, Gradle 8.11.1:

```sh
pip install pygame-ce==2.5.7 pygbag==0.9.3 holidays==0.105 pillow==11.3.0 soundfile==0.13.1
python soba_manual/build_brand_assets.py
python soba_manual/build_audio.py
python soba_android/build.py
cd soba_android
gradle assembleDebug
```

## APK thử và bản chính thức

APK thử được ký bằng khóa debug của môi trường dựng và dùng application ID riêng `vn.dovanphi.quanmicuatoi.androidbeta`. Đây là bản thử cài trực tiếp, chưa đăng Google Play. Khóa debug có thể thay đổi giữa các lần dựng; không dùng nó để hứa cập nhật giữ nguyên dữ liệu. Bản chính thức phải có khóa ký ổn định do chủ game giữ, đưa vào GitHub Actions Secrets, tuyệt đối không commit khóa riêng hoặc mật khẩu. Bản chính thức dùng application ID riêng và cần cơ chế chuyển tiến trình nếu muốn mang dữ liệu từ beta sang.

Cài trực tiếp APK có thể yêu cầu cho phép trình duyệt cài ứng dụng từ nguồn đó và vẫn có thể xuất hiện cảnh báo của Android/Play Protect. Không cam kết APK bên ngoài cửa hàng sẽ không có cảnh báo.
