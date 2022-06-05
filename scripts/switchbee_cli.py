import asyncio
from argparse import ArgumentParser
from dataclasses import asdict
from pprint import PrettyPrinter

from aiohttp import ClientSession, ClientTimeout, TCPConnector
from switchbee.api import CentralUnitAPI, DeviceType, ApiStateCommand

import time
printer = PrettyPrinter(indent=4)


import logging
import sys

root = logging.getLogger()
root.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
root.addHandler(handler)


def initialize_parser() -> ArgumentParser:

    parser = ArgumentParser(description="Discover and print info of SwitchBee devices")
    parser.add_argument(
        "-i",
        "--central-unit-ip",
        help="SwitchBee Central Unit IP address",
        type=str,
        required=True,
    )

    parser.add_argument(
        "-u",
        "--username",
        help="SwitchBee Central Unit IP username",
        type=str,
        required=True,
    )

    parser.add_argument(
        "-p",
        "--password",
        help="SwitchBee Central Unit password",
        type=str,
        required=True,
    )

    subparsers = parser.add_subparsers(dest="action", description="supported actions")
    subparsers.add_parser("get_devices", help="print devices")

    get_states_sp = subparsers.add_parser("get_states", help="get SwitchBee devices states")

    get_states_sp.add_argument(
        "--only-on",
        dest="only_on",
        help="show devices with state ON only",
        required=False,
        action="store_true",
    )

    get_states_sp.add_argument(
        "--delay",
        help="Delay in seconds",
        type=int,
        default=1,
    )

    set_state_sp = subparsers.add_parser("set_state", help="set state")

    set_state_sp.add_argument(
        "-i",
        "--device-id",
        help="device id",
        required=True,
        type=int,
    )

    set_state_sp.add_argument(
        "-s",
        "--state",
        help="new state of the device",
        required=True,
        type=str,
    )

    return parser


async def main(args):

    session = ClientSession(
        connector=TCPConnector(ssl=False),
        timeout=ClientTimeout(total=3),
    )

    cu = CentralUnitAPI(args.central_unit_ip, args.username, args.password, session)

    await cu.connect()

    print(f"Central Unit: {cu.name}")
    print(f"Central MAC: {cu.mac}")
    print(f"Central Version: {cu.version}")


    if args.action == "get_devices":
        for device in cu.devices:
            printer.pprint(asdict(device))

    if args.action == "get_states":
        sec_delay = args.delay
        while sec_delay:
            cu.fetch_states()
            for device in cu.devices.values():
                if args.only_on:
                    if (
                        device.type == DeviceType.Shutter
                        and device.position > 0
                        or device.type == DeviceType.Dimmer
                        and device.brightness > 0
                        or device.type in [DeviceType.Switch, DeviceType.TimedPowerSwitch]
                        and device.state == ApiStateCommand.ON
                    ):
                        printer.pprint(asdict(device))
                        print()

                else:
                    printer.pprint(asdict(device))
                    print()

            time.sleep(1)
            sec_delay -= 1

    if args.action == "set_state":

        if args.state.isdigit():
            printer.pprint(await cu.set_state(args.device_id, int(args.state)))
        elif args.state in [ApiStateCommand.ON, ApiStateCommand.OFF]:
            printer.pprint(await cu.set_state(args.device_id, args.state))
        else:
            print(f"Invalid state {args.state}, only ON|OFF|Number are allowed")



    await session.close()


if __name__ == "__main__":
    parser = initialize_parser()
    args = parser.parse_args()

    asyncio.get_event_loop().run_until_complete(main(args))
    exit()
