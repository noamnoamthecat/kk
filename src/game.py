"""
Main game class – quest exploration mode.

Flow
----
  SPLASH  → show city name for 3 s
  LOADING → fetch OSM data (blocking, shows progress screen)
  PLAYING → drive + quest loop
  PAUSED  → overlay, physics frozen
"""

import sys
import time
import pygame

from config import (
    WINDOW_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT, TARGET_FPS,
    BG_COLOR, MAP_RADIUS_DEG,
)
from location_picker import pick_random_location
from osm_loader      import load_map, find_spawn_point
from car_physics     import Car
from wheel_input     import WheelInput
from renderer        import Renderer
from quest_system    import QuestSystem


SPLASH_DURATION = 3.0   # seconds to show the city name


class Game:
    STATE_SPLASH  = "splash"
    STATE_LOADING = "loading"
    STATE_PLAYING = "playing"
    STATE_PAUSED  = "paused"

    def __init__(self, lat: float | None = None, lon: float | None = None,
                 radius_deg: float = MAP_RADIUS_DEG, city_name: str = ""):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption(WINDOW_TITLE)
        self.clock   = pygame.time.Clock()
        self.running = True

        # Pick a random location unless one is given explicitly
        if lat is None or lon is None:
            self._city_name, lat, lon = pick_random_location()
        else:
            self._city_name = city_name or f"{lat:.4f}, {lon:.4f}"

        self._lat        = lat
        self._lon        = lon
        self._radius_deg = radius_deg

        self.state       = self.STATE_SPLASH
        self._splash_t   = time.monotonic()

        self.map_data    = None
        self.car         = None
        self.quest_sys   = None
        self.wheel       = WheelInput()
        self.renderer    = Renderer(self.screen)
        self.renderer.init()

        self._font = pygame.font.SysFont("monospace", 18)
        self._quest_result_pending = None   # show briefly after completion

        print(f"[Game] Destination: {self._city_name}  "
              f"({self._lat:.4f}, {self._lon:.4f})")

    # ── Entry point ───────────────────────────────────────────────────────────

    def run(self):
        while self.running:
            dt     = self.clock.tick(TARGET_FPS) / 1000.0
            dt     = min(dt, 0.05)
            events = pygame.event.get()

            self._handle_global_events(events)

            if self.state == self.STATE_SPLASH:
                self._tick_splash()
            elif self.state == self.STATE_LOADING:
                self._tick_loading()
            elif self.state == self.STATE_PLAYING:
                self._tick_playing(dt, events)
            elif self.state == self.STATE_PAUSED:
                self._tick_paused()

            for ev in events:
                self.renderer.handle_event(ev)

            pygame.display.flip()

        pygame.quit()

    # ── State ticks ───────────────────────────────────────────────────────────

    def _tick_splash(self):
        self.renderer.draw_city_splash(self._city_name)
        elapsed = time.monotonic() - self._splash_t
        if elapsed >= SPLASH_DURATION:
            self.state = self.STATE_LOADING

    def _tick_loading(self):
        self._draw_loading()
        pygame.display.flip()
        pygame.event.pump()
        self._load_map()          # blocks while fetching

    def _tick_playing(self, dt: float, events: list):
        self.wheel.update(events)
        self.car.set_steer(self.wheel.steer)
        self.car.set_throttle(self.wheel.throttle)
        self.car.set_brake(self.wheel.brake)
        self.car.update(dt)

        # Quest progress
        result = self.quest_sys.update(self.car.x, self.car.y)
        if result:
            self._on_quest_complete(result)

        # Render
        self.renderer.draw(self.car, self.map_data, dt, self.quest_sys)

        # Start next quest immediately after completion
        if (result or self.quest_sys.current is None
                or self.quest_sys.current.is_complete):
            self.quest_sys.start_next_quest(self.car.x, self.car.y)

    def _tick_paused(self):
        self.renderer.draw(self.car, self.map_data, 0.0, self.quest_sys)
        self._draw_pause_overlay()

    # ── Map loading ───────────────────────────────────────────────────────────

    def _load_map(self):
        print(f"[Game] Fetching map data…")
        self.map_data = load_map(
            self._lat, self._lon, self._radius_deg, self._city_name
        )
        print(f"[Game] {len(self.map_data.roads)} roads, "
              f"{len(self.map_data.pois)} POIs")

        spawn = find_spawn_point(self.map_data)
        self.car = Car(x=spawn[0], y=spawn[1], heading=0.0)

        self.renderer.bake_road_surface(self.map_data)

        self.quest_sys = QuestSystem(self.map_data)
        self.quest_sys.start_next_quest(self.car.x, self.car.y)

        self.state = self.STATE_PLAYING

    def _draw_loading(self):
        self.screen.fill(BG_COLOR)
        lines = [
            f"Loading: {self._city_name}",
            "",
            "Fetching road data from OpenStreetMap…",
            "Fetching points of interest…",
            "(results cached after first download)",
        ]
        for i, line in enumerate(lines):
            surf = self._font.render(line, True, (200, 200, 200))
            rect = surf.get_rect(center=(WINDOW_WIDTH  // 2,
                                          WINDOW_HEIGHT // 2 - 50 + i * 28))
            self.screen.blit(surf, rect)

    # ── Quest events ──────────────────────────────────────────────────────────

    def _on_quest_complete(self, result):
        streak_str = "  🔥 STREAK BONUS!" if result.streak_bonus else ""
        self.renderer.flash_completion(
            f"Quest complete! {result.quest.target_name}",
            f"+{result.final_score} pts{streak_str}",
        )
        if self.wheel:
            self.wheel.rumble(0.6)

    # ── Global event handling ─────────────────────────────────────────────────

    def _handle_global_events(self, events: list):
        for ev in events:
            if ev.type == pygame.QUIT:
                self.running = False

            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    if self.state == self.STATE_PAUSED:
                        self.state = self.STATE_PLAYING
                    else:
                        self.running = False

                elif ev.key in (pygame.K_p, pygame.K_PAUSE):
                    if self.state == self.STATE_PLAYING:
                        self.state = self.STATE_PAUSED
                    elif self.state == self.STATE_PAUSED:
                        self.state = self.STATE_PLAYING

                elif ev.key == pygame.K_r and self.state == self.STATE_PLAYING:
                    spawn = find_spawn_point(self.map_data)
                    self.car.x     = spawn[0]
                    self.car.y     = spawn[1]
                    self.car.speed = 0.0

                elif ev.key == pygame.K_n and self.state == self.STATE_PLAYING:
                    # Skip to next quest
                    self.quest_sys.start_next_quest(self.car.x, self.car.y)

    # ── Pause overlay ─────────────────────────────────────────────────────────

    def _draw_pause_overlay(self):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 130))
        self.screen.blit(overlay, (0, 0))

        lines = [
            "── PAUSED ──",
            "",
            f"Location: {self._city_name}",
            f"Quests completed: {self.quest_sys.quests_completed}",
            f"Total score: {self.quest_sys.total_score:,} pts",
            f"Streak: ×{self.quest_sys.streak}",
            "",
            "P / Pause  –  resume",
            "N          –  skip quest",
            "R          –  respawn at start",
            "+  /  −    –  zoom in / out",
            "Scroll     –  zoom",
            "ESC        –  quit",
        ]
        for i, line in enumerate(lines):
            col  = (255, 220, 80) if i == 0 else (210, 210, 210)
            surf = self._font.render(line, True, col)
            rect = surf.get_rect(center=(WINDOW_WIDTH  // 2,
                                          WINDOW_HEIGHT // 2 - 130 + i * 24))
            self.screen.blit(surf, rect)
