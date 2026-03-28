"""
Pygame renderer: top-down view of the OSM road network with a car,
a minimap, and a HUD showing speed / distance / heading.
"""

import math
import pygame

from config import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    BG_COLOR, ROAD_COLORS, CAR_COLOR, CAR_OUTLINE,
    HUD_TEXT, MINIMAP_SIZE, MINIMAP_MARGIN, MINIMAP_BG, MINIMAP_DOT,
)
from osm_loader import MapData
from car_physics import Car


# Pixels per metre at the default zoom level
BASE_SCALE = 6.0

# How many metres of world space the minimap covers (half-side)
MINIMAP_WORLD_HALF = 600.0


class Camera:
    """Smooth-follows the car; supports zoom."""

    def __init__(self, scale: float = BASE_SCALE):
        self.x     = 0.0
        self.y     = 0.0
        self.scale = scale

    def follow(self, car: Car, dt: float):
        """Exponential smoothing toward the car position."""
        alpha = min(1.0, dt * 8.0)
        self.x += (car.x - self.x) * alpha
        self.y += (car.y - self.y) * alpha

    def world_to_screen(self, wx: float, wy: float):
        sx = WINDOW_WIDTH  // 2 + (wx - self.x) * self.scale
        sy = WINDOW_HEIGHT // 2 - (wy - self.y) * self.scale   # y-flip
        return int(sx), int(sy)

    def zoom(self, delta: float):
        self.scale = max(1.0, min(30.0, self.scale + delta))


