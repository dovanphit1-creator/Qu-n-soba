<p align="center"><img src="docs/assets/icon.png" width="110" alt="Bát mì — biểu tượng Quán Mì của tôi"></p>
<h1 align="center">Quán Mì của tôi</h1>
<p align="center"><strong>Một quán nhỏ. Từng bát mì. Câu chuyện của bạn.</strong></p>
<p align="center">Game mô phỏng kinh doanh quán mì bằng tiếng Việt, tự tay thao tác bằng chuột.</p>
<p align="center"><a href="https://quan-mi-cua-toi-web.dovanphit1.chatgpt.site"><strong>🍜 Chơi trên web</strong></a> &nbsp; · &nbsp; <a href="https://github.com/dovanphit1-creator/Qu-n-soba/releases/download/1.0.0/Quan.Mi.c.a.toi.exe"><strong>↓ Tải Windows (.exe)</strong></a> &nbsp; · &nbsp; <a href="https://github.com/dovanphit1-creator/Qu-n-soba/releases">Các bản phát hành</a></p>

![Giao diện thật của Quán Mì của tôi](docs/assets/gameplay.png)

## Tự tay chăm sóc quán của bạn

- **Đón từng nhóm khách:** trả lời còn chỗ hay phải đợi, nhận phiếu ăn, kéo khách đến bàn và ghép chỗ khi cần.
- **Nấu từng bát mì:** 6 nồi bếp, thời gian luộc 3 phút 30 giây; vớt kịp, thêm topping rồi phục vụ đúng bàn.
- **Giữ quán sạch sẽ:** thu bát, bấm rửa, lau bàn và dọn quán trước khi đóng cửa.
- **Xây dựng quán riêng:** mua bàn ghế, mở rộng tối đa 3 tầng, tự tạo menu và tính giá vốn mỗi món.
- **Quản lý nguồn hàng:** hợp đồng nhà cung cấp giảm 3% so với mua lẻ; đặt trước 23 giờ để giao lúc 8 giờ sáng hôm sau.
- **Theo dõi kinh doanh:** tiền VND, giờ và lịch Việt Nam, báo cáo theo ngày, tháng, năm.

Bạn bắt đầu với **10.000.000 VND**, **7% danh tiếng**, **1 bàn 4 chỗ** và **kho trống**. Mua bát đĩa, mì và topping trước khi mở cửa đón khách đầu tiên.

## Chọn phiên bản

| | Web | Windows |
|---|---|---|
| Bắt đầu | Mở link và chơi trên trình duyệt | Tải tệp `.exe`, mở để chơi; không cần Python |
| Tiến trình | Không lưu; tải lại hoặc đóng trang là chơi lại | Tự lưu trên máy, lần sau tiếp tục |
| Thiết bị | Máy tính có chuột và bàn phím | Máy tính Windows |
| Chi phí | Miễn phí | Miễn phí |

Bản Windows lưu trong `%LOCALAPPDATA%\QuanSobaManual\save-vnd.json`. Hai phiên bản không đồng bộ dữ liệu.

Bản `1.0.0` hiện được đánh dấu **Pre-release** trên GitHub. Tệp Windows chưa ký số nên có thể xuất hiện cảnh báo nhà phát hành.

## Góp ý và cập nhật

Báo lỗi hoặc góp ý tại [Issues](https://github.com/dovanphit1-creator/Qu-n-soba/issues). Xem tệp tải và phiên bản tại [Releases](https://github.com/dovanphit1-creator/Qu-n-soba/releases).

## Trang giới thiệu và mã nguồn

- Trang giới thiệu hoàn chỉnh nằm trong [`docs/`](docs/). Xem [hướng dẫn bật GitHub Pages](GITHUB_PAGES.md).
- Mã nguồn game giao diện và quy trình đóng gói Windows hiện ở nhánh [`build-windows-app`](https://github.com/dovanphit1-creator/Qu-n-soba/tree/build-windows-app).
- `soba_game.py` trên nhánh `main` là bản dòng lệnh ban đầu, được giữ lại để tham khảo.
