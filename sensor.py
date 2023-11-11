"""Platform for sensor integration."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

# from . import DesertBus
from .const import DOMAIN, SHIFTS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN]["coordinator"]
    add_entities(
        [
            ShiftSensor(coordinator),
            CurrentlyBussingSensor(coordinator),
            YearSensor(coordinator),
            StartSensor(coordinator),
            RaisedSensor(coordinator),
            HoursSensor(coordinator),
        ]
    )


class BusSensor(CoordinatorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    _key: str = "undefined"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self.entity_id = "sensor.desertbus_{}".format(self._key)
        self._attr_unique_id = "desertbus_{}".format(self._key)
        self._attr_device_info = DeviceInfo(
            name="Desert Bus",
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, "desertbus")},
        )

    @property
    def state(self):
        return self.coordinator.data[self._key]


class CurrentlyBussingSensor(BusSensor):
    _key = "now_bussing"
    _attr_name = "Deset Bus Currently Bussing"


class ShiftSensor(BusSensor):
    """Desert Bus Shift Sensor"""

    _key = "current_shift"

    _attr_name = "Deset Bus Current Shift"
    _attr_options = [
        SHIFTS.DAWN,
        SHIFTS.ALPHA,
        SHIFTS.NIGHT,
        SHIFTS.ZETA,
        SHIFTS.OMEGA,
    ]


class YearSensor(BusSensor):
    _key = "db_year"
    _attr_name = "Deset Bus Year"


class StartSensor(BusSensor):
    _key = "start_time"
    _attr_name = "Deset Bus Start Time"


class RaisedSensor(BusSensor):
    _key = "total_raised"
    _attr_name = "Deset Bus Total Raised"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "USD"


class HoursSensor(BusSensor):
    _key = "run_purchased"
    _attr_name = "Deset Bus Time Paid For"
    _attr_device_class = SensorDeviceClass.DURATION
