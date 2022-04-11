import requests
from datetime import datetime
from switchbee.const import *
import urllib3

REQUEST_TIMEOUT = 3

# SwitchBee Request commands
COMMAND_LOGIN = 'LOGIN'
COMMAND_GET_CONF = 'GET_CONFIGURATION'
COMMAND_GET_MULTI_STATES = 'GET_MULTIPLE_STATES'
COMMAND_OPERATE = 'OPERATE'

# SwitchBee request attributes
TOKEN_ATTR = 'token'
COMMAND_ATTR = 'command'
PARAMS_ATTR = 'params'
USER_ATTR = 'username'
PASS_ATTR = 'password'

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


class SwitchBee():
    def __init__(self, central_unit, user, password, cert=False):
        self.__cunit_ip = central_unit
        self.__user = user
        self.__password = password
        self.__base_url = f'https://{self.__cunit_ip}/{COMMANDS_URL}'
        self.__cert = cert
        self.__token = None

        if not self.__cert:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def __post(self, command, params={}, timeout=REQUEST_TIMEOUT):

        self.login()

        payload = {
            TOKEN_ATTR: self.__token['token'],
            COMMAND_ATTR: command,
            PARAMS_ATTR: params
        }

        response = requests.post(self.__base_url, json=payload, timeout=timeout, verify=self.__cert)
        if response.status_code == 200:
            respj = response.json()
            if respj['status'] != 'OK':
                raise RuntimeError(f'Request failed with status {respj["status"]}')

            return response.json()['data']
        else:
            raise RuntimeError(f'Request with payload {payload} failed!')

    def login(self):

        if self.__token and self.__token['expiration'] < int(datetime.now().timestamp()):
            # already logged in
            return

        payload = {
            COMMAND_ATTR: 'LOGIN',
			PARAMS_ATTR: {
				USER_ATTR: self.__user,
				PASS_ATTR: self.__password
			}
        }

        response = requests.post(self.__base_url, json=payload, timeout=3, verify=self.__cert)
        if response.status_code == 200:            
            self.__token = response.json()['data']
            print(response.json())
        else:
            raise RuntimeError('Login Failed')
    
    def get_devices(self, types=SUPPORTED_ITEMS):

        res = self.__post(COMMAND_GET_CONF)
        data = {}
        for zone in res['zones']:
            for item in zone['items']:
                if item['type'] in types:
                    data[item['id']] = item

        return data

    def get_states(self, ids):
        return self.__post(COMMAND_GET_MULTI_STATES, ids)

    def set_device_state(self, id, state):
        self.__post(COMMAND_OPERATE, {'directive': 'SET' ,'itemId': id, 'value': state})
