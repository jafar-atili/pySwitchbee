import requests
from datetime import datetime
import urllib3

REQUEST_TIMEOUT = 5

# SwitchBee Request commands
CMD_LOGIN = 'LOGIN'
CMD_GET_CONF = 'GET_CONFIGURATION'
CMD_GET_MULTI_STATES = 'GET_MULTIPLE_STATES'
CMD_GET_STATE = 'GET_STATE'
CMD_STATS = 'STATS'
CMD_OPERATE = 'OPERATE'
CMD_STATE = 'STATE'

STATUS_OK = 'OK'
STATUS_INVALID_TOKEN = 'INVALID_TOKEN'

# SwitchBee request attributes
ATTR_COMMAND = 'command'
ATTR_PARAMS = 'params'
ATTR_USER = 'username'
ATTR_PASS = 'password'
ATTR_DATA = 'data'
ATTR_STATUS = 'status'
ATTR_EXPIRATION = 'expiration'
ATTR_TOKEN = 'token'
ATTR_ZONES = 'zones'
ATTR_ITEMS = 'items'
ATTR_TYPE = 'type'
ATTR_ID = 'id'

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

# List of default skipped types
SUPPORTED_ITEMS = [TYPE_DIMMER, TYPE_SWITCH, TYPE_SHUTTER]


def current_timestamp():
    return int(datetime.now().timestamp())


class SwitchBee():
    def __init__(self, central_unit, user, password, cert=False, request_timeout = REQUEST_TIMEOUT):
        self.__cunit_ip = central_unit
        self.__user = user
        self.__password = password
        self.__base_url = f'https://{self.__cunit_ip}/{COMMANDS_URL}'
        self.__cert = cert
        self.__token = None
        self.__token_expiration = current_timestamp()
        self.__tmout = request_timeout
    
        if not self.__cert:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # login as part of initializing the object
        self.__login()

    def __post(self, command: str, params: dict = {}):
        
        # Check if need to re-login
        if self.__token and self.__token_expiration < current_timestamp():
            # Already logged in
            self.__login()

        def __do_post(url, token, command, params, timeout, cert):

            payload = {
                ATTR_TOKEN: token,
                ATTR_COMMAND: command,
                ATTR_PARAMS: params
            }

            return requests.post(url, json=payload, timeout=timeout, verify=cert)
        
        response = __do_post(self.__base_url, self.__token, command, params, self.__tmout, self.__cert)
        if response.status_code == 200:
            respj = response.json()
            if respj[ATTR_STATUS] != STATUS_OK:
                if respj[ATTR_STATUS] == STATUS_INVALID_TOKEN:
                    # Token was revoked, probably another attempt of login happened within the same user
                    # we'll just try to login and send the request again
                    self.__login()
                    return __do_post(self.__base_url, self.__token, command, params, self.__tmout, self.__cert)         

            return response.json()
        else:
            return None

    def __login(self):

        payload = {
            ATTR_COMMAND: CMD_LOGIN,
			ATTR_PARAMS: {
				ATTR_USER: self.__user,
				ATTR_PASS: self.__password
			}
        }
    
        response = requests.post(self.__base_url, json=payload, timeout=self.__tmout, verify=self.__cert)
        if response.status_code == 200:
            self.__token = response.json()[ATTR_DATA][ATTR_TOKEN]
            self.__token_expiration = response.json()[ATTR_DATA][ATTR_EXPIRATION]
            return True
        else:
            return False
    
    def get_devices_map_by_type(self, types: list = SUPPORTED_ITEMS):
        res = self.__post(CMD_GET_CONF)
        data = {}
        for zone in res[ATTR_DATA][ATTR_ZONES]:
            for item in zone[ATTR_ITEMS]:
                if item[ATTR_TYPE] in types:
                    data[item[ATTR_ID]] = item

        return data

    def get_devices_list_by_type(self, types: list = SUPPORTED_ITEMS):
        res = self.__post(CMD_GET_CONF)
        data = []
        for zone in res[ATTR_DATA][ATTR_ZONES]:
            for item in zone[ATTR_ITEMS]:
                if item[ATTR_TYPE] in types:
                    data.append(item[ATTR_ID])

        return data        

    def get_devices_list(self):
        return self.__post(CMD_GET_CONF)

    def get_multiple_states(self, ids: list):
        '''returns JSON {'status': 'OK', 'data': [{'id': 212, 'state': 'OFF'}, {'id': 343, 'state': 'OFF'}]}'''
        return self.__post(CMD_GET_MULTI_STATES, ids)

    def get_state(self, id: int):
        ''' returns JSON {'status': 'OK', 'data': 'OFF'}'''
        return self.__post(CMD_GET_STATE, id)

    def set_state(self, id: int, state):
        ''' returns JSON {'status': 'OK', 'data': 'OFF/ON'}'''
        return self.__post(CMD_OPERATE, {'directive': 'SET' ,'itemId': id, 'value': state})

    def get_stats(self):
        ''' returns {'status': 'OK', 'data': {}} on my unit'''
        return self.__post(CMD_STATS)
