"""The Parrot Olympe integration."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DEVICE_TIMEOUT, DOMAIN, UPDATE_SECONDS
from .models import ParrotOlympeData
from .helpers import ParrotOlympeHelper

# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.CAMERA]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Parrot Olympe from a config entry."""
    address: str = entry.data[CONF_HOST]

    parrot_helper = ParrotOlympeHelper(address)
    parrot_helper.connect()

    async def _async_update():
        """Update the device state."""
        return parrot_helper.drone_connected

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=_async_update,
        update_interval=timedelta(seconds=UPDATE_SECONDS),
    )

    try:
        async with async_timeout.timeout(DEVICE_TIMEOUT):
            await coordinator.async_config_entry_first_refresh()
    except asyncio.TimeoutError as ex:
        raise ConfigEntryNotReady(
            "Unable to communicate with the device; "
            f"Check that the controller is correctly connected to {DOMAIN}"
        ) from ex

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = ParrotOlympeData(
        entry.title, parrot_helper, coordinator
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    async def _async_stop(event: Event) -> None:
        """Close the connection."""
        parrot_helper.disconnect()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_stop)
    )
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    data = hass.data[DOMAIN][entry.entry_id]
    data.device.connect()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    data.device.disconnect()
    return True
