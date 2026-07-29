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
./install.sh
```

Kiểm tra trạng thái sau cài đặt:
```bash
./check_installation.sh
```

## 3. Khởi Chạy Setup Wizard
Truy cập giao diện Web UI qua trình duyệt:
`http://<IP_RASPBERRY_PI>:3000/setup`

Setup Wizard hỗ trợ 10 bước cấu hình trực quan:
1. **System Baseline:** Tên công trình, Múi giờ, Ngôn ngữ.
2. **Admin Account:** Tạo tài khoản quản trị ban đầu.
3. **KNX Gateway:** IP/Host, Port, kiểu kết nối (Tunneling/Routing), địa chỉ cá nhân + Nút kiểm tra Socket connection dry-run.
4. **AI Provider:** OpenAI, Anthropic, Gemini, Ollama + Format dry-run test.
5. **OpenClaw Integration:** Quản lý skill symlink & trạng thái 9router.
6. **Telegram Notification:** Cấu hình Bot Token & Chat ID + Format dry-run test.
7. **Zalo Integration:** Cấu hình Webhook URL + Format dry-run test.
8. **Remote Access:** Kiểm tra trạng thái Tailscale VPN (Read-only).
9. **Review & Summary:** Khái quát toàn bộ cấu hình trước khi lưu.
10. **Complete:** Hoàn tất cài đặt và khóa Setup Wizard.

## 4. Quản Lý Dịch Vụ Systemd
```bash
# Khởi động dịch vụ
systemctl --user start knx-bridge.service knx-frontend.service

# Xem trạng thái
systemctl --user status knx-bridge.service knx-frontend.service
```

## 5. Khôi Phục & Dọn Dẹp
Hủy dịch vụ và giữ lại database / config:
```bash
./uninstall.sh
```

Hủy dịch vụ và xóa toàn bộ virtualenv & config:
```bash
./uninstall.sh --purge
```
