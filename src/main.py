#!/usr/bin/env python3
"""
OSM Street Racer – entry point
Drive through real streets from OpenStreetMap data with a Logitech G923 wheel.

Usage
-----
  python main.py                           # default location (Times Square, NYC)
  python main.py --lat 48.8566 --lon 2.3522          # Paris city centre
  python main.py --lat 51.5074 --lon -0.1278         # London
  python main.py --radius 0.012                      # larger map area
  python main.py --calibrate                         # live axis reader for G923
  python main.py --clear-cache                       # delete cached OSM files
"""

import argparse
import os
import sys
import shutil

# Make sure local src/ is on the path when running as  python src/main.py
sys.path.insert(0, os.path.dirname(__file__))

import pygame

from config import DEFAULT_LAT, DEFAULT_LON, MAP_RADIUS_DEG, CACHE_DIR


def _calibrate():
    """Print live G923 axis values until the user presses Ctrl-C."""
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("No joystick / wheel detected.")
        sys.exit(1)

    j = pygame.joystick.Joystick(0)
    j.init()
    print(f"Device: {j.get_name()}")
    print(f"Axes: {j.get_numaxes()}   Buttons: {j.get_numbuttons()}")
    print("Move the wheel and press pedals to read values. Ctrl-C to quit.\n")

    try:
        while True:
            pygame.event.pump()
            parts = [f"A{i}={j.get_axis(i):+.3f}"
                     for i in range(j.get_numaxes())]
            print("  ".join(parts), end="\r", flush=True)
    except KeyboardInterrupt:
        print()

    pygame.quit()


def _clear_cache():
    if os.path.isdir(CACHE_DIR):
        shutil.rmtree(CACHE_DIR)
        print(f"Deleted cache directory: {CACHE_DIR}")
    else:
        print("Cache directory not found – nothing to delete.")


def main():
    parser = argparse.ArgumentParser(
        description="OSM Street Racer – drive real streets with your G923 wheel"
    )
    parser.add_argument("--lat",         type=float, default=DEFAULT_LAT,
                        help="Centre latitude  (default: Times Square, NYC)")
    parser.add_argument("--lon",         type=float, default=DEFAULT_LON,
                        help="Centre longitude (default: Times Square, NYC)")
    parser.add_argument("--radius",      type=float, default=MAP_RADIUS_DEG,
                        help="Map radius in degrees (default: 0.007 ≈ 800 m)")
    parser.add_argument("--calibrate",   action="store_true",
                        help="Show live G923 axis values and exit")
    parser.add_argument("--clear-cache", action="store_true",
                        help="Delete cached OSM data and exit")
    args = parser.parse_args()

    if args.calibrate:
        _calibrate()
        return

    if args.clear_cache:
        _clear_cache()
        return

    from game import Game
    Game(lat=args.lat, lon=args.lon, radius_deg=args.radius).run()


if __name__ == "__main__":
    main()
