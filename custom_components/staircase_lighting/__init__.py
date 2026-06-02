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


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Staircase Lighting component.

    Registers the www/ directory as a static path so the custom card JS
    is served by HA at /staircase_lighting/staircase-lighting-card.js.
    """
    hass.data.setdefault(DOMAIN, {})

    # Register static path for the card JS file
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(CARD_DIR / CARD_JS), cache_headers=False)]
    )
    _LOGGER.debug("Registered static path: %s -> %s", CARD_URL, CARD_DIR / CARD_JS)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Staircase Lighting from a config entry.

    Spec ref: creates coordinator, stores in hass.data, forwards platforms.
    Also auto-registers the custom Lovelace card resource (once).
    """
    hass.data.setdefault(DOMAIN, {})

    coordinator = StaircaseLightingCoordinator(hass, entry.data)
    await coordinator.async_start()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Auto-register the card as a Lovelace resource (once per HA session)
    await _async_register_card_resource(hass)

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


async def _async_register_card_resource(hass: HomeAssistant) -> None:
    """Register the custom card as a Lovelace frontend resource.

    Only registers once per HA session. The resource URL points to the
    static path served by async_setup. Uses the lovelace resources
    collection so the user doesn't need to add the resource manually.
    """
    # Skip if already registered this session
    if hass.data[DOMAIN].get("card_registered"):
        return

    try:
        # Access the lovelace resources collection
        resources = hass.data.get("lovelace_resources")

        if resources is not None:
            # Check if already registered in persistent storage
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
                    "Auto-registered Lovelace resource: %s (module)", CARD_URL
                )
            else:
                _LOGGER.debug("Card resource already registered")
        else:
            _LOGGER.warning(
                "Lovelace resources not available — "
                "add manually: %s as JavaScript Module",
                CARD_URL,
            )

    except Exception:
        _LOGGER.warning(
            "Could not auto-register card resource — "
            "add manually: %s as JavaScript Module",
            CARD_URL,
        )

    hass.data[DOMAIN]["card_registered"] = True
