"""Support for Cecotec Conga binary sensors."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CongaDataUpdateCoordinator
from .entity import CongaEntity

_LOGGER = logging.getLogger(__name__)

BINARY_SENSORS = [
    {
        "id": "connected",
        "name": "Connected",
        "device_class": BinarySensorDeviceClass.CONNECTIVITY,
    },
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Cecotec Conga binary sensors from a config entry."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinators: dict[str, CongaDataUpdateCoordinator] = entry_data["coordinators"]
    devices = entry_data["devices"]

    entities: list[CongaVacuumBinarySensor] = []
    for device in devices:
        sn = device["sn"]
        if sn not in coordinators:
            continue
        coordinator = coordinators[sn]
        name = device.get("note_name", f"Conga {sn}")
        for sensor_def in BINARY_SENSORS:
            entities.append(CongaVacuumBinarySensor(coordinator, sn, name, sensor_def))

    async_add_entities(entities)


class CongaVacuumBinarySensor(CongaEntity, BinarySensorEntity):
    """Implementation of a Cecotec Conga binary sensor."""

    def __init__(
        self,
        coordinator: CongaDataUpdateCoordinator,
        sn: str,
        device_name: str,
        sensor_def: dict[str, Any],
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, sn, device_name)
        self._attribute_id: str = sensor_def["id"]
        self._attr_name = f"{device_name} {sensor_def['name']}"
        self._attr_unique_id = f"{sn}_{self._attribute_id}"
        self._attr_device_class = sensor_def.get("device_class")
        self._attr_translation_key = self._attribute_id

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if not self.coordinator.data:
            return None
        status = self.coordinator.data.get("status", {})
        val = status.get(self._attribute_id)
        if val is None:
            return None
        return bool(val)
