from typing import Dict, List, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from core.device_service import DeviceService
    from core.state_manager import StateManager

logger = logging.getLogger(__name__)

class HouseRepository:
    """Repository for House Long-term Knowledge and State."""
    def __init__(self, device_service: 'DeviceService', state_manager: 'StateManager'):
        self._device_service = device_service
        self._state_manager = state_manager

    def get_house_context(self) -> Dict:
        """Retrieves long-term house knowledge (e.g. modes, defaults)."""
        try:
            # We fetch long term mode from device_service
            # This ensures we don't duplicate Realtime state.
            return {
                "house_mode": self._device_service.get_house_mode() if hasattr(self._device_service, 'get_house_mode') else "Normal",
                "active_scenes": [] # Placeholder for active long-term scenes
            }
        except Exception as e:
            logger.error(f"Error fetching house context: {e}")
            return {}

    def get_active_automations(self) -> List[Dict]:
        """Retrieves currently active automations affecting the house."""
        return []
