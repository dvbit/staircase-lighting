"""Number platform — runtime parameters with English names."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
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
        TurnOffDelayNumber(coordinator, entry, name),
        BrightnessNumber(coordinator, entry, name),
        BrightnessDimNumber(coordinator, entry, name),
        LuxThresholdNumber(coordinator, entry, name),
    ])


class StaircaseBaseNumber(NumberEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_mode = NumberMode.SLIDER

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


class TurnOffDelayNumber(StaircaseBaseNumber):
    """number.<name>_turn_off_delay"""
    _attr_name = "Turn off delay"
    _attr_icon = "mdi:timer-outline"
    _attr_native_min_value = 10
    _attr_native_max_value = 300
    _attr_native_step = 10
    _attr_native_unit_of_measurement = "s"

    def __init__(self, coordinator, entry, name):
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_turn_off_delay"

    @property
    def native_value(self):
        return self._coordinator.turn_off_delay

    async def async_set_native_value(self, value):
        self._coordinator.turn_off_delay = int(value)
        self.async_write_ha_state()


class BrightnessNumber(StaircaseBaseNumber):
    """number.<name>_brightness"""
    _attr_name = "Brightness"
    _attr_icon = "mdi:brightness-7"
    _attr_native_min_value = 1
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "%"

    def __init__(self, coordinator, entry, name):
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_brightness"

    @property
    def native_value(self):
        return self._coordinator.brightness

    async def async_set_native_value(self, value):
        self._coordinator.brightness = int(value)
        self.async_write_ha_state()


class BrightnessDimNumber(StaircaseBaseNumber):
    """number.<name>_brightness_dim"""
    _attr_name = "Brightness dim"
    _attr_icon = "mdi:brightness-5"
    _attr_native_min_value = 1
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "%"

    def __init__(self, coordinator, entry, name):
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_brightness_dim"

    @property
    def native_value(self):
        return self._coordinator.brightness_dim

    async def async_set_native_value(self, value):
        self._coordinator.brightness_dim = int(value)
        self.async_write_ha_state()


class LuxThresholdNumber(StaircaseBaseNumber):
    """number.<name>_lux_threshold"""
    _attr_name = "Lux threshold"
    _attr_icon = "mdi:weather-sunny"
    _attr_native_min_value = 0
    _attr_native_max_value = 1000
    _attr_native_step = 10
    _attr_native_unit_of_measurement = "lx"

    def __init__(self, coordinator, entry, name):
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_lux_threshold"

    @property
    def native_value(self):
        return self._coordinator.lux_threshold

    async def async_set_native_value(self, value):
        self._coordinator.lux_threshold = int(value)
        self.async_write_ha_state()
