# Bộ cài Quán Mì Của Tôi

GitHub Actions tạo `QuanMiCuaToi-Setup.exe` bằng Inno Setup sau khi kiểm tra game.
Tệp tải không dấu; shortcut Desktop, Start menu và tên game có dấu đầy đủ.

- Cài riêng cho tài khoản hiện tại, không yêu cầu quyền quản trị.
- Vị trí mặc định: `%LOCALAPPDATA%\Programs\QuanMiCuaToi`.
- Lưu game ở vị trí cũ `%LOCALAPPDATA%\QuanSobaManual\save-vnd.json`.
- Không thêm dữ liệu chơi thử vào bộ cài. Cài lại/nâng cấp/gỡ bỏ không xóa bản lưu.
- AppId trong `game.iss` phải được giữ nguyên qua các phiên bản.
- Có biểu tượng trong menu Start và tùy chọn tạo biểu tượng Desktop, bật mặc định.
- Có thể gỡ qua Windows Settings → Apps.
- Game và bộ cài chưa ký số. Thông tin nhà phát hành không thay thế chữ ký số.

Khi phát hành, tải artifact `QuanMiCuaToi-Setup`, giải nén artifact và đính kèm
`QuanMiCuaToi-Setup.exe` trực tiếp vào GitHub Release chính thức. Người chơi tải
bộ cài này mà không phải giải nén. Bộ kiểm tra cập nhật trong game tiếp tục mở
trang Release để người chơi tải bản mới.

Kiểm tra tự động trên Windows dùng hồ sơ CI mới, cài thật, xác nhận shortcut,
chạy game đã cài, cài lại, gỡ bỏ và đối chiếu SHA256 bản lưu sau mỗi bước.
