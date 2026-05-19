"""Switch platform for the Staircase Lighting integration.

Spec ref: Entità esposte — switch.<name>_lux_control.
Runtime toggle for lux-based gating. Bidirectionally linked to coordinator.
"""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
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
    """Set up switch entities from a config entry."""
    coordinator: StaircaseLightingCoordinator = hass.data[DOMAIN][entry.entry_id]
    name = entry.data[CONF_NAME]

    async_add_entities([LuxControlSwitch(coordinator, entry, name)])


class LuxControlSwitch(SwitchEntity):
    """Switch to enable/disable lux-based light gating.

    Spec ref: switch.<name>_lux_control — runtime toggle.
    When off, lights always activate regardless of ambient lux.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "lux_control"
    _attr_icon = "mdi:theme-light-dark"

    def __init__(
        self,
        coordinator: StaircaseLightingCoordinator,
        entry: ConfigEntry,
        name: str,
    ) -> None:
        """Initialize lux control switch."""
        self._coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_lux_control"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=name,
            manufacturer="Staircase Lighting",
            model="Virtual",
            sw_version="1.0.0",
        )

    @property
    def is_on(self) -> bool:
        """Return True if lux control is enabled."""
        return self._coordinator.lux_control_enabled

    async def async_turn_on(self, **kwargs) -> None:
        """Enable lux control."""
        self._coordinator.lux_control_enabled = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Disable lux control — lights always activate."""
        self._coordinator.lux_control_enabled = False
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Register update callback."""
        self._coordinator.async_add_update_callback(
            self._handle_coordinator_update
        )

    async def async_will_remove_from_hass(self) -> None:
        """Remove update callback."""
        self._coordinator.async_remove_update_callback(
            self._handle_coordinator_update
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle coordinator state update."""
        self.async_write_ha_state()
