import json
from math import fabs
from tkinter import COMMAND, SW
import requests
from datetime import datetime
from const import *


class SwitchBee():
    def __init__(self, central_unit, user, password):
        self.__cunit_ip = central_unit
        self.__user = user
        self.__password = password
        self.__base_url = f'https://{self.__cunit_ip}/{COMMANDS_URL}'
        self.__cert = False
        self.__token = None
        self.__cached_items = {}

    def __post(self, command, params={}, timeout = 3):

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
    

    def get_devices(self):

        res = self.__post(COMMAND_GET_CONF)

        for zone in res['zones']:
            for item in zone['items']:
                if item['type'] in SUPPORTED_ITEMS:
                    self.__cached_items[item['id']] = item

        return self.__cached_items


    def get_states(self, ids):
        print(ids)
        res = self.__post(COMMAND_GET_MULTI_STATES, ids)
        print(res)
