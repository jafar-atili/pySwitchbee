import aiohttp
import asyncio
from datetime import datetime
from json import JSONDecodeError

# SwitchBee Request commands
CMD_LOGIN = 'LOGIN'
CMD_GET_CONF = 'GET_CONFIGURATION'
CMD_GET_MULTI_STATES = 'GET_MULTIPLE_STATES'
CMD_GET_STATE = 'GET_STATE'
CMD_STATS = 'STATS'
CMD_OPERATE = 'OPERATE'
CMD_STATE = 'STATE'

STATUS_FAILED = 'FAILED'

STATUS_OK = 'OK'
STATUS_INVALID_TOKEN = 'INVALID_TOKEN'
STATUS_LOGIN_FAILED = 'LOGIN_FAILED'

# SwitchBee request attributes
ATTR_COMMAND = 'command'
ATTR_PARAMS = 'params'
ATTR_USER = 'username'
ATTR_PASS = 'password'
ATTR_DATA = 'data'
ATTR_MAC = 'mac'
ATTR_STATUS = 'status'
ATTR_EXPIRATION = 'expiration'
ATTR_TOKEN = 'token'
ATTR_ZONES = 'zones'
ATTR_ITEMS = 'items'
ATTR_TYPE = 'type'
ATTR_ID = 'id'
ATTR_STATE = 'state'

STATE_ON = 'ON'
STATE_OFF = 'OFF'

COMMANDS_URL = 'commands'

# SwitchBee device types
TYPE_DIMMER = 'DIMMER'
TYPE_REPEATER = 'REPEATER'
TYPE_SWITCH = 'SWITCH'
TYPE_SHUTTER = 'SHUTTER'
TYPE_TWO_WAY = 'TWO_WAY'
TYPE_GROUP_SWITCH = 'GROUP_SWITCH'
TYPE_SCENARIO = 'SCENARIO'
TYPE_TIMED_POWER = 'TIMED_POWER'
TYPE_OUTLET = 'OUTLET'

# List of default skipped types
SUPPORTED_ITEMS = [TYPE_DIMMER, TYPE_SWITCH, TYPE_SHUTTER]

REQUEST_TIMEOUT = 5

def current_timestamp():
    return int(datetime.now().timestamp())


class SwitchBee():
    def __init__(self, central_unit, user, password):
        self.__cunit_ip = central_unit
        self.__user = user
        self.__password = password
        self.__base_url = f'https://{self.__cunit_ip}/{COMMANDS_URL}'
        self.__token = None
        self.__token_expiration = current_timestamp()
        self.__tmout = REQUEST_TIMEOUT
        self.__session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False), 
                    timeout=aiohttp.ClientTimeout(total=self.__tmout))

    async def close(self):
        await self.__session.close()

    async def __send_request(self, command, params={}):            
        async def do_send_request(payload):
            try:
                resp = await self.__session.post(url=self.__base_url, json=payload)
            except asyncio.TimeoutError as e:
                return {ATTR_STATUS: STATUS_FAILED, "code": -200, 'message': e}
            except aiohttp.ClientError as e:
                return {ATTR_STATUS: STATUS_FAILED, "code": -200, 'message': e}
            
            try:
                return await resp.json(content_type=None)
            except JSONDecodeError as e:
                return {ATTR_STATUS: STATUS_FAILED, "code": -200, 'message': 'Unexpected Response'}

        if command == CMD_LOGIN:
            payload = {
                ATTR_COMMAND: CMD_LOGIN,
                ATTR_PARAMS: {
                    ATTR_USER: self.__user,
                    ATTR_PASS: self.__password
                }
            }

        else:
            payload = {
                ATTR_TOKEN: self.__token,
                ATTR_COMMAND: command,
                ATTR_PARAMS: params
            }

        resp = await do_send_request(payload)
        # Someone else must've logged in and refreshed the token, for now just try to log in again
        if resp[ATTR_STATUS] != STATUS_OK and resp[ATTR_STATUS] == STATUS_INVALID_TOKEN:
            self.login()
            resp = await do_send_request(payload)
        
        return resp

    async def login(self):
        resp = await self.__send_request(CMD_LOGIN)
        if resp[ATTR_STATUS] == STATUS_OK:
            self.__token = resp[ATTR_DATA][ATTR_TOKEN]
            self.__token_expiration = resp[ATTR_DATA][ATTR_EXPIRATION]
        
        return resp

    async def get_configuration(self):
        return await self.__send_request(CMD_GET_CONF)

    async def get_multiple_states(self, ids: list):
        '''returns JSON {'status': 'OK', 'data': [{'id': 212, 'state': 'OFF'}, {'id': 343, 'state': 'OFF'}]}'''
        return await self.__send_request(CMD_GET_MULTI_STATES, ids)

    async def get_state(self, id: int):
        ''' returns JSON {'status': 'OK', 'data': 'OFF'}'''
        return await self.__send_request(CMD_GET_STATE, id)

    async def set_state(self, id: int, state):
        ''' returns JSON {'status': 'OK', 'data': 'OFF/ON'}'''
        return await self.__send_request(CMD_OPERATE, {'directive': 'SET' ,'itemId': id, 'value': state})

    async def get_stats(self):
        ''' returns {'status': 'OK', 'data': {}} on my unit'''
        return await self.__send_request(CMD_STATS)
