import aiohttp
import asyncio
from datetime import datetime
from json import JSONDecodeError
import logging

logger = logging.getLogger(__name__)

# SwitchBee Request commands
CMD_LOGIN = "LOGIN"
CMD_GET_CONF = "GET_CONFIGURATION"
CMD_GET_MULTI_STATES = "GET_MULTIPLE_STATES"
CMD_GET_STATE = "GET_STATE"
CMD_STATS = "STATS"
CMD_OPERATE = "OPERATE"
CMD_STATE = "STATE"

STATUS_FAILED = "FAILED"
STATUS_OK = "OK"
STATUS_INVALID_TOKEN = "INVALID_TOKEN"
STATUS_TOKEN_EXPIRED = "TOKEN_EXPIRED"
STATUS_LOGIN_FAILED = "LOGIN_FAILED"

# SwitchBee request attributes
ATTR_COMMAND = "command"
ATTR_PARAMS = "params"
ATTR_USER = "username"
ATTR_PASS = "password"
ATTR_DATA = "data"
ATTR_MAC = "mac"
ATTR_STATUS = "status"
ATTR_EXPIRATION = "expiration"
ATTR_TOKEN = "token"
ATTR_ZONES = "zones"
ATTR_ITEMS = "items"
ATTR_TYPE = "type"
ATTR_ID = "id"
ATTR_STATE = "state"
ATTR_HARDWARE = "hw"
ATTR_NAME = "name"

STATE_ON = "ON"
STATE_OFF = "OFF"


# SwitchBee device hardware
HW_DIMMABLE_SWITCH = "DIMMABLE_SWITCH"
HW_SHUTTER = "SHUTTER"
HW_VIRTUAL = "VIRTUAL"
HW_TIMED_POWER_SWITCH = "TIMED_POWER_SWITCH"


# SwitchBee devie types
TYPE_DIMMER = "DIMMER"
TYPE_REPEATER = "REPEATER"
TYPE_SWITCH = "SWITCH"
TYPE_SHUTTER = "SHUTTER"
TYPE_TWO_WAY = "TWO_WAY"
TYPE_GROUP_SWITCH = "GROUP_SWITCH"
TYPE_SCENARIO = "SCENARIO"
TYPE_TIMED_POWER = "TIMED_POWER"
TYPE_OUTLET = "OUTLET"


class SwitchBeeError(Exception):
    pass


class SwitchBeeAPI:
    def __init__(self, central_unit, user, password, websession):
        self._cunit_ip = central_unit
        self._user = user
        self._password = password
        self._session = websession
        self._token = None
        self._token_expiration = 0
        self._login_count = -1  # we don't count the first login
        self._relogin_on_invalid_token = True

    @property
    def reconnect_count(self):
        return self._login_count

    @property
    def token_expiration(self):
        return self._token_expiration

    @property
    def relogin_on_invalid_token(self):
        return self._relogin_on_invalid_token

    @relogin_on_invalid_token.setter
    def relogin_on_invalid_token(self, value: bool):
        self._relogin_on_invalid_token = value

    async def _send_request(self, command, params={}):

        # Renew the Token if required
        if (
            command != CMD_LOGIN
            and self._token
            and int(datetime.now().timestamp() * 1000) >= self._token_expiration
        ):
            await self.login()

        if command == CMD_LOGIN:
            payload = {
                ATTR_COMMAND: CMD_LOGIN,
                ATTR_PARAMS: {ATTR_USER: self._user, ATTR_PASS: self._password},
            }

        else:
            payload = {
                ATTR_TOKEN: self._token,
                ATTR_COMMAND: command,
                ATTR_PARAMS: params,
            }

        try:
            resp = await self._session.post(
                url=f"https://{self._cunit_ip}/commands", json=payload
            )
            json_result = await resp.json(content_type=None)
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            raise SwitchBeeError(e)
        except JSONDecodeError as e:
            resp = await resp.read()
            raise SwitchBeeError(f"Unexpected response: {resp}")
        else:

            # Someone else logged in with the same user and changed the token,
            # for now just try to login again
            if (
                self._relogin_on_invalid_token
                and json_result[ATTR_STATUS] != STATUS_OK
                and (
                    json_result[ATTR_STATUS] == STATUS_INVALID_TOKEN
                    or json_result[ATTR_STATUS] == STATUS_TOKEN_EXPIRED
                )
            ):
                logger.debug("About to re-login due to %s", json_result[ATTR_STATUS])
                await self.login()
                raise SwitchBeeError(
                    f"data Request failed due to {json_result[ATTR_STATUS]}, trying to re-login"
                )

            else:
                if (
                    ATTR_STATUS not in json_result
                    or json_result[ATTR_STATUS] != STATUS_OK
                ):
                    raise SwitchBeeError(
                        f"Central Unit replied with failure: {json_result}"
                    )
        return json_result

    async def login(self):
        try:
            resp = await self._send_request(CMD_LOGIN)
        except SwitchBeeError as e:
            raise SwitchBeeError(f"Failed to login: {e}")

        if resp and resp[ATTR_STATUS] == STATUS_OK:
            self._login_count += 1
            self._token = resp[ATTR_DATA][ATTR_TOKEN]
            self._token_expiration = resp[ATTR_DATA][ATTR_EXPIRATION]
            return True
        else:
            self._token = None
            self._token_expiration = 0
            return False

    async def get_configuration(self):
        return await self._send_request(CMD_GET_CONF)

    async def get_multiple_states(self, ids: list):
        """returns JSON {'status': 'OK', 'data': [{'id': 212, 'state': 'OFF'}, {'id': 343, 'state': 'OFF'}]}"""
        return await self._send_request(CMD_GET_MULTI_STATES, ids)

    async def get_state(self, id: int):
        """returns JSON {'status': 'OK', 'data': 'OFF'}"""
        return await self._send_request(CMD_GET_STATE, id)

    async def set_state(self, id: int, state):
        """returns JSON {'status': 'OK', 'data': 'OFF/ON'}"""
        return await self._send_request(
            CMD_OPERATE, {"directive": "SET", "itemId": id, "value": state}
        )

    async def get_stats(self):
        """returns {'status': 'OK', 'data': {}} on my unit"""
        return await self._send_request(CMD_STATS)
