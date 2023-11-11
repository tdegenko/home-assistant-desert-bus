import datetime
import json
import logging
import urllib.error
import urllib.request

from homeassistant.core import (CALLBACK_TYPE, Event, HassJob, HassJobType,
                                HomeAssistant, callback)
from homeassistant.helpers import entity, event
from homeassistant.helpers.update_coordinator import \
    TimestampDataUpdateCoordinator

from .const import DB_YEAR_OFFSET, OMEGA_CHECK_URL, SHIFTS, STATS_URL_TEMPLATE

_LOGGER = logging.getLogger(__name__)


class DesertBusUpdateCoordinator(TimestampDataUpdateCoordinator):
    """Desert Bus Data Coordinator"""

    _bus_tz = datetime.timezone(datetime.timedelta(hours=-8))
    _shifts = {
        (datetime.time(0), datetime.time(6)): SHIFTS.ZETA,
        (datetime.time(6), datetime.time(12)): SHIFTS.DAWN,
        (datetime.time(12), datetime.time(18)): SHIFTS.ALPHA,
        (datetime.time(18), datetime.time(23, 59, 59)): SHIFTS.NIGHT,
    }

    _omega_ratelimit = datetime.timedelta(minutes=10)
    _stats_ratelimit = datetime.timedelta(minutes=5)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._last_omega_check = datetime.datetime.min
        self._last_stats_check = datetime.datetime.min

    def get_db_year(self):
        today = datetime.date.today()
        if today.month < 11:
            # If it's before November, we're likely talking about LAST year's
            # DB run.
            return today.year - DB_YEAR_OFFSET - 1
        else:
            # If it's November or later, it's likely THIS year's run
            return today.year - DB_YEAR_OFFSET

    def _fetch_stats(self, year):
        stats_url = STATS_URL_TEMPLATE.format(year=year)
        _LOGGER.debug("Fetching stats from %s", stats_url)
        with urllib.request.urlopen(stats_url) as stats:
            return json.load(stats)[0]

    def _repeat_stats(self):
        return {
            "now_bussing": self.data["now_bussing"],
            "db_year": self.data["db_year"],
            "start_time": self.data["start_time"],
            "total_raised": self.data["total_raised"],
            "run_purchased": self.data["run_purchased"],
        }

    def get_stats(self):
        _LOGGER.debug(self.data)
        now = datetime.datetime.now()
        if self.data is not None:
            _LOGGER.debug("Last updated %s", self._last_stats_check)
            if now.month != 11 and now.week == self._last_stats_check.week:
                # Check stats once a week outside of November
                _LOGGER.debug("Checking once a week")
                return self._repeat_stats()
            elif (
                self.data["start_time"].year < now.year
                and self._last_stats_check + datetime.timedelta(days=1) < now
            ):
                # In november check once a day untill this years stats show up
                _LOGGER.debug("Checking once a day")
                return self._repeat_stats()
            elif (self.data["start_time"] - now) >= datetime.timedelta(days=1) and (
                self._last_stats_check + datetime.timedelta(hours=1) < now
            ):
                # Then every hour until the final day
                _LOGGER.debug("Checking once an hour")
                return self._repeat_stats()
            elif (self.data["start_time"] - now) >= datetime.timedelta(hours=1) and (
                self._last_stats_check + datetime.timedelta(minutes=15) < now
            ):
                # then every 15 minutes for the final hour
                _LOGGER.debug("Checking every 15 min")
                return self._repeat_stats()
            elif (self.data["start_time"] + self.data["run_purchased"]) < now and (
                self._last_stats_check + datetime.timedelta(hours=6) < now
            ):
                # Then every six hours after the run
                _LOGGER.debug("Checking every 6 hours")
                return self._repeat_stats()

            elif self._last_stats_check + self._stats_ratelimit > now:
                # and every 5 minutes durring the run
                _LOGGER.debug("Checking every 5 min")
                return self._repeat_stats()
        try:
            db_stats = self._fetch_stats(self.get_db_year())
        except urllib.error.HTTPError as err:
            if err.code == 404:
                _LOGGER.debug(
                    "Got 404 for DB Stats JSON, new year's probably isn't up yet, try pulling last years"
                )
                db_stats = self._fetch_stats(self.get_db_year() - 1)

        bus_start = datetime.datetime.fromisoformat(db_stats["Year Start Date-Time"])
        bus_start = bus_start.replace(tzinfo=self._bus_tz)
        bus_start = datetime.datetime.fromtimestamp(bus_start.timestamp())
        run_purchased = datetime.timedelta(hours=db_stats["Max Hour Purchased"])
        self._last_stats_check = now
        return {
            "start_time": bus_start,
            "now_bussing": ((bus_start + run_purchased) > now >= bus_start),
            "total_raised": db_stats["Total Raised"],
            "db_year": db_stats["Year Number"],
            "run_purchased": run_purchased,
        }

    def get_shift(self):
        now = datetime.datetime.now()
        if (
            self.data is not None
            and self.data.get("now_bussing")
            and (now - self._last_omega_check >= self._omega_ratelimit)
        ):
            _LOGGER.debug("NEED TO UPDATE OMEGASHIFT")
            with urllib.request.urlopen(OMEGA_CHECK_URL) as omega_check:
                self._last_omega_check = now
                if int(omega_check.read().strip()) == 1:
                    return SHIFTS.OMEGA
        current_shift = None
        bus_now = datetime.datetime.now(tz=self._bus_tz).time()
        for (shift_start, shift_end), shift_name in self._shifts.items():
            if shift_start <= bus_now < shift_end:
                current_shift = shift_name
        return current_shift

    def now_bussing(self):
        return True

    async def _async_update_data(self):
        db_stats = await self.hass.async_add_executor_job(self.get_stats)
        current_shift = await self.hass.async_add_executor_job(self.get_shift)
        return {
            "current_shift": current_shift,
            "now_bussing": db_stats["now_bussing"],
            "total_raised": db_stats["total_raised"],
            "start_time": db_stats["start_time"],
            "db_year": db_stats["db_year"],
            "run_purchased": db_stats["run_purchased"],
        }
