# Khóa upload Google Play

Application ID: `vn.dovanphi.quanmicuatoi`.

Alias upload: `quanmicuatoi-upload`; định dạng keystore PKCS12; thuật toán RSA 4096 / SHA256withRSA.

Bản sao riêng của chủ game có tên `QuanMiCuaToi-UploadKey-PRIVATE.zip`, chứa keystore, mật khẩu và chứng chỉ công khai. Không đưa tệp này lên GitHub, Releases, trang web hoặc chia sẻ cho người chơi. Chủ game cần giữ bản sao an toàn để tiếp tục ký các bản cập nhật. Tệp AAB đã ký tên `QuanMiCuaToi-GooglePlay-1.8.0-beta.1.aab` đã vượt qua Google bundletool validate; đây không phải bằng chứng Google đã duyệt ứng dụng.

Google Play App Signing giữ khóa phân phối ứng dụng. Khóa trên chỉ là khóa upload, dùng để xác thực gói mà chủ game đưa lên Console. Không dùng APK debug làm bản chính thức và không gửi AAB UNSIGNED lên Play.

Ví dụ ký gói mới với Java 17 JDK, đặt khóa và tệp mật khẩu ngoài checkout:

```sh
jarsigner -keystore /path/private/QuanMiCuaToi-upload.p12 -storepass:file /path/private/upload-password.txt -keypass:file /path/private/upload-password.txt -sigalg SHA256withRSA -digestalg SHA-256 -signedjar QuanMiCuaToi-signed.aab QuanMiCuaToi-UNSIGNED.aab quanmicuatoi-upload
jarsigner -verify -keystore /path/private/QuanMiCuaToi-upload.p12 -storepass:file /path/private/upload-password.txt QuanMiCuaToi-signed.aab
```

Tăng versionCode cho mỗi lần tải bản mới lên Play. Hãy kiểm tra application ID, tiến trình lưu và chạy thử trước khi tải lên. Nếu dùng GitHub Actions để ký tự động sau này, chủ repo phải thiết lập Secrets riêng; workflow hiện tại không chứa khóa hoặc mật khẩu.
