"""
Fetches road data from OpenStreetMap via the Overpass API and converts
lat/lon coordinates to a flat local Cartesian system (metres from origin).
Results are cached to disk to avoid repeated network requests.
"""

import json
import math
import os
import hashlib
import requests

from config import (
    OVERPASS_URL, CACHE_DIR, MAP_RADIUS_DEG,
    HIGHWAY_TYPES, ROAD_WIDTHS,
)


# ── Coordinate helpers ────────────────────────────────────────────────────────

EARTH_RADIUS_M = 6_371_000.0


def latlon_to_xy(lat: float, lon: float, origin_lat: float, origin_lon: float):
    """Equirectangular projection → (x, y) in metres from origin."""
    dlat = lat - origin_lat
    dlon = lon - origin_lon
    scale = math.cos(math.radians(origin_lat))
    x =  dlon * scale * math.radians(1) * EARTH_RADIUS_M
    y = -dlat          * math.radians(1) * EARTH_RADIUS_M   # y grows downward
    return x, y


# ── Overpass query ─────────────────────────────────────────────────────────────

def _build_query(lat: float, lon: float, radius_deg: float) -> str:
    s = lat - radius_deg
    n = lat + radius_deg
    w = lon - radius_deg
    e = lon + radius_deg
    hw_filter = "|".join(HIGHWAY_TYPES)
    return f"""
[out:json][timeout:30];
(
  way["highway"~"^({hw_filter})$"]({s},{w},{n},{e});
);
out body;
>;
out skel qt;
""".strip()


def _cache_path(lat: float, lon: float, radius_deg: float) -> str:
    key = f"{lat:.5f}_{lon:.5f}_{radius_deg:.5f}"
    h = hashlib.md5(key.encode()).hexdigest()[:8]
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"osm_{h}.json")


def fetch_osm_data(lat: float, lon: float, radius_deg: float = MAP_RADIUS_DEG) -> dict:
    """Return raw Overpass JSON, using a disk cache when available."""
    path = _cache_path(lat, lon, radius_deg)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)

    query = _build_query(lat, lon, radius_deg)
    resp  = requests.post(OVERPASS_URL, data={"data": query}, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    with open(path, "w") as f:
        json.dump(data, f)
    return data


# ── Parsing ────────────────────────────────────────────────────────────────────

class Road:
    __slots__ = ("points", "kind", "name", "width")

    def __init__(self, points: list, kind: str, name: str):
        self.points = points          # list of (x, y) in metres
        self.kind   = kind
        self.name   = name
        self.width  = ROAD_WIDTHS.get(kind, ROAD_WIDTHS["default"])


class MapData:
    def __init__(self, roads: list, origin_lat: float, origin_lon: float,
                 extent_m: float):
        self.roads      = roads
        self.origin_lat = origin_lat
        self.origin_lon = origin_lon
        self.extent_m   = extent_m   # approx half-side in metres


def parse_osm(data: dict, origin_lat: float, origin_lon: float,
              radius_deg: float = MAP_RADIUS_DEG) -> MapData:
    """Convert Overpass JSON → MapData with local Cartesian roads."""
    # Build node id → (x, y) lookup
    nodes: dict[int, tuple] = {}
    for el in data.get("elements", []):
        if el["type"] == "node":
            x, y = latlon_to_xy(el["lat"], el["lon"], origin_lat, origin_lon)
            nodes[el["id"]] = (x, y)

    roads: list[Road] = []
    for el in data.get("elements", []):
        if el["type"] != "way":
            continue
        tags  = el.get("tags", {})
        kind  = tags.get("highway", "default")
        name  = tags.get("name", "")
        pts   = [nodes[nid] for nid in el.get("nodes", []) if nid in nodes]
        if len(pts) >= 2:
            roads.append(Road(pts, kind, name))

    extent_m = radius_deg * math.radians(1) * EARTH_RADIUS_M
    return MapData(roads, origin_lat, origin_lon, extent_m)


# ── Public API ─────────────────────────────────────────────────────────────────

def load_map(lat: float, lon: float,
             radius_deg: float = MAP_RADIUS_DEG) -> MapData:
    """Fetch (or load from cache) and parse OSM road data centred on lat/lon."""
    raw = fetch_osm_data(lat, lon, radius_deg)
    return parse_osm(raw, lat, lon, radius_deg)


def find_spawn_point(map_data: MapData) -> tuple:
    """Return a (x, y) point on the first road segment near the origin."""
    for road in map_data.roads:
        if road.kind in ("primary", "secondary", "tertiary", "residential"):
            return road.points[0]
    if map_data.roads:
        return map_data.roads[0].points[0]
    return (0.0, 0.0)
