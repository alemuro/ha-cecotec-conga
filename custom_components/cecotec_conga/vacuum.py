from __future__ import annotations

from datetime import timedelta
import logging

from requests import HTTPError

from homeassistant.components.vacuum import (
    STATE_CLEANING,
    STATE_DOCKED,
    STATE_RETURNING,
    STATE_ERROR,
    StateVacuumEntity,
    VacuumEntityFeature,
)
from homeassistant.util import Throttle

from . import Conga

from .const import (
    CONF_DEVICES,
    CONF_USERNAME,
    CONF_PASSWORD,
)

SUPPORTED_FEATURES = (
    VacuumEntityFeature.TURN_ON
    | VacuumEntityFeature.TURN_OFF
    | VacuumEntityFeature.RETURN_HOME
    | VacuumEntityFeature.START
)

_LOGGER = logging.getLogger(__name__)

ICON = "mdi:robot-vacuum"

ATTR_SN = "Serial Number"
ATTR_NAME = "Name"

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=60)

#modes: ["Off", "Eco", "Normal", "Turbo"]


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the TMB sensor from a config entry."""
    entities = []

    conga_client = Conga(
        config_entry.data[CONF_USERNAME], config_entry.data[CONF_PASSWORD])

    for device in config_entry.data[CONF_DEVICES]:
        entities.append(CongaVacuum(
            conga_client,
            device["note_name"],
            device["sn"]
        ))

    async_add_entities(entities, update_before_add=True)


class CongaVacuum(StateVacuumEntity):
    """Implementation of a Cecotec Conga Vacuum."""

    def __init__(self, conga_client, name, sn):
        """Initialize the vacuum."""
        self._conga_client = conga_client
        self._name = name
        self._sn = sn
        self._state = "loading"
        self._supported_features = SUPPORTED_FEATURES

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
    def state(self):
        """Return the vacuum status."""
        if self._state == "sweep":
            return STATE_CLEANING
        elif self._state == "backcharge":
            return STATE_RETURNING
        elif self._state == "fullcharge" or self._state == "charge":
            return STATE_DOCKED
        else:
            _LOGGER.warn(f"Unknown status: {self._state}")
            return STATE_ERROR

    @property
    def extra_state_attributes(self):
        """Return some attributes."""
        return {
            ATTR_SN: self._sn,
            ATTR_NAME: self._name,
        }

    @property
    def supported_features(self):
        """Flag supported features."""
        return self._supported_features

    def start(self):
        """Start or resume the cleaning task."""
        self.turn_on()

    def turn_on(self, **kwargs):
        """Turn the vacuum on."""
        self._conga_client.start(self._sn)
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn off the vacuum."""
        self.return_to_base()

    def return_to_base(self, **kwargs):
        """Ask vacuum to go home."""
        self._conga_client.home(self._sn)
        self.schedule_update_ha_state()

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the next bus information."""
        try:
            response = self._conga_client.status(self._sn)
            self._state = response["state"]["reported"]["mode"]
        except HTTPError:
            _LOGGER.error(
                "Unable to fetch data from API"
            )
