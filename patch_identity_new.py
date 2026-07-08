import re

with open("/home/an/.openclaw/workspace/IDENTITY.md", "r") as f:
    code = f.read()

old_rule_pattern = r"- MỆNH LỆNH BẮT BUỘC \(NGỮ CẢNH NGÔI NHÀ\): Để biết trạng thái hiện tại của toàn bộ thiết bị \(đèn nào đang bật, cửa nào đang mở\) và lịch sử 5 sự kiện gần nhất \(ai vừa bật đèn\), bạn BẮT BUỘC phải dùng TERMINAL chạy lệnh: `curl -s http://127.0.0.1:5055/api/ai/context` trước khi phân tích và trả lời người dùng\."

new_rule = """- MỆNH LỆNH BẮT BUỘC (NGỮ CẢNH NGÔI NHÀ): Trước khi trả lời bất kỳ câu hỏi nào về Smart Home, bạn BẮT BUỘC phải lấy trạng thái thời gian thực bằng cách gọi API tới `http://127.0.0.1:5055/api/ai/context`.
  Preferred order để gọi API:
  1. HTTP Tool (nếu có)
  2. Python requests (qua bash)
  3. curl (chỉ dùng như fallback cuối cùng)"""

code = re.sub(old_rule_pattern, new_rule, code)

with open("/home/an/.openclaw/workspace/IDENTITY.md", "w") as f:
    f.write(code)
