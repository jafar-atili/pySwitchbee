# pySwitchbee

Library to control SwitchBee IoT devices


Usage:

```python

from asyncio import get_event_loop

from aiohttp import ClientSession, ClientTimeout, TCPConnector
from switchbee.api import CentralUnitAPI
from switchbee.devices import DeviceType, SwitchState


async def main():
    session = ClientSession(
        connector=TCPConnector(ssl=False),
        timeout=ClientTimeout(total=3),
    )

    cu = CentralUnitAPI("192.168.50.3", "user", "pass", session)
    await cu.connect()

    print(f"Central Unit: {cu.name}")
    print(f"Central MAC: {cu.mac}")
    print(f"Central Version: {cu.version}")

    devices = await cu.devices

    for device in devices:
        # set the dimmer lights to 50% brightness
        if device.type == DeviceType.Dimmer:
            print(
                "Discovered Dimmer device called {device.name} current brightness is {device.brigt}"
            )
            await cu.set_state(device.id, 50)

        # set the shutters position to 30% opened
        if device.type == DeviceType.Shutter:
            print(
                "Discovered Shutter device called {device.name} current position is {device.position}"
            )
            await cu.set_state(device.id, 30)

        # turn off switches
        if device.type == DeviceType.Switch:
            print(
                "Discovered Switch device called {device.name} current state is {device.state}"
            )
            await cu.set_state(device.id, SwitchState.OFF)

        # set timer switch on for 10 minutes
        if device.type == DeviceType.TimePower:
            print(
                "Discovered Timed Power device called {device.name} current state is {device.state} with {device.minutes_left} minutes left until shutdown"
            )
            await cu.set_state(device.id, 10)

    session.close()


if __name__ == "__main__":

    get_event_loop().run_until_complete(main())
    exit()
```

Alternatively, it is possible to control SwitchBee using the cli tool `switchbee_cli.py` as following:

To list devices that currently on:

`python switchbee_cli.py -i 192.168.50.2 -u USERNAME -p PASSWORD get_states --only-on`

```
   '_state': 'ON',
    'hardware': <HardwareType.Switch: 'DIMMABLE_SWITCH'>,
    'id': 311,
    'name': 'Ceiling',
    'type': <DeviceType.Switch: 'SWITCH'>,
    'zone': 'Outdoo Storage'}

{   '_state': 'ON',
    'hardware': <HardwareType.Switch: 'DIMMABLE_SWITCH'>,
    'id': 142,
    'name': 'Spotlights',
    'type': <DeviceType.Switch: 'SWITCH'>,
    'zone': 'Porch'}
```

To set shutter with device id 392 position 50%:

`python switchbee_cli.py -i 192.168.50.2 -u USERNAME -p PASSWORD set_state --device-id 392 --state 50`


To turn on Power Timed Switch with device id 450 for 30 minutes:

`python switchbee_cli.py -i 192.168.50.2 -u USERNAME -p PASSWORD set_state --device-id 450 --state 30`


To turn off light with device id 122:

`python switchbee_cli.py -i 192.168.50.2 -u USERNAME -p PASSWORD set_state --device-id 122 --state OFF`