import sqlite3
import json
import sys
import os
from datetime import datetime, timedelta

def main():
    args = {}
    input_data = ""
    if not sys.stdin.isatty():
        input_data = sys.stdin.read().strip()
    
    if not input_data and len(sys.argv) > 1:
        input_data = sys.argv[1]
    
    if not input_data and "OPENCLAW_SKILL_ARGS" in os.environ:
        input_data = os.environ["OPENCLAW_SKILL_ARGS"]
        
    if input_data:
        try:
            args = json.loads(input_data)
        except json.JSONDecodeError:
            pass

    limit = args.get("limit", 50)
    target_date_str = args.get("target_date", "")
    time_period = args.get("time_period", "all")
    search_query = args.get("search_query", "")
    
    # Xử lý ngày tháng
    now = datetime.now()
    if not target_date_str:
        target_date = now.date()
    else:
        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
            # Kiểm tra xem có quá 7 ngày không
            if (now.date() - target_date).days > 7:
                print(f"Lỗi: Chỉ hỗ trợ lấy lịch sử trong vòng 7 ngày gần nhất. Ngày yêu cầu: {target_date_str} đã quá hạn.")
                return
        except ValueError:
            print("Lỗi: Định dạng ngày không hợp lệ. Vui lòng dùng định dạng YYYY-MM-DD.")
            return

    # Tính toán khoảng timestamp (microsecond) dựa theo time_period
    start_dt = datetime.combine(target_date, datetime.min.time())
    
    if time_period == "morning":
        end_dt = start_dt + timedelta(hours=12)
    elif time_period == "afternoon":
        start_dt = start_dt + timedelta(hours=12)
        end_dt = start_dt + timedelta(hours=6)
    elif time_period == "evening":
        start_dt = start_dt + timedelta(hours=18)
        end_dt = start_dt + timedelta(hours=6)
    else: # all
        end_dt = start_dt + timedelta(days=1)
        
    start_ts = int(start_dt.timestamp() * 1000000)
    end_ts = int(end_dt.timestamp() * 1000000)

    db_path = "/home/an/knx-bridge/data/chat_history.db"
    
    if not os.path.exists(db_path):
        print("Database không tồn tại hoặc chưa có tin nhắn nào được ghi.")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Lấy ngày của tin nhắn gần nhất để làm gợi ý nếu không tìm thấy
        cursor.execute("SELECT timestamp FROM messages ORDER BY timestamp DESC LIMIT 1")
        last_msg = cursor.fetchone()
        last_msg_date_str = ""
        if last_msg:
            last_msg_date_str = datetime.fromtimestamp(last_msg[0] / 1000000).strftime('%Y-%m-%d')
            
        sql = 'SELECT sender_name, text, timestamp FROM messages WHERE 1=1'
        params = []
        
        if target_date_str:
            sql += ' AND timestamp >= ? AND timestamp < ?'
            params.extend([start_ts, end_ts])
        
        if search_query:
            sql += ' AND text LIKE ?'
            params.append(f'%{search_query}%')
            
        sql += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            if target_date_str:
                msg = f"Không có tin nhắn nào trong lịch sử ngày {target_date}."
                if last_msg_date_str:
                    msg += f" (Gợi ý: Tin nhắn gần nhất trong hệ thống là vào ngày {last_msg_date_str})"
                print(msg)
            else:
                print("Không có tin nhắn nào trong lịch sử.")
            return
            
        lines = []
        # Lật ngược danh sách để in theo thứ tự thời gian tăng dần
        for row in reversed(rows):
            name = row[0] or "Unknown"
            text = row[1] or ""
            # Format time
            msg_dt = datetime.fromtimestamp(row[2] / 1000000)
            msg_time = msg_dt.strftime('%Y-%m-%d %H:%M:%S')
            lines.append(f"[{msg_time}] [{name}]: {text}")
        
        summary_title = f"lịch sử chat của ngày {target_date}" if target_date_str else f"{len(lines)} tin nhắn gần nhất"
        if target_date_str and time_period != "all":
            summary_title += f" (Khung giờ: {time_period})"
        if search_query:
            summary_title += f" [Từ khóa: '{search_query}']"
            
        print(f"Dưới đây là {summary_title}:\n\n" + "\n".join(lines))
    except Exception as e:
        print(f"Lỗi khi đọc Database: {e}")

if __name__ == "__main__":
    main()
