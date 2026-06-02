"""The Staircase Lighting integration.

Spec ref: Integration setup, platform forwarding, config entry unload.
The custom Lovelace card JS is served via a custom HTTP view.
"""

from __future__ import annotations

import logging
from pathlib import Path

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import StaircaseLightingCoordinator

_LOGGER = logging.getLogger(__name__)

CARD_JS = "staircase-lighting-card.js"
CARD_URL = f"/staircase_lighting/{CARD_JS}"
CARD_FILE = Path(__file__).parent / "www" / CARD_JS


class StaircaseCardView(HomeAssistantView):
    """Serve the custom card JS file without authentication."""

    url = CARD_URL
    name = "staircase_lighting:card_js"
    requires_auth = False

    async def get(self, request):
        """Return the card JS file."""
        if not CARD_FILE.exists():
            _LOGGER.error("Card file not found: %s", CARD_FILE)
            return web.Response(status=404, text="Card file not found")
        return web.FileResponse(str(CARD_FILE))


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register the card HTTP view and frontend module."""
    hass.data.setdefault(DOMAIN, {})

    # Register the HTTP view to serve the card JS
    hass.http.register_view(StaircaseCardView)
    _LOGGER.error("STAIRCASE: card view registered at %s", CARD_URL)

    # Tell the frontend to auto-load the JS module
    try:
        from homeassistant.components.frontend import add_extra_js_url
        add_extra_js_url(hass, CARD_URL)
        _LOGGER.error("STAIRCASE: added extra JS URL %s", CARD_URL)
    except ImportError:
        _LOGGER.error(
            "STAIRCASE: add_extra_js_url not available, add resource manually: %s",
            CARD_URL,
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Staircase Lighting from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = StaircaseLightingCoordinator(hass, entry.data)
    await coordinator.async_start()

    hass.data[DOMAIN][entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
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
