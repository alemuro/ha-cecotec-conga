"""Support for Cecotec Conga plan buttons."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CongaDataUpdateCoordinator
from .entity import CongaEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Cecotec Conga plan buttons from a config entry."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinators: dict[str, CongaDataUpdateCoordinator] = entry_data["coordinators"]
    devices = entry_data["devices"]

    entities: list[CongaVacuumPlanButton] = []
    for device in devices:
        sn = device["sn"]
        if sn not in coordinators:
            continue
        coordinator = coordinators[sn]
        name = device.get("note_name", f"Conga {sn}")
        plans = coordinator.data.get("plans", []) if coordinator.data else []

        for plan in plans:
            entities.append(
                CongaVacuumPlanButton(
                    coordinator,
                    sn,
                    name,
                    plan,
                )
            )

    async_add_entities(entities)


class CongaVacuumPlanButton(CongaEntity, ButtonEntity):
    """Implementation of a Cecotec Conga plan button."""

    def __init__(
        self,
        coordinator: CongaDataUpdateCoordinator,
        sn: str,
        device_name: str,
        plan_name: str,
    ) -> None:
        """Initialize the plan button."""
        super().__init__(coordinator, sn, device_name)
        self._plan_name = plan_name
        self._attr_name = f"{device_name} Start {plan_name}"
        self._attr_unique_id = f"{sn}_plan_{plan_name}"
        self._attr_icon = "mdi:map-marker-path"

    async def async_press(self) -> None:
        """Execute plan button press asynchronously."""
        _LOGGER.info("Running plan %s on %s", self._plan_name, self._device_name)
        await self.hass.async_add_executor_job(
            self._conga_client.start_plan, self._sn, self._plan_name
        )
        await self.coordinator.async_request_refresh()
