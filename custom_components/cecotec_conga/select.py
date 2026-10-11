"""Support for Cecotec Conga select entities."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    WATER_LEVEL_0,
    WATER_LEVEL_1,
    WATER_LEVEL_2,
    WATER_LEVEL_3,
)
from .coordinator import CongaDataUpdateCoordinator
from .entity import CongaEntity

_LOGGER = logging.getLogger(__name__)

WATER_LEVELS = [WATER_LEVEL_0, WATER_LEVEL_1, WATER_LEVEL_2, WATER_LEVEL_3]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Cecotec Conga select entities from a config entry."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinators: dict[str, CongaDataUpdateCoordinator] = entry_data["coordinators"]
    devices = entry_data["devices"]

    entities: list[CongaWaterLevelSelect] = []
    for device in devices:
        sn = device["sn"]
        if sn not in coordinators:
            continue
        coordinator = coordinators[sn]
        name = device.get("note_name", f"Conga {sn}")
        entities.append(CongaWaterLevelSelect(coordinator, sn, name))

    async_add_entities(entities)


class CongaWaterLevelSelect(CongaEntity, SelectEntity):
    """Select entity for Conga water scrubbing level."""

    _attr_icon = "mdi:water"
    _attr_options = WATER_LEVELS
    _attr_translation_key = "water_level"

    def __init__(
        self,
        coordinator: CongaDataUpdateCoordinator,
        sn: str,
        device_name: str,
    ) -> None:
        """Initialize the water level select entity."""
        super().__init__(coordinator, sn, device_name)
        self._attr_name = f"{device_name} Water Level"
        self._attr_unique_id = f"{sn}_water_level"

    @property
    def current_option(self) -> str | None:
        """Return the current selected water level."""
        if not self.coordinator.data:
            return None
        status = self.coordinator.data.get("status", {})
        val = status.get("water")

        if isinstance(val, int) and 0 <= val < len(WATER_LEVELS):
            return WATER_LEVELS[val]
        if isinstance(val, str) and val in WATER_LEVELS:
            return val
        return None

    async def async_select_option(self, option: str) -> None:
        """Change the water scrub level."""
        if option not in WATER_LEVELS:
            _LOGGER.error("Invalid water level option: %s", option)
            return

        level_idx = WATER_LEVELS.index(option)
        _LOGGER.info("Setting water level to %s (%d) for %s", option, level_idx, self._sn)
        await self.hass.async_add_executor_job(
            self._conga_client.set_water_level, self._sn, level_idx
        )
        await self.coordinator.async_request_refresh()
