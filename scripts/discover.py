#! python3

"""Python script for discovering SwitchBee Central Units."""

from argparse import ArgumentParser, RawDescriptionHelpFormatter
from asyncio import get_event_loop, sleep
from dataclasses import asdict
from pprint import PrettyPrinter

from switchbee.central_unit import CentralUnitFinder, CentralUnit


printer = PrettyPrinter(indent=4)

parser = ArgumentParser(
    description="Discover and print info of SwitchBee Central Unit devices",
    formatter_class=RawDescriptionHelpFormatter,
)
parser.add_argument(
    "delay",
    help="number of seconds to run, defaults to 3",
    type=int,
    nargs="?",
    default=3,
)


async def print_devices(
    delay: int,
) -> None:
    """Run the SwitchBee finder and register callback for discovered devices."""

    def on_device_found_callback(device: CentralUnit) -> None:
        """Use as a callback printing found devices."""
        printer.pprint(asdict(device))
        print()

    async with CentralUnitFinder(on_device_found_callback):
        await sleep(delay)


if __name__ == "__main__":
    args = parser.parse_args()

    try:
        get_event_loop().run_until_complete(print_devices(args.delay))
    except KeyboardInterrupt:
        exit()
