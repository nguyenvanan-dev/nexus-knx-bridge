# Local Tool Notes

Các skill chính thức nằm trong workspace `skills` và được liên kết tới thư mục
`skills/` của NEXUS KNX Bridge.

## Canonical Skills

- `knx-bridge`: điều khiển và đọc trạng thái KNX.
- `ets-parser`: phân tích dự án ETS và tạo proposal.
- `document-reader`: đọc tài liệu thiết bị.
- `apply-proposal`: áp dụng proposal sau khi được duyệt.
- `scene-creator`, `scene-manager`: tạo và quản lý scene.
- `agent-memory`: ghi nhớ và tìm lại ngữ cảnh.
- `zalo-history`: đọc lịch sử Zalo từ nguồn dữ liệu có thẩm quyền.

Không ghi đường dẫn tuyệt đối, token, địa chỉ thiết bị hoặc thông tin riêng của
công trình vào file template này. Thông tin riêng phải nằm trong cấu hình
runtime, SQLite Device Registry hoặc credential store của OpenClaw.
