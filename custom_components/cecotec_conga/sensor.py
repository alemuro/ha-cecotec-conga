from __future__ import annotations

from datetime import timedelta
import logging

from requests import HTTPError

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import Throttle

from . import Conga

_LOGGER = logging.getLogger(__name__)

ICON = "mdi:robot-vacuum"

ATTR_SN = "Serial Number"
ATTR_NAME = "Name"

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=60)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensors."""

    conga_client = Conga(config['username'], config['password'])
    sensors = []
    for device in conga_client.list_vacuums():
        sensors.append(CongaSensor(
            conga_client,
            device["note_name"],
            device["sn"]
        ))

    add_entities(sensors, True)


class CongaSensor(SensorEntity):
    """Implementation of a Cecotec Conga Sensor."""

    def __init__(self, conga_client, name, sn):
        """Initialize the sensor."""
        self._conga_client = conga_client
        self._name = name
        self._sn = sn
        self._state = "loading"

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        """Return the icon for the frontend."""
        return ICON

    @property
    def unique_id(self):
        """Return a unique, HASS-friendly identifier for this entity."""
        return self._sn

    @property
    def native_value(self):
        """Return the next departure time."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the last update."""
        return {
            ATTR_SN: self._sn,
            ATTR_NAME: self._name,
        }

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the next bus information."""
        try:
            response = self._conga_client.status(self._sn)
            _LOGGER.debug(response)
            self._state = response["state"]["reported"]["mode"]
        except HTTPError:
            _LOGGER.error(
                "Unable to fetch data from API"
            )
