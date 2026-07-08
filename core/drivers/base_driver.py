"""
BaseDriver — Interface chuẩn cho mọi giao thức điều khiển (KNX, MQTT, Zigbee...).
"""
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional


class BaseDriver(ABC):
    """
    Interface chung để kết nối và điều khiển thiết bị qua một giao thức cụ thể.
    """

    def __init__(self):
        # Callback được gọi khi có sự kiện từ bus (ví dụ: KNX Telegram)
        self._on_message_callback: Optional[Callable[[Any], None]] = None

    def register_callback(self, callback: Callable[[Any], None]):
        """Đăng ký callback nhận dữ liệu từ bus."""
        self._on_message_callback = callback

    @abstractmethod
    async def start(self) -> None:
        """Bắt đầu kết nối (connect) tới gateway/broker."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Ngắt kết nối."""
        pass

    @abstractmethod
    async def write(self, address: str, value: Any, value_type: Optional[str] = None) -> None:
        """
        Gửi lệnh ghi giá trị xuống thiết bị.
        - address: Group address (KNX) hoặc Topic (MQTT).
        - value: Giá trị cần ghi (True/False, số, chuỗi...).
        - value_type: Gợi ý kiểu dữ liệu (tùy chọn).
        """
        pass

    @abstractmethod
    async def read(self, address: str, value_type: Optional[str] = None) -> Any:
        """
        Gửi lệnh đọc trạng thái từ thiết bị.
        """
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Trạng thái kết nối hiện tại."""
        pass
