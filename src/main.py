#!/usr/bin/env python3
"""
OSM Quest Explorer – entry point
Drive through real streets from OpenStreetMap, completing quests by
reaching named real-world destinations using your Logitech G923 wheel.

Each session drops you in a randomly chosen city anywhere on Earth.

Usage
-----
  python main.py                       # random city (default)
  python main.py --city "Tokyo, Japan" # force a specific city from the list
  python main.py --lat 48.8566 --lon 2.3522  --city "Paris"  # exact coords
  python main.py --radius 0.012        # larger map area
  python main.py --list-cities         # show available cities
  python main.py --calibrate           # live G923 axis reader
  python main.py --clear-cache         # delete cached OSM files
"""

import argparse
import os
import sys
import shutil

sys.path.insert(0, os.path.dirname(__file__))

import pygame

from config import MAP_RADIUS_DEG, CACHE_DIR


def _calibrate():
    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() == 0:
        print("No joystick / wheel detected.")
        sys.exit(1)
    j = pygame.joystick.Joystick(0)
    j.init()
    print(f"Device : {j.get_name()}")
    print(f"Axes   : {j.get_numaxes()}   Buttons: {j.get_numbuttons()}")
    print("Move wheel and pedals to see values. Ctrl-C to quit.\n")
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
        print(f"Deleted cache: {CACHE_DIR}")
    else:
        print("Cache not found – nothing to delete.")


def _list_cities():
    from location_picker import WORLD_CITIES
    for name, lat, lon in sorted(WORLD_CITIES, key=lambda c: c[0]):
        print(f"  {name:<35}  {lat:+8.4f}  {lon:+9.4f}")


def _find_city(name: str):
    """Return (city_name, lat, lon) by case-insensitive substring match."""
    from location_picker import WORLD_CITIES
    name_l = name.lower()
    matches = [(n, la, lo) for n, la, lo in WORLD_CITIES
               if name_l in n.lower()]
    if not matches:
        print(f"City '{name}' not found. Use --list-cities to see options.")
        sys.exit(1)
    if len(matches) > 1:
        print(f"Multiple matches for '{name}':")
        for m in matches:
            print(f"  {m[0]}")
        print("Using the first match.")
    return matches[0]


def main():
    parser = argparse.ArgumentParser(
        description="OSM Quest Explorer – drive real streets to reach real places"
    )
    parser.add_argument("--city",        type=str,   default=None,
                        help="City name to load (substring match, see --list-cities)")
    parser.add_argument("--lat",         type=float, default=None,
                        help="Override centre latitude")
    parser.add_argument("--lon",         type=float, default=None,
                        help="Override centre longitude")
    parser.add_argument("--radius",      type=float, default=MAP_RADIUS_DEG,
                        help="Map radius in degrees (default 0.007 ≈ 800 m)")
    parser.add_argument("--list-cities", action="store_true",
                        help="Print available cities and exit")
    parser.add_argument("--calibrate",   action="store_true",
                        help="Show live G923 axis values and exit")
    parser.add_argument("--clear-cache", action="store_true",
                        help="Delete cached OSM data and exit")
    args = parser.parse_args()

    if args.list_cities:
        _list_cities()
        return

    if args.calibrate:
        _calibrate()
        return

    if args.clear_cache:
        _clear_cache()
        return

    lat = args.lat
    lon = args.lon
    city_name = ""

    # Resolve city name → coordinates
    if args.city:
        city_name, city_lat, city_lon = _find_city(args.city)
        if lat is None:
            lat = city_lat
        if lon is None:
            lon = city_lon

    from game import Game
    Game(lat=lat, lon=lon, radius_deg=args.radius, city_name=city_name).run()


if __name__ == "__main__":
    main()
