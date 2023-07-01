import logging
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.entity import DeviceInfo

from .conga import Conga
from .const import (
    CONF_USERNAME,
    CONF_PASSWORD,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry):
    """Set up Cecotec Conga sensors based on a config entry."""
    _LOGGER.info("Setting up Cecotec Conga integration")
    hass.data.setdefault(DOMAIN, {})

    conga_client = Conga(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    await hass.async_add_executor_job(
        conga_client.update_shadows, entry.data["devices"][0]["sn"]
    )
    plans = await hass.async_add_executor_job(conga_client.list_plans)

    hass.data[DOMAIN][entry.entry_id] = {
        "controller": conga_client,
        "devices": entry.data["devices"],
        "plans": plans,
        "lastTimeSync": 0,
        "lastFirmwareCheck": 0,
        "latestFirmwareVersion": False,
        "entities": [],
        "name": "test",
    }

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "vacuum")
    )
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "button")
    )
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "binary_sensor")
    )
    return True
