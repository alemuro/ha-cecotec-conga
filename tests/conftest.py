"""Test fixtures and mock modules for Home Assistant."""
import sys
from enum import Enum, IntFlag
from unittest.mock import MagicMock

if "voluptuous" not in sys.modules:
    vol = MagicMock()
    vol.Required = lambda key, *args, **kwargs: key
    vol.Optional = lambda key, *args, **kwargs: key
    vol.In = lambda container: container
    vol.Schema = lambda schema: schema
    sys.modules["voluptuous"] = vol

import types

# Provide lightweight mock of homeassistant if not installed in current environment
if "homeassistant" not in sys.modules:
    def create_pkg(name):
        mod = types.ModuleType(name)
        mod.__path__ = []
        sys.modules[name] = mod
        return mod

    ha = create_pkg("homeassistant")
    ha_components = create_pkg("homeassistant.components")
    ha_helpers = create_pkg("homeassistant.helpers")

    ha_core = types.ModuleType("homeassistant.core")
    ha_core.HomeAssistant = MagicMock
    sys.modules["homeassistant.core"] = ha_core
    ha.core = ha_core

    class ConfigFlow:
        def __init_subclass__(cls, domain=None, **kwargs):
            super().__init_subclass__(**kwargs)
            cls.DOMAIN = domain

    ha_config_entries = types.ModuleType("homeassistant.config_entries")
    ha_config_entries.ConfigEntry = MagicMock
    ha_config_entries.ConfigFlow = ConfigFlow
    sys.modules["homeassistant.config_entries"] = ha_config_entries
    ha.config_entries = ha_config_entries

    ha_flow = types.ModuleType("homeassistant.data_entry_flow")
    ha_flow.FlowResult = dict
    sys.modules["homeassistant.data_entry_flow"] = ha_flow
    ha.data_entry_flow = ha_flow

    sys.modules["homeassistant.exceptions"] = types.ModuleType("homeassistant.exceptions")

    class VacuumActivity(str, Enum):
        CLEANING = "cleaning"
        DOCKED = "docked"
        IDLE = "idle"
        PAUSED = "paused"
        RETURNING = "returning"
        ERROR = "error"

    class VacuumEntityFeature(IntFlag):
        TURN_ON = 1
        TURN_OFF = 2
        PAUSE = 4
        STOP = 8
        RETURN_HOME = 16
        FAN_SPEED = 32
        BATTERY = 64
        CLEAN_SPOT = 128
        MAP = 256
        STATE = 512
        START = 1024
        LOCATE = 2048
        SEND_COMMAND = 4096

    class StateVacuumEntity:
        def __init__(self):
            pass

    ha_vacuum = MagicMock()
    ha_vacuum.VacuumActivity = VacuumActivity
    ha_vacuum.VacuumEntityFeature = VacuumEntityFeature
    ha_vacuum.StateVacuumEntity = StateVacuumEntity
    sys.modules["homeassistant.components.vacuum"] = ha_vacuum

    class SensorDeviceClass(str, Enum):
        BATTERY = "battery"

    class SensorEntity:
        def __init__(self):
            pass

    ha_sensor = MagicMock()
    ha_sensor.SensorDeviceClass = SensorDeviceClass
    ha_sensor.SensorEntity = SensorEntity
    sys.modules["homeassistant.components.sensor"] = ha_sensor

    class BinarySensorDeviceClass(str, Enum):
        CONNECTIVITY = "connectivity"

    class BinarySensorEntity:
        def __init__(self):
            pass

    ha_bin_sensor = MagicMock()
    ha_bin_sensor.BinarySensorDeviceClass = BinarySensorDeviceClass
    ha_bin_sensor.BinarySensorEntity = BinarySensorEntity
    sys.modules["homeassistant.components.binary_sensor"] = ha_bin_sensor

    class ButtonEntity:
        def __init__(self):
            pass

    ha_button = MagicMock()
    ha_button.ButtonEntity = ButtonEntity
    sys.modules["homeassistant.components.button"] = ha_button

    class SelectEntity:
        def __init__(self):
            pass

    ha_select = MagicMock()
    ha_select.SelectEntity = SelectEntity
    sys.modules["homeassistant.components.select"] = ha_select

    class CoordinatorEntity:
        def __init__(self, coordinator):
            self.coordinator = coordinator

    class DataUpdateCoordinator:
        def __init__(self, hass, logger, name, update_interval):
            self.hass = hass
            self.logger = logger
            self.name = name
            self.update_interval = update_interval
            self.data = None

    class UpdateFailed(Exception):
        pass

    ha_coordinator = MagicMock()
    ha_coordinator.CoordinatorEntity = CoordinatorEntity
    ha_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
    ha_coordinator.UpdateFailed = UpdateFailed
    sys.modules["homeassistant.helpers.update_coordinator"] = ha_coordinator

    class DeviceInfo(dict):
        def __init__(self, **kwargs):
            super().__init__(kwargs)

    ha_entity = MagicMock()
    ha_entity.DeviceInfo = DeviceInfo
    sys.modules["homeassistant.helpers.entity"] = ha_entity
    ha_ep = MagicMock()
    sys.modules["homeassistant.helpers.entity_platform"] = ha_ep
    sys.modules["homeassistant.util"] = MagicMock()

    ha_helpers.entity = ha_entity
    ha_helpers.entity_platform = ha_ep
    ha_helpers.update_coordinator = ha_coordinator

    ha_components.vacuum = ha_vacuum
    ha_components.sensor = ha_sensor
    ha_components.binary_sensor = ha_bin_sensor
    ha_components.button = ha_button
    ha_components.select = ha_select

    class UnitOfArea(str, Enum):
        SQUARE_METERS = "m²"

    class UnitOfTime(str, Enum):
        MINUTES = "min"

    ha_const = MagicMock()
    ha_const.PERCENTAGE = "%"
    ha_const.UnitOfArea = UnitOfArea
    ha_const.UnitOfTime = UnitOfTime
    sys.modules["homeassistant.const"] = ha_const
    ha.const = ha_const

    ha_const.UnitOfTime = UnitOfTime
    sys.modules["homeassistant.const"] = ha_const
