import logging
from homeassistant.core import HomeAssistant
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import DeviceInfo, Entity

from .utils import build_device_info
from .const import (
    BRAND,
    CONF_DEVICES,
    DOMAIN,
    MODEL,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Cecotec Conga sensor from a config entry."""
    entities = []

    devices = hass.data[DOMAIN][config_entry.entry_id]["devices"]
    plans = hass.data[DOMAIN][config_entry.entry_id]["plans"]

    for device in devices:
        for plan in plans:
            conga_data = hass.data[DOMAIN][config_entry.entry_id]
            button = CongaVacuumPlanButton(
                hass, conga_data, plan, device["sn"], device["note_name"]
            )
            entities.append(button)
            # hass.data[DOMAIN][config_entry.entry_id]["entities"].append(button)

    async_add_entities(entities, update_before_add=True)


class CongaEntity(Entity):
    def __init__(
        self,
        conga_data: dict,
        device_name: str,
        sn: str,
    ):
        self._enabled = False
        self._device_name = device_name
        self._conga_data = conga_data
        self._conga_client = conga_data["controller"]
        self._sn = sn

    @property
    def device_info(self) -> DeviceInfo:
        return build_device_info(self._device_name, self._sn)

    @property
    def model(self):
        return MODEL

    @property
    def brand(self):
        return BRAND

    async def async_added_to_hass(self) -> None:
        self._enabled = True

    async def async_will_remove_from_hass(self) -> None:
        self._enabled = False


class CongaVacuumPlanButton(ButtonEntity, CongaEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        conga_data: dict,
        plan_name: str,
        sn: str,
        device_name: str,
    ):
        self._hass = hass
        self._conga_data = conga_data
        self._conga_client = conga_data["controller"]
        self._plan_name = plan_name
        self._device_name = device_name
        self._name = f"{self._device_name} Start {self._plan_name}"
        self._sn = sn
        self._unique_id = f"{self._device_name}_{self._plan_name}"
        CongaEntity.__init__(self, conga_data, device_name, sn)
        ButtonEntity.__init__(self)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self) -> str:
        return self._unique_id

    async def async_press(self) -> None:
        _LOGGER.info(f"Running plan {self._plan_name} on {self._device_name}")
        await self._hass.async_add_executor_job(
            self._conga_client.start_plan, self._sn, self._plan_name
        )
