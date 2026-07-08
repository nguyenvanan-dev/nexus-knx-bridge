import asyncio
from xknx import XKNX
from xknx.io.gateway_scanner import GatewayScanner

async def main():
    print("Bắt đầu dò tìm KNX Gateway trên mạng LAN...")
    xknx = XKNX()
    scanner = GatewayScanner(xknx)
    gateways = await scanner.scan()
    if not gateways:
        print("Không tìm thấy KNX Gateway nào.")
    else:
        for gw in gateways:
            print(f"Tìm thấy KNX Gateway:")
            print(f"  - IP: {gw.ip_addr}")
            print(f"  - Port: {gw.port}")
            print(f"  - Supports Routing: {gw.supports_routing}")
            print(f"  - Supports Tunneling: {gw.supports_tunnelling}")

if __name__ == "__main__":
    asyncio.run(main())
