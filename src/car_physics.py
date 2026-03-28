"""
Simple arcade-style car physics for the OSM racing game.

  x, y    – position in metres (local Cartesian)
  heading – angle in degrees, 0 = east (+x), 90 = north (−y on screen)
  speed   – m/s (always ≥ 0; reverse not modelled)
"""

import math
from config import (
    CAR_MAX_SPEED_MS, CAR_ACCEL, CAR_BRAKE,
    CAR_DRAG, CAR_STEER_DEG_S, CAR_STEER_FALLOFF,
)


class Car:
    # Visual dimensions in metres (used by renderer)
    WIDTH  = 2.0
    LENGTH = 4.5

    def __init__(self, x: float = 0.0, y: float = 0.0, heading: float = 0.0):
        self.x       = x
        self.y       = y
        self.heading = heading   # degrees
        self.speed   = 0.0      # m/s

        # Odometer / telemetry
        self.distance_m  = 0.0
        self.elapsed_s   = 0.0

        # Wheel inputs (0..1 each, applied each frame)
        self._throttle = 0.0
        self._brake    = 0.0
        self._steer    = 0.0   # -1 = full left, +1 = full right

    # ── Input setters (called by WheelInput each frame) ──────────────────────

    def set_throttle(self, v: float):
        self._throttle = max(0.0, min(1.0, v))

    def set_brake(self, v: float):
        self._brake = max(0.0, min(1.0, v))

    def set_steer(self, v: float):
        self._steer = max(-1.0, min(1.0, v))

    # ── Physics step ──────────────────────────────────────────────────────────

    def update(self, dt: float):
        """Advance physics by dt seconds."""
        self.elapsed_s += dt

        # ── Longitudinal ──────────────────────────────────────────────────────
        accel = self._throttle * CAR_ACCEL
        decel = self._brake    * CAR_BRAKE

        # Aerodynamic / rolling drag (quadratic-ish)
        drag  = self.speed * CAR_DRAG * self.speed + self.speed * 0.002

        self.speed += (accel - decel - drag) * dt
        self.speed  = max(0.0, min(CAR_MAX_SPEED_MS, self.speed))

        # ── Lateral / steering ────────────────────────────────────────────────
        # Steering authority decreases at high speed to stay stable
        steer_rate = CAR_STEER_DEG_S / (1.0 + self.speed * CAR_STEER_FALLOFF)
        self.heading += self._steer * steer_rate * dt
        self.heading %= 360.0

        # ── Position ──────────────────────────────────────────────────────────
        rad    = math.radians(self.heading)
        dx     = math.cos(rad) * self.speed * dt
        dy     = math.sin(rad) * self.speed * dt   # screen-y is flipped in renderer
        self.x += dx
        self.y += dy

        self.distance_m += self.speed * dt

    # ── Telemetry helpers ─────────────────────────────────────────────────────

    @property
    def speed_kmh(self) -> float:
        return self.speed * 3.6

    @property
    def corners(self) -> list:
        """Four corner (x, y) positions for collision / rendering."""
        hw = self.WIDTH  / 2
        hl = self.LENGTH / 2
        rad = math.radians(self.heading)
        cos_h, sin_h = math.cos(rad), math.sin(rad)

        def rotate(lx, ly):
            return (self.x + lx * cos_h - ly * sin_h,
                    self.y + lx * sin_h + ly * cos_h)

        return [
            rotate( hl,  hw),
            rotate( hl, -hw),
            rotate(-hl, -hw),
            rotate(-hl,  hw),
        ]
