"""Support for Cecotec Conga vacuum cleaner."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    FAN_SPEED_0,
    FAN_SPEED_1,
    FAN_SPEED_2,
    FAN_SPEED_3,
    WATER_LEVEL_0,
    WATER_LEVEL_1,
    WATER_LEVEL_2,
    WATER_LEVEL_3,
)
from .coordinator import CongaDataUpdateCoordinator
from .entity import CongaEntity

_LOGGER = logging.getLogger(__name__)

SERVICE_START_PLAN = "start_plan"
SERVICE_SET_WATER_LEVEL = "set_water_level"

SUPPORTED_FEATURES = (
    VacuumEntityFeature.TURN_ON
    | VacuumEntityFeature.TURN_OFF
    | VacuumEntityFeature.RETURN_HOME
    | VacuumEntityFeature.START
    | VacuumEntityFeature.FAN_SPEED
    | VacuumEntityFeature.SEND_COMMAND
)

ICON = "mdi:robot-vacuum"

ATTR_SN = "Serial Number"
ATTR_NAME = "Name"
ATTR_PLANS = "plans"
ATTR_WATER_LEVELS = "water_levels"

FAN_SPEEDS = [FAN_SPEED_0, FAN_SPEED_1, FAN_SPEED_2, FAN_SPEED_3]
WATER_LEVELS = [WATER_LEVEL_0, WATER_LEVEL_1, WATER_LEVEL_2, WATER_LEVEL_3]

# Conga 5290 AWS IoT shadow eventCode values (empirically confirmed).
# The "mode" field reports the selected work mode (e.g. "sweep"), which can
# be residual when the vacuum is back at the dock. The "eventCode" field is
# the reliable indicator of the actual operational state.
EVENT_CODE_CLEANING = 6023
EVENT_CODE_CHARGING = 6096


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Cecotec Conga vacuum from a config entry."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinators: dict[str, CongaDataUpdateCoordinator] = entry_data["coordinators"]
    devices = entry_data["devices"]

    entities = [
        CongaVacuum(
            coordinators[device["sn"]],
            device["sn"],
            device.get("note_name", f"Conga {device['sn']}"),
        )
        for device in devices
        if device["sn"] in coordinators
    ]

    async_add_entities(entities)

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_START_PLAN,
        {
            vol.Required("plan"): str,
        },
        "async_start_plan",
    )
    platform.async_register_entity_service(
        SERVICE_SET_WATER_LEVEL,
        {
            vol.Required("water_level"): vol.In(WATER_LEVELS),
        },
        "async_set_water_level",
    )


class CongaVacuum(CongaEntity, StateVacuumEntity):
    """Implementation of a Cecotec Conga Vacuum."""

    _attr_icon = ICON

    def __init__(
        self,
        coordinator: CongaDataUpdateCoordinator,
        sn: str,
        name: str,
    ) -> None:
        """Initialize the vacuum."""
        super().__init__(coordinator, sn, name)
        self._attr_name = name
        self._attr_unique_id = sn
        self._attr_supported_features = SUPPORTED_FEATURES
        self._fan_speeds = FAN_SPEEDS
        self._fan_speed = FAN_SPEED_1

    @property
    def _status(self) -> dict[str, Any]:
        """Return the reported shadow status dictionary."""
        return self.coordinator.data.get("status", {}) if self.coordinator.data else {}

    @property
    def _mode(self) -> str | None:
        """Return current mode."""
        return self._status.get("mode")

    @property
    def _event_code(self) -> int | None:
        """Return operational event code."""
        return self._status.get("eventCode")

    @property
    def activity(self) -> VacuumActivity | None:
        """Return the vacuum activity based on mode and eventCode."""
        mode = self._mode
        if mode == "sweep":
            if self._event_code == EVENT_CODE_CHARGING:
                return VacuumActivity.DOCKED
            return VacuumActivity.CLEANING
        if mode in ("backcharge", "DustCenterWorking"):
            return VacuumActivity.RETURNING
        if mode in ("fullcharge", "charge"):
            return VacuumActivity.DOCKED
        if mode == "pause":
            return VacuumActivity.PAUSED
        if mode in ("idle", "shutdown"):
            return VacuumActivity.IDLE
        if mode is None:
            return None

        _LOGGER.warning("Unknown status mode: %s", mode)
        return VacuumActivity.ERROR

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return device-specific attributes."""
        plans = self.coordinator.data.get("plans", []) if self.coordinator.data else []
        return {
            ATTR_SN: self._sn,
            ATTR_NAME: self._device_name,
            ATTR_PLANS: ",".join(plans),
            ATTR_WATER_LEVELS: ",".join(WATER_LEVELS),
        }

    @property
    def fan_speed(self) -> str:
        """Return the fan speed of the vacuum cleaner."""
        work_noisy = self._status.get("workNoisy")
        if isinstance(work_noisy, int) and 0 <= work_noisy < len(self._fan_speeds):
            return self._fan_speeds[work_noisy]
        return self._fan_speed

    @property
    def fan_speed_list(self) -> list[str]:
        """Get the list of available fan speed steps."""
        return self._fan_speeds

    async def async_start(self) -> None:
        """Start or resume the cleaning task."""
        await self.async_turn_on()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the vacuum on."""
        fan_idx = self._fan_speeds.index(self.fan_speed)
        await self.hass.async_add_executor_job(
            self._conga_client.start, self._sn, fan_idx
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the vacuum."""
        await self.async_return_to_base()

    async def async_return_to_base(self, **kwargs: Any) -> None:
        """Ask vacuum to return to dock."""
        await self.hass.async_add_executor_job(
            self._conga_client.home, self._sn
        )
        await self.coordinator.async_request_refresh()

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:
        """Set fan speed."""
        if fan_speed in self._fan_speeds:
            _LOGGER.info("Setting fan speed to %s on %s", fan_speed, self._sn)
            fan_idx = self._fan_speeds.index(fan_speed)
            await self.hass.async_add_executor_job(
                self._conga_client.set_fan_speed, self._sn, fan_idx
            )
            self._fan_speed = fan_speed
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Invalid fan speed: %s. Allowed: %s", fan_speed, self._fan_speeds)

    async def async_send_command(
        self,
        command: str,
        params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Send raw command asynchronously."""
        _LOGGER.info("Sending command %s with params %s to %s", command, params, self._sn)
        params = params or {}

        if command == "start_plan":
            plan = params.get("plan")
            plans = self.coordinator.data.get("plans", []) if self.coordinator.data else []
            if plan in plans:
                await self.hass.async_add_executor_job(
                    self._conga_client.start_plan, self._sn, plan
                )
                await self.coordinator.async_request_refresh()
            else:
                _LOGGER.error("Plan %s not found. Allowed plans: %s", plan, plans)
        elif command == "set_water_level":
            water_level = params.get("water_level")
            if water_level in WATER_LEVELS:
                level_idx = WATER_LEVELS.index(water_level)
                await self.hass.async_add_executor_job(
                    self._conga_client.set_water_level, self._sn, level_idx
                )
                await self.coordinator.async_request_refresh()
            else:
                _LOGGER.error(
                    "Invalid water level: %s. Allowed water levels: %s",
                    water_level,
                    WATER_LEVELS,
                )
        else:
            _LOGGER.error("Unknown command %s", command)

    async def async_start_plan(self, plan: str) -> None:
        """Entity service to start a specific plan."""
        await self.async_send_command("start_plan", {"plan": plan})

    async def async_set_water_level(self, water_level: str) -> None:
        """Entity service to set water level."""
        await self.async_send_command("set_water_level", {"water_level": water_level})

