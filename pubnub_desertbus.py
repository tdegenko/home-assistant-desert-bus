"""Platform for sensor integration."""

from __future__ import annotations

import collections
import logging
import typing
import urllib
import uuid

from homeassistant.helpers.typing import StateType
from pubnub.callbacks import SubscribeCallback
from pubnub.enums import PNStatusCategory
from pubnub.models.consumer.common import PNStatus
from pubnub.models.consumer.history import PNFetchMessagesResult
from pubnub.models.consumer.pubsub import PNMessageResult
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub

_LOGGER = logging.getLogger(__name__)


class BusNubSubscribeCallback(SubscribeCallback):
    def __init__(self, bus: BusNub) -> None:
        super().__init__()
        self.bus = bus

    def status(self, pubnub: PubNub, status: PNStatus) -> None:
        if status.category == PNStatusCategory.PNUnexpectedDisconnectCategory:
            _LOGGER.warning("PubNub disconnected")
            pubnub.reconnect()
        elif status.category == PNStatusCategory.PNTimeoutCategory:
            _LOGGER.warning("PubNub timeout")
            pubnub.reconnect()

    def message(self, pubnub: PubNub, message: PNMessageResult) -> None:
        total_raised = message.message
        _LOGGER.debug("Total updated %f", total_raised)
        self.bus.do_callbacks(total_raised)


class BusNub:
    def __init__(self, subscribe_key, channel) -> None:
        self.pn_config = PNConfiguration()
        self.pn_config.user_id = str(uuid.uuid4())
        self.pn_config.subscribe_key = subscribe_key
        self.pubnub: PubNub = None
        self._callbacks: set = set()
        self._data: dict[str, StateType] = {}
        self._pubnub_inited = False
        self._channel = channel

    def init_api(self) -> None:
        self.pubnub = PubNub(self.pn_config)
        self.pubnub.add_listener(BusNubSubscribeCallback(self))
        total_channel = self.pubnub.channel(self._channel).subscription()
        total_channel.subscribe()

        def fetch_callback(envelope: PNFetchMessagesResult, status: PNStatus) -> None:
            total_raised: float
            if status and status.is_error():
                _LOGGER.warning("PubNub request returned an error!")
                return
            for channel_name, items in envelope.channels.items():
                if channel_name == urllib.parse.quote(self._channel):
                    total_raised = items[0].message
            self._pubnub_inited = True
            self.do_callbacks(total_raised)

        self.pubnub.fetch_messages().channels(self._channel).maximum_per_channel(
            1
        ).pn_async(fetch_callback)

    def close_api(self) -> None:
        self.pubnub._subscription_manager.disconnect()

    @property
    def online(self) -> bool:
        return self._pubnub_inited

    def register_callback(self, call_back: collections.abc.Callable) -> None:
        self._callbacks.add(call_back)

    def remove_callback(self, call_back: collections.abc.Callable) -> None:
        self._callbacks.remove(call_back)

    def do_callbacks(self, new_total: float) -> None:
        self._data["total_raised"] = new_total
        for callback in self._callbacks:
            callback()

    @property
    def total_raised(self) -> float:
        return self._data["total_raised"]
