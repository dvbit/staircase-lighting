"""The Staircase Lighting integration.

Spec ref: Integration setup, platform forwarding, config entry unload.
The custom Lovelace card JS is auto-served and auto-loaded in the frontend.
"""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import StaircaseLightingCoordinator

_LOGGER = logging.getLogger(__name__)

CARD_JS = "staircase-lighting-card.js"
CARD_URL = f"/{DOMAIN}/{CARD_JS}"
CARD_FILE = Path(__file__).parent / "www" / CARD_JS


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register the card JS as a static path and frontend extra module.

    async_setup runs after the HTTP and frontend components are ready,
    so both registrations are safe here.
    """
    hass.data.setdefault(DOMAIN, {})

    card_path = str(CARD_FILE)
    _LOGGER.debug("Card file: %s (exists: %s)", card_path, CARD_FILE.exists())

    # Serve the JS file at /staircase_lighting/staircase-lighting-card.js
    hass.http.register_static_path(CARD_URL, card_path, False)

    # Tell the frontend to load it as an ES module on every page
    add_extra_js_url(hass, CARD_URL)

    _LOGGER.debug("Card registered: static=%s, extra_js=%s", CARD_URL, CARD_URL)
    return True


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
