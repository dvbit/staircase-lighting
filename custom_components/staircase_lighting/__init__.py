"""The Staircase Lighting integration.

Spec ref: Integration setup, platform forwarding, config entry unload.
Each config entry creates one coordinator and forwards platforms.

The custom Lovelace card is automatically registered as a frontend
resource on first config entry setup — no manual file copy or
resource registration needed.
"""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import StaircaseLightingCoordinator

_LOGGER = logging.getLogger(__name__)

# --- Frontend card auto-registration constants ---
CARD_JS = "staircase-lighting-card.js"
CARD_URL = f"/{DOMAIN}/{CARD_JS}"
CARD_DIR = Path(__file__).parent / "www"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Staircase Lighting from a config entry.

    Spec ref: creates coordinator, stores in hass.data, forwards platforms.
    Also auto-registers the custom Lovelace card (once per HA session).
    """
    hass.data.setdefault(DOMAIN, {})

    # --- Auto-install card (once per HA session) ---
    await _async_register_card(hass)

    coordinator = StaircaseLightingCoordinator(hass, entry.data)
    await coordinator.async_start()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Listen for options flow updates to reload coordinator parameters
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info("Staircase Lighting '%s' set up successfully", entry.title)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    Spec ref: config_entry_unload must cancel timers and remove listeners.
    """
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
    """Handle options flow update — reload entry to apply new parameters.

    Spec ref: Options Flow modifiable post-install without HA restart.
    """
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_register_card(hass: HomeAssistant) -> None:
    """Register the custom card static path and Lovelace resource.

    Performs both steps in async_setup_entry (not async_setup) to ensure
    hass.http is available. Runs only once per HA session via guard flag.
    """
    if hass.data[DOMAIN].get("card_registered"):
        return

    # Mark as registered immediately to avoid duplicate attempts
    hass.data[DOMAIN]["card_registered"] = True

    # --- Step 1: Register static path ---
    card_path = str(CARD_DIR / CARD_JS)
    try:
        hass.http.register_static_path(CARD_URL, card_path, cache_headers=False)
        _LOGGER.debug("Registered static path: %s -> %s", CARD_URL, card_path)
    except Exception:
        try:
            await hass.http.async_register_static_paths(
                [StaticPathConfig(CARD_URL, card_path, cache_headers=False)]
            )
            _LOGGER.debug(
                "Registered static path (async): %s -> %s", CARD_URL, card_path
            )
        except Exception as err:
            _LOGGER.warning(
                "Could not register static path for card: %s", err
            )
            return

    # --- Step 2: Register Lovelace resource ---
    try:
        resources = hass.data.get("lovelace_resources")

        if resources is not None:
            existing = [
                r
                for r in resources.async_items()
                if CARD_JS in r.get("url", "")
            ]

            if not existing:
                await resources.async_create_item(
                    {"res_type": "module", "url": CARD_URL}
                )
                _LOGGER.info(
                    "Auto-registered Lovelace resource: %s", CARD_URL
                )
            else:
                _LOGGER.debug("Card resource already registered")
        else:
            _LOGGER.warning(
                "Lovelace resources not available — "
                "add resource manually: %s as JavaScript Module",
                CARD_URL,
            )
    except Exception as err:
        _LOGGER.warning(
            "Could not auto-register card resource: %s — "
            "add manually: %s as JavaScript Module",
            err,
            CARD_URL,
        )
