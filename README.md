# OSM Street Racer – Logitech G923

Drive through **real streets** fetched live from OpenStreetMap, using your
**Logitech G923** (or any compatible) racing wheel.

## Features

| Feature | Details |
|---|---|
| Real-world roads | Fetched from OpenStreetMap via Overpass API, cached locally |
| Logitech G923 | Steering, throttle, brake, clutch axes + force-feedback rumble |
| Keyboard fallback | WASD / arrow keys when no wheel is connected |
| Top-down view | Smooth camera follow, mouse-wheel / +/− zoom |
| Minimap | Inset overview with car position dot |
| HUD | Speed (km/h), distance, heading, elapsed time |
| Any location | Pass `--lat` / `--lon` to drive anywhere on Earth |

## Requirements

- Python 3.10+
- `pygame >= 2.1` (for joystick rumble support)
- `requests`
- Internet connection on first run (OSM data cached after that)

```bash
pip install -r requirements.txt
```

## Running

```bash
# Default: Times Square, New York
python src/main.py

# Paris, France
python src/main.py --lat 48.8566 --lon 2.3522

# London, UK
python src/main.py --lat 51.5074 --lon -0.1278

# Larger map area
python src/main.py --lat 40.7580 --lon -73.9855 --radius 0.015

# Verify your G923 axis layout
python src/main.py --calibrate

# Delete cached map data
python src/main.py --clear-cache
```

## Controls

| Input | Wheel | Keyboard |
|---|---|---|
| Steer | Steering wheel (axis 0) | A / D or ← / → |
| Accelerate | Throttle pedal (axis 1) | W / ↑ |
| Brake | Brake pedal (axis 2) | S / ↓ |
| Pause | – | P |
| Respawn | – | R |
| Zoom | Mouse wheel | + / − |
| Quit | – | ESC |

## G923 Axis Calibration

Connect the wheel, then run:
```bash
python src/main.py --calibrate
```
This prints all raw axis values in real time. If the steering or pedals feel
inverted, edit the constants in `src/config.py`:
```python
G923_AXIS_STEER    = 0   # change index if needed
G923_AXIS_THROTTLE = 1
G923_AXIS_BRAKE    = 2
G923_AXIS_CLUTCH   = 3

G923_INVERT_THROTTLE = True   # flip if pedal reads wrong direction
G923_INVERT_BRAKE    = True
```

## Project Structure

```
kk/
├── src/
│   ├── main.py          # entry point & CLI
│   ├── game.py          # game loop & state machine
│   ├── car_physics.py   # arcade car physics
│   ├── wheel_input.py   # G923 / gamepad input + force feedback
│   ├── osm_loader.py    # OpenStreetMap fetch & parse
│   ├── renderer.py      # pygame top-down rendering
│   └── config.py        # all tuneable constants
├── cache/               # auto-created – OSM JSON cache
├── requirements.txt
└── README.md
```

## Map Data

Road data comes from [OpenStreetMap](https://www.openstreetmap.org) via the
[Overpass API](https://overpass-api.de). It is cached in `cache/` after the
first download for each location.

© OpenStreetMap contributors, [ODbL](https://opendatacommons.org/licenses/odbl/).
