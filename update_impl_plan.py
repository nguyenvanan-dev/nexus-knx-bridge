import re

with open("/home/an/.gemini/antigravity/brain/8c60bceb-0840-405c-b673-0b2d2cfc7109/implementation_plan.md", "r") as f:
    code = f.read()

new_phase_b = """## Phase B: Hoàn thiện Admin Dashboard
Theo đúng Product Vision, Phase B sẽ hoàn tất sau 5 mục tiêu sau đây theo thứ tự ưu tiên:

### Sprint 7: Device Management Hoàn thiện
- Tích hợp Device Wizard (thêm thiết bị dễ dàng).
- Hỗ trợ Bulk Import (từ CSV/ETS).
- Tính năng Clone thiết bị nhanh.

### Sprint 8: Automation CRUD
- Giao diện trực quan tạo, sửa, xóa rule trên Web (Triggers, Conditions, Actions).
- Quản lý metadata rule (enable/disable, priority).

### Sprint 9: Diagnostics Hub
- Live Bus Monitor (hiển thị realtime telegram KNX).
- KNX Group Address Tester.
- Event Center (giám sát EventBus).

### Sprint 10: Database Browser
- Visual CRUD cho các bảng trong SQLite (`smarthome.db`).
- Tính năng Auto Backup & 1-click Restore.

### Sprint 11: Logs & Audit Center
- Giao diện xem lịch sử thiết bị và lệnh (Audit Logs).
- Truy xuất lỗi hệ thống (FastAPI, OpenClaw).

---
## User Review Required"""

old_phase_b_pattern = r"## Phase B: Hoàn thiện Admin Dashboard.*?## User Review Required"
code = re.sub(old_phase_b_pattern, new_phase_b, code, flags=re.DOTALL)

with open("/home/an/.gemini/antigravity/brain/8c60bceb-0840-405c-b673-0b2d2cfc7109/implementation_plan.md", "w") as f:
    f.write(code)
