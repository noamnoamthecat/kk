"""
Configuration for the OSM Quest Explorer.
Logitech G923 axis/button mappings and game settings.
"""

# ── Window ──────────────────────────────────────────────────────────────────
WINDOW_TITLE  = "OSM Quest Explorer – Logitech G923"
WINDOW_WIDTH  = 1280
WINDOW_HEIGHT = 720
TARGET_FPS    = 60

# ── Colours ──────────────────────────────────────────────────────────────────
BG_COLOR            = (30,  30,  30)   # off-road
ROAD_COLORS = {
    "motorway":    (50,  100, 200),
    "trunk":       (80,  140, 200),
    "primary":     (200, 160,  40),
    "secondary":   (200, 200,  60),
    "tertiary":    (160, 160, 160),
    "residential": (120, 120, 120),
    "service":     ( 90,  90,  90),
    "unclassified":(100, 100, 100),
    "default":     ( 80,  80,  80),
}
ROAD_WIDTHS = {
    "motorway":    12,
    "trunk":       10,
    "primary":      8,
    "secondary":    7,
    "tertiary":     5,
    "residential":  4,
    "service":      3,
    "unclassified": 3,
    "default":      3,
}
CAR_COLOR       = (255,  80,  80)
CAR_OUTLINE     = (255, 255, 255)
HUD_BG          = (  0,   0,   0, 160)
HUD_TEXT        = (255, 255, 255)
MINIMAP_BG      = ( 20,  20,  20, 200)
MINIMAP_DOT     = (255,  80,  80)

# ── OSM / Map ─────────────────────────────────────────────────────────────────
# Default location: Times Square, New York
DEFAULT_LAT   =  40.7580
DEFAULT_LON   = -73.9855
# Approx half-side of the bounding box in degrees (~800 m)
MAP_RADIUS_DEG = 0.007

OVERPASS_URL  = "https://overpass-api.de/api/interpreter"
CACHE_DIR     = "cache"

HIGHWAY_TYPES = [
    "motorway", "motorway_link",
    "trunk", "trunk_link",
    "primary", "primary_link",
    "secondary", "secondary_link",
    "tertiary", "tertiary_link",
    "residential",
    "service",
    "unclassified",
]

# ── Car physics ───────────────────────────────────────────────────────────────
CAR_MAX_SPEED_MS   = 55.0     # m/s  (~200 km/h)
CAR_ACCEL          = 12.0     # m/s²  full throttle acceleration
CAR_BRAKE          = 25.0     # m/s²  full brake deceleration
CAR_DRAG           = 0.015    # rolling resistance coefficient
CAR_STEER_DEG_S    = 120.0    # max heading change rate (deg/s) at low speed
CAR_STEER_FALLOFF  = 0.012    # steering reduces with speed

# ── Logitech G923 – Gamepad API axis mapping ──────────────────────────────────
# Test with: python main.py --calibrate
# Axes return values in [-1 .. 1].
# For pedals: fully released = +1, fully pressed = -1 (inverted).
G923_AXIS_STEER    = 0    # steering wheel
G923_AXIS_THROTTLE = 1    # throttle pedal (combined or separate)
G923_AXIS_BRAKE    = 2    # brake pedal
G923_AXIS_CLUTCH   = 3    # clutch pedal

# Set to True to flip the pedal sign (depends on driver/OS)
G923_INVERT_THROTTLE = True
G923_INVERT_BRAKE    = True
G923_INVERT_CLUTCH   = True

# Deadzone for steering axis (0..1)
G923_STEER_DEADZONE = 0.02

# ── Force-feedback ─────────────────────────────────────────────────────────────
# pygame 2 rumble: (low_freq, high_freq, duration_ms)
FF_ENABLED        = True
FF_BUMP_LOW       = 0.5
FF_BUMP_HIGH      = 0.8
FF_BUMP_DURATION  = 120   # ms

# ── Minimap ───────────────────────────────────────────────────────────────────
MINIMAP_SIZE   = 200   # square pixels
MINIMAP_MARGIN = 12
MINIMAP_ALPHA  = 200
