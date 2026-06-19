from __future__ import annotations

from datetime import timedelta
import logging

from requests import HTTPError

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumEntityFeature,
    VacuumActivity,
)
from homeassistant.util import Throttle
from homeassistant.helpers.entity import DeviceInfo

from .utils import build_device_info
from .button import CongaEntity

from .const import (
    BRAND,
    DOMAIN,
    MODEL,
    FAN_SPEED_0,
    FAN_SPEED_1,
    FAN_SPEED_2,
    FAN_SPEED_3,
    WATER_LEVEL_0,
    WATER_LEVEL_1,
    WATER_LEVEL_2,
    WATER_LEVEL_3,
)

SUPPORTED_FEATURES = (
    VacuumEntityFeature.TURN_ON
    | VacuumEntityFeature.TURN_OFF
    | VacuumEntityFeature.RETURN_HOME
    | VacuumEntityFeature.START
    | VacuumEntityFeature.FAN_SPEED
    | VacuumEntityFeature.SEND_COMMAND
)

_LOGGER = logging.getLogger(__name__)

ICON = "mdi:robot-vacuum"

ATTR_SN = "Serial Number"
ATTR_NAME = "Name"
ATTR_PLANS = "plans"
ATTR_WATER_LEVELS = "water_levels"

FAN_SPEEDS = [FAN_SPEED_0, FAN_SPEED_1, FAN_SPEED_2, FAN_SPEED_3]

WATER_LEVELS = [WATER_LEVEL_0, WATER_LEVEL_1, WATER_LEVEL_2, WATER_LEVEL_3]

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=60)

# Conga 5290 AWS IoT shadow eventCode values (empirically confirmed).
# The "mode" field reports the selected work mode (e.g. "sweep"), which can
# be residual when the vacuum is back at the dock. The "eventCode" field is
# the reliable indicator of the actual operational state.
EVENT_CODE_CLEANING = 6023
EVENT_CODE_CHARGING = 6096


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Cecotec Conga sensor from a config entry."""
    entities = []

    devices = hass.data[DOMAIN][config_entry.entry_id]["devices"]

    for device in devices:
        conga_data = hass.data[DOMAIN][config_entry.entry_id]
        entities.append(
            CongaVacuum(
                conga_data,
                device["note_name"],
                device["sn"],
            )
        )

    hass.data[DOMAIN][config_entry.entry_id]["entities"] = entities

    async_add_entities(entities, update_before_add=True)


class CongaVacuum(StateVacuumEntity, CongaEntity):
    """Implementation of a Cecotec Conga Vacuum."""

    def __init__(self, conga_data, name, sn):
        """Initialize the vacuum."""
        self._conga_data = conga_data
        self._conga_client = conga_data["controller"]
        self._name = name
        self._sn = sn
        self._state = "loading"
        self._event_code = None
        self._state_all = {}
        self._plans = []
        self._water_levels = WATER_LEVELS
        self._water_level = WATER_LEVEL_1
        self._fan_speeds = FAN_SPEEDS
        self._fan_speed = FAN_SPEED_1
        self._supported_features = SUPPORTED_FEATURES
        CongaEntity.__init__(self, conga_data, name, sn)
        StateVacuumEntity.__init__(self)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def brand(self):
        return BRAND

    @property
    def model(self):
        return MODEL

    @property
    def device_info(self) -> DeviceInfo:
        return build_device_info(self._name, self._sn)

    @property
    def icon(self):
        """Return the icon for the frontend."""
        return ICON

    @property
    def unique_id(self):
        """Return a unique, HASS-friendly identifier for this entity."""
        return self._sn

    @property
    def activity(self) -> VacuumActivity | None:
        """Return the vacuum activity.

        The Conga 5290 reports ``mode`` as the selected work mode, not the
        operational state. When the vacuum returns to the dock the mode stays
        at ``"sweep"`` (residual). We use ``eventCode`` to disambiguate:
        6023 = actively cleaning, 6096 = docked/charging.
        """
        if self._state == "sweep":
            if self._event_code == EVENT_CODE_CHARGING:
                return VacuumActivity.DOCKED
            return VacuumActivity.CLEANING
        elif self._state == "backcharge" or self._state == "DustCenterWorking":
            return VacuumActivity.RETURNING
        elif self._state == "fullcharge" or self._state == "charge":
            return VacuumActivity.DOCKED
        elif self._state == "pause":
            return VacuumActivity.PAUSED
        elif self._state == "idle":
            return VacuumActivity.IDLE
        elif self._state == "shutdown":
            return VacuumActivity.IDLE
        else:
            _LOGGER.warning(f"Unknown status: {self._state}")
            return VacuumActivity.ERROR

    @property
    def extra_state_attributes(self):
        """Return some attributes."""
        return {
            ATTR_SN: self._sn,
            ATTR_NAME: self._name,
            ATTR_PLANS: ",".join(self._plans),
            ATTR_WATER_LEVELS: ",".join(self._water_levels),
        }

    @property
    def fan_speed(self):
        """Return the fan speed of the vacuum cleaner."""
        return self._fan_speed

    @property
    def fan_speed_list(self):
        """Get the list of available fan speed steps of the vacuum cleaner."""
        return self._fan_speeds

    @property
    def supported_features(self):
        """Flag supported features."""
        return self._supported_features

    def start(self):
        """Start or resume the cleaning task."""
        self.turn_on()

    def turn_on(self, **kwargs):
        """Turn the vacuum on."""
        self._conga_client.start(self._sn, self._fan_speeds.index(self._fan_speed))
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn off the vacuum."""
        self.return_to_base()

    def return_to_base(self, **kwargs):
        """Ask vacuum to go home."""
        self._conga_client.home(self._sn)
        self.schedule_update_ha_state()

    def set_fan_speed(self, fan_speed, **kwargs):
        """Set fan speed."""

        _LOGGER.info(f"Setting fan speed to {fan_speed}")

        self._conga_client.set_fan_speed(self._sn, self._fan_speeds.index(fan_speed))
        self._fan_speed = fan_speed
        self.schedule_update_ha_state()

    def send_command(self, command, params=None, **kwargs):
        """Send raw command."""
        _LOGGER.info(f"Sending command {command} with params {params}")

        if command == "start_plan":
            plan = params["plan"]
            if plan in self._plans:
                self._conga_client.start_plan(self._sn, plan)
                self.schedule_update_ha_state()
            else:
                _LOGGER.error(f"Plan {plan} not found. Allowed plans: {self._plans}")
        elif command == "set_water_level":
            water_level = params["water_level"]
            if water_level in self._water_levels:
                self._conga_client.set_water_level(
                    self._sn, self._water_levels.index(water_level)
                )
                self.schedule_update_ha_state()
            else:
                _LOGGER.error(
                    f"Invalid water level: {water_level}. Allowed water levels: {self._water_levels}"
                )
        else:
            _LOGGER.error(f"Unknown command {command}")

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the next bus information."""
        try:
            self._conga_client.update_shadows(self._sn)
            self._state_all = self._conga_client.get_status()

            self._state = self._state_all["mode"]
            self._event_code = self._state_all.get("eventCode")
            self._plans = self._conga_client.list_plans()
        except HTTPError:
            _LOGGER.error("Unable to fetch data from API")
