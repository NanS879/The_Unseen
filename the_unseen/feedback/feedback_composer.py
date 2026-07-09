"""
V5 Immersive Feedback System.

Cinematic multi-stage feedback for every space ability.
All effects work within py5 (no shaders required):

    CameraEffectManager — zoom, shake, drift via py5 matrix stack
    TimeManager          — freeze, slow-mo, time scaling
    PostEffectManager    — bloom, vignette, exposure overlays
    LightingManager      — global ambient/glow modulation
    FeedbackComposer     — orchestrates 3-stage ability feedback

Design:
    Ability activation → FeedbackComposer starts cinematic sequence
    Stage 1 (0-100ms): immediate hand-level feedback
    Stage 2 (100-800ms): space-level response
    Stage 3 (1-3s): outcome resolution
    Camera/Time/Post all use smoothstep easing — no sudden jumps.
"""

import math
import random
import time

from ..utils.easing import smoothstep, ease_out_cubic


# ============================================================
# Camera Effect Manager
# ============================================================

class CameraEffectManager:
    """Screen-space camera transforms via py5 matrix stack.

    Effects: zoom, shake, drift, impulse.
    All use smoothstep easing and layer additively.

    Usage:
        camera.apply(py5)  # call at start of draw(), inside push_matrix()
    """

    def __init__(self) -> None:
        # Per-effect state: {name: (strength, elapsed, duration, easing_fn)}
        self._effects: dict[str, tuple[float, float, float, str]] = {}

    def trigger(
        self,
        effect: str,
        strength: float = 1.0,
        duration: float = 0.5,
        easing: str = "ease_out",
    ) -> None:
        """Trigger a camera effect.

        Args:
            effect: "zoom_in", "zoom_out", "shake", "drift", "impulse".
            strength: Effect intensity.
            duration: Effect duration in seconds.
            easing: "ease_out", "smoothstep", or "linear".
        """
        self._effects[effect] = (strength, 0.0, duration, easing)

    def update(self, dt: float) -> None:
        """Advance all active effects."""
        to_remove = []
        for name, (strength, elapsed, duration, easing) in self._effects.items():
            elapsed += dt
            if elapsed >= duration:
                to_remove.append(name)
            else:
                self._effects[name] = (strength, elapsed, duration, easing)
        for name in to_remove:
            del self._effects[name]

    def apply(self, py5) -> None:
        """Apply camera transform. Call inside push_matrix()."""
        if not self._effects:
            return

        total_zoom = 1.0
        total_shake_x = 0.0
        total_shake_y = 0.0
        total_drift_x = 0.0
        total_drift_y = 0.0
        total_impulse = 0.0

        for name, (strength, elapsed, duration, easing_name) in self._effects.items():
            t = min(1.0, elapsed / duration)

            # Easing
            if easing_name == "ease_out":
                t_val = ease_out_cubic(t)
            elif easing_name == "smoothstep":
                t_val = smoothstep(t)
            else:
                t_val = t

            # Decay factor: 1 at start, 0 at end
            decay = 1.0 - t_val

            if name == "zoom_in":
                total_zoom += strength * 0.01 * t_val
            elif name == "zoom_out":
                total_zoom -= strength * 0.01 * t_val
            elif name == "shake":
                total_shake_x += random.uniform(-1, 1) * strength * 2.5 * decay
                total_shake_y += random.uniform(-1, 1) * strength * 2.5 * decay
            elif name == "drift":
                phase = py5.frame_count * 0.03
                total_drift_x += math.sin(phase) * strength * 3.0 * decay
                total_drift_y += math.cos(phase * 1.3) * strength * 2.0 * decay
            elif name == "impulse":
                # Quick bounce: up then back
                bounce = math.sin(t_val * math.pi) * strength * 5.0
                total_impulse += bounce * decay

        # Apply transforms
        cx, cy = py5.width / 2, py5.height / 2
        py5.translate(cx, cy)
        if total_zoom != 1.0:
            py5.scale(total_zoom)
        py5.translate(
            total_shake_x + total_drift_x + total_impulse,
            total_shake_y + total_drift_y,
        )
        py5.translate(-cx, -cy)


# ============================================================
# Time Manager
# ============================================================

