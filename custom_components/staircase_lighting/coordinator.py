"""Coordinator for the Staircase Lighting integration.

Spec ref: Logica operativa (Coordinator) — handles sensor events,
zone timers, lux gating, dim mode determination, and light control.
Each instance is fully isolated (timers, state, parameters).
"""

from __future__ import annotations

import logging
from datetime import datetime, time as dt_time, timedelta
from time import monotonic
from typing import Any

from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, Event, callback, CALLBACK_TYPE
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers import event as evt

from .const import (
    CONF_SENSOR_BOTTOM,
    CONF_SENSOR_TOP,
    CONF_LIGHT_BOTTOM,
    CONF_LIGHT_TOP,
    CONF_LUX_SENSOR,
    CONF_TURN_OFF_DELAY,
    CONF_BRIGHTNESS,
    CONF_BRIGHTNESS_DIM,
    CONF_LUX_THRESHOLD,
    CONF_LUX_CONTROL_ENABLED,
    CONF_DIM_MODE,
    CONF_DIM_START,
    CONF_DIM_END,
    CONF_DIM_ENTITY,
    DIM_MODE_NONE,
    DIM_MODE_TIME_RANGE,
    DIM_MODE_EXTERNAL_ENTITY,
    DEFAULT_TURN_OFF_DELAY,
    DEFAULT_BRIGHTNESS,
    DEFAULT_BRIGHTNESS_DIM,
    DEFAULT_LUX_THRESHOLD,
    DEFAULT_LUX_CONTROL_ENABLED,
    STATE_IDLE,
    STATE_ACTIVE,
    MODE_NORMAL,
    MODE_DIM,
)

_LOGGER = logging.getLogger(__name__)


