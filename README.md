# pySwitchbee

Library to control SwitchBee IoT devices


Usage:

import switchbee

async def main():
    api = SwitchBee('192.168.50.10', 'name@domain.com', 'P4$$w0rd')
    await api.login()
    json_resp = await api.get_configuration()
    if json_resp[switchbee.ATTR_STATUS] == switchbee.STATUS_OK:
        print(json_resp)
    await api.close()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())

