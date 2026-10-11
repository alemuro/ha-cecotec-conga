"""Support for Cecotec Conga vacuum cleaners."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .conga import Conga
from .const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
)
from .coordinator import CongaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["vacuum", "button", "sensor", "binary_sensor", "select"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Cecotec Conga based on a config entry."""
    _LOGGER.info("Setting up Cecotec Conga integration")
    hass.data.setdefault(DOMAIN, {})

    conga_client = Conga(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])

    devices = entry.data.get("devices", [])
    coordinators: dict[str, CongaDataUpdateCoordinator] = {}

    for device in devices:
        sn = device["sn"]
        name = device.get("note_name", f"Conga {sn}")
        coordinator = CongaDataUpdateCoordinator(hass, conga_client, sn, name)
        await coordinator.async_config_entry_first_refresh()
        await coordinator.async_start_mqtt()
        coordinators[sn] = coordinator

    # Keep backward-compatibility keys for any components expecting them
    first_sn = devices[0]["sn"] if devices else None
    first_coordinator = coordinators.get(first_sn) if first_sn else None
    first_plans = first_coordinator.data.get("plans", []) if first_coordinator else []

    hass.data[DOMAIN][entry.entry_id] = {
        "controller": conga_client,
        "devices": devices,
        "coordinators": coordinators,
        "plans": first_plans,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Cecotec Conga config entry."""
    _LOGGER.info("Unloading Cecotec Conga integration")

    entry_data = hass.data[DOMAIN].get(entry.entry_id, {})
    coordinators: dict[str, CongaDataUpdateCoordinator] = entry_data.get("coordinators", {})
    for coordinator in coordinators.values():
        await coordinator.async_stop_mqtt()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