class StaircaseLightingCoordinator:
    """Manages the operational logic for a single staircase instance.

    Spec ref: each instance is completely isolated — timers, state
    and parameters are not shared between instances.
    """

    def __init__(self, hass: HomeAssistant, entry_data: dict[str, Any]) -> None:
        """Initialize coordinator with config entry data."""
        self.hass = hass

        # --- Entity IDs from config (spec ref: Step 2 entity selection) ---
        self.sensor_bottom: str = entry_data[CONF_SENSOR_BOTTOM]
        self.sensor_top: str = entry_data[CONF_SENSOR_TOP]
        self.light_bottom: str = entry_data[CONF_LIGHT_BOTTOM]
        self.light_top: str = entry_data[CONF_LIGHT_TOP]
        self.lux_sensor: str | None = entry_data.get(CONF_LUX_SENSOR)

        # --- Runtime parameters (spec ref: Step 3 parameters) ---
        # These are read at activation time, not at config time.
        self.turn_off_delay: int = entry_data.get(
            CONF_TURN_OFF_DELAY, DEFAULT_TURN_OFF_DELAY
        )
        self.brightness: int = entry_data.get(CONF_BRIGHTNESS, DEFAULT_BRIGHTNESS)
        self.brightness_dim: int = entry_data.get(
            CONF_BRIGHTNESS_DIM, DEFAULT_BRIGHTNESS_DIM
        )
        self.lux_threshold: int = entry_data.get(
            CONF_LUX_THRESHOLD, DEFAULT_LUX_THRESHOLD
        )
        self.lux_control_enabled: bool = entry_data.get(
            CONF_LUX_CONTROL_ENABLED, DEFAULT_LUX_CONTROL_ENABLED
        )

        # --- Dim mode config (spec ref: Step 4 dim mode) ---
        self.dim_mode: str = entry_data.get(CONF_DIM_MODE, DIM_MODE_NONE)
        self.dim_start: str | None = entry_data.get(CONF_DIM_START)
        self.dim_end: str | None = entry_data.get(CONF_DIM_END)
        self.dim_entity: str | None = entry_data.get(CONF_DIM_ENTITY)

        # --- Internal state ---
        self._state: str = STATE_IDLE
        self._mode: str = MODE_NORMAL
        self._timer_bottom: CALLBACK_TYPE | None = None
        self._timer_top: CALLBACK_TYPE | None = None
        self._listeners: list[CALLBACK_TYPE] = []
        self._update_callbacks: list[callback] = []

        # --- Timer expiry timestamps (monotonic) for countdown calculation ---
        self._expiry_bottom: float | None = None
        self._expiry_top: float | None = None

        # --- 1-second countdown interval handle ---
        self._countdown_unsub: CALLBACK_TYPE | None = None

        # --- Current brightness applied (0 when lights off) ---
        self._current_brightness_pct: int = 0

        # --- Mirrored sensor states (real-time via state change listeners) ---
        self._motion_bottom: bool = False
        self._motion_top: bool = False
        self._lux_value: float | None = None

    # ------------------------------------------------------------------
    # State properties (spec ref: Entità esposte — sensor state/mode)
    # ------------------------------------------------------------------

    @property
    def state(self) -> str:
        """Current staircase state: idle or active."""
        return self._state

    @property
    def mode(self) -> str:
        """Current brightness mode: normal or dim."""
        return self._mode

    @property
    def motion_bottom(self) -> bool:
        """Mirrored state of the bottom motion sensor."""
        return self._motion_bottom

    @property
    def motion_top(self) -> bool:
        """Mirrored state of the top motion sensor."""
        return self._motion_top

    @property
    def lux_value(self) -> float | None:
        """Mirrored value of the ambient lux sensor (None if unconfigured)."""
        return self._lux_value

    @property
    def time_remaining(self) -> int:
        """Seconds remaining until lights turn off.

        Returns the maximum of the two zone timers (both must expire
        before lights turn off). Returns 0 when idle.
        """
        if self._state == STATE_IDLE:
            return 0
        now = monotonic()
        remaining_bottom = max(0, self._expiry_bottom - now) if self._expiry_bottom else 0
        remaining_top = max(0, self._expiry_top - now) if self._expiry_top else 0
        return int(max(remaining_bottom, remaining_top))

    @property
    def current_brightness(self) -> int:
        """Current brightness percentage applied to the lights.

        Reads the brightness attribute from the bottom light entity.
        Returns 0 when lights are off. HA brightness is 0-255, converted to %.
        """
        state = self.hass.states.get(self.light_bottom)
        if state is None or state.state != STATE_ON:
            return 0
        brightness = state.attributes.get("brightness")
        if brightness is None:
            return 0
        try:
            return round(int(brightness) * 100 / 255)
        except (ValueError, TypeError):
            return 0

    # ------------------------------------------------------------------
    # Callback registration for entity updates
    # ------------------------------------------------------------------

    @callback
    def async_add_update_callback(self, cb: callback) -> None:
        """Register a callback to notify entities of state changes."""
        self._update_callbacks.append(cb)

    @callback
    def async_remove_update_callback(self, cb: callback) -> None:
        """Unregister a callback."""
        if cb in self._update_callbacks:
            self._update_callbacks.remove(cb)

    @callback
    def _async_notify_update(self) -> None:
        """Notify all registered entities that state has changed."""
        for cb in self._update_callbacks:
            cb()

    # ------------------------------------------------------------------
    # Start / Stop (spec ref: config_entry_unload)
    # ------------------------------------------------------------------

    async def async_start(self) -> None:
        """Start listening to sensor state changes.

        Spec ref: uses async_track_state_change_event for sensor monitoring.
        Also tracks motion, lux, and light sensors for real-time mirrored entities.
        Starts a 1-second interval for countdown updates.
        """
        self._listeners.append(
            async_track_state_change_event(
                self.hass,
                self.sensor_bottom,
                self._async_on_sensor_bottom,
            )
        )
        self._listeners.append(
            async_track_state_change_event(
                self.hass,
                self.sensor_top,
                self._async_on_sensor_top,
            )
        )

        # --- Lux sensor listener for real-time mirroring ---
        if self.lux_sensor:
            self._listeners.append(
                async_track_state_change_event(
                    self.hass,
                    self.lux_sensor,
                    self._async_on_lux_changed,
                )
            )

        # --- Light state listeners for real-time brightness mirroring ---
        self._listeners.append(
            async_track_state_change_event(
                self.hass,
                self.light_bottom,
                self._async_on_light_changed,
            )
        )
        self._listeners.append(
            async_track_state_change_event(
                self.hass,
                self.light_top,
                self._async_on_light_changed,
            )
        )

        # --- 1-second countdown interval for time_remaining sensor ---
        self._countdown_unsub = async_track_time_interval(
            self.hass,
            self._async_countdown_tick,
            timedelta(seconds=1),
        )

        # --- Read initial states for mirrored entities ---
        self._sync_initial_states()

        _LOGGER.debug(
            "Coordinator started: bottom=%s, top=%s, lux=%s",
            self.sensor_bottom,
            self.sensor_top,
            self.lux_sensor,
        )

    async def async_stop(self) -> None:
        """Stop listeners and cancel active timers.

        Spec ref: config_entry_unload must cancel timers and remove listeners.
        """
        for unsub in self._listeners:
            unsub()
        self._listeners.clear()

        # Cancel countdown interval
        if self._countdown_unsub is not None:
            self._countdown_unsub()
            self._countdown_unsub = None

        if self._timer_bottom is not None:
            self._timer_bottom()
            self._timer_bottom = None
        if self._timer_top is not None:
            self._timer_top()
            self._timer_top = None

        self._expiry_bottom = None
        self._expiry_top = None

        _LOGGER.debug("Coordinator stopped, timers cancelled")

    # ------------------------------------------------------------------
    # Initial state sync for mirrored entities
    # ------------------------------------------------------------------

    @callback
    def _sync_initial_states(self) -> None:
        """Read current states of motion and lux sensors at startup.

        Ensures mirrored entities reflect the correct state immediately
        after coordinator start, before any state_change events fire.
        """
        bottom = self.hass.states.get(self.sensor_bottom)
        self._motion_bottom = (
            bottom is not None and bottom.state == STATE_ON
        )

        top = self.hass.states.get(self.sensor_top)
        self._motion_top = (
            top is not None and top.state == STATE_ON
        )

        if self.lux_sensor:
            lux = self.hass.states.get(self.lux_sensor)
            if lux is not None and lux.state not in (
                STATE_UNAVAILABLE, STATE_UNKNOWN
            ):
                try:
                    self._lux_value = float(lux.state)
                except (ValueError, TypeError):
                    self._lux_value = None
            else:
                self._lux_value = None

    # ------------------------------------------------------------------
    # Sensor event handlers
    # ------------------------------------------------------------------

    @callback
    def _async_on_sensor_bottom(self, event: Event) -> None:
        """Handle bottom sensor state change.

        Spec ref: Attivazione sensore — when sensor passes to 'on'.
        Also updates mirrored motion state in real-time.
        """
        new_state = event.data.get("new_state")
        if new_state is None:
            return

        # --- Update mirrored state for binary_sensor entity ---
        self._motion_bottom = new_state.state == STATE_ON
        self._async_notify_update()

        # --- Trigger activation logic only on 'on' transition ---
        if new_state.state != STATE_ON:
            return
        self._async_handle_activation("bottom")

    @callback
    def _async_on_sensor_top(self, event: Event) -> None:
        """Handle top sensor state change.

        Spec ref: Attivazione sensore — when sensor passes to 'on'.
        Also updates mirrored motion state in real-time.
        """
        new_state = event.data.get("new_state")
        if new_state is None:
            return

        # --- Update mirrored state for binary_sensor entity ---
        self._motion_top = new_state.state == STATE_ON
        self._async_notify_update()

        # --- Trigger activation logic only on 'on' transition ---
        if new_state.state != STATE_ON:
            return
        self._async_handle_activation("top")

    @callback
    def _async_on_lux_changed(self, event: Event) -> None:
        """Handle lux sensor state change for real-time mirroring.

        Updates the mirrored lux value displayed by the sensor entity.
        """
        new_state = event.data.get("new_state")
        if new_state is None:
            self._lux_value = None
        elif new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            self._lux_value = None
        else:
            try:
                self._lux_value = float(new_state.state)
            except (ValueError, TypeError):
                self._lux_value = None
        self._async_notify_update()

    @callback
    def _async_on_light_changed(self, event: Event) -> None:
        """Handle light entity state change for real-time brightness mirroring.

        Notifies entities so current_brightness property is re-read.
        """
        self._async_notify_update()

    @callback
    def _async_countdown_tick(self, _now: Any) -> None:
        """1-second interval tick to update time_remaining sensor.

        Only notifies when active (timers running) to avoid unnecessary updates.
        """
        if self._state == STATE_ACTIVE:
            self._async_notify_update()

    # ------------------------------------------------------------------
    # Core activation logic
    # ------------------------------------------------------------------

    @callback
    def _async_handle_activation(self, zone: str) -> None:
        """Process a sensor activation event for the given zone.

        Spec ref: Attivazione sensore — check lux, determine mode,
        turn on lights, start/restart zone timer.
        """
        # --- Lux gating (spec ref: Condizione di accensione) ---
        if not self._check_lux_condition():
            _LOGGER.debug("Lux condition not met, ignoring %s activation", zone)
            return

        # --- Determine dim mode (spec ref: Determinazione modalità luminosità) ---
        # Mode is fixed at activation time for the cycle.
        current_mode = self._determine_mode()
        if self._state == STATE_IDLE:
            self._mode = current_mode

        brightness_pct = (
            self.brightness_dim if self._mode == MODE_DIM else self.brightness
        )

        # --- Turn on both lights (spec ref: forces brightness even if already on) ---
        self.hass.async_create_task(
            self._async_turn_on_lights(brightness_pct)
        )

        # --- Start/restart zone timer (spec ref: async_call_later) ---
        # Read delay at activation time, not at config time.
        delay = self.turn_off_delay
        if zone == "bottom":
            if self._timer_bottom is not None:
                self._timer_bottom()
            self._timer_bottom = evt.async_call_later(
                self.hass, delay, self._async_timer_bottom_expired
            )
            self._expiry_bottom = monotonic() + delay
        else:
            if self._timer_top is not None:
                self._timer_top()
            self._timer_top = evt.async_call_later(
                self.hass, delay, self._async_timer_top_expired
            )
            self._expiry_top = monotonic() + delay

        # --- Update state ---
        self._state = STATE_ACTIVE
        self._async_notify_update()
        _LOGGER.debug(
            "Zone %s activated, mode=%s, brightness=%d%%, delay=%ds",
            zone,
            self._mode,
            brightness_pct,
            delay,
        )

    # ------------------------------------------------------------------
    # Lux condition check
    # ------------------------------------------------------------------

    def _check_lux_condition(self) -> bool:
        """Evaluate whether lights should turn on based on lux.

        Spec ref: Condizione di accensione (controllo lux) —
        returns True if any of the fail-safe conditions are met
        or lux is below threshold.
        """
        # Disabled → always allow
        if not self.lux_control_enabled:
            return True

        # No sensor configured → fail-safe allow
        if not self.lux_sensor:
            return True

        state = self.hass.states.get(self.lux_sensor)

        # Unavailable/unknown → fail-safe allow
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return True

        try:
            current_lux = float(state.state)
        except (ValueError, TypeError):
            # Unparseable → fail-safe allow
            return True

        return current_lux < self.lux_threshold

    # ------------------------------------------------------------------
    # Dim mode determination
    # ------------------------------------------------------------------

    def _determine_mode(self) -> str:
        """Determine current brightness mode at activation time.

        Spec ref: Determinazione modalità luminosità —
        dim_entity OR time_range, mutually exclusive by config.
        """
        if self.dim_mode == DIM_MODE_EXTERNAL_ENTITY and self.dim_entity:
            state = self.hass.states.get(self.dim_entity)
            if state is not None and state.state == STATE_ON:
                return MODE_DIM
            return MODE_NORMAL

        if self.dim_mode == DIM_MODE_TIME_RANGE and self.dim_start and self.dim_end:
            return self._check_time_range()

        # DIM_MODE_NONE or unconfigured → always normal
        return MODE_NORMAL

    def _check_time_range(self) -> str:
        """Check if current time falls within dim time range.

        Spec ref: supports midnight-spanning ranges (e.g. 23:00–07:00).
        """
        now = datetime.now().time()
        try:
            start = dt_time.fromisoformat(self.dim_start)
            end = dt_time.fromisoformat(self.dim_end)
        except (ValueError, TypeError):
            _LOGGER.warning(
                "Invalid dim time range: %s–%s, defaulting to normal",
                self.dim_start,
                self.dim_end,
            )
            return MODE_NORMAL

        # Spec ref: midnight-spanning range handling
        if start <= end:
            # Same-day range (e.g. 08:00–22:00)
            if start <= now < end:
                return MODE_DIM
        else:
            # Midnight-spanning range (e.g. 23:00–07:00)
            if now >= start or now < end:
                return MODE_DIM

        return MODE_NORMAL

    # ------------------------------------------------------------------
    # Light control
    # ------------------------------------------------------------------

    async def _async_turn_on_lights(self, brightness_pct: int) -> None:
        """Turn on both staircase lights at the specified brightness.

        Spec ref: accende light_bottom e light_top alla luminosità
        corrispondente, anche se già accese (forza luminosità).
        brightness_pct is 1-100, HA light.turn_on expects 0-255.
        """
        brightness_value = round(brightness_pct * 255 / 100)
        for light_id in (self.light_bottom, self.light_top):
            await self.hass.services.async_call(
                "light",
                "turn_on",
                {"entity_id": light_id, "brightness": brightness_value},
            )

    async def _async_turn_off_lights(self) -> None:
        """Turn off both staircase lights."""
        for light_id in (self.light_bottom, self.light_top):
            await self.hass.services.async_call(
                "light",
                "turn_off",
                {"entity_id": light_id},
            )

    # ------------------------------------------------------------------
    # Timer expiration handlers
    # ------------------------------------------------------------------

    @callback
    def _async_timer_bottom_expired(self, _now: Any) -> None:
        """Handle bottom zone timer expiration.

        Spec ref: Scadenza timer di zona — turn off only when BOTH expired.
        """
        self._timer_bottom = None
        self._expiry_bottom = None
        self._async_check_all_timers_expired()

    @callback
    def _async_timer_top_expired(self, _now: Any) -> None:
        """Handle top zone timer expiration.

        Spec ref: Scadenza timer di zona — turn off only when BOTH expired.
        """
        self._timer_top = None
        self._expiry_top = None
        self._async_check_all_timers_expired()

    @callback
    def _async_check_all_timers_expired(self) -> None:
        """Check if both zone timers have expired; if so, turn off lights.

        Spec ref: if both timers expired → turn off lights, set idle.
        If one still active → no action, state remains active.
        """
        if self._timer_bottom is None and self._timer_top is None:
            self._state = STATE_IDLE
            self._mode = MODE_NORMAL
            self._current_brightness_pct = 0
            self.hass.async_create_task(self._async_turn_off_lights())
            self._async_notify_update()
            _LOGGER.debug("Both timers expired, lights off, state=idle")
    # ------------------------------------------------------------------
    # Button action: set lux threshold to current lux value
    # ------------------------------------------------------------------

    @callback
    def set_lux_threshold_to_current(self) -> bool:
        """Set lux_threshold to the current ambient lux reading.

        Returns True if successful, False if sensor is unavailable.
        Used by the set_lux_threshold button entity.
        """
        if self._lux_value is not None:
            self.lux_threshold = int(self._lux_value)
            self._async_notify_update()
            _LOGGER.info(
                "Lux threshold set to current value: %d lx",
                self.lux_threshold,
            )
            return True

        _LOGGER.warning(
            "Cannot set lux threshold: lux sensor unavailable or not configured"
        )
        return False
