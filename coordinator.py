import datetime
import json
import logging
import urllib.error
import urllib.request
import typing

import homeassistant.util.dt as hass_dt
from homeassistant.core import (CALLBACK_TYPE, Event, HassJob, HassJobType,
                                HomeAssistant, callback)
from homeassistant.helpers import entity, event
from homeassistant.helpers.update_coordinator import \
    TimestampDataUpdateCoordinator

from .const import (BUS_TIMEZONE, DB_YEAR_OFFSET, OMEGA_CHECK_URL, RATE_LIMITS,
                    SHIFTS, STATS_URL_TEMPLATE)

_LOGGER = logging.getLogger(__name__)


class DesertBusUpdateCoordinator(TimestampDataUpdateCoordinator):
    """Desert Bus Data Coordinator"""

    _shifts = {
        (datetime.time(0), datetime.time(6)): SHIFTS.ZETA,
        (datetime.time(6), datetime.time(12)): SHIFTS.DAWN,
        (datetime.time(12), datetime.time(18)): SHIFTS.ALPHA,
        (datetime.time(18), datetime.time(23, 59, 59)): SHIFTS.NIGHT,
    }

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self._last_omega_check = datetime.datetime.min.replace(tzinfo=BUS_TIMEZONE)
        self._last_stats_check = datetime.datetime.min.replace(tzinfo=BUS_TIMEZONE)

    def get_db_year(self) -> int:
        today = datetime.date.today()
        if today.month < 11:
            # If it's before November, we're likely talking about LAST year's
            # DB run.
            return today.year - DB_YEAR_OFFSET - 1
        # If it's November or later, it's likely THIS year's run
        return today.year - DB_YEAR_OFFSET

    def _fetch_stats(self, year: int) -> dict:
        stats_url = STATS_URL_TEMPLATE.format(year=year)
        _LOGGER.debug("Fetching stats from %s", stats_url)
        with urllib.request.urlopen(stats_url) as stats:
            db_stats = json.load(stats)[0]
            assert isinstance(db_stats, dict)
            return db_stats

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
        _LOGGER.debug(self.data)
        now = hass_dt.now()
        if self.data is not None:
            _LOGGER.debug("Last updated %s", self._last_stats_check)
            if (
                now.month != 11
                and now.isocalendar().week == self._last_stats_check.isocalendar().week
            ):
                # Check stats once a week outside of November
                _LOGGER.debug("Checking once a week")
                return self._repeat_stats()
            elif (
                self.data["start_time"].year < now.year
                and self._last_stats_check.day < now.day
            ):
                # In november check once a day untill this years stats show up
                _LOGGER.debug("Checking once a day")
                return self._repeat_stats()
            elif (
                self.data["start_time"]
                + datetime.timedelta(hours=self.data["run_purchased"])
            ) < now and (
                self._last_stats_check + RATE_LIMITS["STATS"]["POST_RUN"] < now
            ):
                # Then every six hours after the run
                _LOGGER.debug("Checking every %s", RATE_LIMITS["STATS"]["POST_RUN"])
                return self._repeat_stats()

            elif self._last_stats_check + RATE_LIMITS["STATS"]["DURING_RUN"] > now:
                # and every 5 minutes durring the run
                _LOGGER.debug("Checking every %s", RATE_LIMITS["STATS"]["DURING_RUN"])
                return self._repeat_stats()

        db_stats = {}
        try:
            db_stats = self._fetch_stats(self.get_db_year())
        except urllib.error.HTTPError as err:
            if err.code == 404:
                _LOGGER.debug(
                    "Got 404 for DB Stats JSON, new year's probably isn't up yet, try pulling last years"
                )
                db_stats = self._fetch_stats(self.get_db_year() - 1)
        except json.JSONDecodeError as err:
            _LOGGER.critical(err)

        if db_stats:
            self._last_stats_check = now
        else:
            return self._repeat_stats()

        bus_start = datetime.datetime.fromisoformat(db_stats["Year Start Date-Time"])
        bus_start = bus_start.replace(tzinfo=BUS_TIMEZONE)
        run_purchased = int(db_stats["Max Hour Purchased"])

        total = float(db_stats["Total Raised"])

        # Math from: https://loadingreadyrun.com/forum/viewtopic.php?t=10231
        cost_of_purchased = round((1.07 ** (run_purchased)) * (100 / 7), 2)
        next_hour_price_total = round(1.07 ** (run_purchased), 2)
        next_hour_price_remaining = next_hour_price_total - (total - cost_of_purchased)
        return {
            "start_time": bus_start,
            "now_bussing": (
                (bus_start + datetime.timedelta(hours=run_purchased)) > now >= bus_start
            ),
            "total_raised": total,
            "db_year": db_stats["Year Number"],
            "run_purchased": run_purchased,
            "next_hour_price_total": next_hour_price_total,
            "next_hour_price_remaining": next_hour_price_remaining,
        }

    def get_shift(self) -> str | None:
        now = hass_dt.now()
        if (
            self.data is not None
            and self.data.get("now_bussing")
            and (now - self._last_omega_check >= RATE_LIMITS["OMEGA_SHIFT"])
        ):
            _LOGGER.debug("NEED TO UPDATE OMEGA SHIFT")
            with urllib.request.urlopen(OMEGA_CHECK_URL) as omega_check:
                self._last_omega_check = now
                if int(omega_check.read().strip()) == 1:
                    return SHIFTS.OMEGA
        current_shift = None
        bus_now = datetime.datetime.now(tz=BUS_TIMEZONE).time()
        for (shift_start, shift_end), shift_name in self._shifts.items():
            if shift_start <= bus_now < shift_end:
                current_shift = shift_name
        return current_shift

    async def _async_update_data(self) -> dict:
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
