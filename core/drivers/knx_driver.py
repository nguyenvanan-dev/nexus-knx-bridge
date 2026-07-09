import asyncio
import logging
import socket
import time
from typing import Any, Callable, Optional

from xknx import XKNX
from xknx.io import ConnectionConfig, ConnectionType
from xknx.tools import group_value_write, read_group_value
from xknx.telegram import Telegram

from core.drivers.base_driver import BaseDriver

logger = logging.getLogger(__name__)

def get_local_ip():
    """Utility to get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class KNXDriver(BaseDriver):
    """
    Trình điều khiển cho giao thức KNX, đóng gói thư viện xknx.
    """

    def __init__(self, gateway_ip: str, gateway_port: int = 3671, local_ip: str = "auto"):
        super().__init__()
        self.gateway_ip = gateway_ip
        self.gateway_port = gateway_port
        
        if local_ip == "auto" or not local_ip:
            self.local_ip = get_local_ip()
        elif local_ip == "127.0.0.1":
            self.local_ip = None
        else:
            self.local_ip = local_ip
            
        self._xknx: Optional[XKNX] = None
        self._lock = asyncio.Lock()
        
        self.connection_time: Optional[float] = None
        self.reconnect_count: int = 0
        self.tunnel_state: str = "DISCONNECTED"

    async def start(self) -> None:
        """Bắt đầu kết nối KNX."""
        async with self._lock:
            if self._xknx is not None:
                return

            connection_config = ConnectionConfig(
                connection_type=ConnectionType.TUNNELING,
                gateway_ip=self.gateway_ip,
                gateway_port=self.gateway_port,
                local_ip=self.local_ip,
            )

            inst = XKNX(connection_config=connection_config)
            
            # Đăng ký callback nội bộ của driver
            inst.telegram_queue.register_telegram_received_cb(self._internal_telegram_cb)

            try:
                await inst.start()
                self._xknx = inst
                self.connection_time = time.time()
                self.reconnect_count += 1
                self.tunnel_state = "CONNECTED"
                logger.info(f"KNX tunnel started to {self.gateway_ip}:{self.gateway_port}")
            except Exception as exc:
                self._xknx = None
                self.tunnel_state = "ERROR"
                logger.error(f"KNX tunnel start failed: {type(exc).__name__}: {exc}")

    async def stop(self) -> None:
        """Ngắt kết nối KNX."""
        async with self._lock:
            if self._xknx is not None:
                try:
                    await self._xknx.stop()
                    logger.info("KNX tunnel stopped")
                except Exception as e:
                    logger.error(f"Error stopping KNX tunnel: {e}")
                finally:
                    self._xknx = None
                    self.tunnel_state = "DISCONNECTED"

    async def _internal_telegram_cb(self, telegram: Telegram):
        """Nhận telegram từ xknx và đẩy lên qua callback đã đăng ký."""
        if self._on_message_callback:
            # Wrap the task to not block xknx internal loops
            asyncio.create_task(self._safe_invoke_callback(telegram))
            
    async def _safe_invoke_callback(self, telegram: Telegram):
        try:
            if asyncio.iscoroutinefunction(self._on_message_callback):
                await self._on_message_callback(telegram)
            else:
                self._on_message_callback(telegram)
        except Exception as e:
            logger.error(f"Error in driver message callback: {e}")

    async def write(self, address: str, value: Any, value_type: Optional[str] = None) -> None:
        """Ghi giá trị xuống KNX bus."""
        async with self._lock:
            if self._xknx is None:
                logger.warning(f"Cannot write to {address}, KNX not connected")
                return

            if value_type:
                group_value_write(self._xknx, address, value, value_type=value_type)
            else:
                group_value_write(self._xknx, address, value)
            
            # Allow yielding to event loop for the write task to be scheduled by xknx
            await asyncio.sleep(0.01)

    async def read(self, address: str, value_type: Optional[str] = None) -> Any:
        """Đọc giá trị từ KNX bus (Read Request)."""
        if self._xknx is None:
            logger.warning(f"Cannot read from {address}, KNX not connected")
            return None
        
        # read_group_value is an async function in xknx
        return await read_group_value(self._xknx, address, value_type=value_type)

    @property
    def is_connected(self) -> bool:
        """Trả về True nếu đang kết nối KNX."""
        return self._xknx is not None

    @property
    def current_address(self) -> Optional[str]:
        """Trả về địa chỉ vật lý hiện tại của bridge (nếu có)."""
        if self._xknx and hasattr(self._xknx, 'current_address'):
            return str(self._xknx.current_address)
        return None
