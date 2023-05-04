from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any, List, final

from ..const import ApiDeviceHardware, ApiDeviceType, ApiStateCommand
from ..utils import timestamp_now


@unique
class DeviceType(Enum):
    """Enum class representing the device's type."""

    Dimmer = ApiDeviceType.DIMMER, "Light"
    Switch = ApiDeviceType.SWITCH, "Switch"
    Shutter = ApiDeviceType.SHUTTER, "Shutter"
    Scenario = ApiDeviceType.SCENARIO, "Scenario"
    Repeater = ApiDeviceType.REPEATER, "Repeater"
    GroupSwitch = ApiDeviceType.GROUP_SWITCH, "Group Switch"
    TwoWay = ApiDeviceType.TWO_WAY, "Two Way"
    TimedPowerSwitch = ApiDeviceType.TIMED_POWER, "Timed Power Switch"
    Thermostat = ApiDeviceType.THERMOSTAT, "Thermostat"
    LockGroup = ApiDeviceType.LOCK_GROUP, "Lock Group"
    TimedSwitch = ApiDeviceType.TIMED_SWITCH, "Timed Switch"
    Somfy = ApiDeviceType.SOMFY, "Somfy"
    IrDevice = ApiDeviceType.IR_DEVICE, "Infra Red Device"
    RollingScenario = ApiDeviceType.ROLLING_SCENARIO, "Rolling Scenario"

    def __new__(cls, *args: Any, **kwds: Any):  # type: ignore
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    # ignore the first param since it's already set by __new__
    def __init__(self, _: str, display: str = "") -> None:
        self._display = display

    def __str__(self) -> str:
        return self.display

    # this makes sure that the description is read-only
    @property
    def display(self) -> str:
        return self._display


class HardwareType(Enum):
    Virtual = ApiDeviceHardware.VIRTUAL, "Virtual"
    Dimmable = ApiDeviceHardware.DIMMABLE_SWITCH, "Switch"
    Shutter = ApiDeviceHardware.SHUTTER, "Shutter"
    TimedPowerSwitch = ApiDeviceHardware.TIMED_POWER_SWITCH, "Timed Power Switch"
    Thermostat = ApiDeviceHardware.THERMOSTAT, "CoolSwitch"
    Somfy = ApiDeviceHardware.SOMFY, "Somfy"
    SocketIR = ApiDeviceHardware.SOCKET_IR, "Socket IR"
    StickerSwitch = ApiDeviceHardware.STIKER_SWITCH, "Sticker Switch"
    RegularSwitch = ApiDeviceHardware.REGULAR_SWITCH, "Regular Switch"
    Repeater = ApiDeviceHardware.REPEATER, "Repeater"

    def __new__(cls, *args: Any, **kwds: Any):  # type: ignore
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    # ignore the first param since it's already set by __new__
    def __init__(self, _: str, display: str = "") -> None:
        self._display = display

    def __str__(self) -> str:
        return self.display

    # this makes sure that the description is read-only
    @property
    def display(self) -> str:
        return self._display


@dataclass
class SwitchBeeBaseDevice(ABC):
    id: int
    name: str
    zone: str
    type: DeviceType
    hardware: HardwareType

    def __post_init__(self) -> None:
        """Post initialization, set last_data_update to the instantiation datetime."""
        self.last_data_update = timestamp_now()
        self.unit_id = self.id // 10

    def __hash__(self) -> int:
        return self.id


@dataclass
class SwitchBeeBaseSwitch(ABC):
    _state: str | int | None = field(init=False, default=None)

    @property
    def state(self) -> str | int | None:
        return self._state

    @state.setter
    def state(self, value: str | int) -> None:
        if value == 0:
            self._state = ApiStateCommand.OFF
        elif value == 100:
            self._state = ApiStateCommand.ON
        else:
            self._state = value


@dataclass
class SwitchBeeBaseShutter(ABC):
    _position: int | None = field(init=False, repr=False, default=None)

    @property
    def position(self) -> int | None:
        return self._position

    @position.setter
    def position(self, value: str | int) -> None:
        if isinstance(value, int):
            self._position = int(value)
        else:
            if value == ApiStateCommand.ON:
                self._position = 100
            else:
                self._position = 0


@dataclass
class SwitchBeeBaseDimmer(ABC):
    _brightness: int = field(init=False)

    @property
    def brightness(self) -> int:
        return self._brightness

    @brightness.setter
    def brightness(self, value: str | int) -> None:
        if isinstance(value, int):
            self._brightness = int(value)
        else:
            if value == ApiStateCommand.ON:
                self._brightness = 100
            else:  # OFF/OFFLINE
                self._brightness = 0


