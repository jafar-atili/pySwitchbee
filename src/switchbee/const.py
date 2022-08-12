class ApiCommand:
    # SwitchBee Request commands
    LOGIN = "LOGIN"
    GET_CONF = "GET_CONFIGURATION"
    GET_MULTI_STATES = "GET_MULTIPLE_STATES"
    GET_STATE = "GET_STATE"
    STATS = "STATS"
    OPERATE = "OPERATE"
    STATE = "STATE"


class ApiStatus:
    FAILED = "FAILED"
    OK = "OK"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    LOGIN_FAILED = "LOGIN_FAILED"
    OFFLINE = "OFFLINE"


class ApiAttribute:
    # SwitchBee request attributes
    COMMAND = "command"
    PARAMS = "params"
    USER = "username"
    PASS = "password"
    DATA = "data"
    MAC = "mac"
    STATUS = "status"
    EXPIRATION = "expiration"
    TOKEN = "token"
    ZONES = "zones"
    ITEMS = "items"
    TYPE = "type"
    ID = "id"
    STATE = "state"
    NAME = "name"
    HARDWARE = "hw"
    VERSION = "version"
    LAST_CONF_CHANGE = "lastConfChange"
    TEMPERATURE_UNITS = "temperatureUnits"
    MODES = "modes"
    POWER = "power"
    MODE = "mode"
    FAN = "fan"
    CONFIGURED_TEMPERATURE = "configuredTemperature"
    ROOM_TEMPERATURE = "roomTemperature"


class ApiStateCommand:
    ON = "ON"
    OFF = "OFF"


# SwitchBee device hardware
class ApiDeviceHardware:
    DIMMABLE_SWITCH = "DIMMABLE_SWITCH"
    SHUTTER = "SHUTTER"
    VIRTUAL = "VIRTUAL"
    TIMED_POWER_SWITCH = "TIMED_POWER_SWITCH"


class ApiDeviceType:
    # SwitchBee device types
    DIMMER = "DIMMER"
    REPEATER = "REPEATER"
    SWITCH = "SWITCH"
    SHUTTER = "SHUTTER"
    TWO_WAY = "TWO_WAY"
    GROUP_SWITCH = "GROUP_SWITCH"
    SCENARIO = "SCENARIO"
    TIMED_POWER = "TIMED_POWER"
    OUTLET = "OUTLET"
    THERMOSTAT = "THERMOSTAT"
