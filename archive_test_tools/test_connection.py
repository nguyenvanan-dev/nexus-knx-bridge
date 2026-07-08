import asyncio
from xknx import XKNX
from xknx.io import ConnectionConfig, ConnectionType

async def main():
    print("Testing connection to 10.1.10.232...")
    connection_config = ConnectionConfig(
        connection_type=ConnectionType.TUNNELING,
        gateway_ip="10.1.10.137",
        gateway_port=3671,
        local_ip="10.1.10.110"
    )
    xknx = XKNX(connection_config=connection_config)
    
    try:
        await xknx.start()
        print("Connected successfully!")
        await xknx.stop()
        print("Disconnected.")
    except Exception as e:
        print(f"Connection failed: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
