"""DataUpdateCoordinator for Cecotec Conga with hybrid WebSocket Push and polling fallback."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .conga import Conga
from .mqtt_client import CongaMqttClient

_LOGGER = logging.getLogger(__name__)

# Polling fallback interval: with real-time push active, a safety check every 15 minutes is plenty.
SCAN_INTERVAL = timedelta(minutes=15)


class CongaDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Cecotec Conga data with real-time push."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: Conga,
        sn: str,
        device_name: str,
    ) -> None:
        """Initialize coordinator."""
        self.client = client
        self.sn = sn
        self.device_name = device_name

        self.mqtt_client = CongaMqttClient(
            hass, client, sn, self._async_handle_mqtt_update
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"Cecotec Conga {device_name}",
            update_interval=SCAN_INTERVAL,
        )

    def _async_handle_mqtt_update(
        self,
        status: dict[str, Any] | None,
        plans: list[str] | None,
    ) -> None:
        """Handle incoming real-time MQTT message from AWS IoT shadow."""
        if not self.data:
            self.data = {"status": {}, "plans": []}

        if status:
            _LOGGER.debug("Real-time push update for %s: %s", self.sn, status)
            # Update reported shadow dictionary with latest keys
            new_status = dict(self.data.get("status", {}))
            new_status.update(status)
            self.data["status"] = new_status

        if plans:
            _LOGGER.debug("Real-time plans update for %s: %s", self.sn, plans)
            self.data["plans"] = plans

        self.async_set_updated_data(self.data)

    async def async_start_mqtt(self) -> None:
        """Start the background MQTT WebSocket client."""
        await self.hass.async_add_executor_job(self.mqtt_client.start)

    async def async_stop_mqtt(self) -> None:
        """Stop the background MQTT WebSocket client."""
        await self.hass.async_add_executor_job(self.mqtt_client.stop)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from AWS IoT shadow and service shadow (polling fallback)."""
        try:
            shadow = await self.hass.async_add_executor_job(
                self.client.update_shadows, self.sn
            )
            plans = await self.hass.async_add_executor_job(
                self.client.list_plans, self.sn
            )
            return {
                "status": shadow,
                "plans": plans,
            }
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Cecotec API for {self.sn}: {err}") from err
