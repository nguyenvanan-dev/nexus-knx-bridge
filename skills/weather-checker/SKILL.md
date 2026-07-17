---
name: weather-checker
description: Lấy thông tin thời tiết thực tế tại khu vực của nhà để làm dữ kiện tự động tạo Kịch bản.
---
# Hướng dẫn
Sử dụng tool này khi người dùng hỏi về thời tiết, hoặc yêu cầu tự động tạo Kịch bản (Scene) dựa trên thời tiết.
Tool sẽ trả về nhiệt độ và tình trạng thời tiết (Mưa, Nắng, Mây...).

## Execution

Pass empty string or JSON through standard input:

```bash
/home/an/knx-bridge/.venv/bin/python /home/an/knx-bridge/skills/weather-checker/main.py
```

## Inputs

No inputs required.

## Safety and Constraints
- Chỉ sử dụng canonical executable được khai báo ở trên.
- Khi executable lỗi hoặc thiếu, trả lỗi rõ ràng.
- Không tự dò trong: skills/official, archived, backups, staging, drafts.
- Không tự dùng web_search khi yêu cầu cấm web_search.
- Không tự tạo scene khi yêu cầu chỉ đọc dữ liệu.
