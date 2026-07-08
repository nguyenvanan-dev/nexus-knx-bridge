import asyncio
from xknx import XKNX
from xknx.io import ConnectionConfig, ConnectionType
async def main():
    connection_config = ConnectionConfig(
        connection_type=ConnectionType.TUNNELING,
        gateway_ip="10.1.10.137",
        gateway_port=3671,
    )
    xknx = XKNX(connection_config=connection_config)
    try:
        await xknx.start()
        print("Connected successfully via TUNNELING!")
        await xknx.stop()
    except Exception as e:
        print(f"Failed via TUNNELING: {e}")

    connection_config_routing = ConnectionConfig(
        connection_type=ConnectionType.ROUTING,
    )
    xknx_routing = XKNX(connection_config=connection_config_routing)
    try:
        await xknx_routing.start()
        print("Connected successfully via ROUTING!")
        await xknx_routing.stop()
    except Exception as e:
        print(f"Failed via ROUTING: {e}")

asyncio.run(main())
