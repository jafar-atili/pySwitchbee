# pySwitchbee

Library to control SwitchBee IoT devices


Usage:

import switchbee

async def main():
    session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False), 
                    timeout=aiohttp.ClientTimeout(total=3)
    
    api = SwitchBee('192.168.50.10', 'name@domain.com', 'P4$$w0rd', session)
    await api.login()
    json_resp = await api.get_configuration()
    if json_resp[switchbee.ATTR_STATUS] == switchbee.STATUS_OK:
        print(json_resp)
    else:
        print('Failed')
    await session.close()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())

