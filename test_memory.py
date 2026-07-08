import os
from local_memory import (
    MemoryStore,
    remember_knx_device,
    find_knx_device,
    remember_error,
    search_errors,
    build_wakeup_context
)

def run_tests():
    print("--- Khởi tạo Local Memory ---")
    
    # 1. Thêm memory KNX device
    print("\n[1] Thêm thiết bị KNX...")
    remember_knx_device(
        name="Đèn phòng khách ON/OFF",
        room="Phòng khách",
        device_type="light",
        group_address="1/1/1",
        dpt="1.001",
        direction="write"
    )
    print("✅ Đã lưu thiết bị Đèn phòng khách.")

    # 2. Lưu lỗi Gemini quota 429
    print("\n[2] Lưu lỗi hệ thống...")
    remember_error(
        service="OpenClaw Gateway",
        error_text="Google API 429 quota exceeded.",
        cause="Gemini API hết quota/rate limit.",
        solution="Đợi reset quota, hoặc chuyển sang dùng Groq Llama 3.",
        severity=5
    )
    print("✅ Đã lưu lỗi 429 Quota.")

    # 3. Search theo "đèn phòng khách"
    print("\n[3] Tìm kiếm 'đèn phòng khách':")
    results = find_knx_device("đèn phòng khách")
    for r in results:
        print(f"  -> Tìm thấy: {r['raw_text']}")

    # 4. Search theo group address "1/1/1"
    print("\n[4] Tìm kiếm GA '1/1/1':")
    results = find_knx_device("1/1/1")
    for r in results:
        print(f"  -> Tìm thấy: {r['raw_text']}")

    # 5. Search lỗi "quota"
    print("\n[5] Tìm kiếm lỗi 'quota':")
    results = search_errors("quota")
    for r in results:
        print(f"  -> Tìm thấy: {r['raw_text']}")

    # 6. Build wakeup context
    print("\n[6] Wake-up Context (KNX):")
    context = build_wakeup_context(project="KNX", max_tokens=800)
    print(context)
    
    print("\n[6] Wake-up Context (OpenClaw Gateway):")
    context = build_wakeup_context(project="OpenClaw Gateway", max_tokens=800)
    print(context)

if __name__ == "__main__":
    # Đảm bảo chạy trong thư mục knx-bridge
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    run_tests()
