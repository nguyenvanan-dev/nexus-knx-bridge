# KNX Bridge - Tích Hợp OpenClaw & AI Skills

Tài liệu chi tiết cơ chế tích hợp giữa KNX Bridge và OpenClaw Engine.

## 1. Kiến Trúc Symlink Single Source of Truth
 đảm bảo tất cả AI Skills được đồng bộ trực tiếp từ repository KNX Bridge sang workspace của OpenClaw mà không bị trùng lặp code, hệ thống duy trì đường liên kết symlink:

```text
$HOME/.openclaw/workspace/skills  --->  <project-directory>/skills
```

Khi cập nhật cấu hình OpenClaw từ Setup Wizard hoặc backend service (`services/openclaw_config_service.py`), hệ thống tự động kiểm tra và khởi tạo symlink này.

## 2. Quản Lý AI Provider & Credentials Safe Mode
- Cấu hình provider / model của OpenClaw được lưu tại `~/.openclaw/openclaw.json`.
- Chú ý: File secret credentials (`~/.openclaw/credentials`) chứa API Key của OpenClaw tuyệt đối **KHÔNG** được ghi đè hoặc hiển thị qua bất kỳ endpoint API công khai nào.
- Endpoint `GET /api/setup/openclaw/status` chỉ trả về thông tin metadata an toàn (tên provider, model, trạng thái 9router service, tính hợp lệ của skills symlink).

## 3. An Toàn Vận Hành (Safety Rules)
- Không kill / restart service `9router` tự động ngoại trừ các lệnh bảo trì thủ công được xác nhận bởi admin.
- Mọi tương tác AI Skill đều tuân thủ nguyên tắc Read-Only / Proposal trước khi thực hiện KNX Write.
