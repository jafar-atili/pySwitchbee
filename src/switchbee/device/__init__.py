from abc import ABC
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import List, Union, final

from ..api.utils import timestamp_now
from ..const import ApiDeviceHardware, ApiDeviceType, ApiStateCommand


@unique
class DeviceType(Enum):
    """Enum class representing the device's type."""

    Dimmer = ApiDeviceType.DIMMER, "Dimming Light"
    Switch = ApiDeviceType.SWITCH, "Switch"
    Shutter = ApiDeviceType.SHUTTER, "Shutter"
    Scenario = ApiDeviceType.SCENARIO, "Scenario"
    Repeater = ApiDeviceType.REPEATER, "Repeater"
    GroupSwitch = ApiDeviceType.GROUP_SWITCH, "Group Switch"
    TWO_WAY = ApiDeviceType.TWO_WAY, "Two Way"
    TimedPowerSwitch = ApiDeviceType.TIMED_POWER, "Timed Power Switch"
    Thermostat = ApiDeviceType.THERMOSTAT, "Thermostat"

    def __new__(cls, *args, **kwds):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    # ignore the first param since it's already set by __new__
    def __init__(self, _: str, display: str = None):
        self._display = display

    def __str__(self):
        return self.display

    # this makes sure that the description is read-only
    @property
    def display(self):
        return self._display


class HardwareType(Enum):
    Virtual = ApiDeviceHardware.VIRTUAL, "Virtual"
    Dimmable = ApiDeviceHardware.DIMMABLE_SWITCH, "Dimmable Switch"
    Shutter = ApiDeviceHardware.SHUTTER, "Shutter"
    TimedPowerSwitch = ApiDeviceHardware.TIMED_POWER_SWITCH, "Time Power Switch"

    def __new__(cls, *args, **kwds):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    # ignore the first param since it's already set by __new__
    def __init__(self, _: str, display: str = None):
        self._display = display

    def __str__(self):
        return self.display

    # this makes sure that the description is read-only
    @property
    def display(self):
        return self._display


class ThermostatMode(Enum):
    HEAT = "HEAT"
    COOL = "COOL"
    FAN = "FAN"


class ThermostatFanSpeed(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    AUTO = "AUTO"


class ThermostatTemperatureUnit(Enum):
    CELSIUS = "CELSIUS"
    FAHRENHEIT = "FAHRENHEIT"


@dataclass
class SwitchBeeBaseDevice(ABC):
    id: int
    name: str
    zone: str
    type: DeviceType
    hardware: str

    def __post_init__(self) -> None:
        """Post initialization, set last_data_update to the instantiation datetime."""
        self.last_data_update = timestamp_now()

    def __hash__(self):
        return self.id


@dataclass
class SwitchBeeBaseSwitch(ABC):
    _state: ApiStateCommand = field(init=False, default=None)

    @property
    def state(self) -> ApiStateCommand:
        return self._state

    @state.setter
    def state(self, value: str) -> None:
        self._state = value


@dataclass
class SwitchBeeBaseShutter(ABC):
    _position: int = field(init=False, repr=False, default=None)

    @property
    def position(self) -> int:
        return self._position

    @position.setter
    def position(self, value: Union[str, int]) -> None:

        if value == ApiStateCommand.OFF:
            self._position = 0
        elif value == ApiStateCommand.ON:
            self._position = 100
        else:
            self._position = int(value)


@dataclass
class SwitchBeeBaseDimmer(ABC):

    _brightness: int = field(init=False)

    @property
    def brightness(self) -> int:
        return self._brightness

    @brightness.setter
    def brightness(self, value: Union[str, int]) -> None:

        if value == ApiStateCommand.OFF or value == 0:
            self._brightness = 0
        elif value == ApiStateCommand.ON or value == 100:
            self._brightness = 100
        else:
            self._brightness = int(value)


@dataclass
class SwitchBeeBaseTimer(ABC):
    _minutes_left: int = field(init=False)
    _state: ApiStateCommand = field(init=False)

    @property
    def state(self) -> ApiStateCommand:
        return self._state

    @property
    def minutes_left(self) -> int:
        return self._minutes_left

    @state.setter
    def state(self, value: Union[str, int]) -> None:

        if value:
            if value == ApiStateCommand.OFF:
                self._minutes_left = 0
                self._state = value
            else:
                self._minutes_left = int(value)
                self._state = ApiStateCommand.ON


@dataclass
class SwitchBeeBaseThermostat(ABC):

    _modes: List[ThermostatMode] = field(init=False)
    _unit: ThermostatTemperatureUnit = field(init=False)
    _mode: ThermostatMode = field(init=False)
    _fan: ThermostatFanSpeed = field(init=False)
    _target_temperature: int = field(init=False)
    _temperature: int = field(init=False)

    @property
    def modes(self) -> List[str]:
        return self._modes

    @property
    def mode(self) -> ThermostatMode:
        return self._mode

    @mode.setter
    def mode(self, value: ThermostatMode) -> None:
        self._mode = value

    @property
    def fan(self) -> ThermostatFanSpeed:
        return self._fan

    @fan.setter
    def mode(self, value: ThermostatFanSpeed) -> None:
        self._fan = value

    @property
    def target_temperature(self) -> int:
        return self._target_temperature

    @target_temperature.setter
    def mode(self, value: int) -> None:
        self._target_temperature = value

    @property
    def temperature(self) -> int:
        return self._temperature


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
class SwitchBeeGroupSwitch(SwitchBeeBaseSwitch, SwitchBeeBaseDevice):
    def __post_init__(self) -> None:
        """Post initialization validate device type category as GroupSwitch."""
        if self.type != DeviceType.GroupSwitch:
            raise ValueError("only GroupSwitch are allowed")
        super().__post_init__()


@final
@dataclass
class SwitchBeeThermostat(
    SwitchBeeBaseThermostat, SwitchBeeBaseSwitch, SwitchBeeBaseDevice
):
    def __post_init__(self) -> None:
        """Post initialization validate device type category as GroupSwitch."""
        if self.type != DeviceType.Thermostat:
            raise ValueError("only Thermostat are allowed")
        super().__post_init__()
