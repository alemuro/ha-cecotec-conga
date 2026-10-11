"""Support for Cecotec Conga sensors."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfArea,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CongaDataUpdateCoordinator
from .entity import CongaEntity

_LOGGER = logging.getLogger(__name__)

SENSORS = [
    {
        "id": "cleanArea",
        "name": "Clean Area",
        "icon": "mdi:vector-square",
        "unit": UnitOfArea.SQUARE_METERS,
    },
    {
        "id": "allArea",
        "name": "Clean All Area",
        "icon": "mdi:vector-square",
        "unit": UnitOfArea.SQUARE_METERS,
    },
    {
        "id": "cleanTime",
        "name": "Clean Time",
        "icon": "mdi:clock-outline",
        "unit": UnitOfTime.MINUTES,
    },
    {
        "id": "allTime",
        "name": "Clean All Time",
        "icon": "mdi:clock-outline",
        "unit": UnitOfTime.MINUTES,
    },
    {
        "id": "elec",
        "name": "Battery",
        "icon": "mdi:battery",
        "unit": PERCENTAGE,
        "device_class": SensorDeviceClass.BATTERY,
    },
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Cecotec Conga sensors from a config entry."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinators: dict[str, CongaDataUpdateCoordinator] = entry_data["coordinators"]
    devices = entry_data["devices"]

    entities: list[CongaVacuumSensor] = []
    for device in devices:
        sn = device["sn"]
        if sn not in coordinators:
            continue
        coordinator = coordinators[sn]
        name = device.get("note_name", f"Conga {sn}")
        for sensor_def in SENSORS:
            entities.append(CongaVacuumSensor(coordinator, sn, name, sensor_def))

    async_add_entities(entities)


class CongaVacuumSensor(CongaEntity, SensorEntity):
    """Implementation of a Cecotec Conga sensor."""

    def __init__(
        self,
        coordinator: CongaDataUpdateCoordinator,
        sn: str,
        device_name: str,
        sensor_def: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, sn, device_name)
        self._attribute_id: str = sensor_def["id"]
        self._attr_name = f"{device_name} {sensor_def['name']}"
        self._attr_unique_id = f"{sn}_{self._attribute_id}"
        self._attr_translation_key = self._attribute_id
        self._attr_native_unit_of_measurement = sensor_def.get("unit")
        self._attr_device_class = sensor_def.get("device_class")
        self._attr_icon = sensor_def.get("icon")

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        status = self.coordinator.data.get("status", {})
        val = status.get(self._attribute_id)
        if val is None:
            return None

        if self._attribute_id in ("cleanTime", "allTime"):
            try:
                return round(float(val) / 60)
            except (ValueError, TypeError):
                return None

        return val