class Renderer:
    def __init__(self, screen: pygame.Surface):
        self.screen  = screen
        self.camera  = Camera()
        self._font_s = None
        self._font_l = None
        self._minimap_surf: pygame.Surface | None = None

    # ── Initialise fonts (called after pygame.init()) ─────────────────────────

    def init(self):
        self._font_s = pygame.font.SysFont("monospace", 15)
        self._font_l = pygame.font.SysFont("monospace", 28, bold=True)

    # ── Pre-render the static road network to a surface ───────────────────────

    def bake_road_surface(self, map_data: MapData):
        """Build a large off-screen surface containing all roads."""
        half   = map_data.extent_m
        size_m = half * 2
        scale  = BASE_SCALE

        px = int(size_m * scale)
        self._road_surf  = pygame.Surface((px, px), pygame.SRCALPHA)
        self._road_surf.fill((0, 0, 0, 0))

        def to_surf(x, y):
            sx = int((x + half) * scale)
            sy = int((half - y) * scale)
            return sx, sy

        for road in map_data.roads:
            color = ROAD_COLORS.get(road.kind, ROAD_COLORS["default"])
            pts   = [to_surf(x, y) for x, y in road.points]
            if len(pts) >= 2:
                w = max(1, int(road.width * scale * 0.5))
                pygame.draw.lines(self._road_surf, color, False, pts, w)

        self._road_half  = half
        self._road_scale = scale

        # Build minimap surface
        self._bake_minimap(map_data)

    def _bake_minimap(self, map_data: MapData):
        """Render a small static minimap (road network only)."""
        mm = MINIMAP_SIZE
        surf = pygame.Surface((mm, mm), pygame.SRCALPHA)
        surf.fill((*MINIMAP_BG[:3], 200) if len(MINIMAP_BG) >= 4 else (20, 20, 20, 200))

        half  = map_data.extent_m
        scale = mm / (half * 2)

        def to_mm(x, y):
            return int((x + half) * scale), int((half - y) * scale)

        for road in map_data.roads:
            color = ROAD_COLORS.get(road.kind, ROAD_COLORS["default"])
            pts   = [to_mm(x, y) for x, y in road.points]
            if len(pts) >= 2:
                pygame.draw.lines(surf, color, False, pts, 1)

        self._minimap_surf = surf
        self._minimap_half  = half
        self._minimap_scale = scale

    # ── Per-frame draw ────────────────────────────────────────────────────────

    def draw(self, car: Car, map_data: MapData, dt: float):
        self.camera.follow(car, dt)
        self.screen.fill(BG_COLOR)

        self._draw_roads()
        self._draw_car(car)
        self._draw_hud(car)
        self._draw_minimap(car)

    # ── Roads from baked surface ──────────────────────────────────────────────

    def _draw_roads(self):
        if not hasattr(self, "_road_surf"):
            return
        half  = self._road_half
        scale = self._road_scale
        # Where does (−half, +half) end up on screen?
        ox, oy = self.camera.world_to_screen(-half, half)
        self.screen.blit(self._road_surf, (ox, oy))

    # ── Car ───────────────────────────────────────────────────────────────────

    def _draw_car(self, car: Car):
        pts_world  = car.corners
        pts_screen = [self.camera.world_to_screen(x, y) for x, y in pts_world]
        pygame.draw.polygon(self.screen, CAR_COLOR,  pts_screen)
        pygame.draw.polygon(self.screen, CAR_OUTLINE, pts_screen, 2)

        # Direction indicator
        cx, cy = self.camera.world_to_screen(car.x, car.y)
        rad     = math.radians(car.heading)
        ex      = int(cx + math.cos(rad) * 14)
        ey      = int(cy - math.sin(rad) * 14)
        pygame.draw.line(self.screen, CAR_OUTLINE, (cx, cy), (ex, ey), 2)

    # ── HUD ───────────────────────────────────────────────────────────────────

    def _draw_hud(self, car: Car):
        lines = [
            f"{car.speed_kmh:5.1f} km/h",
            f"{car.distance_m/1000:6.2f} km",
            f"HDG {car.heading:5.1f}°",
            f"{car.elapsed_s/60:4.1f} min",
        ]
        labels = ["SPEED", "DIST ", "HEAD ", "TIME "]
        x, y = 12, 12
        pad  = 6
        lh   = 22
        box_h = len(lines) * lh + pad * 2
        box_w = 190
        hud_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        hud_surf.fill((0, 0, 0, 160))
        self.screen.blit(hud_surf, (x - pad, y - pad))

        for i, (lbl, val) in enumerate(zip(labels, lines)):
            txt = self._font_s.render(f"{lbl}: {val}", True, HUD_TEXT)
            self.screen.blit(txt, (x, y + i * lh))

        # Big speed digit
        spd_txt = self._font_l.render(f"{int(car.speed_kmh):3d}", True,
                                       (255, 220, 80))
        self.screen.blit(spd_txt, (WINDOW_WIDTH - 80, 12))

    # ── Minimap ───────────────────────────────────────────────────────────────

    def _draw_minimap(self, car: Car):
        if self._minimap_surf is None:
            return

        mm_x = WINDOW_WIDTH  - MINIMAP_SIZE - MINIMAP_MARGIN
        mm_y = WINDOW_HEIGHT - MINIMAP_SIZE - MINIMAP_MARGIN
        self.screen.blit(self._minimap_surf, (mm_x, mm_y))

        # Car dot
        scale = self._minimap_scale
        half  = self._minimap_half
        dx    = int((car.x + half) * scale)
        dy    = int((half - car.y) * scale)
        if 0 <= dx < MINIMAP_SIZE and 0 <= dy < MINIMAP_SIZE:
            pygame.draw.circle(self.screen, MINIMAP_DOT,
                               (mm_x + dx, mm_y + dy), 4)

        # Minimap border
        pygame.draw.rect(self.screen, (200, 200, 200),
                         (mm_x, mm_y, MINIMAP_SIZE, MINIMAP_SIZE), 1)

    # ── Zoom support ──────────────────────────────────────────────────────────

    def handle_event(self, ev: pygame.event.Event):
        if ev.type == pygame.MOUSEWHEEL:
            self.camera.zoom(ev.y * 0.5)
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_PLUS  or ev.key == pygame.K_EQUALS:
                self.camera.zoom(1.0)
            elif ev.key == pygame.K_MINUS:
                self.camera.zoom(-1.0)
