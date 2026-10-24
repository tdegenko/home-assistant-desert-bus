"""Platform for sensor integration."""

from __future__ import annotations

import collections
import logging
import time
import typing
import urllib
import uuid
import threading

from homeassistant.helpers.typing import StateType

import desertbus

_LOGGER = logging.getLogger(__name__)


class APIBus:
    """"""

    _total: desertbus.data_types.Total

    def __init__(
        self, series: desertbus.Series, connect_check_interval: int = 10
    ) -> None:
        """"""
        self._api_inited = False
        self._callbacks: set = set()
        self.series = series
        self.event: desertbus.Event
        self._db_listener: desertbus.PushListener
        self.connect_check_interval = connect_check_interval
        self.topics = [desertbus.ListenTopics.TOTAL]

    def init_api(self) -> None:
        """Set up API for push info."""
        events = desertbus.get_events(self.series)
        self.event = max(events, key=lambda x: x.start_time)
        self._db_listener = desertbus.PushListener(self.event)

        self._db_listener.subscribe_total(self.do_callbacks)
        self._db_listener.setup(self.topics)
        threading.Thread(target=self._reconnect, args=[], daemon=True).start()
        self._api_inited = True

    def close_api(self) -> None:
        """Close API connections."""
        if self.online:
            self._db_listener.teardown()
        self._db_listener = None

    def _reconnect(self):
        """Handle automatic reconnection."""
        while self._db_listener is not None:
            if not self._db_listener.connected:
                _LOGGER.info("Lost DB Push connection, reconnecting...")
                self._db_listener.setup(self.topics)
            time.sleep(self.connect_check_interval)

    @property
    def online(self) -> bool:
        """"""
        return self._api_inited and self._db_listener.connected

    def register_callback(self, call_back: collections.abc.Callable) -> None:
        """"""
        self._callbacks.add(call_back)

    def remove_callback(self, call_back: collections.abc.Callable) -> None:
        """"""
        self._callbacks.remove(call_back)

    def do_callbacks(self, new_total: desertbus.Event) -> None:
        """"""
        self._total = new_total
        _LOGGER.info(f"got new pushed event {new_total}")
        for callback in self._callbacks:
            callback()

    @property
    def total_raised(self) -> float:
        """"""
        return float(self._total.amount)
