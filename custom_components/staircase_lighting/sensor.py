"""Sensor platform for the Staircase Lighting integration.

Spec ref: Entità esposte — English _attr_name for stable entity_ids.
translation_key kept only for state value translations (idle/active, normal/dim).
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
        DirectionSensor(coordinator, entry, name),
    ]

    if entry.data.get(CONF_LUX_SENSOR):
        entities.append(StaircaseLuxSensor(coordinator, entry, name))

    async_add_entities(entities)


class StaircaseBaseSensor(SensorEntity):
    """Base class for staircase sensors with shared device info."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator, entry, name) -> None:
        """Initialize base sensor."""
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
        self._coordinator.async_add_update_callback(self._handle_coordinator_update)

    async def async_will_remove_from_hass(self) -> None:
        self._coordinator.async_remove_update_callback(self._handle_coordinator_update)

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class StaircaseStateSensor(StaircaseBaseSensor):
    """sensor.<name>_state — idle/active. translation_key kept for state values."""

    _attr_name = "State"
    _attr_translation_key = "staircase_state"
    _attr_icon = "mdi:stairs"

    def __init__(self, coordinator, entry, name) -> None:
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_state"

    @property
    def native_value(self) -> str:
        return self._coordinator.state


class StaircaseModeSensor(StaircaseBaseSensor):
    """sensor.<name>_mode — normal/dim. translation_key kept for state values."""

    _attr_name = "Mode"
    _attr_translation_key = "staircase_mode"
    _attr_icon = "mdi:brightness-6"

    def __init__(self, coordinator, entry, name) -> None:
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_mode"

    @property
    def native_value(self) -> str:
        return self._coordinator.mode


class StaircaseLuxSensor(StaircaseBaseSensor):
    """sensor.<name>_ambient_lux — mirrored illuminance."""

    _attr_name = "Ambient lux"
    _attr_icon = "mdi:brightness-5"
    _attr_device_class = SensorDeviceClass.ILLUMINANCE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = LIGHT_LUX

    def __init__(self, coordinator, entry, name) -> None:
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_ambient_lux"

    @property
    def native_value(self) -> float | None:
        return self._coordinator.lux_value


class TimeRemainingSensor(StaircaseBaseSensor):
    """sensor.<name>_time_remaining — countdown in seconds."""

    _attr_name = "Time remaining"
    _attr_icon = "mdi:timer-sand"
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry, name) -> None:
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_time_remaining"

    @property
    def native_value(self) -> int:
        return self._coordinator.time_remaining


class CurrentBrightnessSensor(StaircaseBaseSensor):
    """sensor.<name>_current_brightness — real brightness from light entity."""

    _attr_name = "Current brightness"
    _attr_icon = "mdi:brightness-percent"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry, name) -> None:
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_current_brightness"

    @property
    def native_value(self) -> int:
        return self._coordinator.current_brightness


class DirectionSensor(StaircaseBaseSensor):
    """sensor.<name>_direction — transit direction: up, down, none.

    up = bottom sensor first, then top (going upstairs).
    down = top sensor first, then bottom (going downstairs).
    none = no transit detected or idle.
    """

    _attr_name = "Direction"
    _attr_translation_key = "staircase_direction"
    _attr_icon = "mdi:swap-vertical"

    def __init__(self, coordinator, entry, name) -> None:
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_direction"

    @property
    def native_value(self) -> str:
        return self._coordinator.direction
