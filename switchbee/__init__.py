import requests
from datetime import datetime
from const import *
import urllib3

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

        self.__login()

        payload = {
            TOKEN_KEY: self.__token['token'],
            COMMAND_KEY: command,
            PARAMS_KEY: params
        }

        response = requests.post(self.__base_url, json=payload, timeout=timeout, verify=self.__cert)
        if response.status_code == 200:
            respj = response.json()
            if respj['status'] != 'OK':
                raise RuntimeError(f'Request failed with status {respj["status"]}')

            return response.json()['data']
        else:
            raise RuntimeError(f'Request with payload {payload} failed!')

    def __login(self):

        if self.__token and self.__token['expiration'] < int(datetime.now().timestamp()):
            print("already logged in")
            # already logged in
            return

        payload = {
            COMMAND_KEY: 'LOGIN',
			PARAMS_KEY: {
				USER_KEY: self.__user,
				PASS_KEY: self.__password
			}
        }

        response = requests.post(self.__base_url, json=payload, timeout=3, verify=self.__cert)
        if response.status_code == 200:            
            self.__token = response.json()['data']
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