"""Sensor platform for the Staircase Lighting integration.

Spec ref: Entità esposte — sensor.<name>_state (idle/active),
sensor.<name>_mode (normal/dim), sensor.<name>_lux (mirrored ambient lux).
"""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import LIGHT_LUX, PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, CONF_NAME, CONF_LUX_SENSOR
from .coordinator import StaircaseLightingCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities from a config entry."""
    coordinator: StaircaseLightingCoordinator = hass.data[DOMAIN][entry.entry_id]
    name = entry.data[CONF_NAME]

    entities = [
        StaircaseStateSensor(coordinator, entry, name),
        StaircaseModeSensor(coordinator, entry, name),
        TimeRemainingSensor(coordinator, entry, name),
        CurrentBrightnessSensor(coordinator, entry, name),
    ]

    # Only add lux mirror sensor if a lux sensor is configured
    if entry.data.get(CONF_LUX_SENSOR):
        entities.append(StaircaseLuxSensor(coordinator, entry, name))

    async_add_entities(entities)


class StaircaseBaseSensor(SensorEntity):
    """Base class for staircase sensors with shared device info."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: StaircaseLightingCoordinator,
        entry: ConfigEntry,
        name: str,
    ) -> None:
        """Initialize base sensor."""
        self._coordinator = coordinator
        self._entry = entry
        # Spec ref: has_entity_name=True avoids duplicate name segments
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
        """Handle coordinator state update."""
        self.async_write_ha_state()


class StaircaseStateSensor(StaircaseBaseSensor):
    """Sensor showing current staircase state: idle or active.

    Spec ref: sensor.<name>_state — idle (no activity) / active (timer running).
    """

    _attr_translation_key = "staircase_state"
    _attr_icon = "mdi:stairs"

    def __init__(self, coordinator, entry, name) -> None:
        """Initialize state sensor."""
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_state"

    @property
    def native_value(self) -> str:
        """Return current state."""
        return self._coordinator.state


class StaircaseModeSensor(StaircaseBaseSensor):
    """Sensor showing current brightness mode: normal or dim.

    Spec ref: sensor.<name>_mode — normal (full brightness) / dim (reduced).
    """

    _attr_translation_key = "staircase_mode"
    _attr_icon = "mdi:brightness-6"

    def __init__(self, coordinator, entry, name) -> None:
        """Initialize mode sensor."""
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_mode"

    @property
    def native_value(self) -> str:
        """Return current mode."""
        return self._coordinator.mode


class StaircaseLuxSensor(StaircaseBaseSensor):
    """Mirrored ambient lux sensor.

    Reflects the real-time value of the configured illuminance sensor.
    Updated via async_track_state_change_event in the coordinator.
    Only created when a lux sensor is configured.
    """

    _attr_translation_key = "ambient_lux"
    _attr_icon = "mdi:brightness-5"
    _attr_device_class = SensorDeviceClass.ILLUMINANCE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = LIGHT_LUX

    def __init__(self, coordinator, entry, name) -> None:
        """Initialize lux mirror sensor."""
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_ambient_lux"

    @property
    def native_value(self) -> float | None:
        """Return current lux value from coordinator."""
        return self._coordinator.lux_value

class TimeRemainingSensor(StaircaseBaseSensor):
    """Countdown sensor showing seconds until lights turn off.

    Updated every 1 second via async_track_time_interval in the coordinator.
    Shows 0 when idle (no timers active).
    """

    _attr_translation_key = "time_remaining"
    _attr_icon = "mdi:timer-sand"
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry, name) -> None:
        """Initialize time remaining sensor."""
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_time_remaining"

    @property
    def native_value(self) -> int:
        """Return seconds remaining until lights turn off."""
        return self._coordinator.time_remaining


class CurrentBrightnessSensor(StaircaseBaseSensor):
    """Sensor showing the current brightness of the staircase lights.

    Reads the brightness attribute from the bottom light entity in real-time.
    Returns 0 when lights are off. Updated via light state change listener.
    """

    _attr_translation_key = "current_brightness"
    _attr_icon = "mdi:brightness-percent"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry, name) -> None:
        """Initialize current brightness sensor."""
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_current_brightness"

    @property
    def native_value(self) -> int:
        """Return current brightness percentage from the light entity."""
        return self._coordinator.current_brightness
