# Quán Soba 🍜

Game mô phỏng kinh doanh quán mì soba bằng Python, chơi trên dòng lệnh bằng tiếng Việt. Bạn bắt đầu với 1.800 xu, chuẩn bị nguyên liệu và phục vụ khách mỗi ngày. Mục tiêu là đạt **10.000 xu** và **80 danh tiếng**.

## Cách chạy

Cần Python 3.9 trở lên; không cần cài thư viện ngoài.

```bash
python soba_game.py
```

Trên một số máy, dùng `python3 soba_game.py` hoặc `py soba_game.py`.

## Cách chơi

1. **Mua nguyên liệu:** mì, nước dùng, rau và thịt. Soba truyền thống cần mì + nước dùng + rau; soba đặc biệt cần thêm thịt.
2. **Đặt giá:** giá cao tăng tiền mỗi tô nhưng giảm khả năng khách mua. Giá tham khảo là 160 xu cho món truyền thống và 250 xu cho món đặc biệt.
3. **Nâng cấp:** bếp và bàn ghế tăng sức phục vụ; biển hiệu thu hút khách. Quảng cáo giá 150 xu và chỉ áp dụng cho ngày hiện tại.
4. **Mở cửa:** thời tiết, danh tiếng, giá bán, sức chứa và kho nguyên liệu quyết định kết quả trong ngày. Quán trả tiền thuê và lương hàng ngày.
5. **Xem báo cáo:** theo dõi doanh thu và lãi/lỗ vận hành của 10 ngày gần nhất.

Game tự lưu vào `soba_save.json` sau mỗi ngày và khi thoát. Chọn **Chơi lại từ đầu** trong menu để tạo ván mới. Tệp lưu này nằm cùng thư mục với chương trình và không cần đưa lên GitHub.

## Lưu ý

Lãi/lỗ vận hành trong báo cáo là doanh thu trừ tiền thuê và lương; chi phí mua nguyên liệu, nâng cấp và quảng cáo được trừ trực tiếp khỏi tiền mặt khi bạn chi. Game tiếp tục sau khi đạt mục tiêu để bạn tự phát triển quán.
