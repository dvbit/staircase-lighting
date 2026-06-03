"""Binary sensor platform — mirrored motion sensors with English names."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
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
        MotionBottomBinarySensor(coordinator, entry, name),
        MotionTopBinarySensor(coordinator, entry, name),
    ])


class StaircaseMotionBase(BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_device_class = BinarySensorDeviceClass.MOTION

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


class MotionBottomBinarySensor(StaircaseMotionBase):
    """binary_sensor.<name>_motion_bottom"""
    _attr_name = "Motion bottom"
    _attr_icon = "mdi:motion-sensor"

    def __init__(self, coordinator, entry, name):
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_motion_bottom"

    @property
    def is_on(self):
        return self._coordinator.motion_bottom


class MotionTopBinarySensor(StaircaseMotionBase):
    """binary_sensor.<name>_motion_top"""
    _attr_name = "Motion top"
    _attr_icon = "mdi:motion-sensor"

    def __init__(self, coordinator, entry, name):
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_motion_top"

    @property
    def is_on(self):
        return self._coordinator.motion_top