@dataclass
class SwitchBeeBaseTimer(ABC):
    _minutes_left: int = field(init=False)
    _state: str | int = field(init=False)

    @property
    def state(self) -> str | int:
        return self._state

    @state.setter
    def state(self, value: str | int) -> None:
        if value:
            if value == ApiStateCommand.OFF:
                self._minutes_left = 0
                self._state = value
            else:
                self._minutes_left = int(value)
                self._state = ApiStateCommand.ON

    @property
    def minutes_left(self) -> int:
        return self._minutes_left


@dataclass
class SwitchBeeBaseThermostat(ABC):
    modes: List[str]
    unit: str
    mode: str = field(init=False)
    fan: str = field(init=False)
    target_temperature: int = field(init=False)
    temperature: int = field(init=False)
    max_temperature: int = 31
    min_temperature: int = 16


@final
@dataclass
class SwitchBeeSwitch(SwitchBeeBaseSwitch, SwitchBeeBaseDevice):
    def __post_init__(self) -> None:
        """Post initialization validate device type category as Switch."""
        if self.type != DeviceType.Switch:
            raise ValueError("only Switch are allowed")
        super().__post_init__()


@final
@dataclass
class SwitchBeeShutter(SwitchBeeBaseShutter, SwitchBeeBaseDevice):
    def __post_init__(self) -> None:
        """Post initialization validate device type category as Shutter."""
        if self.type != DeviceType.Shutter:
            raise ValueError("only Shutter are allowed")
        super().__post_init__()


@final
@dataclass
class SwitchBeeDimmer(SwitchBeeBaseDimmer, SwitchBeeBaseDevice):
    def __post_init__(self) -> None:
        """Post initialization validate device type category as Dimmer."""
        if self.type != DeviceType.Dimmer:
            raise ValueError("only Dimmer are allowed")
        super().__post_init__()


@final
@dataclass
class SwitchBeeTimerSwitch(SwitchBeeBaseTimer, SwitchBeeBaseDevice):
    def __post_init__(self) -> None:
        """Post initialization validate device type category as TimedPowerSwitch."""
        if self.type != DeviceType.TimedPowerSwitch:
            raise ValueError("only TimedPowerSwitch are allowed")
        super().__post_init__()


@final
@dataclass
class SwitchBeeScenario(SwitchBeeBaseDevice):
    def __post_init__(self) -> None:
        """Post initialization validate device type category as Scenario."""
        if self.type != DeviceType.Scenario:
            raise ValueError("only Scenario are allowed")
        super().__post_init__()


@final
@dataclass
class SwitchBeeRollingScenario(SwitchBeeBaseDevice):
    def __post_init__(self) -> None:
        """Post initialization validate device type category as Rolling Scenario."""
        if self.type != DeviceType.RollingScenario:
            raise ValueError("only Rolling Scenario are allowed")
        super().__post_init__()


@final
@dataclass
class SwitchBeeGroupSwitch(SwitchBeeBaseSwitch, SwitchBeeBaseDevice):
    def __post_init__(self) -> None:
        """Post initialization validate device type category as GroupSwitch."""
        if self.type != DeviceType.GroupSwitch:
            raise ValueError("only GroupSwitch are allowed")
        super().__post_init__()


@final
@dataclass
class SwitchBeeTimedSwitch(SwitchBeeBaseSwitch, SwitchBeeBaseDevice):
    def __post_init__(self) -> None:
        """Post initialization validate device type category as TimedSwitch."""
        if self.type != DeviceType.TimedSwitch:
            raise ValueError("only TimedSwitch are allowed")
        super().__post_init__()


@final
@dataclass
class SwitchBeeThermostat(
    SwitchBeeBaseThermostat, SwitchBeeBaseSwitch, SwitchBeeBaseDevice
):
    def __post_init__(self) -> None:
        """Post initialization validate device type category as Thermostat."""
        if self.type != DeviceType.Thermostat:
            raise ValueError("only Thermostat are allowed")
        super().__post_init__()


@final
@dataclass
class SwitchBeeLockGroup(SwitchBeeBaseSwitch, SwitchBeeBaseDevice):
    def __post_init__(self) -> None:
        """Post initialization validate device type category as Switch."""
        if self.type != DeviceType.LockGroup:
            raise ValueError("only lock group are allowed")
        super().__post_init__()


@final
@dataclass
class SwitchBeeTwoWay(SwitchBeeBaseSwitch, SwitchBeeBaseDevice):
    def __post_init__(self) -> None:
        """Post initialization validate device type category as TwoWay."""
        if self.type != DeviceType.TwoWay:
            raise ValueError("only Two Way are allowed")
        super().__post_init__()


@final
@dataclass
class SwitchBeeSomfy(SwitchBeeBaseDevice):
    def __post_init__(self) -> None:
        """Post initialization validate device type category as Scenario."""
        if self.type != DeviceType.Somfy:
            raise ValueError("only Scenario are allowed")
        super().__post_init__()
