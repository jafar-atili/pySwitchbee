from abc import ABC
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Union, final

from ..api.utils import timestamp_now

from ..const import (
    HW_DIMMABLE_SWITCH,
    HW_SHUTTER,
    HW_TIMED_POWER_SWITCH,
    HW_VIRTUAL,
    STATE_OFF,
    STATE_ON,
    Types,
)


class SwitchState:
    ON = STATE_ON
    OFF = STATE_OFF


@unique
class DeviceType(Enum):
    """Enum class representing the device's state."""

    Dimmer = Types.DIMMER
    Switch = Types.SWITCH
    Shutter = Types.SHUTTER
    Scenario = Types.SCENARIO
    Repeater = Types.REPEATER
    GroupSwitch = Types.GROUP_SWITCH
    TWO_WAY = Types.TWO_WAY
    TimePower = Types.TIMED_POWER


class HardwareType(Enum):
    Virtual = HW_VIRTUAL
    Switch = HW_DIMMABLE_SWITCH
    Shutter = HW_SHUTTER
    TimedSwitch = HW_TIMED_POWER_SWITCH


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
    _state: SwitchState = field(init=False, default=None)

    @property
    def state(self) -> SwitchState:
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

        if value:
            if value == SwitchState.OFF:
                self._position = 0
            elif value == SwitchState.ON:
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

        if value == SwitchState.OFF or value == 0:
            self._brightness = 0
        elif value == SwitchState.ON or value == 100:
            self._brightness = 100
        else:
            self._brightness = int(value)


@dataclass
class SwitchBeeBaseTimer(ABC):
    _minutes_left: int = field(init=False)
    _state: SwitchState = field(init=False)

    @property
    def state(self) -> SwitchState:
        return self._state

    @property
    def minutes_left(self) -> int:
        return self._minutes_left

    @state.setter
    def state(self, value: Union[str, int]) -> None:

        if value:
            if value == SwitchState.OFF:
                self._minutes_left = 0
                self._state = value
            else:
                self._minutes_left = int(value)
                self._state = SwitchState.ON


@dataclass
class SwitchBeeSwitch(SwitchBeeBaseSwitch, SwitchBeeBaseDevice):
    def __post_init__(self) -> None:
        """Post initialization validate device type category as POWER_PLUG."""
        super().__post_init__()


@final
@dataclass
class SwitchBeeShutter(SwitchBeeBaseShutter, SwitchBeeBaseDevice):
    def __post_init__(self) -> None:
        """Post initialization validate device type category as POWER_PLUG."""
        super().__post_init__()


@final
@dataclass
class SwitchBeeDimmer(SwitchBeeBaseDimmer, SwitchBeeBaseDevice):
    def __post_init__(self) -> None:
        """Post initialization validate device type category as POWER_PLUG."""
        super().__post_init__()


@final
@dataclass
class SwitchBeeTimerSwitch(SwitchBeeBaseTimer, SwitchBeeBaseDevice):
    def __post_init__(self) -> None:
        """Post initialization validate device type category as POWER_PLUG."""
        super().__post_init__()


@final
@dataclass
class SwitchBeeScenario(SwitchBeeBaseDevice):
    def __post_init__(self) -> None:
        """Post initialization validate device type category as POWER_PLUG."""
        super().__post_init__()


@final
@dataclass
class SwitchBeeGroupSwitch(SwitchBeeBaseSwitch, SwitchBeeBaseDevice):
    def __post_init__(self) -> None:
        """Post initialization validate device type category as POWER_PLUG."""
        super().__post_init__()
