"""
Fetches road data AND points of interest from OpenStreetMap via the Overpass API.
Converts lat/lon to a flat local Cartesian system (metres from origin).
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
    y = -dlat          * math.radians(1) * EARTH_RADIUS_M
    return x, y


# ── Overpass queries ──────────────────────────────────────────────────────────

def _bbox(lat, lon, radius_deg):
    return lat - radius_deg, lon - radius_deg, lat + radius_deg, lon + radius_deg


def _build_road_query(lat: float, lon: float, radius_deg: float) -> str:
    s, w, n, e = _bbox(lat, lon, radius_deg)
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


def _build_poi_query(lat: float, lon: float, radius_deg: float) -> str:
    """Fetch named nodes that are likely interesting quest destinations."""
    s, w, n, e = _bbox(lat, lon, radius_deg)
    return f"""
[out:json][timeout:30];
(
  node["amenity"]["name"]({s},{w},{n},{e});
  node["tourism"]["name"]({s},{w},{n},{e});
  node["leisure"]["name"]({s},{w},{n},{e});
  node["shop"]["name"]({s},{w},{n},{e});
  node["historic"]["name"]({s},{w},{n},{e});
  node["natural"~"peak|spring|waterfall"]["name"]({s},{w},{n},{e});
);
out body;
""".strip()


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _cache_path(lat: float, lon: float, radius_deg: float, suffix: str) -> str:
    key = f"{lat:.5f}_{lon:.5f}_{radius_deg:.5f}"
    h = hashlib.md5(key.encode()).hexdigest()[:8]
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"osm_{suffix}_{h}.json")


def _fetch(query: str, cache_file: str) -> dict:
    if os.path.exists(cache_file):
        with open(cache_file) as f:
            return json.load(f)
    resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    with open(cache_file, "w") as f:
        json.dump(data, f)
    return data


# ── Data classes ──────────────────────────────────────────────────────────────

class Road:
    __slots__ = ("points", "kind", "name", "width")

    def __init__(self, points: list, kind: str, name: str):
        self.points = points
        self.kind   = kind
        self.name   = name
        self.width  = ROAD_WIDTHS.get(kind, ROAD_WIDTHS["default"])


class POI:
    """A named point of interest from OSM."""
    __slots__ = ("x", "y", "name", "category", "kind")

    def __init__(self, x: float, y: float, name: str, category: str, kind: str):
        self.x        = x
        self.y        = y
        self.name     = name
        self.category = category   # amenity / tourism / leisure / shop / historic
        self.kind     = kind       # café / museum / park / etc.

    def __repr__(self):
        return f"POI({self.name!r}, {self.category}/{self.kind})"


class MapData:
    def __init__(self, roads: list, pois: list,
                 origin_lat: float, origin_lon: float, extent_m: float,
                 city_name: str = ""):
        self.roads      = roads
        self.pois       = pois
        self.origin_lat = origin_lat
        self.origin_lon = origin_lon
        self.extent_m   = extent_m
        self.city_name  = city_name


# ── Parsers ───────────────────────────────────────────────────────────────────

def _parse_roads(data: dict, origin_lat: float, origin_lon: float,
                 radius_deg: float) -> list:
    nodes: dict[int, tuple] = {}
    for el in data.get("elements", []):
        if el["type"] == "node":
            x, y = latlon_to_xy(el["lat"], el["lon"], origin_lat, origin_lon)
            nodes[el["id"]] = (x, y)

    roads = []
    for el in data.get("elements", []):
        if el["type"] != "way":
            continue
        tags = el.get("tags", {})
        kind = tags.get("highway", "default")
        name = tags.get("name", "")
        pts  = [nodes[nid] for nid in el.get("nodes", []) if nid in nodes]
        if len(pts) >= 2:
            roads.append(Road(pts, kind, name))
    return roads


def _parse_pois(data: dict, origin_lat: float, origin_lon: float) -> list:
    pois = []
    for el in data.get("elements", []):
        if el["type"] != "node":
            continue
        tags = el.get("tags", {})
        name = tags.get("name", "").strip()
        if not name:
            continue

        category = next(
            (k for k in ("amenity", "tourism", "leisure", "shop", "historic", "natural")
             if k in tags),
            "place"
        )
        kind = tags.get(category, "point")
        x, y = latlon_to_xy(el["lat"], el["lon"], origin_lat, origin_lon)
        pois.append(POI(x, y, name, category, kind))
    return pois


# ── Public API ────────────────────────────────────────────────────────────────

def load_map(lat: float, lon: float,
             radius_deg: float = MAP_RADIUS_DEG,
             city_name: str = "") -> MapData:
    """Fetch (or load from cache) roads + POIs centred on lat/lon."""
    road_data = _fetch(
        _build_road_query(lat, lon, radius_deg),
        _cache_path(lat, lon, radius_deg, "roads"),
    )
    poi_data = _fetch(
        _build_poi_query(lat, lon, radius_deg),
        _cache_path(lat, lon, radius_deg, "pois"),
    )

    roads = _parse_roads(road_data, lat, lon, radius_deg)
    pois  = _parse_pois(poi_data, lat, lon)
    extent_m = radius_deg * math.radians(1) * EARTH_RADIUS_M

    print(f"[OSM] {len(roads)} roads, {len(pois)} POIs loaded.")
    return MapData(roads, pois, lat, lon, extent_m, city_name)


def find_spawn_point(map_data: MapData) -> tuple:
    """Return a (x, y) on a good road near the origin."""
    for kind in ("residential", "tertiary", "secondary", "primary"):
        for road in map_data.roads:
            if road.kind == kind and len(road.points) >= 2:
                # Return a mid-point of the road segment for variety
                mid = len(road.points) // 2
                return road.points[mid]
    if map_data.roads:
        return map_data.roads[0].points[0]
    return (0.0, 0.0)


def road_points_sample(map_data: MapData, n: int = 20) -> list:
    """Return n random points distributed across the road network."""
    import random
    points = []
    for road in map_data.roads:
        points.extend(road.points)
    if not points:
        return []
    return random.sample(points, min(n, len(points)))
