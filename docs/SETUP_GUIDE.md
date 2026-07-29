# KNX Bridge - Hướng Dẫn Thiết Lập & Cấu Hình (Setup Guide)

Tài liệu hướng dẫn cài đặt, cấu hình và vận hành hệ thống KNX Bridge cho công trình mới.

## 1. Yêu Cầu Hệ Thống
- **Hệ điều hành:** Linux (Ubuntu / Debian / Raspberry Pi OS 64-bit)
- **Python:** >= 3.10
- **Node.js:** >= 18.x
- **Cổng kết nối:**
  - `5055` - KNX Bridge FastAPI Backend
  - `3000` - KNX Bridge Next.js Web UI
  - `3671` - KNX IP Gateway (UDP/TCP)

## 2. Cài Đặt Tự Động (Automated Installation)
Thực thi script installer đi kèm repository:
```bash
# Chỉ kiểm tra yêu cầu, không thay đổi hệ thống
./install.sh --check-only

# Cài đặt
./install.sh
```

Nếu đây là lần cài đầu tiên, installer tạo `.env` với quyền `0600` và ba
khóa ngẫu nhiên phục vụ JWT, API nội bộ và bootstrap setup. Các khóa này chỉ
nằm trên máy cài đặt, không được đưa vào Git.

Kiểm tra trạng thái sau cài đặt:
```bash
./check_installation.sh
```

## 3. Khởi Chạy Setup Wizard
Truy cập giao diện Web UI qua trình duyệt:
`http://<IP_RASPBERRY_PI>:3000/setup`

Sau khi đăng nhập, Setup Wizard cũng có thể mở từ:
`Settings & System -> Integration Setup`.

Ở lần thiết lập đầu tiên, lấy bootstrap token ngay trên máy cài đặt:
```bash
grep '^SETUP_BOOTSTRAP_TOKEN=' .env
```
Không gửi token này qua chat hoặc commit vào repository.

Setup Wizard hỗ trợ 10 bước cấu hình trực quan:
1. **System Baseline:** Tên công trình, Múi giờ, Ngôn ngữ.
2. **Admin Account:** Tạo tài khoản quản trị ban đầu.
3. **KNX Gateway:** IP/Host, Port, kiểu kết nối (Tunneling/Routing), địa chỉ cá nhân + Nút kiểm tra Socket connection dry-run.
4. **AI Provider:** Thêm nhiều provider, danh sách nhiều model, model mặc định,
   kiểu API, base URL, timeout và API key được che an toàn.
5. **OpenClaw Integration:** Runtime, workspace, provider/model, skill symlink,
   trạng thái 9router và credential riêng cho skill/plugin.
6. **Telegram Notification:** Bot Token, Chat ID, allow-list và trạng thái pairing.
7. **Zalo Integration:** Zalo Bot token/webhook/allow-list và Zalo Personal
   QR login, trạng thái runtime, lựa chọn group, giới hạn lịch sử và chế độ chỉ
   phản hồi khi được nhắc tên.
8. **Remote Access:** Kiểm tra trạng thái Tailscale VPN (Read-only).
9. **Review & Summary:** Khái quát toàn bộ cấu hình trước khi lưu.
10. **Complete:** Kiểm tra các trường bắt buộc, lưu cấu hình và thông báo service cần restart.

Các nút kiểm tra trong Wizard chỉ xác minh cấu trúc hoặc kết nối được mô tả
trên giao diện. Chúng không gửi Telegram/Zalo thật và không ghi KNX.

## 4. Kiểm Tra Trước Khi Kết Nối Thiết Bị Thật

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/ -q
cd frontend
npm audit --audit-level=high
npm run build
```

Chỉ chạy KNX write hoặc gửi tin nhắn thử sau khi chủ hệ thống xác nhận rõ.

## 5. Quản Lý Dịch Vụ Systemd
```bash
# Khởi động dịch vụ
systemctl --user start knx-bridge.service knx-frontend.service

# Xem trạng thái
systemctl --user status knx-bridge.service knx-frontend.service
```

## 6. Khôi Phục & Dọn Dẹp
Hủy dịch vụ và giữ lại database / config:
```bash
./uninstall.sh
```

Hủy dịch vụ và xóa toàn bộ virtualenv & config:
```bash
./uninstall.sh --purge
```
