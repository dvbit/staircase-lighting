"""Binary sensor platform for the Staircase Lighting integration.

Mirrors the configured motion sensors (bottom/top) as entities belonging
to the virtual device. Updated in real-time via async_track_state_change_event
in the coordinator.
"""

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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities from a config entry."""
    coordinator: StaircaseLightingCoordinator = hass.data[DOMAIN][entry.entry_id]
    name = entry.data[CONF_NAME]

    async_add_entities(
        [
            MotionBottomBinarySensor(coordinator, entry, name),
            MotionTopBinarySensor(coordinator, entry, name),
        ]
    )


class StaircaseMotionBaseSensor(BinarySensorEntity):
    """Base class for mirrored motion binary sensors.

    Real-time updates via coordinator callback — no polling.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_device_class = BinarySensorDeviceClass.MOTION

    def __init__(
        self,
        coordinator: StaircaseLightingCoordinator,
        entry: ConfigEntry,
        name: str,
    ) -> None:
        """Initialize mirrored motion sensor."""
        self._coordinator = coordinator
        self._entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=name,
            manufacturer="Staircase Lighting",
            model="Virtual",
            sw_version="1.0.0",
        )

    async def async_added_to_hass(self) -> None:
        """Register update callback when entity is added."""
        self._coordinator.async_add_update_callback(
            self._handle_coordinator_update
        )

    async def async_will_remove_from_hass(self) -> None:
        """Remove update callback when entity is removed."""
        self._coordinator.async_remove_update_callback(
            self._handle_coordinator_update
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle coordinator state update — push new state to HA."""
        self.async_write_ha_state()


class MotionBottomBinarySensor(StaircaseMotionBaseSensor):
    """Mirrored bottom motion sensor.

    Reflects the real-time state of the configured bottom binary_sensor.
    """

    _attr_translation_key = "motion_bottom"
    _attr_icon = "mdi:motion-sensor"

    def __init__(self, coordinator, entry, name) -> None:
        """Initialize bottom motion sensor."""
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_motion_bottom"

    @property
    def is_on(self) -> bool:
        """Return True if bottom motion sensor is active."""
        return self._coordinator.motion_bottom


class MotionTopBinarySensor(StaircaseMotionBaseSensor):
    """Mirrored top motion sensor.

    Reflects the real-time state of the configured top binary_sensor.
    """

    _attr_translation_key = "motion_top"
    _attr_icon = "mdi:motion-sensor"

    def __init__(self, coordinator, entry, name) -> None:
        """Initialize top motion sensor."""
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_motion_top"

    @property
    def is_on(self) -> bool:
        """Return True if top motion sensor is active."""
        return self._coordinator.motion_top
