---
name: ets-parser
description: Đọc và bóc tách dữ liệu cấu hình phần cứng từ file .knxproj hoặc .esf. Cấm dùng tool đọc tài liệu văn bản (document-reader) để xử lý các file đuôi này.
---

# ets-parser

Công cụ AI chuyên dụng để phân tích và bóc tách danh sách thiết bị KNX từ các file cấu hình dự án ETS (.knxproj, .esf) được tải lên từ Zalo/Telegram.

## Tính năng an toàn (Anti-Risk)
- Tool này sử dụng `core.knxproj_parser.ETSParser` để giải mã dữ liệu offline.
- KHÔNG thao tác trực tiếp với Database.
- Tool đóng vai trò tạo ra "Bản Nháp" (Proposal) và xuất ra đoạn hội thoại an toàn để Agent xác nhận với Quản trị viên (Admin) trước khi import thực tế.
