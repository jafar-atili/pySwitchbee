# pySwitchbee

Library to control SwitchBee IoT devices


Usage:

import switchbee

async def main():
    api = SwitchBee('192.168.50.10', 'name@domain.com', 'P4$$w0rd')
    await api.login()
    print(await api.get_devices_list_by_filter(type_filter=[TYPE_DIMMER, TYPE_SWITCH]))
    await api.close()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())

