"""The Staircase Lighting integration.

Spec ref: Integration setup, platform forwarding, config entry unload.
Each config entry creates one coordinator and forwards platforms.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import StaircaseLightingCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Staircase Lighting from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = StaircaseLightingCoordinator(hass, entry.data)
    await coordinator.async_start()

    hass.data[DOMAIN][entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info("Staircase Lighting '%s' set up successfully", entry.title)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: StaircaseLightingCoordinator = hass.data[DOMAIN].pop(
            entry.entry_id
        )
        await coordinator.async_stop()
    return unload_ok


async def _async_update_listener(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Handle options flow update."""
    await hass.config_entries.async_reload(entry.entry_id)
