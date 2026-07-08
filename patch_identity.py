with open("/home/an/.openclaw/workspace/IDENTITY.md", "r") as f:
    code = f.read()

new_rule = """
- MỆNH LỆNH BẮT BUỘC (NGỮ CẢNH NGÔI NHÀ): Để biết trạng thái hiện tại của toàn bộ thiết bị (đèn nào đang bật, cửa nào đang mở) và lịch sử 5 sự kiện gần nhất (ai vừa bật đèn), bạn BẮT BUỘC phải dùng TERMINAL chạy lệnh: `curl -s http://127.0.0.1:5055/api/ai/context` trước khi phân tích và trả lời người dùng.
"""

if "MỆNH LỆNH BẮT BUỘC (NGỮ CẢNH NGÔI NHÀ)" not in code:
    code = code.replace(
        "- Để xem trạng thái thiết bị hoặc điều khiển thiết bị, hãy dùng TERMINAL (bash) để gọi lệnh `curl` vào KNX Bridge.",
        "- Để điều khiển thiết bị, hãy dùng TERMINAL (bash) để gọi lệnh `curl` vào KNX Bridge.\n" + new_rule
    )

with open("/home/an/.openclaw/workspace/IDENTITY.md", "w") as f:
    f.write(code)
