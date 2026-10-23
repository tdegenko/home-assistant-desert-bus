"""Platform for sensor integration."""

from __future__ import annotations

import collections
import logging
import typing
import urllib
import uuid

from homeassistant.helpers.typing import StateType

import desertbus

_LOGGER = logging.getLogger(__name__)


class APIBus:
    """"""

    _total: desertbus.data_types.Total

    def __init__(self, series: desertbus.Series) -> None:
        """"""
        self._api_inited = False
        self._callbacks: set = set()

    def init_api(self) -> None:
        """"""
        events = desertbus.get_events("12pEtImeluwLBvtnl7zlaV")
        self.event = max(events, key=lambda x: x.start_time)
        self._db_listener = desertbus.PushListener(self.event)

        self._db_listener.subscribe_total(self.do_callbacks)
        self._db_listener.setup()
        self._api_inited = True

    def close_api(self) -> None:
        """"""
        self._db_listener.close()

    @property
    def online(self) -> bool:
        """"""
        return self._api_inited

    def register_callback(self, call_back: collections.abc.Callable) -> None:
        """"""
        self._callbacks.add(call_back)

    def remove_callback(self, call_back: collections.abc.Callable) -> None:
        """"""
        self._callbacks.remove(call_back)

    def do_callbacks(self, new_total: desertbus.Event) -> None:
        self._total = new_total
        for callback in self._callbacks:
            callback()

    @property
    def total_raised(self) -> float:
        """"""
        return float(self._total.amount)
