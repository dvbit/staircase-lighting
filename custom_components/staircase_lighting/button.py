"""Button platform for the Staircase Lighting integration.

Provides a button to set the lux threshold to the current ambient lux reading.
"""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, CONF_NAME, CONF_LUX_SENSOR
from .coordinator import StaircaseLightingCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entities from a config entry.

    Only creates the button if a lux sensor is configured.
    """
    coordinator: StaircaseLightingCoordinator = hass.data[DOMAIN][entry.entry_id]
    name = entry.data[CONF_NAME]

    if entry.data.get(CONF_LUX_SENSOR):
        async_add_entities([SetLuxThresholdButton(coordinator, entry, name)])


class SetLuxThresholdButton(ButtonEntity):
    """Button to set lux threshold to the current ambient lux value.

    When pressed, reads the current lux_value from the coordinator
    and sets lux_threshold to that value. No-op if lux sensor
    is unavailable or returns None.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "set_lux_threshold"
    _attr_icon = "mdi:white-balance-sunny"

    def __init__(
        self,
        coordinator: StaircaseLightingCoordinator,
        entry: ConfigEntry,
        name: str,
    ) -> None:
        """Initialize set lux threshold button."""
        self._coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_set_lux_threshold"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=name,
            manufacturer="Staircase Lighting",
            model="Virtual",
            sw_version="1.0.0",
        )

    async def async_press(self) -> None:
        """Handle button press — set threshold to current lux value."""
        self._coordinator.set_lux_threshold_to_current()
