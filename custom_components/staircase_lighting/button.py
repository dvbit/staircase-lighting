"""Button platform — set lux threshold with English name."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, CONF_NAME, CONF_LUX_SENSOR
from .coordinator import StaircaseLightingCoordinator


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    name = entry.data[CONF_NAME]
    if entry.data.get(CONF_LUX_SENSOR):
        async_add_entities([SetLuxThresholdButton(coordinator, entry, name)])


class SetLuxThresholdButton(ButtonEntity):
    """button.<name>_set_lux_threshold"""
    _attr_has_entity_name = True
    _attr_name = "Set lux threshold"
    _attr_icon = "mdi:white-balance-sunny"

    def __init__(self, coordinator, entry, name):
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_set_lux_threshold"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=name, manufacturer="Staircase Lighting",
            model="Virtual", sw_version="1.0.0",
        )

    async def async_press(self):
        self._coordinator.set_lux_threshold_to_current()
