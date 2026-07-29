# NEXUS KNX Bridge Security Policy

## Reporting a Vulnerability

Do not publish API keys, credentials, pairing data, database contents or a
working exploit in a public issue. Use GitHub's private vulnerability reporting
feature for this repository. Include affected version, reproduction steps and
the expected impact without attaching production secrets.

## 1. Nguyên Tắc Zero-Secret Exposure
1. **Không in hoặc lưu secret trong Git:** Toàn bộ API Key, Password, Token Telegram/Zalo, Credentials OpenClaw tuyệt đối không được ghi vào file source code hoặc commit vào Git.
2. **Atomic Write & File Permission:** File cấu hình tập trung `config.json` chỉ lưu giá trị trong local filesystem với phân quyền strict `0600` (chỉ user sở hữu có quyền đọc/ghi).
3. **Secret Masking:** Các endpoint API công khai (`GET /api/setup/status`, `GET /api/system/integrations`) luôn che giấu secret dưới dạng `{ "configured": true, "masked_hint": "a1b2..." }`.

## 2. API Key Security & Fail-Closed Model
- Mọi request ghi (POST/PUT/DELETE) từ IP ngoại mạng yêu cầu header `X-API-KEY`.
- Nếu biến môi trường `API_KEY` chưa được thiết lập hoặc sử dụng key mặc định
  yếu (`knx-secret-key-123`, `admin`, `123456`), request ghi từ máy khác bị
  từ chối theo cơ chế **fail-closed**. Installer tạo key ngẫu nhiên khi cài mới.

## 3. Sanitize Database Query & Bus Safety
- Endpoint thực thi SQL (`/api/database/query`) loại bỏ hoàn toàn các trường nhạy cảm như hash mật khẩu hoặc API Key nếu được gọi qua public API.
- Không gửi telegrams KNX giả lập hoặc thực hiện ghi đè dữ liệu bus (`KNX write`) khi chạy các bước kiểm tra (dry-run test) trong Setup Wizard.
