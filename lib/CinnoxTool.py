import requests
from .loginEncrypt import passwordEncryption
import yaml


class CinnoxTool:
    def __init__(self):
        self.edge_server = 'https://hkpd-ed-aws.cx.cinnox.com'       # internal service
        self.service_id = 'internal.lc.m800.com'
        config = yaml.load(open('config.yaml'), Loader=yaml.FullLoader)['CinnoxTool']
        self.account = config['account']
        self.password = config['password']
        self.room_id = config['room_ID']  # space: tf_idd_fee
        self.room_name = config['room_name']

        self.encrypt_password, self.rnd = passwordEncryption(self.password)

        self.s = requests.Session()

    def get_eid_token(self):
        url = f'{self.edge_server}/auth/v1/service/{self.service_id}/users/token'
        headers = {'accept': 'application/json', 'content-type': 'application/json;charset=UTF-8'}
        body = {'username': self.account, 'password': self.encrypt_password, 'grant_type': 'password', 'challenge': {'type': 'mcpwv3', 'rand': self.rnd}}
        response = self.s.post(url, headers=headers, json=body)
        eid = response.json()['result']['eid']
        token = response.json()['result']['access_token']

        return eid, token

    def send_message_to_room(self, text):
        eid, token = self.get_eid_token()
        url = f'{self.edge_server}/im/v1/im/events/rooms/{self.room_id}/message'
        headers = {'x-m800-eid': eid, 'authorization': f'bearer {token}',
                   'x-m800-dp-sendername': 'Monitor',
                   'x-m800-dp-styledtext': 'Monitor',
                   'x-m800-dp-roomname': self.room_name
                   }

        # print(text)
        body = {'type': 1, 'text': f'{text}'}
        response = self.s.post(url, headers=headers, json=body)

        return
