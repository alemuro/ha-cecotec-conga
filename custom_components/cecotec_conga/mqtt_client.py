"""MQTT over WebSockets client for real-time AWS IoT Shadow updates."""
from __future__ import annotations

import json
import logging
import threading
import uuid
from typing import Any, Callable

import paho.mqtt.client as mqtt

from .conga import Conga

_LOGGER = logging.getLogger(__name__)

# Cognito tokens typically expire after 3600 seconds. Reconnect after 45 mins.
TOKEN_REFRESH_INTERVAL = 2700
RECONNECT_DELAY = 5


class CongaMqttClient:
    """Manages an MQTT-over-WebSocket connection to AWS IoT Core."""

    def __init__(
        self,
        hass: Any,
        conga_client: Conga,
        sn: str,
        on_update_callback: Callable[[dict[str, Any] | None, list[str] | None], None],
    ) -> None:
        """Initialize the MQTT client."""
        self._hass = hass
        self._conga_client = conga_client
        self._sn = sn
        self._on_update_callback = on_update_callback

        self._client: mqtt.Client | None = None
        self._connected = False
        self._stopped = False
        self._reconnect_timer: threading.Timer | None = None
        self._refresh_timer: threading.Timer | None = None

    @property
    def is_connected(self) -> bool:
        """Return True if currently connected."""
        return self._connected

    def start(self) -> None:
        """Start the MQTT client in a background thread."""
        self._stopped = False
        self._connect()

    def stop(self) -> None:
        """Stop and disconnect the MQTT client."""
        self._stopped = True
        self._cancel_timers()

        if self._client is not None:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception as err:
                _LOGGER.debug("Error while disconnecting MQTT client for %s: %s", self._sn, err)
            finally:
                self._client = None
                self._connected = False

    def _cancel_timers(self) -> None:
        """Cancel any pending reconnect or token refresh timers."""
        if self._reconnect_timer is not None:
            self._reconnect_timer.cancel()
            self._reconnect_timer = None
        if self._refresh_timer is not None:
            self._refresh_timer.cancel()
            self._refresh_timer = None

    def _connect(self) -> None:
        """Establish the MQTT WebSocket connection."""
        if self._stopped:
            return

        self._cancel_timers()

        try:
            endpoint_host, ws_path = self._conga_client.get_presigned_ws_path()
            client_id = f"ha_conga_{self._sn}_{uuid.uuid4().hex[:6]}"

            if hasattr(mqtt, "CallbackAPIVersion"):
                client = mqtt.Client(
                    mqtt.CallbackAPIVersion.VERSION2,
                    client_id=client_id,
                    transport="websockets",
                )
            else:
                client = mqtt.Client(
                    client_id=client_id,
                    transport="websockets",
                )

            client.tls_set()
            client.ws_set_options(path=ws_path)

            client.on_connect = self._on_connect
            client.on_disconnect = self._on_disconnect
            client.on_message = self._on_message

            _LOGGER.info("Connecting to AWS IoT WebSocket for Conga %s", self._sn)
            client.connect(endpoint_host, port=443, keepalive=60)
            client.loop_start()
            self._client = client

            # Schedule token renewal reconnect before the 1-hour credential window ends
            self._refresh_timer = threading.Timer(TOKEN_REFRESH_INTERVAL, self._renew_connection)
            self._refresh_timer.daemon = True
            self._refresh_timer.start()

        except Exception as err:
            _LOGGER.warning("Failed to connect MQTT WebSocket for %s: %s", self._sn, err)
            self._schedule_reconnect()

    def _renew_connection(self) -> None:
        """Disconnect and reconnect with fresh Cognito credentials."""
        if self._stopped:
            return
        _LOGGER.info("Renewing AWS IoT credentials for %s", self._sn)
        if self._client is not None:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception:
                pass
        self._connect()

    def _schedule_reconnect(self) -> None:
        """Schedule a reconnect attempt after an error or unexpected disconnect."""
        if self._stopped:
            return
        self._cancel_timers()
        _LOGGER.debug("Scheduling MQTT reconnect for %s in %ds", self._sn, RECONNECT_DELAY)
        self._reconnect_timer = threading.Timer(RECONNECT_DELAY, self._connect)
        self._reconnect_timer.daemon = True
        self._reconnect_timer.start()

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: Any, rc: Any, *args: Any) -> None:
        """Callback when the client connects to AWS IoT."""
        if (isinstance(rc, int) and rc == 0) or (hasattr(rc, "is_failure") and not rc.is_failure):
            self._connected = True
            _LOGGER.info("AWS IoT WebSocket connected for Conga %s", self._sn)

            # Subscribe to shadow updates
            shadow_topic = f"$aws/things/{self._sn}/shadow/update/accepted"
            service_shadow_topic = f"$aws/things/{self._sn}/shadow/name/service/update/accepted"
            get_accepted_topic = f"$aws/things/{self._sn}/shadow/get/accepted"

            client.subscribe([(shadow_topic, 0), (service_shadow_topic, 0), (get_accepted_topic, 0)])

            # Request initial state
            get_topic = f"$aws/things/{self._sn}/shadow/get"
            client.publish(get_topic, "{}")
        else:
            _LOGGER.warning("MQTT connect failed for %s with code %s", self._sn, rc)
            self._connected = False

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, *args: Any) -> None:
        """Callback when disconnected from AWS IoT."""
        self._connected = False
        _LOGGER.debug("AWS IoT WebSocket disconnected for Conga %s", self._sn)
        if not self._stopped:
            self._schedule_reconnect()

    def _on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        """Callback when an MQTT message arrives."""
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            topic = msg.topic
            _LOGGER.debug("Received MQTT message on %s: %s", topic, payload)

            reported = payload.get("state", {}).get("reported", {})

            if "name/service" in topic:
                # Service shadow contains plans (timeTactics)
                tactics_str = reported.get("getTimeTactics", {}).get("body", {}).get("timeTactics", "{}")
                plan_names = []
                try:
                    tactics_val = json.loads(tactics_str).get("value", [])
                    for tactic in tactics_val:
                        if "planName" in tactic:
                            plan_names.append(tactic["planName"])
                except Exception:
                    pass

                if plan_names:
                    self._dispatch_update(None, plan_names)
            else:
                # Regular shadow contains vacuum operational state and sensor data
                if reported:
                    self._dispatch_update(reported, None)

        except Exception as err:
            _LOGGER.error("Error parsing MQTT payload on %s: %s", msg.topic, err)

    def _dispatch_update(self, status: dict[str, Any] | None, plans: list[str] | None) -> None:
        """Dispatch update to Home Assistant thread safely."""
        if hasattr(self._hass, "loop") and self._hass.loop.is_running():
            self._hass.loop.call_soon_threadsafe(self._on_update_callback, status, plans)
        else:
            self._on_update_callback(status, plans)
