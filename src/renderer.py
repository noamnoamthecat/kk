"""
Pygame renderer: top-down OSM road view + car + quest UI.

Quest-specific additions
------------------------
  - Pulsing waypoint marker at quest target
  - Navigation arrow on the car pointing toward the target
  - Quest panel (top-left): title, description, distance, score
  - Completion flash overlay
  - POI dots on minimap
"""

import math
import time
import pygame

from config import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    BG_COLOR, ROAD_COLORS, CAR_COLOR, CAR_OUTLINE,
    HUD_TEXT, MINIMAP_SIZE, MINIMAP_MARGIN, MINIMAP_BG, MINIMAP_DOT,
)
from osm_loader  import MapData
from car_physics import Car

try:
    from quest_system import Quest, QuestSystem
    _QUEST_AVAILABLE = True
except ImportError:
    _QUEST_AVAILABLE = False

BASE_SCALE = 6.0


# ── Camera ────────────────────────────────────────────────────────────────────

class Camera:
    def __init__(self, scale: float = BASE_SCALE):
        self.x     = 0.0
        self.y     = 0.0
        self.scale = scale

    def follow(self, car: Car, dt: float):
        alpha  = min(1.0, dt * 8.0)
        self.x += (car.x - self.x) * alpha
        self.y += (car.y - self.y) * alpha

    def world_to_screen(self, wx: float, wy: float):
        sx = WINDOW_WIDTH  // 2 + (wx - self.x) * self.scale
        sy = WINDOW_HEIGHT // 2 - (wy - self.y) * self.scale
        return int(sx), int(sy)

    def zoom(self, delta: float):
        self.scale = max(1.0, min(30.0, self.scale + delta))


# ── Renderer ──────────────────────────────────────────────────────────────────

