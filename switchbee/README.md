# pySwitchbee

Library to control SwitchBee IoT devices


Usage:

from switchbee import *


async def main():
    session = aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(ssl=False),
        timeout=aiohttp.ClientTimeout(total=3),
    )

    api = SwitchBeeAPI("192.168.50.10", "name@domain.com", "PASSWORD", session)
    try:
        await api.login()
    except SwitchBeeError as e:
        print(f"Failed to login: {e}")
        return
    
    try:
        result = await api.get_configuration()
    except SwitchBeeError as e:
        print(f"Failed to fetch configuration: {e}")

    my_lights = {}
    for zone in result[ATTR_DATA][ATTR_ZONES]:
        for item in zone[ATTR_ITEMS]:
            if item[ATTR_TYPE] in [TYPE_SWITCH, TYPE_DIMMER]:
                my_lights[item[ATTR_ID]] = item
    
    try:
        resp = api.get_multiple_states(my_lights.items())
    except SwitchBeeError as e:
        print(f"Failed to get multiple states: {resp}")
        return
    
    # update the states of the lights in my data structure
    for state in resp:
        my_lights[state[ATTR_ID]]["state"] = state[ATTR_STATE]

    # turn off all the lights
    for light in my_lights:
        try:
            api.set_state(light, STATE_OFF)
        except SwitchBeeError as e:
            print(f"Failed to set {my_lights[light][ATTR_NAME]} state to OFF")
        

    await session.close()


loop = asyncio.get_event_loop()
loop.run_until_complete(main())


