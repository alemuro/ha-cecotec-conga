import requests
import json
import boto3
from pycognito import Cognito
from pycognito.utils import RequestsSrpAuth

CECOTEC_API_BASE_URL = "https://qafbskf2ug.execute-api.eu-west-2.amazonaws.com"
AWS_IOT_ENDPOINT = "https://a39k27k2ztga9m-ats.iot.eu-west-2.amazonaws.com"


class Conga():
    def __init__(self, username, password):
        self._username = username
        self._password = password
        self._devices = []
        self._api_token = self._get_api_token()
        self._iot_client = self._get_iot_client()

    def list_vacuums(self):
        devices = requests.post(
            f'{CECOTEC_API_BASE_URL}/api/user_machine/list',
            json={},
            auth=self._api_token
        )
        self._devices = devices.json()["data"]["page_items"]
        return self._devices

    def status(self, sn):
        r = self._iot_client.get_thing_shadow(thingName=sn)
        return json.load(r['payload'])

    def start(self, sn):
        payload = {
            "state": {
                "desired": {
                    "startClean": {
                        "state": 1,
                        "body": {
                            "mode": "Auto",
                            "deepClean": 0,
                            "fanLevel": 1,
                            "water": 1,
                            "autoBoost": 0,
                            "params": "[]"
                        }
                    }
                }
            }
        }

        self._send_payload(sn, payload)

    def home(self, sn):
        payload = {
            "state": {
                "desired": {
                    "startFindCharge": {"state": 1}
                }
            }
        }

        self._send_payload(sn, payload)

    def _send_payload(self, sn, payload):
        response = self._iot_client.update_thing_shadow(
            thingName=sn,
            shadowName='service',
            payload=bytes(json.dumps(payload), "ascii")
        )

        print(response)

    def _get_api_token(self):
        return RequestsSrpAuth(
            username=self._username,
            password=self._password,
            user_pool_id='eu-west-2_L5T0M5yrf',
            client_id='6iep27ce22ojt8bgb2vji3d387',
            user_pool_region='eu-west-2',
        )

    def _get_iot_client(self):
        u = Cognito('eu-west-2_L5T0M5yrf', '6iep27ce22ojt8bgb2vji3d387',
                    username=self._username)
        u.authenticate(password=self._password)
        cognito = boto3.client('cognito-identity', 'eu-west-2')
        response = cognito.get_id(
            IdentityPoolId='eu-west-2:0cdeb155-55bb-45f8-9710-4895bd40d605',
            Logins={
                'cognito-idp.eu-west-2.amazonaws.com/eu-west-2_L5T0M5yrf': u.id_token
            }
        )
        creds = cognito.get_credentials_for_identity(
            IdentityId=response["IdentityId"],
            Logins={
                'cognito-idp.eu-west-2.amazonaws.com/eu-west-2_L5T0M5yrf': u.id_token
            }
        )
        return boto3.client(
            'iot-data',
            region_name='eu-west-2',
            endpoint_url=AWS_IOT_ENDPOINT,
            aws_access_key_id=creds["Credentials"]["AccessKeyId"],
            aws_secret_access_key=creds["Credentials"]["SecretKey"],
            aws_session_token=creds["Credentials"]["SessionToken"],
        )
