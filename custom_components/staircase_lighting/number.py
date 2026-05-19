"""Number platform for the Staircase Lighting integration.

Spec ref: Entità esposte — number entities for runtime parameter adjustment.
Bidirectionally linked to coordinator: dashboard changes update internal
values immediately without restart. Values read at activation time.
"""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
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
    """Set up number entities from a config entry."""
    coordinator: StaircaseLightingCoordinator = hass.data[DOMAIN][entry.entry_id]
    name = entry.data[CONF_NAME]

    async_add_entities(
        [
            TurnOffDelayNumber(coordinator, entry, name),
            BrightnessNumber(coordinator, entry, name),
            BrightnessDimNumber(coordinator, entry, name),
            LuxThresholdNumber(coordinator, entry, name),
        ]
    )


class StaircaseBaseNumber(NumberEntity):
    """Base class for staircase number entities with shared device info."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_mode = NumberMode.SLIDER

    def __init__(
        self,
        coordinator: StaircaseLightingCoordinator,
        entry: ConfigEntry,
        name: str,
    ) -> None:
        """Initialize base number entity."""
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
        """Handle coordinator state update."""
        self.async_write_ha_state()


class TurnOffDelayNumber(StaircaseBaseNumber):
    """Runtime-adjustable turn-off delay.

    Spec ref: number.<name>_turn_off_delay — seconds, range 10-300, step 10.
    Bidirectional: changes from dashboard update coordinator immediately.
    """

    _attr_translation_key = "turn_off_delay"
    _attr_icon = "mdi:timer-outline"
    _attr_native_min_value = 10
    _attr_native_max_value = 300
    _attr_native_step = 10
    _attr_native_unit_of_measurement = "s"

    def __init__(self, coordinator, entry, name) -> None:
        """Initialize turn-off delay number."""
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_turn_off_delay"

    @property
    def native_value(self) -> float:
        """Return current delay value from coordinator."""
        return self._coordinator.turn_off_delay

    async def async_set_native_value(self, value: float) -> None:
        """Update coordinator delay value.

        Spec ref: bidirectional link, immediate effect at next activation.
        """
        self._coordinator.turn_off_delay = int(value)
        self.async_write_ha_state()


class BrightnessNumber(StaircaseBaseNumber):
    """Runtime-adjustable normal brightness.

    Spec ref: number.<name>_brightness — %, range 1-100, step 1.
    """

    _attr_translation_key = "brightness"
    _attr_icon = "mdi:brightness-7"
    _attr_native_min_value = 1
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "%"

    def __init__(self, coordinator, entry, name) -> None:
        """Initialize brightness number."""
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_brightness"

    @property
    def native_value(self) -> float:
        """Return current brightness from coordinator."""
        return self._coordinator.brightness

    async def async_set_native_value(self, value: float) -> None:
        """Update coordinator brightness value."""
        self._coordinator.brightness = int(value)
        self.async_write_ha_state()


class BrightnessDimNumber(StaircaseBaseNumber):
    """Runtime-adjustable dim brightness.

    Spec ref: number.<name>_brightness_dim — %, range 1-100, step 1.
    """

    _attr_translation_key = "brightness_dim"
    _attr_icon = "mdi:brightness-5"
    _attr_native_min_value = 1
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "%"

    def __init__(self, coordinator, entry, name) -> None:
        """Initialize dim brightness number."""
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_brightness_dim"

    @property
    def native_value(self) -> float:
        """Return current dim brightness from coordinator."""
        return self._coordinator.brightness_dim

    async def async_set_native_value(self, value: float) -> None:
        """Update coordinator dim brightness value."""
        self._coordinator.brightness_dim = int(value)
        self.async_write_ha_state()


class LuxThresholdNumber(StaircaseBaseNumber):
    """Runtime-adjustable lux threshold.

    Spec ref: number.<name>_lux_threshold — lux, range 0-1000, step 10.
    """

    _attr_translation_key = "lux_threshold"
    _attr_icon = "mdi:weather-sunny"
    _attr_native_min_value = 0
    _attr_native_max_value = 1000
    _attr_native_step = 10
    _attr_native_unit_of_measurement = "lx"

    def __init__(self, coordinator, entry, name) -> None:
        """Initialize lux threshold number."""
        super().__init__(coordinator, entry, name)
        self._attr_unique_id = f"{entry.entry_id}_lux_threshold"

    @property
    def native_value(self) -> float:
        """Return current lux threshold from coordinator."""
        return self._coordinator.lux_threshold

    async def async_set_native_value(self, value: float) -> None:
        """Update coordinator lux threshold value."""
        self._coordinator.lux_threshold = int(value)
        self.async_write_ha_state()
