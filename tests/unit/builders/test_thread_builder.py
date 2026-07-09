from core.builders.thread_builder import SimpleThreadBuilder

def test_thread_builder_active_topic():
    builder = SimpleThreadBuilder()
    messages = [
        {"role": "user", "content": "Bật đèn phòng khách"},
        {"role": "assistant", "content": "Đã bật đèn."}
    ]
    working_memory = builder.build(messages)
    
    assert working_memory["active_topic"]["last_room"] == "phòng khách"
    assert working_memory["active_topic"]["last_device"] == "light"

def test_thread_builder_follow_up():
    builder = SimpleThreadBuilder()
    messages = [
        {"role": "user", "content": "Bật điều hòa phòng ngủ"},
        {"role": "assistant", "content": "Đã bật."},
        {"role": "user", "content": "Tắt nó đi"}
    ]
    working_memory = builder.build(messages)
    
    assert working_memory["active_topic"]["last_room"] == "phòng ngủ"
    assert working_memory["active_topic"]["last_device"] == "ac"