class TimeManager:
    """Time scaling for slow-motion and freeze-frame effects.

    Smooth transitions — never sudden time jumps.
    """

    def __init__(self) -> None:
        self._scale: float = 1.0
        self._target: float = 1.0
        self._transition_speed: float = 5.0

    def trigger_freeze(self, duration: float = 0.15) -> None:
        """Brief freeze frame, then smooth recovery."""
        self._target = 0.01  # near-zero
        # Auto-recover after duration
        self._auto_recover = duration

    def trigger_slow_motion(self, duration: float = 0.5,
                            scale: float = 0.3) -> None:
        """Slow down time, then smooth recovery."""
        self._target = scale
        self._auto_recover = duration

    def update(self, dt: float) -> None:
        """Smoothly approach target time scale."""
        if hasattr(self, '_auto_recover') and self._auto_recover > 0:
            self._auto_recover -= dt
            if self._auto_recover <= 0:
                self._target = 1.0

        diff = self._target - self._scale
        if abs(diff) < 0.001:
            self._scale = self._target
        else:
            self._scale += diff * min(1.0, self._transition_speed * dt)

    def apply(self, dt: float) -> float:
        """Return time-scaled dt for simulation."""
        return dt * self._scale

    @property
    def time_scale(self) -> float:
        return self._scale


# ============================================================
# Post Effect Manager
# ============================================================

class PostEffectManager:
    """Screen-space post effects via overlay rectangles.

    No shaders needed. Effects layer on top of rendered frame.
    All use smooth alpha transitions.
    """

    def __init__(self) -> None:
        self._effects: dict[str, tuple[float, float, float]] = {}
        # {name: (strength, elapsed, duration)}

    def trigger(
        self,
        effect: str,
        strength: float = 1.0,
        duration: float = 0.8,
    ) -> None:
        """Trigger a post effect.

        Args:
            effect: "bloom", "vignette", "exposure_up", "exposure_down",
                    "purple_wash", "gold_flash".
            strength: 0.0–1.0.
            duration: Seconds.
        """
        self._effects[effect] = (strength, 0.0, duration)

    def update(self, dt: float) -> None:
        to_remove = []
        for name, (s, elapsed, dur) in self._effects.items():
            elapsed += dt
            if elapsed >= dur:
                to_remove.append(name)
            else:
                self._effects[name] = (s, elapsed, dur)
        for name in to_remove:
            del self._effects[name]

    def apply(self, py5) -> None:
        """Draw post effects. Call at end of draw()."""
        if not self._effects:
            return

        w, h = py5.width, py5.height

        for name, (strength, elapsed, duration) in self._effects.items():
            t = min(1.0, elapsed / duration)
            # Fade in then out (bell curve)
            fade = 1.0 - abs(2.0 * t - 1.0)  # 0→1→0
            alpha = strength * fade * smoothstep(t * 2.0 if t < 0.5 else (1.0 - t) * 2.0)

            py5.no_stroke()

            if name == "bloom":
                py5.fill(255, 255, 255, alpha * 15.0)
                py5.rect(0, 0, w, h)

            elif name == "vignette":
                cx, cy = w / 2, h / 2
                max_r = math.sqrt(cx * cx + cy * cy)
                steps = 8
                for i in range(steps):
                    r = max_r * (0.3 + i * 0.09)
                    a = alpha * 4.0 * (1.0 - i / steps)
                    py5.fill(0, 0, 0, a)
                    py5.circle(cx, cy, r * 2)

            elif name == "exposure_up":
                py5.fill(255, 255, 255, alpha * 10.0)
                py5.rect(0, 0, w, h)

            elif name == "exposure_down":
                py5.fill(0, 0, 0, alpha * 15.0)
                py5.rect(0, 0, w, h)

            elif name == "purple_wash":
                py5.fill(100, 60, 180, alpha * 8.0)
                py5.rect(0, 0, w, h)

            elif name == "gold_flash":
                py5.fill(255, 210, 80, alpha * 12.0)
                py5.rect(0, 0, w, h)


# ============================================================
# Lighting Manager
# ============================================================

