# Sprint 10.5 (Phase A) - Manual Test Validation

Đây là danh sách các bài kiểm thử thực địa (Manual Test) bắt buộc phải thực hiện trên phần cứng Raspberry Pi (hoặc Server) kết hợp với các thiết bị cuối (KNX, Zalo, Telegram, Voice).

Hãy copy bảng này và tick [x] vào cột `Result` nếu hệ thống vượt qua. Nếu fail, hãy ghi chú lại log/mã lỗi vào cột `Actual`.

## 1. Zalo / Telegram Integration (Group Chat)

| Test Case | Steps | Expected | Actual | Result |
|---|---|---|---|---|
| **1.1. Thread Isolation** | 1. Group có User A và User B.<br>2. User A: "Bật đèn phòng khách"<br>3. User B: "Thời tiết hôm nay"<br>4. User A: "Giảm còn 30%" | Lệnh của User A phải điều chỉnh đèn, không bị nhiễu bởi câu hỏi của User B. | ... | `[ ]` |
| **1.2. Multiple Replies** | 1. User A gửi nhiều tin nhắn liên tiếp trước khi Bot trả lời.<br>2. Bot gom lại hoặc trả lời theo đúng ngữ cảnh mới nhất. | Bot đọc đúng Context từ Working Memory thay vì mất trí nhớ do xử lý song song. | ... | `[ ]` |
| **1.3. Explicit Mention** | 1. User gọi `@Bot` trong nhóm có nhiều bot khác.<br>2. Bot chỉ phản hồi khi được gọi trực tiếp. | Bot nhận lệnh và trả lời đúng. | ... | `[ ]` |

## 2. KNX Command Pipeline Verification

| Test Case | Steps | Expected | Actual | Result |
|---|---|---|---|---|
| **2.1. Basic Control** | 1. Gửi lệnh: "Bật đèn phòng ngủ"<br>2. KNX bật đèn thật.<br>3. StateManager đổi trạng thái thành ON. | Đèn sáng, Dashboard cập nhật ON ngay lập tức, Bot xác nhận "Đã bật". | ... | `[ ]` |
| **2.2. Value Setting** | 1. Gửi lệnh: "Đặt nhiệt độ điều hòa 24 độ"<br>2. KNX set DPT 9.001 thành 24. | Máy lạnh chuyển 24, Bot xác nhận. | ... | `[ ]` |
| **2.3. Read-back Verification** | 1. Thay đổi trạng thái thiết bị bằng công tắc cơ/phần cứng.<br>2. Hỏi Bot: "Đèn phòng khách đang bật hay tắt?" | Bot trả lời đúng trạng thái hiện tại lấy từ StateManager. | ... | `[ ]` |

## 3. Restart Recovery (End-to-End)

| Test Case | Steps | Expected | Actual | Result |
|---|---|---|---|---|
| **3.1. DB Reconnect** | 1. Chat tạo vài context.<br>2. `systemctl restart smarthome-db` (hoặc restart service DB giả lập).<br>3. Tiếp tục chat tiếp ngữ cảnh. | Bot không bị crash, tự động kết nối lại DB và nhớ câu chuyện trước đó. | ... | `[ ]` |
| **3.2. Cold Restart** | 1. Rút điện Raspberry Pi / Reboot Server.<br>2. Gửi lệnh chat ngay khi server lên. | AI tự động load lại Preference, Summary từ SQLite, tiếp tục hoạt động. | ... | `[ ]` |
