"""Unit tests for MQTT over WebSockets push updates."""
import json
from unittest.mock import MagicMock, patch

from custom_components.cecotec_conga.conga import Conga
from custom_components.cecotec_conga.coordinator import CongaDataUpdateCoordinator
from custom_components.cecotec_conga.mqtt_client import CongaMqttClient


def test_conga_get_presigned_ws_path():
    client = Conga("test_user", "test_pass")
    client._refresh_iot_client = MagicMock()
    client._iot_credentials = {
        "AccessKeyId": "ASIAEXAMPLEKEYID",
        "SecretKey": "EXAMPLESECRETKEY",
        "SessionToken": "EXAMPLETOKEN",
    }

    host, path = client.get_presigned_ws_path()
    assert host == "a39k27k2ztga9m-ats.iot.eu-west-2.amazonaws.com"
    assert path.startswith("/mqtt?")
    assert "X-Amz-Algorithm=AWS4-HMAC-SHA256" in path
    assert "X-Amz-Credential=" in path
    assert "X-Amz-Signature=" in path


def test_mqtt_client_on_message_regular_shadow():
    mock_hass = MagicMock()
    mock_hass.loop.is_running.return_value = False
    mock_conga = MagicMock()
    callback = MagicMock()

    mqtt_client = CongaMqttClient(mock_hass, mock_conga, "sn_test", callback)

    msg = MagicMock()
    msg.topic = "$aws/things/sn_test/shadow/update/accepted"
    msg.payload = json.dumps({
        "state": {
            "reported": {
                "mode": "sweep",
                "eventCode": 6023,
                "elec": 90,
            }
        }
    }).encode("utf-8")

    mqtt_client._on_message(MagicMock(), MagicMock(), msg)

    callback.assert_called_once_with(
        {"mode": "sweep", "eventCode": 6023, "elec": 90},
        None,
    )


def test_mqtt_client_on_message_service_shadow():
    mock_hass = MagicMock()
    mock_hass.loop.is_running.return_value = False
    mock_conga = MagicMock()
    callback = MagicMock()

    mqtt_client = CongaMqttClient(mock_hass, mock_conga, "sn_test", callback)

    tactics_payload = json.dumps({
        "value": [
            {"planName": "Cuina"},
            {"planName": "Menjador"},
        ]
    })

    msg = MagicMock()
    msg.topic = "$aws/things/sn_test/shadow/name/service/update/accepted"
    msg.payload = json.dumps({
        "state": {
            "reported": {
                "getTimeTactics": {
                    "body": {
                        "timeTactics": tactics_payload,
                    }
                }
            }
        }
    }).encode("utf-8")

    mqtt_client._on_message(MagicMock(), MagicMock(), msg)

    callback.assert_called_once_with(
        None,
        ["Cuina", "Menjador"],
    )


def test_coordinator_mqtt_update_handler():
    mock_hass = MagicMock()
    mock_conga = MagicMock()

    with patch("custom_components.cecotec_conga.coordinator.CongaMqttClient"):
        coord = CongaDataUpdateCoordinator(mock_hass, mock_conga, "sn_test", "Test Conga")
        coord.data = {
            "status": {"mode": "charge", "elec": 50},
            "plans": ["Pla1"],
        }
        coord.async_set_updated_data = MagicMock()

        # Simulate push update
        coord._async_handle_mqtt_update({"elec": 55, "mode": "sweep"}, ["Pla1", "Pla2"])

        assert coord.data["status"]["elec"] == 55
        assert coord.data["status"]["mode"] == "sweep"
        assert coord.data["plans"] == ["Pla1", "Pla2"]
        coord.async_set_updated_data.assert_called_once_with(coord.data)
