"""Sensor platform for the Staircase Lighting integration.

Spec ref: Entità esposte — sensor.<name>_state (idle/active),
sensor.<name>_mode (normal/dim).
"""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
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
    """Set up sensor entities from a config entry."""
    coordinator: StaircaseLightingCoordinator = hass.data[DOMAIN][entry.entry_id]
    name = entry.data[CONF_NAME]

    async_add_entities(
        [
            StaircaseStateSensor(coordinator, entry, name),
            StaircaseModeSensor(coordinator, entry, name),
        ]
    )


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
