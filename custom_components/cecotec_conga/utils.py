import logging
from homeassistant.helpers.entity import DeviceInfo

from .const import (
    BRAND,
    DOMAIN,
    MODEL,
)

_LOGGER = logging.getLogger(__name__)


def build_device_info(name, sn) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, sn)},
        name=name,
        manufacturer=BRAND,
        model=MODEL,
        sw_version="Not provided",
    )
