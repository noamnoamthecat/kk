"""
Quest system for the OSM exploration game.

Each quest asks the player to navigate to a specific named location
(POI from OpenStreetMap) or to a random waypoint on the road network.
Quests are generated one at a time; completing one immediately generates
the next.

Score
-----
  base points  – set per quest, based on distance
  time bonus   – halved every 60 s beyond the expected travel time
  streak bonus – ×1.5 multiplier applied from the 3rd consecutive quest
"""

import math
import random
import time
from dataclasses import dataclass, field
from typing import Optional

from osm_loader import MapData, POI, road_points_sample


# ── Quest templates ────────────────────────────────────────────────────────────

# (category_filter, verb)  – category_filter=None matches any POI
QUEST_TEMPLATES = [
    (None,       "Navigate to"),
    ("amenity",  "Find the"),
    ("tourism",  "Visit"),
    ("leisure",  "Explore"),
    ("historic", "Discover"),
    ("shop",     "Stop at"),
    ("natural",  "Reach"),
]

# Friendly names for POI kinds shown in quest text
KIND_LABELS = {
    "cafe": "café", "restaurant": "restaurant", "bar": "bar",
    "pub": "pub", "fast_food": "fast food place",
    "hospital": "hospital", "pharmacy": "pharmacy",
    "school": "school", "library": "library",
    "cinema": "cinema", "theatre": "theatre",
    "museum": "museum", "gallery": "art gallery",
    "park": "park", "garden": "garden", "playground": "playground",
    "viewpoint": "viewpoint", "attraction": "attraction",
    "monument": "monument", "ruins": "ruins", "castle": "castle",
    "supermarket": "supermarket", "convenience": "convenience store",
    "hotel": "hotel", "hostel": "hostel",
    "peak": "mountain peak", "waterfall": "waterfall", "spring": "spring",
}

COMPLETION_RADIUS_M = 40.0    # how close the player must get
MIN_QUEST_DIST_M    = 80.0    # don't generate trivially-close targets
MAX_WAYPOINT_DIST_M = 900.0   # max distance for road-based waypoints

# Points per metre of quest distance (base rate)
POINTS_PER_METRE = 0.15
STREAK_THRESHOLD = 3          # consecutive quests needed for streak bonus


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class Quest:
    title:       str
    description: str
    target_x:    float
    target_y:    float
    target_name: str
    base_points: int
    category:    str = "waypoint"
    kind:        str = ""

    started_at:   float = field(default_factory=time.monotonic)
    completed_at: Optional[float] = None

    @property
    def distance_to(self) -> float:
        """Current Euclidean distance from the target (set by QuestSystem)."""
        return getattr(self, "_dist", 0.0)

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self.started_at

    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None

    def mark_complete(self):
        self.completed_at = time.monotonic()

    def score(self) -> int:
        if not self.is_complete:
            return 0
        dt = self.completed_at - self.started_at
        # Expected travel time at 30 km/h
        expected_s = (self.base_points / POINTS_PER_METRE) / (30000 / 3600)
        bonus_mult = max(0.1, 1.0 - max(0, dt - expected_s) / max(1, expected_s))
        return max(10, int(self.base_points * bonus_mult))


@dataclass
class QuestResult:
    quest:        Quest
    final_score:  int
    streak_bonus: bool


# ── Quest system ───────────────────────────────────────────────────────────────

