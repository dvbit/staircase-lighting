"""Config flow for the Staircase Lighting integration.

Spec ref: Config Flow — 4 steps (name, entities, parameters, dim mode).
Options Flow mirrors steps 2-4 for post-install modification without restart.
"""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_NAME,
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
    CONF_WARNING_DIM_PCT,
    CONF_WARNING_DIM_DURATION,
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
    DEFAULT_WARNING_DIM_PCT,
    DEFAULT_WARNING_DIM_DURATION,
)


# ------------------------------------------------------------------
# Reusable schema builders for config and options flows
# ------------------------------------------------------------------

def _entities_schema(defaults: dict | None = None) -> vol.Schema:
    """Build schema for Step 2: Entity selection.

    Spec ref: sensor_bottom, sensor_top (binary_sensor),
    light_bottom, light_top (light), lux_sensor (sensor, optional).
    """
    d = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_SENSOR_BOTTOM,
                default=d.get(CONF_SENSOR_BOTTOM, ""),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="binary_sensor")
            ),
            vol.Required(
                CONF_SENSOR_TOP,
                default=d.get(CONF_SENSOR_TOP, ""),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="binary_sensor")
            ),
            vol.Required(
                CONF_LIGHT_BOTTOM,
                default=d.get(CONF_LIGHT_BOTTOM, ""),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="light")
            ),
            vol.Required(
                CONF_LIGHT_TOP,
                default=d.get(CONF_LIGHT_TOP, ""),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="light")
            ),
            vol.Optional(
                CONF_LUX_SENSOR,
                default=d.get(CONF_LUX_SENSOR, ""),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class="illuminance",
                )
            ),
        }
    )


def _parameters_schema(defaults: dict | None = None) -> vol.Schema:
    """Build schema for Step 3: Parameters.

    Spec ref: turn_off_delay, brightness, brightness_dim,
    lux_threshold, lux_control_enabled with min/max/step/default.
    """
    d = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_TURN_OFF_DELAY,
                default=d.get(CONF_TURN_OFF_DELAY, DEFAULT_TURN_OFF_DELAY),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=10, max=300, step=10, mode="slider",
                    unit_of_measurement="s",
                )
            ),
            vol.Required(
                CONF_BRIGHTNESS,
                default=d.get(CONF_BRIGHTNESS, DEFAULT_BRIGHTNESS),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=100, step=1, mode="slider",
                    unit_of_measurement="%",
                )
            ),
            vol.Required(
                CONF_BRIGHTNESS_DIM,
                default=d.get(CONF_BRIGHTNESS_DIM, DEFAULT_BRIGHTNESS_DIM),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=100, step=1, mode="slider",
                    unit_of_measurement="%",
                )
            ),
            vol.Required(
                CONF_LUX_THRESHOLD,
                default=d.get(CONF_LUX_THRESHOLD, DEFAULT_LUX_THRESHOLD),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=1000, step=10, mode="slider",
                    unit_of_measurement="lx",
                )
            ),
            vol.Required(
                CONF_LUX_CONTROL_ENABLED,
                default=d.get(CONF_LUX_CONTROL_ENABLED, DEFAULT_LUX_CONTROL_ENABLED),
            ): selector.BooleanSelector(),
            vol.Required(
                CONF_WARNING_DIM_PCT,
                default=d.get(CONF_WARNING_DIM_PCT, DEFAULT_WARNING_DIM_PCT),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=100, step=1, mode="slider",
                    unit_of_measurement="%",
                )
            ),
            vol.Required(
                CONF_WARNING_DIM_DURATION,
                default=d.get(CONF_WARNING_DIM_DURATION, DEFAULT_WARNING_DIM_DURATION),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=60, step=1, mode="slider",
                    unit_of_measurement="s",
                )
            ),
        }
    )


