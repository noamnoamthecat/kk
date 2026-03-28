"""
Logitech G923 (and compatible) wheel input via pygame's joystick API.

Axis layout (default – override in config.py if yours differs):
  Axis 0 – Steering        (-1 full-left … +1 full-right)
  Axis 1 – Throttle pedal  (+1 released  … -1 fully pressed)
  Axis 2 – Brake pedal     (+1 released  … -1 fully pressed)
  Axis 3 – Clutch pedal    (+1 released  … -1 fully pressed)

Run  python main.py --calibrate  to print live axis values so you can
verify / remap the config constants.
"""

import pygame
from config import (
    G923_AXIS_STEER, G923_AXIS_THROTTLE, G923_AXIS_BRAKE, G923_AXIS_CLUTCH,
    G923_INVERT_THROTTLE, G923_INVERT_BRAKE, G923_INVERT_CLUTCH,
    G923_STEER_DEADZONE, FF_ENABLED, FF_BUMP_LOW, FF_BUMP_HIGH, FF_BUMP_DURATION,
)

# Substrings to match when auto-detecting the G923
_G923_NAMES = ("g923", "g29", "g920", "logitech", "wheel")


def _find_wheel() -> pygame.joystick.Joystick | None:
    """Return the first joystick whose name matches a known Logitech wheel."""
    count = pygame.joystick.get_count()
    for i in range(count):
        j = pygame.joystick.Joystick(i)
        name = j.get_name().lower()
        if any(k in name for k in _G923_NAMES):
            return j
    # Fall back to any joystick
    if count > 0:
        return pygame.joystick.Joystick(0)
    return None


def _apply_deadzone(value: float, dz: float) -> float:
    if abs(value) < dz:
        return 0.0
    sign = 1.0 if value > 0 else -1.0
    return sign * (abs(value) - dz) / (1.0 - dz)


class WheelInput:
    """Reads G923 axes and exposes normalised (0..1) control values."""

    def __init__(self):
        pygame.joystick.init()
        self.joystick = _find_wheel()
        self.available = self.joystick is not None

        if self.available:
            self.joystick.init()
            print(f"[Wheel] Connected: {self.joystick.get_name()}"
                  f"  axes={self.joystick.get_numaxes()}"
                  f"  buttons={self.joystick.get_numbuttons()}")
        else:
            print("[Wheel] No wheel detected – keyboard fallback active.")

        # Normalised outputs (0..1 or -1..1)
        self.steer    = 0.0   # -1..+1
        self.throttle = 0.0   # 0..1
        self.brake    = 0.0   # 0..1
        self.clutch   = 0.0   # 0..1

        # Keyboard fallback state
        self._kb_left  = False
        self._kb_right = False
        self._kb_accel = False
        self._kb_brake = False

    # ── Public update (call once per frame, after pygame.event.pump()) ────────

    def update(self, events: list):
        """Update from pygame events (keyboard) and joystick axes."""
        for ev in events:
            if ev.type == pygame.KEYDOWN:
                self._on_key(ev.key, True)
            elif ev.type == pygame.KEYUP:
                self._on_key(ev.key, False)

        if self.available:
            self._read_wheel()
        else:
            self._read_keyboard()

    # ── Wheel reading ─────────────────────────────────────────────────────────

    def _read_wheel(self):
        n_axes = self.joystick.get_numaxes()

        def axis(idx: float) -> float:
            if idx < n_axes:
                return self.joystick.get_axis(int(idx))
            return 0.0

        raw_steer    = axis(G923_AXIS_STEER)
        raw_throttle = axis(G923_AXIS_THROTTLE)
        raw_brake    = axis(G923_AXIS_BRAKE)
        raw_clutch   = axis(G923_AXIS_CLUTCH)

        # Steering deadzone
        self.steer = _apply_deadzone(raw_steer, G923_STEER_DEADZONE)

        # Pedals: invert so "fully pressed" → 1.0
        def pedal(raw: float, invert: bool) -> float:
            v = -raw if invert else raw
            return max(0.0, (v + 1.0) / 2.0)   # remap [-1,1] → [0,1]

        self.throttle = pedal(raw_throttle, G923_INVERT_THROTTLE)
        self.brake    = pedal(raw_brake,    G923_INVERT_BRAKE)
        self.clutch   = pedal(raw_clutch,   G923_INVERT_CLUTCH)

    # ── Keyboard fallback ─────────────────────────────────────────────────────

    def _on_key(self, key: int, down: bool):
        if key in (pygame.K_LEFT,  pygame.K_a): self._kb_left  = down
        if key in (pygame.K_RIGHT, pygame.K_d): self._kb_right = down
        if key in (pygame.K_UP,    pygame.K_w): self._kb_accel = down
        if key in (pygame.K_DOWN,  pygame.K_s): self._kb_brake = down

    def _read_keyboard(self):
        if   self._kb_left  and not self._kb_right: self.steer = -1.0
        elif self._kb_right and not self._kb_left:  self.steer =  1.0
        else:                                        self.steer =  0.0
        self.throttle = 1.0 if self._kb_accel else 0.0
        self.brake    = 1.0 if self._kb_brake else 0.0
        self.clutch   = 0.0

    # ── Force feedback ────────────────────────────────────────────────────────

    def rumble(self, intensity: float = 1.0):
        """Short rumble pulse (e.g., for kerbs/collisions)."""
        if FF_ENABLED and self.available:
            try:
                low  = FF_BUMP_LOW  * intensity
                high = FF_BUMP_HIGH * intensity
                self.joystick.rumble(low, high, FF_BUMP_DURATION)
            except Exception:
                pass  # FF not supported by this device / driver

    def stop_rumble(self):
        if self.available:
            try:
                self.joystick.stop_rumble()
            except Exception:
                pass

    # ── Calibration helper ────────────────────────────────────────────────────

    def print_axes(self):
        """Print all raw axis values (used by --calibrate mode)."""
        if not self.available:
            print("[Wheel] No wheel connected.")
            return
        parts = [f"A{i}={self.joystick.get_axis(i):+.3f}"
                 for i in range(self.joystick.get_numaxes())]
        print("  ".join(parts), end="\r")
