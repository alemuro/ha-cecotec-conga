import datetime
import json
import logging
import random
import string
import urllib.parse

import boto3
import botocore.auth
import botocore.awsrequest
import botocore.credentials
import requests
from pycognito import Cognito
from pycognito.utils import RequestsSrpAuth

_LOGGER = logging.getLogger(__name__)

CECOTEC_API_BASE_URL = "https://qafbskf2ug.execute-api.eu-west-2.amazonaws.com"
AWS_IOT_ENDPOINT = "https://a39k27k2ztga9m-ats.iot.eu-west-2.amazonaws.com"
AWS_IOT_REGION = "eu-west-2"


class Conga:
    def __init__(self, username, password):
        self._username = username
        self._password = password
        self._devices = []
        self._shadows = {}
        self._plans = {}
        self._plan_names = {}
        self._shadow = {}
        self._plan_names_list = []
        self._api_token = None
        self._iot_client = None
        self._iot_token_expiration = None

    def list_vacuums(self):
        self._refresh_api_token()
        devices = requests.post(
            f"{CECOTEC_API_BASE_URL}/api/user_machine/list",
            json={},
            auth=self._api_token,
        )
        devices.raise_for_status()
        self._devices = devices.json()["data"]["page_items"]
        _LOGGER.debug(self._devices)
        return self._devices

    def list_plans(self, sn=None):
        if sn is not None and sn in self._plan_names:
            return self._plan_names[sn]
        return self._plan_names_list

    def update_shadows(self, sn):
        self._refresh_iot_client()
        shadow = self._iot_client.get_thing_shadow(thingName=sn)
        shadow_service = self._iot_client.get_thing_shadow(
            thingName=sn, shadowName="service"
        )

        shadow = json.load(shadow["payload"])["state"]["reported"]
        shadow_service = json.load(shadow_service["payload"])["state"]["reported"]

        self._shadow = shadow
        self._shadows[sn] = shadow

        tactics_str = shadow_service.get("getTimeTactics", {}).get("body", {}).get("timeTactics", "{}")

        # Fill plans variables
        plans = []
        plan_names = []
        try:
            tactics_val = json.loads(tactics_str).get("value", [])
            for tactic in tactics_val:
                if "planName" in tactic:
                    plans.append(tactic)
                    plan_names.append(tactic["planName"])
        except (json.JSONDecodeError, AttributeError):
            _LOGGER.warning("Failed to parse timeTactics for device %s", sn)

        self._plans[sn] = plans
        self._plan_names[sn] = plan_names
        self._plan_names_list = plan_names

        return shadow

    def get_status(self, sn=None):
        if sn is not None and sn in self._shadows:
            return self._shadows[sn]
        return self._shadow

    def start(self, sn, fan_speed):
        payload = {
            "state": {
                "desired": {
                    "startClean": {
                        "state": 1,
                        "body": {
                            "mode": "Auto",
                            "deepClean": 0,
                            "fanLevel": fan_speed,
                            "water": 1,
                            "autoBoost": 0,
                            "params": "[]",
                        },
                    }
                }
            }
        }

        self._send_payload(sn, payload)

    def set_fan_speed(self, sn, level):
        payload = {"state": {"desired": {"workNoisy": level}}}
        _LOGGER.debug(payload)
        self._refresh_iot_client()
        self._iot_client.update_thing_shadow(
            thingName=sn, payload=bytes(json.dumps(payload), "ascii")
        )

    def set_water_level(self, sn, level):
        payload = {"state": {"desired": {"water": level}}}
        _LOGGER.debug(payload)
        self._refresh_iot_client()
        self._iot_client.update_thing_shadow(
            thingName=sn, payload=bytes(json.dumps(payload), "ascii")
        )

    def start_plan(self, sn, plan_name):
        _LOGGER.info(f"Starting plan {plan_name} on {sn}")
        allowed_chars = string.ascii_lowercase + string.ascii_uppercase + string.digits
        result_str = "".join(random.choice(allowed_chars) for i in range(10))
        plan = self._get_plan_details(plan_name, sn)
        payload = {
            "state": {
                "desired": {
                    "StartTimedCleanTask": {
                        "id": result_str,
                        "params": json.dumps(plan),
                    }
                }
            }
        }
        _LOGGER.debug(payload)
        self._send_payload(sn, payload)

    def home(self, sn):
        payload = {"state": {"desired": {"startFindCharge": {"state": 1}}}}

        self._send_payload(sn, payload)

    def _get_plan_details(self, plan_name, sn=None):
        _LOGGER.debug(f"Looking for plan {plan_name}")
        plans = self._plans.get(sn, []) if sn is not None else []
        if not plans and hasattr(self, "_plans") and isinstance(self._plans, list):
            plans = self._plans
        _LOGGER.debug(f"Plans: {plans}")
        for plan in plans:
            if plan.get("planName") == plan_name:
                return plan
        return ""

    def _send_payload(self, sn, payload):
        _LOGGER.debug(payload)
        self._refresh_iot_client()
        self._iot_client.update_thing_shadow(
            thingName=sn,
            shadowName="service",
            payload=bytes(json.dumps(payload), "ascii"),
        )

    def _refresh_api_token(self):
        if self._api_token is not None:
            return self._api_token

        self._api_token = RequestsSrpAuth(
            username=self._username,
            password=self._password,
            user_pool_id="eu-west-2_L5T0M5yrf",
            client_id="6iep27ce22ojt8bgb2vji3d387",
            user_pool_region="eu-west-2",
        )
        return self._api_token

    def _refresh_iot_client(self):
        if (
            self._iot_client is not None
            and self._iot_token_expiration is not None
            and datetime.datetime.now().timestamp()
            < self._iot_token_expiration.timestamp()
        ):
            return self._iot_client

        _LOGGER.info("Refreshing Cecotec Conga token")

        u = Cognito(
            "eu-west-2_L5T0M5yrf", "6iep27ce22ojt8bgb2vji3d387", username=self._username
        )
        u.authenticate(password=self._password)
        cognito = boto3.client("cognito-identity", "eu-west-2")
        response = cognito.get_id(
            IdentityPoolId="eu-west-2:0cdeb155-55bb-45f8-9710-4895bd40d605",
            Logins={
                "cognito-idp.eu-west-2.amazonaws.com/eu-west-2_L5T0M5yrf": u.id_token
            },
        )
        creds = cognito.get_credentials_for_identity(
            IdentityId=response["IdentityId"],
            Logins={
                "cognito-idp.eu-west-2.amazonaws.com/eu-west-2_L5T0M5yrf": u.id_token
            },
        )
        self._iot_credentials = creds["Credentials"]
        self._iot_client = boto3.client(
            "iot-data",
            region_name="eu-west-2",
            endpoint_url=AWS_IOT_ENDPOINT,
            aws_access_key_id=creds["Credentials"]["AccessKeyId"],
            aws_secret_access_key=creds["Credentials"]["SecretKey"],
            aws_session_token=creds["Credentials"]["SessionToken"],
        )
        self._iot_token_expiration = creds["Credentials"]["Expiration"]

    def get_presigned_ws_path(self) -> tuple[str, str]:
        """Generate a presigned WSS URL path for AWS IoT MQTT over WebSockets.

        Returns:
            A tuple of (endpoint_host, path_with_query_string).
        """
        self._refresh_iot_client()
        creds = self._iot_credentials
        endpoint_host = urllib.parse.urlparse(AWS_IOT_ENDPOINT).netloc

        credentials = botocore.credentials.Credentials(
            creds["AccessKeyId"],
            creds["SecretKey"],
            creds["SessionToken"],
        )
        request = botocore.awsrequest.AWSRequest(
            method="GET",
            url=f"https://{endpoint_host}/mqtt",
            headers={"host": endpoint_host},
        )
        auth = botocore.auth.SigV4QueryAuth(
            credentials,
            "iotdevicegateway",
            AWS_IOT_REGION,
            expires=3600,
        )
        auth.add_auth(request)
        parsed = urllib.parse.urlparse(request.url)
        return parsed.netloc, f"{parsed.path}?{parsed.query}"