def _dim_mode_schema(defaults: dict | None = None) -> vol.Schema:
    """Build schema for Step 4: Dim mode selection.

    Spec ref: mutually exclusive — none / time_range / external_entity.
    """
    d = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_DIM_MODE,
                default=d.get(CONF_DIM_MODE, DIM_MODE_NONE),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": DIM_MODE_NONE, "label": DIM_MODE_NONE},
                        {"value": DIM_MODE_TIME_RANGE, "label": DIM_MODE_TIME_RANGE},
                        {
                            "value": DIM_MODE_EXTERNAL_ENTITY,
                            "label": DIM_MODE_EXTERNAL_ENTITY,
                        },
                    ],
                    mode="dropdown",
                    translation_key="dim_mode",
                )
            ),
        }
    )


def _dim_time_schema(defaults: dict | None = None) -> vol.Schema:
    """Build schema for dim time range sub-step.

    Spec ref: dim_start, dim_end as HH:MM, supports midnight spanning.
    """
    d = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_DIM_START,
                default=d.get(CONF_DIM_START, "23:00"),
            ): selector.TimeSelector(),
            vol.Required(
                CONF_DIM_END,
                default=d.get(CONF_DIM_END, "07:00"),
            ): selector.TimeSelector(),
        }
    )


def _dim_entity_schema(defaults: dict | None = None) -> vol.Schema:
    """Build schema for dim external entity sub-step.

    Spec ref: dim_entity accepts binary_sensor or input_boolean.
    """
    d = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_DIM_ENTITY,
                default=d.get(CONF_DIM_ENTITY, ""),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["binary_sensor", "input_boolean"]
                )
            ),
        }
    )


# ==================================================================
# Config Flow
# ==================================================================


