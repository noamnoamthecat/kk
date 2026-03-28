# OSM Quest Explorer – Logitech G923

Explore **real streets** from OpenStreetMap data using your **Logitech G923** wheel.
Every session drops you in a **randomly selected city anywhere on Earth**.
Complete quests by driving to real named locations – cafés, parks, museums,
landmarks, and more.

## How it works

1. **Random city** is picked from a list of 100+ world cities on each launch.
2. Road data and **Points of Interest** are fetched from OpenStreetMap (cached after first download).
3. A **quest** appears: "Navigate to [real place name]" – e.g. a café, museum, viewpoint, park.
4. A **navigation arrow** on your car points toward the target; the **minimap** shows both your position and the quest marker.
5. Reach the target → quest complete → score added → next quest generated immediately.
6. **Score bonus** for speed; **streak multiplier (×1.5)** kicks in after 3 consecutive completions.

## Features

| Feature | Details |
|---|---|
| Random real location | 100+ world cities, random offset per session |
| Real named destinations | Fetched from OSM: amenities, tourism, historic, leisure, shops |
| Waypoint fallback | If no POIs nearby, uses random road-network points |
| Navigation arrow | Points from your car to the quest target |
| Minimap | Road network + POI dots + quest marker + car dot |
| Score system | Distance-based points, time bonus, streak ×1.5 |
| G923 wheel | Steering, throttle, brake, clutch + force-feedback on completion |
| Keyboard fallback | WASD / arrow keys when no wheel connected |

## Requirements

```bash
pip install -r requirements.txt
```

- Python 3.10+
- `pygame >= 2.1`
- `requests`
- Internet connection (first run per location only)

## Running

```bash
# Random city every time (default)
python src/main.py

# Force a specific city
python src/main.py --city "Tokyo"
python src/main.py --city "Paris"
python src/main.py --city "Buenos Aires"

# Exact coordinates
python src/main.py --lat 48.8566 --lon 2.3522 --city "Paris"

# Larger map area (more quests)
python src/main.py --radius 0.015

# See all available cities
python src/main.py --list-cities

# Verify your G923 axis layout
python src/main.py --calibrate

# Clear cached map data
python src/main.py --clear-cache
```

## Controls

| Action | Wheel (G923) | Keyboard |
|---|---|---|
| Steer | Steering wheel | A / D or ← / → |
| Accelerate | Throttle pedal | W / ↑ |
| Brake | Brake pedal | S / ↓ |
| Pause | – | P |
| Skip quest | – | N |
| Respawn | – | R |
| Zoom in/out | – | + / − or scroll |
| Quit | – | ESC |

## Quest types

| Type | Example |
|---|---|
| Navigate to named POI | "Visit Musée d'Orsay" |
| Find amenity | "Find the café called Le Marais" |
| Discover historic site | "Discover Notre-Dame Cathedral" |
| Reach natural feature | "Reach Mont Blanc" |
| Road waypoint (fallback) | "Reach Waypoint #4" |

## G923 Calibration

```bash
python src/main.py --calibrate
```

Prints all raw axis values live. Edit `src/config.py` if axes feel wrong:

```python
G923_AXIS_STEER    = 0
G923_AXIS_THROTTLE = 1
G923_AXIS_BRAKE    = 2
G923_INVERT_THROTTLE = True   # flip if pedal reads backwards
G923_INVERT_BRAKE    = True
```

## Project Structure

```
kk/
├── src/
│   ├── main.py            # CLI entry point
│   ├── game.py            # game loop & state machine
│   ├── location_picker.py # random city selection (100+ world cities)
│   ├── quest_system.py    # quest generation, scoring, streak logic
│   ├── osm_loader.py      # OpenStreetMap fetch + POI parsing
│   ├── car_physics.py     # arcade car physics
│   ├── wheel_input.py     # G923 / gamepad + force-feedback
│   ├── renderer.py        # pygame top-down rendering + quest UI
│   └── config.py          # all tuneable constants
├── cache/                 # auto-created – OSM JSON cache
├── requirements.txt
└── README.md
```

## Map & POI Data

© [OpenStreetMap](https://www.openstreetmap.org) contributors,
[ODbL](https://opendatacommons.org/licenses/odbl/).
Fetched via [Overpass API](https://overpass-api.de).
