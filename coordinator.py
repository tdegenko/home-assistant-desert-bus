import datetime
import json
import logging
import typing
import urllib.error
import urllib.request

import homeassistant.util.dt as dt_util
# from homeassistant.core import (CALLBACK_TYPE, Event, HassJob, HassJobType,
#                                 HomeAssistant, callback)
# from homeassistant.helpers import entity, event
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

import desertbus

from .const import BUS_TIMEZONE, OMEGA_CHECK_URL, RATE_LIMITS, SHIFTS
from .util import BusMath

_LOGGER = logging.getLogger(__name__)


class DesertBusUpdateCoordinator(DataUpdateCoordinator):
    """Desert Bus Data Coordinator."""

    def __init__(
        self, *args: typing.Any, db_series: desertbus.Series,  **kwargs: typing.Any
    ) -> None:
        """Initialize."""
        super().__init__(*args, **kwargs)
        self._last_omega_check = datetime.datetime.min.replace(tzinfo=BUS_TIMEZONE)
        self._last_stats_check = datetime.datetime.min.replace(tzinfo=BUS_TIMEZONE)
        self.series = db_series

    def _fetch_stats(self) -> desertbus.Event:
        events = desertbus.get_events(self.series)
        return max(events, key=lambda x: x.start_time)

    def _repeat_stats(self) -> dict:
        return {
            "now_bussing": self.data["now_bussing"],
            "db_year": self.data["db_year"],
            "start_time": self.data["start_time"],
            "total_raised": self.data["total_raised"],
            "run_purchased": self.data["run_purchased"],
            "next_hour_price_total": self.data["next_hour_price_total"],
            "next_hour_price_remaining": self.data["next_hour_price_remaining"],
        }

    def get_stats(self) -> dict:
        """Fetch desertbus stats from API."""
        _LOGGER.debug(self.data)
        now = dt_util.now()
        if self.data is not None:
            _LOGGER.debug("Last updated %s", self._last_stats_check)
            if (
                self.data["start_time"].year < now.year
                and self._last_stats_check.day < now.day
            ):
                # In november check once a day untill this years stats show up
                _LOGGER.debug("New year, no stats: Checking once a day")
                return self._repeat_stats()
            if (
                now < self.data["start_time"]
                and self._last_stats_check + RATE_LIMITS["STATS"]["PRE_RUN"] < now
            ):
                _LOGGER.debug(
                    "Pre-Run: Checking every %s", RATE_LIMITS["STATS"]["PRE_RUN"]
                )
                return self._repeat_stats()
            if (
                self.data["start_time"]
                + datetime.timedelta(hours=self.data["run_purchased"])
            ) < now and (
                self._last_stats_check + RATE_LIMITS["STATS"]["POST_RUN"] < now
            ):
                # Then every six hours after the run
                _LOGGER.debug(
                    "Post-Run: Checking every %s", RATE_LIMITS["STATS"]["POST_RUN"]
                )
                return self._repeat_stats()

            if self._last_stats_check + RATE_LIMITS["STATS"]["DURING_RUN"] > now:
                # and every 15 minutes durring the run
                _LOGGER.debug("Checking every %s", RATE_LIMITS["STATS"]["DURING_RUN"])
                return self._repeat_stats()

        try:
            db_stats = self._fetch_stats()
        except json.JSONDecodeError as err:
            _LOGGER.critical(err)

        if db_stats:
            self._last_stats_check = now
        else:
            return self._repeat_stats()

        bus_start = db_stats.start_time
        # bus_start = bus_start.replace(tzinfo=BUS_TIMEZONE)
        total = float(db_stats.total.amount)
        run_purchased = BusMath.dollars_to_hours(total)

        cost_of_purchased = BusMath.hours_to_dollars(run_purchased)
        next_hour_price_total = BusMath.price_for_hour(run_purchased)
        next_hour_price_remaining = next_hour_price_total - (total - cost_of_purchased)
        return {
            "start_time": bus_start,
            "now_bussing": (
                (bus_start + datetime.timedelta(hours=run_purchased)) > now >= bus_start
            ),
            "total_raised": total,
            "db_year": BusMath.get_db_count(bus_start.year),
            "run_purchased": run_purchased,
            "next_hour_price_total": next_hour_price_total,
            "next_hour_price_remaining": next_hour_price_remaining,
        }

    def get_shift(self) -> str | None:
        """Calculates and returns current DB Prime shift."""
        now = dt_util.now()
        if (
            self.data is not None
            and self.data.get("now_bussing")
            and (now - self._last_omega_check >= RATE_LIMITS["OMEGA_SHIFT"])
        ):
            _LOGGER.debug("NEED TO UPDATE OMEGA SHIFT")
            with urllib.request.urlopen(OMEGA_CHECK_URL) as omega_check:
                self._last_omega_check = now
                if int(omega_check.read().strip()) == 1:
                    return SHIFTS.OMEGA.value
        bus_now = datetime.datetime.now(tz=BUS_TIMEZONE).time()
        return SHIFTS.from_time(bus_now).value

    async def _async_update_data(self) -> dict[str, StateType]:
        try:
            db_stats = await self.hass.async_add_executor_job(self.get_stats)
        except urllib.error.URLError as e:
            _LOGGER.critical(e)
        current_shift = await self.hass.async_add_executor_job(self.get_shift)
        return {
            "current_shift": current_shift,
            "now_bussing": db_stats["now_bussing"],
            "total_raised": db_stats["total_raised"],
            "start_time": db_stats["start_time"],
            "db_year": db_stats["db_year"],
            "run_purchased": db_stats["run_purchased"],
            "next_hour_price_total": db_stats["next_hour_price_total"],
            "next_hour_price_remaining": db_stats["next_hour_price_remaining"],
        }
