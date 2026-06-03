"""Switch platform — lux control + manual lights with English names."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, CONF_NAME
from .coordinator import StaircaseLightingCoordinator


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    name = entry.data[CONF_NAME]
    async_add_entities([
        LuxControlSwitch(coordinator, entry, name),
        LightsSwitch(coordinator, entry, name),
    ])


class StaircaseBaseSwitch(SwitchEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator, entry, name):
        self._coordinator = coordinator
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=name, manufacturer="Staircase Lighting",
            model="Virtual", sw_version="1.0.0",
        )

    async def async_added_to_hass(self):
        self._coordinator.async_add_update_callback(self._update)

    async def async_will_remove_from_hass(self):
        self._coordinator.async_remove_update_callback(self._update)

    @callback
    def _update(self):
        self.async_write_ha_state()


class LuxControlSwitch(StaircaseBaseSwitch):
    """switch.<name>_lux_control"""
    _attr_name = "Lux control"
    _attr_icon = "mdi:theme-light-dark"

    def __init__(self, coordinator, entry, name):
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_lux_control"

    @property
    def is_on(self):
        return self._coordinator.lux_control_enabled

    async def async_turn_on(self, **kwargs):
        self._coordinator.lux_control_enabled = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self._coordinator.lux_control_enabled = False
        self.async_write_ha_state()


class LightsSwitch(StaircaseBaseSwitch):
    """switch.<name>_lights"""
    _attr_name = "Lights"
    _attr_icon = "mdi:lightbulb-group"

    def __init__(self, coordinator, entry, name):
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_lights"

    @property
    def is_on(self):
        return self._coordinator.lights_on

    async def async_turn_on(self, **kwargs):
        await self._coordinator.async_manual_turn_on()

    async def async_turn_off(self, **kwargs):
        await self._coordinator.async_manual_turn_off()
