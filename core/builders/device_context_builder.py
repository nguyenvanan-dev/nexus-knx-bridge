from typing import Dict, List, TYPE_CHECKING
from core.builders.intent_extractor import Intent

if TYPE_CHECKING:
    from core.device_service import DeviceService
    from core.state_manager import StateManager

class DeviceContextBuilder:
    def __init__(self, device_service: 'DeviceService', state_manager: 'StateManager'):
        self._device_service = device_service
        self._state_manager = state_manager

    def build(self, intent: Intent) -> Dict:
        """Filters device context based on the extracted Intent."""
        all_devices = self._device_service.get_all_devices_with_state()
        filtered_devices = {}

        for dev_id, dev_info in all_devices.items():
            # If intent specified a room, filter by it
            if intent.room and dev_info.get("room", "").lower() != intent.room:
                continue
            
            # If intent specified a device type, filter by it
            # Assuming device_info has type, or we match keyword in name
            name_lower = dev_info.get("name", "").lower()
            if intent.device_type and intent.device_type not in name_lower: # simplistic fallback
                if dev_info.get("type", "") != intent.device_type:
                    continue
                    
            filtered_devices[dev_id] = dev_info

        if not filtered_devices:
            # Fallback to a limited set to prevent token explosion
            return dict(list(all_devices.items())[:10])
            
        return filtered_devices
