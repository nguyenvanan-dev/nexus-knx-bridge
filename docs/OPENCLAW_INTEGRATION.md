# KNX Bridge - OpenClaw, 9router & AI Skills

OpenClaw và 9router có vai trò độc lập:

```text
AI providers/accounts -> 9router -> OpenClaw -> skills -> KNX Bridge
```

- **9router** gom các provider/tài khoản AI, quản lý quota và tự động fallback.
  Nó cung cấp endpoint OpenAI-compatible, mặc định
  `http://127.0.0.1:20128/v1`.
- **OpenClaw** là agent runtime xử lý Telegram/Zalo, điều phối skills và gọi
  KNX Bridge. OpenClaw có thể dùng 9router làm provider hoặc kết nối trực tiếp
  tới một provider khác.
- **KNX Bridge** vẫn có thể hoạt động độc lập cho KNX-only mà không cần hai
  runtime trên.

API key của provider trực tiếp được nhập ở bước **AI Provider** trong Setup
Wizard. 9router chỉ xuất hiện như một lựa chọn provider OpenAI-compatible khi
người dùng chủ động muốn dùng cơ chế gom tài khoản và fallback quota.

## 1. Kiến Trúc Symlink Single Source of Truth
 đảm bảo tất cả AI Skills được đồng bộ trực tiếp từ repository KNX Bridge sang workspace của OpenClaw mà không bị trùng lặp code, hệ thống duy trì đường liên kết symlink:

```text
$HOME/.openclaw/workspace/skills  --->  <project-directory>/skills
```

Khi cập nhật cấu hình OpenClaw từ Setup Wizard hoặc backend service (`services/openclaw_config_service.py`), hệ thống tự động kiểm tra và khởi tạo symlink này.

## 2. Workspace Template

Repository cung cấp template sạch tại:

```text
openclaw/workspace-template/
├── AGENTS.md
├── IDENTITY.md
├── SOUL.md
└── TOOLS.md
```

Installer hoặc Setup Wizard chỉ tạo các file còn thiếu trong
`$HOME/.openclaw/workspace`. File đã tồn tại được giữ nguyên và không bao giờ bị
ghi đè tự động. Credential, pairing và cấu hình riêng tiếp tục nằm ngoài Git.

## 3. Quản Lý AI Provider & Credentials Safe Mode
- Cấu hình provider / model của OpenClaw được lưu tại `~/.openclaw/openclaw.json`.
- Chú ý: File secret credentials (`~/.openclaw/credentials`) chứa API Key của OpenClaw tuyệt đối **KHÔNG** được ghi đè hoặc hiển thị qua bất kỳ endpoint API công khai nào.
- Endpoint `GET /api/setup/openclaw/status` chỉ trả về metadata an toàn: trạng
  thái OpenClaw runtime, trạng thái 9router riêng biệt, provider/model và tính
  hợp lệ của skills symlink.

## 4. An Toàn Vận Hành (Safety Rules)
- Không kill/restart OpenClaw hoặc `9router` tự động ngoài thao tác bảo trì được
  admin xác nhận.
- Mọi tương tác AI Skill đều tuân thủ nguyên tắc Read-Only / Proposal trước khi thực hiện KNX Write.
