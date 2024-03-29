import asyncio
import time
from argparse import ArgumentParser
from dataclasses import asdict
from pprint import PrettyPrinter
import logging
import sys
from typing import Any

from aiohttp import ClientSession, ClientTimeout, TCPConnector

from switchbee.api.wsrpc import CentralUnitWsRPC
from switchbee.device import ApiStateCommand

printer = PrettyPrinter(indent=4)


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

    get_states_sp = subparsers.add_parser(
        "get_states", help="get SwitchBee devices states"
    )

    subparsers.add_parser("get_stats", help="get SwitchBee devices stats")
    subparsers.add_parser("get_configuration", help="get SwitchBee configuration")

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

def on_notification(data: dict[str, Any]):
    print(f'Device {data["name"]} ({data["id"]}) state changed to {data["newValue"]}')


async def main(args):

    async with ClientSession(
        connector=TCPConnector(ssl=False),
        timeout=ClientTimeout(total=10),
    ) as session:

        cu = CentralUnitWsRPC(args.central_unit_ip, args.username, args.password, session, on_notification)

        await cu.connect()
        await cu.fetch_configuration()
        await cu.fetch_states()


        print(f"Central Unit: {cu.name}")
        print(f"Central MAC: {cu.mac}")
        print(f"Central Version: {cu.version}")
        await asyncio.sleep(10000)

        if args.action == "get_devices":
            for device in cu.devices.values():
                printer.pprint(asdict(device))

        if args.action == "get_states":
            sec_delay = args.delay
            while sec_delay:
                await cu.fetch_configuration()
                await cu.fetch_states()
                for device in cu.devices.values():
                    if args.only_on:
                        if (
                            device.type == DeviceType.Shutter
                            and device.position > 0
                            or device.type == DeviceType.Dimmer
                            and device.brightness > 0
                            or device.type
                            in [DeviceType.Switch, DeviceType.TimedPowerSwitch]
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

        if args.action == "get_stats":
            printer.pprint(await cu.get_stats())

        if args.action == "get_configuration":
            printer.pprint(await cu.get_configuration())



if __name__ == "__main__":
    parser = initialize_parser()
    args = parser.parse_args()
    asyncio.run(main(args))
    exit()
