from datetime import timedelta
import logging
from homeassistant.util import Throttle
from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.const import (
    AREA_SQUARE_METERS,
    UnitOfTime,    
)
from requests import HTTPError

from .button import CongaEntity
from .utils import build_device_info
from .const import (
    BRAND,
    CONF_DEVICES,
    DOMAIN,
    MODEL,
)

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=60)

_LOGGER = logging.getLogger(__name__)

sensors = [
    {
        "id": "cleanArea",
        "name": "Clean Area",
        "icon": "mdi:vector-square",
        "unit": AREA_SQUARE_METERS,
    },
    {
        "id": "allArea",
        "name": "Clean All Area",
        "icon": "mdi:vector-square",
        "unit": AREA_SQUARE_METERS,
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
]

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Cecotec Conga sensor from a config entry."""
    entities = []

    devices = hass.data[DOMAIN][config_entry.entry_id]["devices"]

    for device in devices:
        conga_data = hass.data[DOMAIN][config_entry.entry_id]
        for sensor in sensors:
            sensor_entity = CongaVacuumPlanButton(
                hass, conga_data, device["sn"], device["note_name"], sensor
            )
            entities.append(sensor_entity)

    async_add_entities(entities, update_before_add=True)



class CongaVacuumPlanButton(SensorEntity, CongaEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        conga_data: dict,
        sn: str,
        device_name: str,
        sensor: dict,
    ):
        self._hass = hass
        self._conga_data = conga_data
        self._conga_client = conga_data["controller"]
        self._device_name = device_name
        self._unit_of_measurement = sensor['unit']
        self._name = f"{self._device_name} {sensor['name']}"
        self._icon = sensor['icon']
        self._sn = sn
        self._state = None
        self._attribute_id = sensor['id']
        self._unique_id = f"{self._device_name}_{sensor['id']}"
        CongaEntity.__init__(self, conga_data, device_name, sn)
        SensorEntity.__init__(self)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self) -> str:
        return self._unique_id

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement
    
    @property
    def native_value(self):
        return self._state

    @property
    def icon(self) -> str | None:
        """Icon of the entity."""
        return self._icon

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the next bus information."""
        try:
            state_all = self._conga_client.get_status()

            if self._attribute_id in ["cleanTime", "allTime"]:
                self._state = round(state_all[self._attribute_id] / 60)
            else:
                self._state = state_all[self._attribute_id]

        except HTTPError:
            _LOGGER.error("Unable to fetch data from API")
