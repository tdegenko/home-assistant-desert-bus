"""Platform for sensor integration."""

from __future__ import annotations

import datetime
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

import desertbus

# from . import DesertBus
from .const import DOMAIN, SHIFTS
from .coordinator import DesertBusUpdateCoordinator
# from .pubnub_desertbus import BusNub
from .db_api import APIBus
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
    series = await hass.async_add_executor_job(desertbus.get_series)
    entities = []
    for s in series:
        coordinator = DesertBusUpdateCoordinator(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=datetime.timedelta(seconds=15),
            db_series=s,
        )
        await coordinator.async_config_entry_first_refresh()
        hass.data.setdefault(DOMAIN, {})[config_entry.entry_id]["coordinator"][
            s.id
        ] = coordinator
        bus_api = APIBus(s)
        if s.name == "Prime":
            entities += [
                ShiftSensor(coordinator),
                YearSensor(coordinator),
                HoursSensor(bus_api),
                HoursCostSensor(bus_api),
            ]
        entities += [
            StartSensor(coordinator),
            RaisedSensor(bus_api),
            CurrentlyBussingSensor(coordinator),
        ]
        await hass.async_add_executor_job(bus_api.init_api)
        hass.data.setdefault(DOMAIN, {})[config_entry.entry_id]["api"][s.id] = bus_api
    add_entities(entities)


class BusSensor(CoordinatorEntity):
    """Desert Bus API pull sensors."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    _key: str = "undefined"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: DesertBusUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
#        self.entity_id = f"sensor.desertbus_{coordinator.series.name.lower()}_{self._key}"
        self._attr_unique_id = f"{coordinator.series.name.lower()}_{self._key}"
        self._attr_device_info = DeviceInfo(
            name=f"Desert Bus {coordinator.series.name}",
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, f"desertbus-{coordinator.series.id}")},
        )

    @property
    def state(self) -> StateType:
        """Get sensor state."""
        return self.coordinator.data[self._key]


class CurrentlyBussingSensor(BusSensor):
    """"""

    _key = "now_bussing"
    _attr_name = "Desert Bus Currently Bussing"


class ShiftSensor(BusSensor):
    """"""

    """Desert Bus Shift Sensor"""

    _key = "current_shift"

    _attr_name = "Desert Bus Current Shift"
    _attr_options = [shift.name for shift in SHIFTS]

    @property
    def extra_state_attributes(self):
        """"""
        shift_colors = SHIFTS(self.state).colors
        return {
            "color_primary": shift_colors["primary"],
            "color_secondary": shift_colors["secondary"],
            "color_tertiary": shift_colors["tertiary"],
        }


class YearSensor(BusSensor):
    """"""

    _key = "db_year"
    _attr_name = "Desert Bus Year"


class StartSensor(BusSensor):
    """"""

    _key = "start_time"
    _attr_name = "Desert Bus Start Time"
    _attr_device_class = SensorDeviceClass.TIMESTAMP


class FastBusSensor(SensorEntity):
    """Desert Bus API push sensor."""

    @property
    def _key(self) -> str:
        raise NotImplementedError

    should_poll = False

    def __init__(self, bus_api: APIBus) -> None:
        """Initialize the sensor."""
        # Usual setup is done here. Callbacks are added in async_added_to_hass.
#        self.entity_id = f"sensor.desertbus_{bus_api.series.name.lower()}_{self._key}"
        self._attr_unique_id = f"{bus_api.series.name.lower()}_{self._key}"
        self._attr_device_info = DeviceInfo(
            name=f"Desert Bus {bus_api.series.name}",
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, f"desertbus-{bus_api.series.id}")},
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
    """"""

    _key = "total_raised"
    _attr_name = "Desert Bus Total Raised"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "USD"
    #    _attr_suggested_unit_of_measurement = "USD"
    _attr_state_class = SensorStateClass.TOTAL

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""
        return self._api.total_raised


class HoursSensor(FastBusSensor):
    """"""

    _key = "run_purchased"
    _attr_name = "Desert Bus Time Paid For"
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
    """"""

    _key = "next_hour_price_remaining"
    _attr_name = "Desert Bus Cost Remaining to Next Hour"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "USD"
    #    _attr_suggested_unit_of_measurement = "USD"

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""
        total = self._api.total_raised
        _LOGGER.debug(f"total:{total}:{total.__class__}")
        run_purchased = BusMath.dollars_to_hours(total)
        cost_of_purchased = BusMath.hours_to_dollars(run_purchased)
        next_hour_price_total = BusMath.price_for_hour(run_purchased)
        next_hour_price_remaining = next_hour_price_total - (total - cost_of_purchased)
        return next_hour_price_remaining

    @property
    def extra_state_attributes(self) -> dict:
        """"""
        total = self._api.total_raised
        run_purchased = BusMath.dollars_to_hours(total)
        next_hour_price_total = BusMath.price_for_hour(run_purchased)
        return {"Total": next_hour_price_total}
