---
name: scene-manager
description: Quản lý kịch bản (Scene) của nhà thông minh. Dùng skill này để lưu kịch bản mới, xem thông tin một kịch bản, xem danh sách tất cả kịch bản, hoặc xóa kịch bản. Skill này KHÔNG kích hoạt kịch bản, nó chỉ thao tác với dữ liệu. Để kích hoạt, bạn hãy dùng skill này để đọc nội dung kịch bản, sau đó dùng skill knx-bridge để ra lệnh cho các thiết bị.
---
# Scene Manager Skill

## Mô tả
Skill này cho phép bạn quản lý các kịch bản (scenes) của hệ thống nhà thông minh. Các kịch bản được lưu trữ trong file `/home/an/knx-bridge/scenes.json`.

## Cách sử dụng

### 1. Xem danh sách kịch bản
```json
{
  "action": "list"
}
```

### 2. Xem chi tiết một kịch bản
```json
{
  "action": "get",
  "scene_name": "Scene Chill"
}
```

### 3. Lưu/Cập nhật một kịch bản
`scene_data` phải là một chuỗi JSON hợp lệ chứa các thuộc tính của kịch bản, ví dụ:
```json
{
  "action": "save",
  "scene_name": "Scene Chill",
  "scene_data": "{\"description\": \"Kịch bản thư giãn\", \"actions\": [{\"device\": \"den_tron\", \"action\": \"off\"}]}"
}
```

### 4. Xóa kịch bản
```json
{
  "action": "delete",
  "scene_name": "Scene Chill"
}
```

## Lưu ý quan trọng
Skill này **chỉ quản lý dữ liệu**, không trực tiếp giao tiếp với KNX Bridge để thay đổi trạng thái thiết bị.
Để **Kích hoạt** một kịch bản:
1. Dùng lệnh `get` để đọc nội dung kịch bản.
2. Dịch các `actions` trong kịch bản thành câu lệnh tiếng Việt (ví dụ: "Tắt đèn tròn, bật đèn led dây...").
3. Dùng skill `knx-bridge` để gửi câu lệnh tiếng Việt đó đến hệ thống điều khiển.
