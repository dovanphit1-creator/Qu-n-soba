# Quán Mì Của Tôi — iPhone

Nhà phát hành: **Đỗ Văn Phi**. Bản iOS thử nghiệm **1.8.0**, dùng gameplay 1.7.3.

Đây là dự án ứng dụng iOS riêng: giao diện UIKit/WKWebView, Python/pygame chạy bằng WebAssembly được đóng gói trong ứng dụng. Không mở website game công khai. Bộ chạy, mã game, font và âm báo nằm trong gói cài; game không cần tải mã từ Internet. Dữ liệu lưu ở Application Support của ứng dụng, không ở cache trình duyệt. Bản Windows và web hiện hành không bị thay đổi.

## Trạng thái phát hành

Chưa phát hành lên TestFlight/App Store, chưa có IPA được ký để người chơi cài đặt. Chủ game đã tạo tài khoản Apple Developer miễn phí; chưa xác nhận đăng ký Apple Developer Program trả phí. Artifact có chữ `UNSIGNED` chỉ dành cho phát triển, **không phải bộ cài dùng được trên iPhone**. Chỉ đánh dấu sẵn sàng thử nghiệm sau khi workflow `Build and test iPhone application` đạt toàn bộ bước, sau đó vẫn cần kiểm tra trên iPhone thật.

## Các phần dành riêng cho iPhone

- Chạm, kéo thả và giữ tay để dọn dẹp; bỏ sự kiện chuột trùng do SDL tạo từ cùng một lần chạm.
- Chơi ngang, chừa vùng camera và thanh điều hướng.
- Nút phóng to/thu nhỏ, di chuyển vùng nhìn và trở về toàn cảnh; giữ nguyên tỷ lệ hình ảnh.
- Bàn phím iOS cho tên món, giá và tên ca làm.
- Lưu tự động theo chu kỳ của game và yêu cầu lưu khi ứng dụng sắp xuống nền. iOS có thể kết thúc ứng dụng đột ngột; lần lưu gần nhất là điểm phục hồi.
- Lưu nguyên tử; bản lưu lỗi không bị ghi đè. Bắt đầu ván mới sau lỗi sẽ sao lưu dữ liệu gốc trước.
- Đọc món bằng giọng hệ thống `vi-VN` nếu iPhone có giọng này; nhật ký chữ trong game vẫn hoạt động.
- iOS đình chỉ ứng dụng khi ra nền. Bản này không chạy nhân viên liên tục trong nền như Windows. Không coi khoảng thời gian bị đình chỉ là một khung hình dài để tránh nấu hỏng hàng loạt khi quay lại.

## Đóng gói

Workflow trong `.github/workflows/build-ios.yml`:

1. Linux dựng tài nguyên từ Python chung, xác minh SHA-256 của runtime theo `runtime-lock.json`.
2. macOS tạo Xcode project bằng XcodeGen, biên dịch cho iPhone không ký.
3. Simulator kiểm tra lưu/bảo vệ bản lưu, đường dẫn máy chủ nội bộ và khởi động game tới khung hình Python đầu tiên.
4. Lưu kết quả kiểm tra; chỉ tạo artifact ứng dụng phát triển nếu các bước trước thành công.

Để dựng thủ công trên Linux:

```sh
pip install pygame-ce==2.5.7 pygbag==0.9.3 holidays==0.105 pillow==11.3.0 soundfile==0.13.1
python soba_manual/build_brand_assets.py
python soba_manual/build_audio.py
python soba_ios/build.py
```

Font DejaVu được lấy từ gói phát hành chính thức, xác minh SHA-256 và giữ giấy phép; âm thanh chuyển bằng libsndfile qua SoundFile. Không cần cài ffmpeg hoặc gói hệ thống. Chép `soba_ios/Game` và `soba_ios/Assets.xcassets` sang Mac cùng mã nguồn. Hoặc lấy artifact `ios-offline-resources` từ workflow.

Trên Mac có Xcode:

```sh
brew install xcodegen
xcodegen generate --spec soba_ios/project.yml
open soba_ios/QuanMiCuaToi.xcodeproj
```

## Ký và phát hành khi đã có Apple Developer

1. Đăng nhập Apple Account trong Xcode Settings → Accounts trên máy Mac của chủ game. Không đưa mật khẩu, chứng chỉ hay khóa riêng lên GitHub.
2. Trong target QuanMiCuaToi → Signing & Capabilities, chọn Team của chủ game và bật Automatically manage signing. Bundle ID dự kiến: `vn.dovanphi.quanmicuatoi`; đăng ký ID trong tài khoản đó hoặc thay nếu ID không khả dụng.
3. Kết nối iPhone, chọn thiết bị và chạy thử: mở game, tạo ván, mua nguyên liệu, kéo khách, nấu/vớt, giữ để rửa, nhập tiếng Việt, tắt/mở lại, bật chế độ máy bay.
4. Product → Archive → Distribute App → App Store Connect. Tạo hồ sơ game tên **Quán Mì Của Tôi**, thêm thông tin nhà phát hành, ảnh và thông tin quyền riêng tư chính xác.
5. Phát hành bản thử qua TestFlight sau các bước xử lý/xét duyệt của Apple; lấy link mời từ App Store Connect. Việc được duyệt không được đảm bảo bởi bản dựng thành công.

Mã game Python vẫn là nguồn chung. Các thay đổi riêng cho iPhone nằm tại đây, không bật lưu trên bản web dùng thử.

## Kiểm tra bổ sung bằng WebKit

`node soba_ios/test_webkit.cjs` (cần Playwright 1.62.1 và WebKit) chặn mọi kết nối ngoài máy, kiểm tra vào game, chạm nút bắt đầu, phóng to, ghi dữ liệu qua bridge và khôi phục ngân sách đã đổi trong một phiên WebKit hoàn toàn mới. Kiểm tra này không thay thế kiểm tra trên thiết bị iPhone thật.

## Thành phần bên thứ ba

Runtime lấy từ pygame-web/pygbag 0.9.3 (https://github.com/pygame-web/pygbag), CPython 3.12 (https://www.python.org/), pygame-ce 2.5.7 (https://github.com/pygame-community/pygame-ce); cùng holidays, python-dateutil, six và DejaVu fonts. Giữ lại metadata/giấy phép trong các gói phụ thuộc. Khi phát hành chính thức, bổ sung màn hình thông tin giấy phép và gói thông báo đầy đủ cho các thư viện runtime trước khi nộp duyệt.
