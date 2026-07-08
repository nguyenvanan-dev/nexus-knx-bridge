import logging
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from core.device_registry import DeviceRegistry
    from core.state_manager import StateManager

logger = logging.getLogger(__name__)

class DeviceService:
    """
    Facade/Service kết hợp DeviceRegistry (Metadata) và StateManager (RAM State).
    Tránh để các module khác (như AI Context) gọi trực tiếp StateManager.
    Đảm bảo tính phân tầng (Layering).
    """
    
    def __init__(self, registry: 'DeviceRegistry', state_manager: 'StateManager'):
        self._registry = registry
        self._state_manager = state_manager
        
    def get_all_devices_with_state(self) -> Dict[str, Any]:
        """
        Lấy snapshot của TẤT CẢ thiết bị từ Registry,
        kèm theo state hiện tại từ StateManager.
        Nếu thiết bị chưa có state (chưa từng report), gán 'Unknown'.
        """
        snapshot = {}
        all_metadata = self._registry.all_dict()
        all_states = self._state_manager.get_all()
        
        for dev_id, device in all_metadata.items():
            state_obj = all_states.get(dev_id)
            # The get_all() returns a dict of dicts, where each dict has a "state" key
            current_state = state_obj.get("state") if state_obj else "Unknown"
            snapshot[dev_id] = current_state
            
        return snapshot
        
    def get_device_state(self, device_id: str) -> str:
        # self._state_manager.get_state returns just the string state directly usually?
        # Wait, get_state returns Any.
        state_val = self._state_manager.get_state(device_id)
        return state_val if state_val is not None else "Unknown"

    def get_house_mode(self) -> str:
        state_val = self._state_manager.get_state("sys_house_mode")
        return state_val if state_val is not None else "Home"

