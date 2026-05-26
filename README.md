# Staircase Lighting

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Custom Home Assistant integration for automatic staircase lighting with zone-based timers, lux gating, and dim mode support. Each staircase is configured as an independent instance via the UI.

## Features

- **Dual-zone motion detection**: independent sensors for bottom and top of staircase
- **Zone-based timers**: lights stay on until both zone timers have expired
- **Lux-based gating**: optional ambient light check before turning on lights
- **Dim mode**: reduced brightness via time range or external entity
- **Runtime adjustable**: all parameters can be changed from the dashboard without restart
- **Multi-instance**: configure as many staircases as needed, fully isolated
- **Localized**: English, Italian, French, Spanish, German

## Requirements

- Home Assistant 2024.1 or newer
- HACS installed

## Installation

### HACS (recommended)

1. Open HACS → Integrations → 3-dot menu → Custom repositories
2. Add `https://github.com/dvbit/staircase_lighting` as **Integration**
3. Search "Staircase Lighting" and install
4. Restart Home Assistant

### Manual

1. Download the latest release zip
2. Extract `custom_components/staircase_lighting/` into your HA `config/custom_components/`
3. Restart Home Assistant

## Configuration

Go to **Settings → Devices & Services → Add Integration → Staircase Lighting**.

### Step 1 — Name
| Field | Description |
|---|---|
| Name | A descriptive name for this staircase (e.g. "First Floor Stairs") |

### Step 2 — Entities
| Field | Description |
|---|---|
| Bottom motion sensor | `binary_sensor` at the bottom of the staircase |
| Top motion sensor | `binary_sensor` at the top of the staircase |
| Bottom light | `light` entity at the bottom |
| Top light | `light` entity at the top |
| Ambient light sensor | Optional `sensor` with `illuminance` device class |

### Step 3 — Parameters
| Field | Range | Default | Description |
|---|---|---|---|
| Turn-off delay | 10–300 s | 60 | Seconds before zone timer expires |
| Normal brightness | 1–100 % | 100 | Brightness in normal mode |
| Dim brightness | 1–100 % | 20 | Brightness in dim mode |
| Lux threshold | 0–1000 lx | 50 | Below this value, lights turn on |
| Enable lux control | on/off | on | Toggle lux-based gating |

### Step 4 — Dim Mode
Choose one of:
- **Disabled**: always normal brightness
- **Time range**: dim during a time window (supports midnight-spanning, e.g. 23:00–07:00)
- **External entity**: dim when a `binary_sensor` or `input_boolean` is ON

## Exposed Entities

For each configured staircase (example name: "Hall Stairs"):

| Entity | Type | Description |
|---|---|---|
| `binary_sensor.hall_stairs_motion_bottom` | binary_sensor | Real-time bottom motion sensor state |
| `binary_sensor.hall_stairs_motion_top` | binary_sensor | Real-time top motion sensor state |
| `sensor.hall_stairs_state` | sensor | `idle` or `active` |
| `sensor.hall_stairs_mode` | sensor | `normal` or `dim` |
| `sensor.hall_stairs_time_remaining` | sensor | Seconds until lights turn off (0 when idle) |
| `sensor.hall_stairs_current_brightness` | sensor | Current brightness % from the light entity |
| `sensor.hall_stairs_ambient_lux` | sensor | Real-time ambient lux (only if lux sensor configured) |
| `number.hall_stairs_turn_off_delay` | number | Runtime delay (slider) |
| `number.hall_stairs_brightness` | number | Runtime normal brightness |
| `number.hall_stairs_brightness_dim` | number | Runtime dim brightness |
| `number.hall_stairs_lux_threshold` | number | Runtime lux threshold |
| `switch.hall_stairs_lux_control` | switch | Enable/disable lux gating |
| `button.hall_stairs_set_lux_threshold` | button | Set lux threshold to current ambient value |

## Usage Examples

### Example 1 — Basic staircase (no lux, no dim)

Configure with two PIR sensors and two lights. Leave lux sensor empty, set dim mode to "Disabled". The lights turn on at 100% when motion is detected and turn off after 60 seconds of inactivity.

### Example 2 — Lux-controlled staircase

Add an illuminance sensor (e.g. `sensor.hallway_lux`). Set threshold to 30 lx. Lights only turn on when ambient light is below 30 lx. Disable lux control from the dashboard switch to override temporarily.

### Example 3 — Night dim mode with time range

Set dim mode to "Time range", start 23:00, end 07:00. During nighttime, lights turn on at 20% brightness. During the day, normal brightness applies. Adjust `number.hall_stairs_brightness_dim` from the dashboard to fine-tune.

### Example 4 — Dim via external entity

Create an `input_boolean.night_mode` helper. Set dim mode to "External entity" and select it. Toggle the boolean from an automation or manually. When ON, the staircase uses dim brightness.

## Operational Logic

1. **Motion detected** on either zone sensor
2. **Lux check**: if lux control is enabled and sensor reads above threshold → event ignored
3. **Mode determination**: check dim condition (time range or entity) → set `normal` or `dim`
4. **Turn on** both lights at the determined brightness (forces brightness even if already on)
5. **Start/restart** the zone timer for the triggered zone
6. **Timer expiry**: when a zone timer expires, check if the other is also expired
   - Both expired → turn off all lights, state = `idle`
   - One still active → no action, state remains `active`

Mode is locked at activation and does not change mid-cycle.

## Specification

This integration was built from the following consolidated requirement:

- Config flow: 4 steps (name, entities, parameters, dim mode)
- Dim mode: mutually exclusive — none / time_range / external_entity
- Single time range per instance, midnight-spanning supported
- Lux gating with fail-safe (missing/unavailable sensor = allow)
- Zone timers via `async_call_later`, turn off only when both expired
- Bidirectional number/switch entities — immediate effect at next cycle
- Mirrored binary sensors (motion bottom/top) and lux sensor on virtual device
- Time remaining countdown sensor (1s update interval)
- Current brightness sensor (reads real brightness attribute from light entity)
- Button to set lux threshold to current ambient lux value
- Options flow mirrors config flow steps 2-4, no restart required
- Full instance isolation
- Minimum compatibility: Home Assistant 2024.1

## License

MIT
