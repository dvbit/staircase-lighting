"""Constants for the Staircase Lighting integration.

Spec ref: Config Flow fields, entity defaults, domain identifier.
"""

DOMAIN = "staircase_lighting"

# --- Config Flow keys ---
# Step 1: Instance identification
CONF_NAME = "name"

# Step 2: Entity selection
CONF_SENSOR_BOTTOM = "sensor_bottom"
CONF_SENSOR_TOP = "sensor_top"
CONF_LIGHT_BOTTOM = "light_bottom"
CONF_LIGHT_TOP = "light_top"
CONF_LUX_SENSOR = "lux_sensor"

# Step 3: Parameters
CONF_TURN_OFF_DELAY = "turn_off_delay"
CONF_BRIGHTNESS = "brightness"
CONF_BRIGHTNESS_DIM = "brightness_dim"
CONF_LUX_THRESHOLD = "lux_threshold"
CONF_LUX_CONTROL_ENABLED = "lux_control_enabled"
CONF_WARNING_DIM_PCT = "warning_dim_pct"
CONF_WARNING_DIM_DURATION = "warning_dim_duration"

# Step 4: Dim mode
CONF_DIM_MODE = "dim_mode"
CONF_DIM_START = "dim_start"
CONF_DIM_END = "dim_end"
CONF_DIM_ENTITY = "dim_entity"

# --- Dim mode options ---
DIM_MODE_NONE = "none"
DIM_MODE_TIME_RANGE = "time_range"
DIM_MODE_EXTERNAL_ENTITY = "external_entity"

# --- Defaults (spec ref: Parameters table) ---
DEFAULT_TURN_OFF_DELAY = 60
DEFAULT_BRIGHTNESS = 100
DEFAULT_BRIGHTNESS_DIM = 20
DEFAULT_LUX_THRESHOLD = 50
DEFAULT_LUX_CONTROL_ENABLED = True
DEFAULT_WARNING_DIM_PCT = 30
DEFAULT_WARNING_DIM_DURATION = 10

# --- State values (spec ref: sensor state/mode values) ---
STATE_IDLE = "idle"
STATE_ACTIVE = "active"
STATE_WARNING = "warning"
MODE_NORMAL = "normal"
MODE_DIM = "dim"

# --- Direction values ---
DIR_NONE = "none"
DIR_UP = "up"
DIR_DOWN = "down"

# --- Platforms ---
PLATFORMS = ["binary_sensor", "button", "sensor", "number", "switch"]