class Renderer:
    def __init__(self, screen: pygame.Surface):
        self.screen  = screen
        self.camera  = Camera()
        self._font_s = None
        self._font_m = None
        self._font_l = None
        self._minimap_surf = None

        # Flash overlay state
        self._flash_alpha    = 0
        self._flash_color    = (80, 255, 120)
        self._flash_msg      = ""
        self._flash_score    = ""

    def init(self):
        self._font_s = pygame.font.SysFont("monospace", 14)
        self._font_m = pygame.font.SysFont("monospace", 18)
        self._font_l = pygame.font.SysFont("monospace", 28, bold=True)

    # ── Map baking ────────────────────────────────────────────────────────────

    def bake_road_surface(self, map_data: MapData):
        half  = map_data.extent_m
        scale = BASE_SCALE
        px    = int(half * 2 * scale)

        self._road_surf = pygame.Surface((px, px), pygame.SRCALPHA)
        self._road_surf.fill((0, 0, 0, 0))

        def to_surf(x, y):
            return int((x + half) * scale), int((half - y) * scale)

        for road in map_data.roads:
            color = ROAD_COLORS.get(road.kind, ROAD_COLORS["default"])
            pts   = [to_surf(x, y) for x, y in road.points]
            if len(pts) >= 2:
                w = max(1, int(road.width * scale * 0.5))
                pygame.draw.lines(self._road_surf, color, False, pts, w)

        self._road_half  = half
        self._road_scale = scale
        self._bake_minimap(map_data)

    def _bake_minimap(self, map_data: MapData):
        mm    = MINIMAP_SIZE
        surf  = pygame.Surface((mm, mm), pygame.SRCALPHA)
        surf.fill((20, 20, 20, 200))
        half  = map_data.extent_m
        scale = mm / (half * 2)

        def to_mm(x, y):
            return int((x + half) * scale), int((half - y) * scale)

        for road in map_data.roads:
            color = ROAD_COLORS.get(road.kind, ROAD_COLORS["default"])
            pts   = [to_mm(x, y) for x, y in road.points]
            if len(pts) >= 2:
                pygame.draw.lines(surf, color, False, pts, 1)

        # POI dots on minimap
        for poi in map_data.pois:
            px_mm, py_mm = to_mm(poi.x, poi.y)
            if 0 <= px_mm < mm and 0 <= py_mm < mm:
                pygame.draw.circle(surf, (255, 220, 60), (px_mm, py_mm), 2)

        self._minimap_surf  = surf
        self._minimap_half  = half
        self._minimap_scale = scale

    # ── Main draw ─────────────────────────────────────────────────────────────

    def draw(self, car: Car, map_data: MapData, dt: float,
             quest_sys=None):
        self.camera.follow(car, dt)
        self.screen.fill(BG_COLOR)

        self._draw_roads()

        if quest_sys and quest_sys.current:
            self._draw_waypoint(quest_sys.current)

        self._draw_car(car)

        if quest_sys and quest_sys.current:
            self._draw_nav_arrow(car, quest_sys)

        self._draw_hud(car)

        if quest_sys:
            self._draw_quest_panel(quest_sys, car)

        self._draw_minimap(car, quest_sys)
        self._draw_flash(dt)

    # ── Roads ─────────────────────────────────────────────────────────────────

    def _draw_roads(self):
        if not hasattr(self, "_road_surf"):
            return
        half  = self._road_half
        ox, oy = self.camera.world_to_screen(-half, half)
        self.screen.blit(self._road_surf, (ox, oy))

    # ── Pulsing waypoint marker ───────────────────────────────────────────────

    def _draw_waypoint(self, quest: "Quest"):
        sx, sy = self.camera.world_to_screen(quest.target_x, quest.target_y)
        t      = time.monotonic()
        pulse  = int(8 + 5 * math.sin(t * 3.0))

        # Outer pulsing ring
        pygame.draw.circle(self.screen, (255, 200, 0), (sx, sy), pulse + 10, 2)
        # Inner solid dot
        pygame.draw.circle(self.screen, (255, 200, 0), (sx, sy), 6)
        # Quest name tag
        lbl = self._font_s.render(quest.target_name[:28], True, (255, 220, 80))
        self.screen.blit(lbl, (sx + 14, sy - 8))

    # ── Car ───────────────────────────────────────────────────────────────────

    def _draw_car(self, car: Car):
        pts = [self.camera.world_to_screen(x, y) for x, y in car.corners]
        pygame.draw.polygon(self.screen, CAR_COLOR,  pts)
        pygame.draw.polygon(self.screen, CAR_OUTLINE, pts, 2)

        cx, cy = self.camera.world_to_screen(car.x, car.y)
        rad = math.radians(car.heading)
        ex  = int(cx + math.cos(rad) * 14)
        ey  = int(cy - math.sin(rad) * 14)
        pygame.draw.line(self.screen, CAR_OUTLINE, (cx, cy), (ex, ey), 2)

    # ── Navigation arrow ──────────────────────────────────────────────────────

    def _draw_nav_arrow(self, car: Car, quest_sys: "QuestSystem"):
        bearing_world = quest_sys.bearing_to_target(car.x, car.y)
        # Convert world bearing to screen bearing (y-flip)
        bearing_screen = -bearing_world

        cx, cy = self.camera.world_to_screen(car.x, car.y)
        r   = 28
        rad = math.radians(bearing_screen)
        tx  = int(cx + math.cos(rad) * r)
        ty  = int(cy + math.sin(rad) * r)

        # Arrow head
        _draw_arrow(self.screen, (cx, cy), (tx, ty),
                    color=(255, 200, 0), width=3, head_size=10)

    # ── HUD (speed / dist / time) ─────────────────────────────────────────────

    def _draw_hud(self, car: Car):
        lines  = [
            f"{car.speed_kmh:5.1f} km/h",
            f"{car.distance_m/1000:6.2f} km",
            f"HDG {car.heading:5.1f}°",
            f"{car.elapsed_s/60:4.1f} min",
        ]
        labels = ["SPD", "DST", "HDG", "TME"]
        x, y = 12, 12
        lh   = 20
        box_h = len(lines) * lh + 10
        box_w = 175

        surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 150))
        self.screen.blit(surf, (x - 4, y - 4))

        for i, (lbl, val) in enumerate(zip(labels, lines)):
            txt = self._font_s.render(f"{lbl}: {val}", True, HUD_TEXT)
            self.screen.blit(txt, (x, y + i * lh))

        # Big speed
        spd = self._font_l.render(f"{int(car.speed_kmh):3d}", True, (255, 220, 80))
        self.screen.blit(spd, (WINDOW_WIDTH - 76, 10))

    # ── Quest panel ───────────────────────────────────────────────────────────

    def _draw_quest_panel(self, qs: "QuestSystem", car: Car):
        q    = qs.current
        dist = qs.distance_to_target(car.x, car.y)
        x    = WINDOW_WIDTH // 2 - 220
        y    = 10
        w, h = 440, 80

        bg = pygame.Surface((w, h), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 170))
        self.screen.blit(bg, (x, y))

        # Quest title
        title_col = (255, 200, 50) if q else (160, 160, 160)
        title_txt = q.title if q else "Loading quest…"
        t = self._font_m.render(title_txt[:42], True, title_col)
        self.screen.blit(t, (x + 8, y + 6))

        # Distance
        if q:
            dist_str = f"{int(dist):,} m away"
            d = self._font_s.render(dist_str, True, (180, 240, 180))
            self.screen.blit(d, (x + 8, y + 30))

            # Quest description (truncated)
            desc = self._font_s.render(q.description[:60], True, (200, 200, 200))
            self.screen.blit(desc, (x + 8, y + 50))

        # Score + streak (right side)
        score_txt = self._font_m.render(f"{qs.total_score:,} pts", True, (255, 220, 80))
        self.screen.blit(score_txt, (x + w - score_txt.get_width() - 8, y + 6))

        streak_col = (255, 120, 40) if qs.streak >= 3 else (160, 160, 160)
        streak_txt = self._font_s.render(
            f"#{qs.quests_completed} done  🔥×{qs.streak}" if qs.streak >= 3
            else f"#{qs.quests_completed} done",
            True, streak_col,
        )
        self.screen.blit(streak_txt, (x + w - streak_txt.get_width() - 8, y + 34))

    # ── Minimap ───────────────────────────────────────────────────────────────

    def _draw_minimap(self, car: Car, quest_sys=None):
        if self._minimap_surf is None:
            return
        mm_x = WINDOW_WIDTH  - MINIMAP_SIZE - MINIMAP_MARGIN
        mm_y = WINDOW_HEIGHT - MINIMAP_SIZE - MINIMAP_MARGIN
        self.screen.blit(self._minimap_surf, (mm_x, mm_y))

        scale = self._minimap_scale
        half  = self._minimap_half

        # Quest target dot on minimap
        if quest_sys and quest_sys.current:
            q  = quest_sys.current
            qx = int((q.target_x + half) * scale)
            qy = int((half - q.target_y) * scale)
            if 0 <= qx < MINIMAP_SIZE and 0 <= qy < MINIMAP_SIZE:
                pygame.draw.circle(self.screen, (255, 200, 0),
                                   (mm_x + qx, mm_y + qy), 5)

        # Car dot
        dx = int((car.x + half) * scale)
        dy = int((half - car.y) * scale)
        if 0 <= dx < MINIMAP_SIZE and 0 <= dy < MINIMAP_SIZE:
            pygame.draw.circle(self.screen, MINIMAP_DOT,
                               (mm_x + dx, mm_y + dy), 4)

        pygame.draw.rect(self.screen, (200, 200, 200),
                         (mm_x, mm_y, MINIMAP_SIZE, MINIMAP_SIZE), 1)

    # ── Quest completion flash ────────────────────────────────────────────────

    def flash_completion(self, message: str, score: str,
                         color=(80, 255, 120)):
        self._flash_alpha = 255
        self._flash_msg   = message
        self._flash_score = score
        self._flash_color = color

    def _draw_flash(self, dt: float):
        if self._flash_alpha <= 0:
            return
        self._flash_alpha = max(0, self._flash_alpha - dt * 200)
        a = int(self._flash_alpha)

        overlay = pygame.Surface((WINDOW_WIDTH, 90), pygame.SRCALPHA)
        r, g, b = self._flash_color
        overlay.fill((r, g, b, min(120, a)))
        self.screen.blit(overlay, (0, WINDOW_HEIGHT // 2 - 45))

        msg = self._font_l.render(self._flash_msg, True, (255, 255, 255))
        msg.set_alpha(a)
        rect = msg.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 14))
        self.screen.blit(msg, rect)

        sub = self._font_m.render(self._flash_score, True, (230, 230, 80))
        sub.set_alpha(a)
        rect2 = sub.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 18))
        self.screen.blit(sub, rect2)

    # ── Zoom ──────────────────────────────────────────────────────────────────

    def handle_event(self, ev: pygame.event.Event):
        if ev.type == pygame.MOUSEWHEEL:
            self.camera.zoom(ev.y * 0.5)
        elif ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_PLUS, pygame.K_EQUALS):
                self.camera.zoom(1.0)
            elif ev.key == pygame.K_MINUS:
                self.camera.zoom(-1.0)

    # ── City name splash ──────────────────────────────────────────────────────

    def draw_city_splash(self, city_name: str):
        """Full-screen banner shown briefly at game start."""
        self.screen.fill(BG_COLOR)
        t1 = self._font_l.render("You are in…", True, (160, 160, 160))
        t2 = pygame.font.SysFont("monospace", 36, bold=True).render(
            city_name, True, (255, 220, 80))
        t3 = self._font_m.render("Complete quests by driving to the marked locations.",
                                  True, (200, 200, 200))
        t4 = self._font_s.render("P = pause   R = respawn   +/- = zoom   ESC = quit",
                                  True, (140, 140, 140))
        for i, surf in enumerate([t1, t2, t3, t4]):
            r = surf.get_rect(center=(WINDOW_WIDTH // 2,
                                       WINDOW_HEIGHT // 2 - 60 + i * 44))
            self.screen.blit(surf, r)


# ── Arrow helper ──────────────────────────────────────────────────────────────

def _draw_arrow(surface, start, end, color, width=2, head_size=8):
    pygame.draw.line(surface, color, start, end, width)
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return
    ux, uy = dx / length, dy / length
    lx =  uy * head_size
    ly = -ux * head_size
    left  = (end[0] - ux * head_size + lx, end[1] - uy * head_size + ly)
    right = (end[0] - ux * head_size - lx, end[1] - uy * head_size - ly)
    pygame.draw.polygon(surface, color, [end, left, right])
