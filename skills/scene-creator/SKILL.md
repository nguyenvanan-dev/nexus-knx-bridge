---
name: scene-creator
description: Dùng để dự thảo Kịch bản tự động (Scene) dựa trên yêu cầu của người dùng. Tuân thủ chuẩn Anti-Risk: không ghi trực tiếp vào DB.
---
# Hướng dẫn
Sử dụng tool này khi người dùng yêu cầu tạo Kịch bản (Scene).
Ví dụ: "Tạo kịch bản đi ngủ tắt hết đèn"

Tham số đầu vào (--actions_json) là một chuỗi JSON array định nghĩa các hành động. Phải escape quote cẩn thận.
Mẫu JSON: '[{"device": "den_led_day", "action": "off", "delay_seconds": 0}]'
Action có thể là: 'on', 'off', 'set'

## Tính năng an toàn (Anti-Risk)
- Tool này KHÔNG ghi trực tiếp vào Database.
- Tool sẽ sinh ra một "Bản Nháp" (Proposal) và xuất ra hội thoại để Bot xin phép Quản trị viên trước khi thao tác.
