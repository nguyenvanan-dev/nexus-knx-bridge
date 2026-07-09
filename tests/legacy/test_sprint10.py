import sqlite3
import json
import asyncio
from core.ai_context import ContextBuilder
from pathlib import Path

# Mock DeviceService and EventBus
class MockDeviceService:
    def get_house_mode(self): return "Normal"
    def get_all_devices_with_state(self):
        return {
            "light_living_1": {"name": "Đèn phòng khách", "room": "Living Room", "state": "off"},
            "light_bed_1": {"name": "Đèn phòng ngủ", "room": "Bedroom", "state": "on"}
        }

class MockEventBus: pass

async def main():
    db_path = Path("smarthome.db")
    cb = ContextBuilder(MockDeviceService(), MockEventBus(), db_path)
    
    # Simulate saving messages
    print("Testing saving messages...")
    cb.save_message("test_session_123", "user", "Bật đèn phòng khách")
    cb.save_message("test_session_123", "assistant", "Đã bật")
    cb.save_message("test_session_123", "user", "Giảm 30%")
    
    await asyncio.sleep(1) # wait for background tasks
    
    # Test build context
    print("Testing context build...")
    context_str = cb.build_context(session_id="test_session_123", query="Giảm 30%")
    context_json = json.loads(context_str)
    
    # Validate Working Memory
    print(f"Working Memory: {context_json['working_memory']}")
    assert len(context_json['working_memory']) >= 3, "Working memory incomplete"
    
    # Validate Device Filter
    print(f"Filtered Devices: {context_json['devices']}")
    assert "light_living_1" in context_json['devices'], "Missing living room light"
    # Note: bedroom light might also be there depending on fallback logic, but living room must be.
    
    print("Test passed!")

if __name__ == "__main__":
    asyncio.run(main())