class StaircaseLightingConfigFlow(
    config_entries.ConfigFlow, domain=DOMAIN
):
    """Handle a config flow for Staircase Lighting.

    Spec ref: Config Flow — Steps 1 through 4.
    """

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow data accumulator."""
        self._data: dict = {}

    async def async_step_user(self, user_input=None):
        """Step 1: Instance name.

        Spec ref: Step 1 — name field.
        """
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_entities()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME): selector.TextSelector(),
                }
            ),
        )

    async def async_step_entities(self, user_input=None):
        """Step 2: Entity selection.

        Spec ref: Step 2 — sensor/light/lux entity selectors.
        """
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_parameters()

        return self.async_show_form(
            step_id="entities",
            data_schema=_entities_schema(),
        )

    async def async_step_parameters(self, user_input=None):
        """Step 3: Operational parameters.

        Spec ref: Step 3 — delay, brightness, lux threshold, lux control.
        """
        if user_input is not None:
            # NumberSelector returns float; cast to int per spec
            user_input[CONF_TURN_OFF_DELAY] = int(user_input[CONF_TURN_OFF_DELAY])
            user_input[CONF_BRIGHTNESS] = int(user_input[CONF_BRIGHTNESS])
            user_input[CONF_BRIGHTNESS_DIM] = int(user_input[CONF_BRIGHTNESS_DIM])
            user_input[CONF_LUX_THRESHOLD] = int(user_input[CONF_LUX_THRESHOLD])
            user_input[CONF_WARNING_DIM_PCT] = int(user_input[CONF_WARNING_DIM_PCT])
            user_input[CONF_WARNING_DIM_DURATION] = int(user_input[CONF_WARNING_DIM_DURATION])
            self._data.update(user_input)
            return await self.async_step_dim_mode()

        return self.async_show_form(
            step_id="parameters",
            data_schema=_parameters_schema(),
        )

    async def async_step_dim_mode(self, user_input=None):
        """Step 4: Dim mode selection.

        Spec ref: Step 4 — none / time_range / external_entity.
        Routes to sub-step if needed.
        """
        if user_input is not None:
            self._data.update(user_input)
            mode = user_input[CONF_DIM_MODE]
            if mode == DIM_MODE_TIME_RANGE:
                return await self.async_step_dim_time()
            if mode == DIM_MODE_EXTERNAL_ENTITY:
                return await self.async_step_dim_entity()
            # mode == none → finalize
            return self._async_create_entry()

        return self.async_show_form(
            step_id="dim_mode",
            data_schema=_dim_mode_schema(),
        )

    async def async_step_dim_time(self, user_input=None):
        """Sub-step: Dim time range configuration."""
        if user_input is not None:
            self._data.update(user_input)
            return self._async_create_entry()

        return self.async_show_form(
            step_id="dim_time",
            data_schema=_dim_time_schema(),
        )

    async def async_step_dim_entity(self, user_input=None):
        """Sub-step: Dim external entity configuration."""
        if user_input is not None:
            self._data.update(user_input)
            return self._async_create_entry()

        return self.async_show_form(
            step_id="dim_entity",
            data_schema=_dim_entity_schema(),
        )

    @callback
    def _async_create_entry(self):
        """Create the config entry with accumulated data."""
        return self.async_create_entry(
            title=self._data[CONF_NAME],
            data=self._data,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        return StaircaseLightingOptionsFlow(config_entry)


# ==================================================================
# Options Flow (spec ref: identical to steps 2-4, no restart needed)
# ==================================================================


class StaircaseLightingOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Staircase Lighting.

    Spec ref: Options Flow mirrors steps 2-4, modifiable post-install.
    """

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize with current config entry data as defaults."""
        self._data: dict = dict(config_entry.data)

    async def async_step_init(self, user_input=None):
        """Entry point — start with entities step."""
        return await self.async_step_entities(user_input)

    async def async_step_entities(self, user_input=None):
        """Options: entity selection."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_parameters()

        return self.async_show_form(
            step_id="entities",
            data_schema=_entities_schema(self._data),
        )

    async def async_step_parameters(self, user_input=None):
        """Options: operational parameters."""
        if user_input is not None:
            user_input[CONF_TURN_OFF_DELAY] = int(user_input[CONF_TURN_OFF_DELAY])
            user_input[CONF_BRIGHTNESS] = int(user_input[CONF_BRIGHTNESS])
            user_input[CONF_BRIGHTNESS_DIM] = int(user_input[CONF_BRIGHTNESS_DIM])
            user_input[CONF_LUX_THRESHOLD] = int(user_input[CONF_LUX_THRESHOLD])
            user_input[CONF_WARNING_DIM_PCT] = int(user_input[CONF_WARNING_DIM_PCT])
            user_input[CONF_WARNING_DIM_DURATION] = int(user_input[CONF_WARNING_DIM_DURATION])
            self._data.update(user_input)
            return await self.async_step_dim_mode()

        return self.async_show_form(
            step_id="parameters",
            data_schema=_parameters_schema(self._data),
        )

    async def async_step_dim_mode(self, user_input=None):
        """Options: dim mode selection."""
        if user_input is not None:
            self._data.update(user_input)
            mode = user_input[CONF_DIM_MODE]
            if mode == DIM_MODE_TIME_RANGE:
                return await self.async_step_dim_time()
            if mode == DIM_MODE_EXTERNAL_ENTITY:
                return await self.async_step_dim_entity()
            # Clear stale dim config when switching to 'none'
            self._data.pop(CONF_DIM_START, None)
            self._data.pop(CONF_DIM_END, None)
            self._data.pop(CONF_DIM_ENTITY, None)
            return self._async_save_options()

        return self.async_show_form(
            step_id="dim_mode",
            data_schema=_dim_mode_schema(self._data),
        )

    async def async_step_dim_time(self, user_input=None):
        """Options: dim time range."""
        if user_input is not None:
            self._data.update(user_input)
            # Clear stale entity config
            self._data.pop(CONF_DIM_ENTITY, None)
            return self._async_save_options()

        return self.async_show_form(
            step_id="dim_time",
            data_schema=_dim_time_schema(self._data),
        )

    async def async_step_dim_entity(self, user_input=None):
        """Options: dim external entity."""
        if user_input is not None:
            self._data.update(user_input)
            # Clear stale time config
            self._data.pop(CONF_DIM_START, None)
            self._data.pop(CONF_DIM_END, None)
            return self._async_save_options()

        return self.async_show_form(
            step_id="dim_entity",
            data_schema=_dim_entity_schema(self._data),
        )

    @callback
    def _async_save_options(self):
        """Save options and update config entry data.

        Spec ref: Options Flow without restart — updates entry data in place.
        """
        self.hass.config_entries.async_update_entry(
            self.config_entry, data=self._data
        )
        return self.async_create_entry(title="", data={})
