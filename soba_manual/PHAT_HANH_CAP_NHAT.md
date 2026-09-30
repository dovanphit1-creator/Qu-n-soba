# Phát hành để người chơi nhận thông báo

Bản EXE có kiểm tra cập nhật dùng `GAME_VERSION` trong `soba_manual/brand.py` (hiện 1.0.0).
Mỗi lần mở, game gửi một GET công khai tới GitHub Releases ở luồng nền, timeout 5 giây.
Không gửi dữ liệu chơi, không yêu cầu tài khoản hoặc token, không tự cài hay ghi đè EXE.
Khi offline, hết hạn mức GitHub hoặc dữ liệu không hợp lệ, người chơi tiếp tục chơi.

Cho bản tiếp theo:

1. Tăng GAME_VERSION, ví dụ 1.0.1 hoặc 1.1.0, rồi đóng gói Windows.
2. Tạo GitHub Release trong kho dovanphit1-creator/Qu-n-soba với tag tương ứng: v1.0.1 hoặc 1.0.1.
3. Viết ghi chú thay đổi, đính kèm EXE hoặc ZIP dành cho Windows.
4. Publish release chính thức; không chọn Pre-release và đánh dấu bản đó là Latest.
5. Người dùng bản có chức năng này nhận thông báo ở lần mở game tiếp theo khi có Internet.

Các bản EXE cũ chưa có bộ kiểm tra phải được tải thay thế một lần bằng bản có tính năng này.
Nút Tải bản mới mở trang phát hành GitHub; người chơi tự tải, thoát bản cũ và chạy bản mới.
Giữ nguyên đường dẫn lưu QuanSobaManual/save-vnd.json và tương thích định dạng bản lưu.
Không đổi tên game hoặc icon bát mì.
