"""The Staircase Lighting integration.

Spec ref: Integration setup, platform forwarding, config entry unload.
Each config entry creates one coordinator and forwards platforms.

The custom Lovelace card is automatically registered as a frontend
resource on first config entry setup.
"""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import StaircaseLightingCoordinator

_LOGGER = logging.getLogger(__name__)

# --- Frontend card constants ---
CARD_JS = "staircase-lighting-card.js"
CARD_URL = f"/{DOMAIN}/{CARD_JS}"
CARD_FILE = Path(__file__).parent / "www" / CARD_JS


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Staircase Lighting from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # --- Auto-install card (once per HA session) ---
    if not hass.data[DOMAIN].get("card_registered"):
        await _async_register_card(hass)

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
        _LOGGER.info("Staircase Lighting '%s' unloaded", entry.title)
    return unload_ok


async def _async_update_listener(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Handle options flow update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_register_card(hass: HomeAssistant) -> None:
    """Register the custom card static path and Lovelace resource."""
    hass.data[DOMAIN]["card_registered"] = True

    card_path = str(CARD_FILE)
    _LOGGER.warning("Card file path: %s, exists: %s", card_path, CARD_FILE.exists())

    # --- Step 1: Register static path ---
    try:
        # Try the sync method first (available in most HA versions)
        hass.http.register_static_path(CARD_URL, card_path, False)
        _LOGGER.warning("Static path registered (sync): %s", CARD_URL)
    except AttributeError:
        _LOGGER.warning("register_static_path not available, trying async")
        try:
            from homeassistant.components.http import StaticPathConfig
            await hass.http.async_register_static_paths(
                [StaticPathConfig(CARD_URL, card_path, cache_headers=False)]
            )
            _LOGGER.warning("Static path registered (async): %s", CARD_URL)
        except Exception as err:
            _LOGGER.error("Failed to register static path: %s", err)
            return
    except Exception as err:
        _LOGGER.error("Failed to register static path (sync): %s", err)
        return

    # --- Step 2: Register Lovelace resource ---
    try:
        # Log available lovelace keys for debugging
        lovelace_keys = [k for k in hass.data if "lovelace" in str(k).lower()]
        _LOGGER.warning("Lovelace-related keys in hass.data: %s", lovelace_keys)

        resources = hass.data.get("lovelace_resources")
        if resources is None:
            # Try alternative key used in some HA versions
            lovelace_data = hass.data.get("lovelace")
            if lovelace_data and hasattr(lovelace_data, "resources"):
                resources = lovelace_data.resources
                _LOGGER.warning("Found resources via lovelace data object")

        if resources is not None:
            existing = [
                r for r in resources.async_items()
                if CARD_JS in r.get("url", "")
            ]
            if not existing:
                await resources.async_create_item(
                    {"res_type": "module", "url": CARD_URL}
                )
                _LOGGER.warning("Auto-registered Lovelace resource: %s", CARD_URL)
            else:
                _LOGGER.warning("Card resource already registered: %s", existing)
        else:
            _LOGGER.error(
                "Lovelace resources collection not found. "
                "Add manually: %s as JavaScript Module", CARD_URL
            )
    except Exception as err:
        _LOGGER.error("Failed to register Lovelace resource: %s", err)
