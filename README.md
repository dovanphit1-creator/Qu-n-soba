# Quán Soba — Tự tay vận hành

Game Python 2D nhìn từ trên xuống, thao tác chuột. Có người đi bộ ngoài phố và nhóm 1–4 khách vào hỏi chỗ. Người chơi trả lời khách, nhận phiếu ở máy bán vé, kéo nhóm vào bàn đủ ghế, nấu từng bát mì rồi phục vụ và vệ sinh quán.

## Chơi trên Windows

Giải nén bản `QuanSoba-Manual-Windows`, nhấp đúp `QuanSoba.exe`. Không cần Python hay Internet. Bản Windows được tạo bằng GitHub Actions và chính tệp exe được chạy kiểm tra chu trình phục vụ trước khi phát hành gói tải.

## Chạy từ mã nguồn

```sh
python -m pip install pygame-ce==2.5.7
python soba_manual/main.py
```

## Thao tác

- Chọn **Luyện tập** để có sẵn nhóm đầu tiên; hoặc mở quán thường với danh tiếng 2%.
- Trả lời khách ở cửa; sau khi chấp nhận, đợi máy in phiếu rồi nhấp phiếu vàng.
- Kéo nhóm đã nhận phiếu đến bàn sạch đủ số ghế. Nhấp tên nhóm hoặc bàn để đọc món theo thứ tự khách trên phiếu.
- Kéo mì tươi vào một trong **6 nồi**. Mỗi nồi luộc **210 giây thực**, sau đó có **10 giây** để nhấp vớt. Mì quá thời gian bị nhão, vẫn có thể dùng; nhấp phải nồi để đổ bỏ.
- Kéo bát vừa vớt từ nồi xuống ô quầy topping. Kéo từng topping vào bát, rồi kéo từng bát đến bàn. Làm sai món vẫn giao được nhưng khách chấm điểm theo tính cách.
- Khách ăn xong: kéo bát bẩn đến bồn, nhấp bàn để lau, nhấp **Rửa bát** để rửa từng mẻ tối đa 6 bát. Bồn không tự rửa.
- Nhập hàng, ngừng đón khách và dọn sạch quán trước khi sang ngày mới.
- **Space** tạm dừng; **F1** mở hướng dẫn. Game tự tạm dừng khi mất tiêu điểm.

## Lượng khách

Mỗi nhóm đi ngang cửa được xét ghé quán một lần. Công thức là danh tiếng cộng điểm phần trăm:

| Loại ngày | Giờ thường | Cao điểm |
| --- | --- | --- |
| Thứ Hai–Năm | +0 | +10 |
| Thứ Sáu–Chủ nhật | +5 | +20 |
| Ngày lễ | +15 | +30 |

Cao điểm: 11–14h và 17–20h. Lễ trong lịch game: ngày 14, 28, 42… Danh tiếng bắt đầu 2%, không giảm dưới 0 và không giới hạn khi tăng. Xác suất khách vào tối đa 100%. Ba giây thực bằng một phút trong quán; điều này không rút ngắn thời gian luộc 210 giây.

Tiến trình lưu tại `%LOCALAPPDATA%\QuanSobaManual\save.json`; luyện tập dùng `practice.json` riêng.

## Kiểm tra

```sh
python soba_manual/test_game.py
python soba_manual/main.py --smoke-test smoke.json
```

Kiểm tra bao gồm chu trình nhận phiếu, kéo nhóm vào bàn, nấu/vớt/di chuyển bát, thêm topping, phục vụ, dọn/rửa thủ công, giới hạn ghế, thời điểm mì nhão, công thức lượng khách và lưu/đọc ván chơi. Bản dòng lệnh cũ vẫn ở `soba_game.py`; giao diện quản lý cũ ở `soba_gui.py`.
