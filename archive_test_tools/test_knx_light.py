import asyncio
import socket
from xknx import XKNX
from xknx.io import ConnectionConfig, ConnectionType
from xknx.tools import group_value_write

KNX_GATEWAY_IP = "10.1.10.137"
KNX_GATEWAY_PORT = 3671

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((KNX_GATEWAY_IP, KNX_GATEWAY_PORT))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

KNX_LOCAL_IP = get_local_ip()

async def main():
    connection_config = ConnectionConfig(
        connection_type=ConnectionType.TUNNELING,
        gateway_ip=KNX_GATEWAY_IP,
        gateway_port=KNX_GATEWAY_PORT,
        local_ip=KNX_LOCAL_IP,
    )

    async with XKNX(connection_config=connection_config) as xknx:
        print("Bật Đèn Led Dây - GA 0/0/1")
        group_value_write(xknx, "0/0/1", True)

        await asyncio.sleep(3)

        print("Tắt Đèn Led Dây - GA 0/0/1")
        group_value_write(xknx, "0/0/1", False)

        await asyncio.sleep(1)

        print("Hoàn tất test.")

asyncio.run(main())