class QuestSystem:
    def __init__(self, map_data: MapData):
        self._map      = map_data
        self._pois     = list(map_data.pois)
        self._road_pts = road_points_sample(map_data, n=60)

        self.current:    Optional[Quest] = None
        self.history:    list[QuestResult] = []
        self.total_score = 0
        self._streak     = 0
        self._used_pois: set[int] = set()   # ids of already-visited POIs

    # ── Public API ─────────────────────────────────────────────────────────────

    def start_next_quest(self, car_x: float, car_y: float) -> Quest:
        """Generate and activate a new quest."""
        q = self._generate(car_x, car_y)
        self.current = q
        return q

    def update(self, car_x: float, car_y: float) -> Optional[QuestResult]:
        """
        Call every frame. Returns a QuestResult when the current quest is
        completed, otherwise None.
        """
        if self.current is None or self.current.is_complete:
            return None

        dist = _dist(car_x, car_y, self.current.target_x, self.current.target_y)
        self.current._dist = dist

        if dist <= COMPLETION_RADIUS_M:
            self.current.mark_complete()
            self._streak += 1
            streak_bonus = self._streak >= STREAK_THRESHOLD
            pts = self.current.score()
            if streak_bonus:
                pts = int(pts * 1.5)
            self.total_score += pts
            result = QuestResult(self.current, pts, streak_bonus)
            self.history.append(result)
            return result

        return None

    @property
    def quests_completed(self) -> int:
        return len(self.history)

    @property
    def streak(self) -> int:
        return self._streak

    def distance_to_target(self, car_x: float, car_y: float) -> float:
        if self.current is None:
            return 0.0
        return _dist(car_x, car_y, self.current.target_x, self.current.target_y)

    def bearing_to_target(self, car_x: float, car_y: float) -> float:
        """Angle in degrees from car to quest target (0=east)."""
        if self.current is None:
            return 0.0
        dx = self.current.target_x - car_x
        dy = self.current.target_y - car_y
        return math.degrees(math.atan2(dy, dx))

    # ── Quest generation ───────────────────────────────────────────────────────

    def _generate(self, car_x: float, car_y: float) -> Quest:
        # 1. Try to find a suitable named POI
        poi = self._pick_poi(car_x, car_y)
        if poi:
            return self._quest_from_poi(poi)

        # 2. Fall back to a random road waypoint
        return self._quest_from_road_point(car_x, car_y)

    def _pick_poi(self, car_x: float, car_y: float) -> Optional[POI]:
        candidates = [
            p for i, p in enumerate(self._pois)
            if i not in self._used_pois
            and _dist(car_x, car_y, p.x, p.y) >= MIN_QUEST_DIST_M
        ]
        if not candidates:
            # All POIs used – reset so we can revisit them
            self._used_pois.clear()
            candidates = [
                p for p in self._pois
                if _dist(car_x, car_y, p.x, p.y) >= MIN_QUEST_DIST_M
            ]
        if not candidates:
            return None

        # Prefer POIs in the 100–600 m range; weight by distance bucket
        def weight(p):
            d = _dist(car_x, car_y, p.x, p.y)
            if d < MIN_QUEST_DIST_M:
                return 0.0
            if d > 800:
                return 0.3
            return 1.0

        pool = [(p, weight(p)) for p in candidates]
        pool = [(p, w) for p, w in pool if w > 0]
        if not pool:
            return None

        total = sum(w for _, w in pool)
        r = random.random() * total
        for p, w in pool:
            r -= w
            if r <= 0:
                idx = self._pois.index(p)
                self._used_pois.add(idx)
                return p
        return None

    def _quest_from_poi(self, poi: POI) -> Quest:
        _, verb = random.choice(QUEST_TEMPLATES)
        kind_label = KIND_LABELS.get(poi.kind, poi.kind.replace("_", " "))
        dist_hint  = f"{int(_dist(0, 0, poi.x, poi.y)):,} m" if (poi.x or poi.y) else ""
        title       = f"{verb} {poi.name}"
        description = f"{verb} the {kind_label} called '{poi.name}'."
        base_pts    = max(50, int(_dist(0, 0, poi.x, poi.y) * POINTS_PER_METRE))
        return Quest(
            title=title,
            description=description,
            target_x=poi.x,
            target_y=poi.y,
            target_name=poi.name,
            base_points=base_pts,
            category=poi.category,
            kind=poi.kind,
        )

    def _quest_from_road_point(self, car_x: float, car_y: float) -> Quest:
        """Generate a quest toward a random point on the road network."""
        candidates = [
            p for p in self._road_pts
            if MIN_QUEST_DIST_M <= _dist(car_x, car_y, p[0], p[1]) <= MAX_WAYPOINT_DIST_M
        ]
        if not candidates:
            candidates = self._road_pts or [(200.0, 0.0)]

        target = random.choice(candidates)
        dist   = _dist(car_x, car_y, target[0], target[1])
        num    = self.quests_completed + 1
        return Quest(
            title=f"Waypoint #{num}",
            description=f"Reach the marked waypoint {int(dist):,} m ahead.",
            target_x=target[0],
            target_y=target[1],
            target_name=f"Waypoint #{num}",
            base_points=max(30, int(dist * POINTS_PER_METRE)),
            category="waypoint",
        )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _dist(ax, ay, bx, by) -> float:
    return math.hypot(bx - ax, by - ay)
