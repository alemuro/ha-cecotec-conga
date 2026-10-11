"""Base entity for Cecotec Conga integration."""
from __future__ import annotations

import logging

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BRAND, MODEL
from .coordinator import CongaDataUpdateCoordinator
from .utils import build_device_info

_LOGGER = logging.getLogger(__name__)


class CongaEntity(CoordinatorEntity):
    """Defines a base Cecotec Conga entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CongaDataUpdateCoordinator,
        sn: str,
        device_name: str,
    ) -> None:
        """Initialize the base entity."""
        super().__init__(coordinator)
        self._sn = sn
        self._device_name = device_name
        self._conga_client = coordinator.client

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this Cecotec Conga."""
        return build_device_info(self._device_name, self._sn)

    @property
    def name(self) -> str | None:
        """Return the name of the entity."""
        return self._attr_name

    @property
    def unique_id(self) -> str | None:
        """Return the unique ID of the entity."""
        return self._attr_unique_id

    @property
    def brand(self) -> str:
        """Return brand name."""
        return BRAND

    @property
    def model(self) -> str:
        """Return model name."""
        return MODEL

