"""Platform for sensor integration."""

from __future__ import annotations

import logging
import typing

import homeassistant.const as ha_const
from homeassistant.components.sensor import (SensorDeviceClass, SensorEntity,
                                             SensorStateClass)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import (UNDEFINED, ConfigType,
                                          DiscoveryInfoType, StateType,
                                          UndefinedType)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

# from . import DesertBus
from .const import DOMAIN, SHIFTS
from .coordinator import DesertBusUpdateCoordinator
from .pubnub_desertbus import BusNub
from .util import BusMath

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    _LOGGER.debug(config_entry.data)
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    bus_api = BusNub(
        subscribe_key=config_entry.data["subscribe_key"],
        channel=config_entry.data["channel"],
    )
    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id]["api"] = bus_api
    add_entities(
        [
            ShiftSensor(coordinator),
            CurrentlyBussingSensor(coordinator),
            YearSensor(coordinator),
            StartSensor(coordinator),
            HoursSensor(bus_api),
            HoursCostSensor(bus_api),
            RaisedSensor(bus_api),
        ]
    )
    bus_api.init_api()


class BusSensor(CoordinatorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    _key: str = "undefined"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: DesertBusUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self.entity_id = "sensor.desertbus_{}".format(self._key)
        self._attr_unique_id = "desertbus_{}".format(self._key)
        self._attr_device_info = DeviceInfo(
            name="Desert Bus",
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, "desertbus")},
        )

    @property
    def state(self) -> StateType:
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
    _shift_colors = {
        SHIFTS.DAWN: {
            "primary": [239, 130, 34],
            "secondary": [192, 106, 41],
            "tertiary": [236, 227, 58],
        },
        SHIFTS.ALPHA: {
            "primary": [188, 37, 41],
            "secondary": [116, 18, 20],
            "tertiary": [188, 37, 41],
        },
        SHIFTS.NIGHT: {
            "primary": [9, 114, 186],
            "secondary": [36, 34, 98],
            "tertiary": [34, 171, 226],
        },
        SHIFTS.ZETA: {
            "primary": [94, 55, 137],
            "secondary": [145, 100, 171],
            "tertiary": [94, 55, 137],
        },
        SHIFTS.OMEGA: {
            "primary": [117, 204, 214],
            "secondary": [229, 160, 43],
            "tertiary": [115, 116, 116],
        },
    }

    @property
    def extra_state_attributes(self):
        return {
            "color_primary": self._shift_colors[self.state]["primary"],
            "color_secondary": self._shift_colors[self.state]["secondary"],
            "color_tertiary": self._shift_colors[self.state]["tertiary"],
        }


class YearSensor(BusSensor):
    _key = "db_year"
    _attr_name = "Deset Bus Year"


class StartSensor(BusSensor):
    _key = "start_time"
    _attr_name = "Deset Bus Start Time"
    _attr_device_class = SensorDeviceClass.TIMESTAMP


class FastBusSensor(SensorEntity):
    @property
    def _key(self) -> str:
        raise NotImplementedError

    should_poll = False

    def __init__(self, bus_api: BusNub) -> None:
        """Initialize the sensor."""
        # Usual setup is done here. Callbacks are added in async_added_to_hass.
        self.entity_id = "sensor.desertbus_{}".format(self._key)
        self._attr_unique_id = "desertbus_{}".format(self._key)
        self._attr_device_info = DeviceInfo(
            name="Desert Bus",
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, "desertbus")},
        )
        self._api = bus_api

    async def async_added_to_hass(
        self,
    ) -> None:
        """Run when this Entity has been added to HA."""

        # Importantly for a push integration, the module that will be getting
        # updates needs to notify HA of changes. The dummy device has a
        # registercallback method, so to this we add the
        # 'self.async_write_ha_state' method, to be called where ever there are
        # changes.  The call back registration is done once this entity is
        # registered with HA (rather than in the __init__)
        self._api.register_callback(self.schedule_update_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Entity being removed from hass."""
        # The opposite of async_added_to_hass. Remove any registered call backs here.
        self._api.remove_callback(self.schedule_update_ha_state)

    # This property is important to let HA know if this entity is online or not.
    # If an entity is offline (return False), the UI will refelect this.
    @property
    def available(self) -> bool:
        """Return True if roller and hub is available."""
        return self._api.online


class RaisedSensor(FastBusSensor):
    _key = "total_raised"
    _attr_name = "Deset Bus Total Raised"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "USD"
    #    _attr_suggested_unit_of_measurement = "USD"
    _attr_state_class = SensorStateClass.TOTAL

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""
        return self._api.total_raised


class HoursSensor(FastBusSensor):
    _key = "run_purchased"
    _attr_name = "Deset Bus Time Paid For"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = ha_const.UnitOfTime.HOURS
    _attr_suggested_unit_of_measurement = ha_const.UnitOfTime.HOURS
    _attr_state_class = SensorStateClass.TOTAL

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""
        total = self._api.total_raised
        return BusMath.dollars_to_hours(total)


class HoursCostSensor(FastBusSensor):
    _key = "next_hour_price_remaining"
    _attr_name = "Deset Bus Cost Remaining to Next Hour"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "USD"
    #    _attr_suggested_unit_of_measurement = "USD"

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""
        total = self._api.total_raised
        run_purchased = BusMath.dollars_to_hours(total)
        cost_of_purchased = BusMath.hours_to_dollars(run_purchased)
        next_hour_price_total = BusMath.price_for_hour(run_purchased)
        next_hour_price_remaining = next_hour_price_total - (total - cost_of_purchased)
        return next_hour_price_remaining

    @property
    def extra_state_attributes(self) -> dict:
        total = self._api.total_raised
        run_purchased = BusMath.dollars_to_hours(total)
        next_hour_price_total = BusMath.price_for_hour(run_purchased)
        return {"Total": next_hour_price_total}