class LightingManager:
    """Global ambient light and glow modulation.

    Modulates: background brightness, particle glow boost,
    color temperature shift.
    """

    def __init__(self) -> None:
        # Target values (smoothly approached)
        self._ambient: float = 0.0       # 0 (dark) to 1 (bright)
        self._glow_boost: float = 1.0    # 1 = normal, 2 = double
        self._warmth: float = 0.5        # 0 = cool, 1 = warm
        self._transition_speed: float = 2.0

    def set_ambient(self, value: float) -> None:
        self._ambient = max(0.0, min(1.0, value))

    def set_glow_boost(self, value: float) -> None:
        self._glow_boost = max(0.5, min(2.5, value))

    def set_warmth(self, value: float) -> None:
        self._warmth = max(0.0, min(1.0, value))

    def update(self, dt: float) -> None:
        """Smoothly approach targets. Called in draw()."""
        pass  # Currently instant — smooth in future if needed

    def apply(self, py5) -> None:
        """Apply global lighting. Call before particle rendering."""
        if self._ambient > 0.01:
            py5.no_stroke()
            py5.fill(255, 255, 255, self._ambient * 8.0)
            py5.rect(0, 0, py5.width, py5.height)

    @property
    def glow_multiplier(self) -> float:
        return self._glow_boost

    @property
    def warmth(self) -> float:
        return self._warmth


# ============================================================
# Feedback Composer
# ============================================================

