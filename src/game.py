"""
Main game class: owns the game loop, state machine, and wires together
OSM data, car physics, wheel input, and rendering.

States
------
  LOADING  – fetching / parsing OSM data
  PLAYING  – normal driving
  PAUSED   – overlay shown, physics frozen
"""

import sys
import pygame

from config import (
    WINDOW_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT, TARGET_FPS,
    BG_COLOR, DEFAULT_LAT, DEFAULT_LON, MAP_RADIUS_DEG,
)
from osm_loader  import load_map, find_spawn_point
from car_physics import Car
from wheel_input import WheelInput
from renderer    import Renderer


class Game:
    STATE_LOADING = "loading"
    STATE_PLAYING = "playing"
    STATE_PAUSED  = "paused"

    def __init__(self, lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON,
                 radius_deg: float = MAP_RADIUS_DEG):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption(WINDOW_TITLE)
        self.clock   = pygame.time.Clock()
        self.running = True

        self._lat        = lat
        self._lon        = lon
        self._radius_deg = radius_deg

        self.state    = self.STATE_LOADING
        self.map_data = None
        self.car      = None
        self.wheel    = WheelInput()
        self.renderer = Renderer(self.screen)
        self.renderer.init()

        self._font = pygame.font.SysFont("monospace", 20)

    # ── Public entry point ────────────────────────────────────────────────────

    def run(self):
        self._load_map()
        while self.running:
            dt = self.clock.tick(TARGET_FPS) / 1000.0
            dt = min(dt, 0.05)  # cap at 50 ms to avoid spiral of death

            events = pygame.event.get()
            self._handle_global_events(events)

            if self.state == self.STATE_PLAYING:
                self._update(dt, events)
                self.renderer.draw(self.car, self.map_data, dt)
            elif self.state == self.STATE_PAUSED:
                self.renderer.draw(self.car, self.map_data, 0.0)
                self._draw_pause_overlay()
            elif self.state == self.STATE_LOADING:
                self._draw_loading()

            # Pass events to renderer for zoom etc.
            for ev in events:
                self.renderer.handle_event(ev)

            pygame.display.flip()

        pygame.quit()

    # ── Loading ───────────────────────────────────────────────────────────────

    def _load_map(self):
        """Fetch OSM data synchronously (shows a loading screen first)."""
        self._draw_loading()
        pygame.display.flip()
        pygame.event.pump()

        print(f"[Game] Loading map  lat={self._lat:.4f}  lon={self._lon:.4f}"
              f"  r={self._radius_deg:.4f}°")
        self.map_data = load_map(self._lat, self._lon, self._radius_deg)
        print(f"[Game] Loaded {len(self.map_data.roads)} road segments.")

        spawn = find_spawn_point(self.map_data)
        self.car = Car(x=spawn[0], y=spawn[1], heading=0.0)

        self.renderer.bake_road_surface(self.map_data)
        self.state = self.STATE_PLAYING

    def _draw_loading(self):
        self.screen.fill(BG_COLOR)
        lines = [
            "OSM Street Racer",
            "",
            "Fetching map data from OpenStreetMap …",
            "(cached after first download)",
            "",
            "Press ESC to quit",
        ]
        for i, line in enumerate(lines):
            surf = self._font.render(line, True, (200, 200, 200))
            rect = surf.get_rect(center=(WINDOW_WIDTH // 2,
                                         WINDOW_HEIGHT // 2 - 60 + i * 28))
            self.screen.blit(surf, rect)

    # ── Game update ───────────────────────────────────────────────────────────

    def _update(self, dt: float, events: list):
        self.wheel.update(events)
        self.car.set_steer(self.wheel.steer)
        self.car.set_throttle(self.wheel.throttle)
        self.car.set_brake(self.wheel.brake)
        self.car.update(dt)

    # ── Event handling ────────────────────────────────────────────────────────

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

                elif ev.key == pygame.K_p or ev.key == pygame.K_PAUSE:
                    if self.state == self.STATE_PLAYING:
                        self.state = self.STATE_PAUSED
                    elif self.state == self.STATE_PAUSED:
                        self.state = self.STATE_PLAYING

                elif ev.key == pygame.K_r and self.state != self.STATE_LOADING:
                    # Respawn at map origin
                    spawn = find_spawn_point(self.map_data)
                    self.car.x     = spawn[0]
                    self.car.y     = spawn[1]
                    self.car.speed = 0.0

    # ── Pause overlay ─────────────────────────────────────────────────────────

    def _draw_pause_overlay(self):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.screen.blit(overlay, (0, 0))

        lines = [
            "── PAUSED ──",
            "",
            "P / Pause  –  resume",
            "R          –  respawn",
            "+ / −      –  zoom",
            "ESC        –  quit",
            "",
            "Wheel: steer / throttle / brake",
            "Keyboard fallback: WASD / arrow keys",
        ]
        for i, line in enumerate(lines):
            surf = self._font.render(line, True, (220, 220, 220))
            rect = surf.get_rect(center=(WINDOW_WIDTH // 2,
                                          WINDOW_HEIGHT // 2 - 100 + i * 26))
            self.screen.blit(surf, rect)
