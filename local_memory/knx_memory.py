from local_memory.db import MemoryStore

store = MemoryStore()

def remember_knx_device(name: str, room: str, device_type: str, group_address: str, dpt: str, direction: str, note: str = ""):
    raw_text = f"{name} ở {room} dùng GA {group_address} DPT {dpt} ({direction}). {note}".strip()
    
    return store.add_memory(
        wing="KNX",
        hall="devices",
        room=room,
        device_name=name,
        group_address=group_address,
        dpt=dpt,
        raw_text=raw_text,
        project="KNX",
        topic=device_type,
        importance=4,
        tags=f"knx, device, {device_type}, {room}"
    )

def find_knx_device(query: str):
    return store.search_memory(query)