class FeedbackComposer:
    """Orchestrates cinematic 3-stage feedback for ability activation.

    Stage 1 (0-100ms): Hand-level immediate feedback
    Stage 2 (100-800ms): Space-level response
    Stage 3 (1-3s): Outcome resolution

    Usage:
        composer.play("connect", x, y)
        composer.update(dt)  # each frame
        composer.apply_camera(py5)  # start of draw
        composer.apply_post(py5)    # end of draw
    """

    def __init__(self) -> None:
        self.camera = CameraEffectManager()
        self.time = TimeManager()
        self.post = PostEffectManager()
        self.lighting = LightingManager()

        # Active cinematic sequence
        self._sequence: dict | None = None
        self._stage: int = 0
        self._timer: float = 0.0

    # ── Play ──────────────────────────────────────────

    def play(self, ability: str, x: float, y: float) -> None:
        """Start the cinematic feedback sequence for an ability.

        Args:
            ability: "connect", "gather", "create", "guide", "expand", "merge".
            x, y: Ability position (for centered effects).
        """
        self._stage = 0
        self._timer = 0.0

        if ability == "connect":
            self._sequence = {
                "stages": [
                    {"t": 0.0, "effects": [
                        ("post", "bloom", 0.25, 0.5),
                    ]},
                    {"t": 0.06, "effects": [
                        ("camera", "drift", 0.6, 1.2, "smoothstep"),
                        ("lighting", "ambient", 0.25),
                        ("lighting", "glow", 1.2),
                    ]},
                    {"t": 0.4, "effects": [
                        ("post", "bloom", 0.15, 0.8),
                        ("lighting", "ambient", 0.1),
                    ]},
                ]
            }

        elif ability == "gather":
            self._sequence = {
                "stages": [
                    {"t": 0.0, "effects": [
                        ("camera", "zoom_in", 4.0, 0.8, "ease_out"),
                        ("post", "vignette", 0.8, 1.2),
                        ("post", "gold_flash", 0.3, 0.3),
                    ]},
                    {"t": 0.3, "effects": [
                        ("lighting", "glow", 1.6),
                        ("lighting", "warmth", 0.9),
                        ("post", "gold_flash", 0.2, 0.4),
                    ]},
                    {"t": 0.7, "effects": [
                        ("camera", "impulse", 0.5, 0.4, "smoothstep"),
                        ("post", "bloom", 0.2, 0.6),
                    ]},
                ]
            }

        elif ability == "create":
            self._sequence = {
                "stages": [
                    {"t": 0.0, "effects": [
                        ("time", "freeze", 0.15),
                        ("post", "gold_flash", 1.0, 0.4),
                        ("post", "bloom", 0.6, 1.8),
                    ]},
                    {"t": 0.15, "effects": [
                        ("camera", "zoom_in", 2.5, 1.0, "ease_out"),
                        ("lighting", "ambient", 0.5),
                        ("lighting", "glow", 2.0),
                        ("lighting", "warmth", 1.0),
                        ("post", "bloom", 0.4, 1.5),
                    ]},
                    {"t": 0.9, "effects": [
                        ("post", "bloom", 0.2, 1.0),
                        ("camera", "impulse", 0.4, 0.4, "smoothstep"),
                    ]},
                ]
            }

        elif ability == "guide":
            self._sequence = {
                "stages": [
                    {"t": 0.0, "effects": [
                        ("camera", "drift", 0.4, 0.6, "smoothstep"),
                        ("post", "bloom", 0.15, 0.3),
                    ]},
                    {"t": 0.08, "effects": [
                        ("lighting", "glow", 1.15),
                    ]},
                    {"t": 0.3, "effects": [
                        ("post", "bloom", 0.1, 0.3),
                    ]},
                ]
            }

        elif ability == "expand":
            self._sequence = {
                "stages": [
                    {"t": 0.0, "effects": [
                        ("camera", "zoom_out", 5.0, 1.5, "ease_out"),
                        ("post", "exposure_up", 0.4, 1.2),
                        ("post", "bloom", 0.5, 2.0),
                    ]},
                    {"t": 0.3, "effects": [
                        ("lighting", "ambient", 0.6),
                        ("lighting", "glow", 0.7),
                    ]},
                    {"t": 0.9, "effects": [
                        ("post", "bloom", 0.2, 1.2),
                        ("lighting", "ambient", 0.2),
                    ]},
                ]
            }

        elif ability == "merge":
            self._sequence = {
                "stages": [
                    {"t": 0.0, "effects": [
                        ("time", "slow_motion", 0.5),
                        ("post", "purple_wash", 0.6, 2.5),
                        ("camera", "drift", 1.0, 2.5, "smoothstep"),
                    ]},
                    {"t": 0.6, "effects": [
                        ("lighting", "glow", 1.6),
                        ("post", "bloom", 0.5, 2.0),
                        ("post", "purple_wash", 0.3, 1.5),
                    ]},
                    {"t": 1.8, "effects": [
                        ("camera", "zoom_in", 2.0, 1.0, "ease_out"),
                        ("post", "purple_wash", 0.1, 0.6),
                        ("post", "bloom", 0.3, 1.0),
                        ("camera", "impulse", 0.3, 0.3, "smoothstep"),
                    ]},
                ]
            }

    # ── Update ────────────────────────────────────────

    def update(self, dt: float) -> None:
        """Advance the cinematic sequence and all effect managers."""
        self.camera.update(dt)
        self.time.update(dt)
        self.post.update(dt)
        self.lighting.update(dt)

        # Process sequence stages
        if self._sequence is None:
            return

        self._timer += dt
        stages = self._sequence.get("stages", [])

        while self._stage < len(stages):
            stage = stages[self._stage]
            if self._timer >= stage["t"]:
                self._apply_stage(stage)
                self._stage += 1
            else:
                break

        # Clean up finished sequence
        if self._stage >= len(stages) and self._timer > 3.0:
            self._sequence = None

    def _apply_stage(self, stage: dict) -> None:
        """Apply all effects in a feedback stage."""
        for effect in stage["effects"]:
            kind = effect[0]

            if kind == "camera":
                _, name, strength, duration, easing = effect
                self.camera.trigger(name, strength, duration, easing)

            elif kind == "post":
                _, name, strength, duration = effect
                self.post.trigger(name, strength, duration)

            elif kind == "time":
                _, name, value = effect
                if name == "freeze":
                    self.time.trigger_freeze(value)
                elif name == "slow_motion":
                    self.time.trigger_slow_motion(value)

            elif kind == "lighting":
                _, name, value = effect
                if name == "ambient":
                    self.lighting.set_ambient(value)
                elif name == "glow":
                    self.lighting.set_glow_boost(value)
                elif name == "warmth":
                    self.lighting.set_warmth(value)

    # ── Apply ─────────────────────────────────────────

    def apply_camera(self, py5) -> None:
        """Apply camera transform. Call at start of draw() inside push_matrix()."""
        self.camera.apply(py5)

    def apply_post(self, py5) -> None:
        """Apply post effects and lighting. Call at end of draw()."""
        self.lighting.apply(py5)
        self.post.apply(py5)

    def apply_dt(self, dt: float) -> float:
        """Apply time scaling to dt. Returns modulated dt."""
        return self.time.apply(dt)
