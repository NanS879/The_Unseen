"""
Professional debug HUD with glass-morphism design.

Shows: FPS sparkline, frame time, particles/layer, organisms,
energy bar, space state, hand tracking, time phase.

Keybindings: D=toggle, F=FPS badge, R=release mode

Perf: Font is loaded once via set_font(), not every frame.
When hidden, only FPS history is tracked (negligible cost).
"""

from collections import deque


# ── Color palette ───────────────────────────────────────
C_BG       = (10, 10, 20, 200)    # dark glass panel
C_HEADER   = (180, 190, 230)      # title text
C_LABEL    = (130, 140, 170)      # section labels
C_VALUE    = (210, 215, 235)      # data values
C_DIVIDER  = (50, 55, 75, 120)    # thin separator
C_FPS_OK   = (80, 220, 100)       # 55+ fps
C_FPS_WARN  = (240, 200, 50)      # 30-55 fps
C_FPS_BAD   = (240, 70, 70)       # <30 fps
C_ENERGY   = (255, 200, 70)       # energy gold
C_ENERGY_LO = (120, 130, 180)     # energy low
C_HAND     = (240, 190, 110)      # hand data
C_HINT     = (100, 105, 125)      # key hints
C_STATE: dict[str, tuple[int, int, int]] = {
    "IDLE":    (90, 130, 240),
    "ACTIVE":  (80, 230, 100),
    "EXCITED": (255, 170, 50),
    "CALM":    (110, 190, 245),
}

PANEL_W = 300
PANEL_X = 12
PANEL_Y = 12
LINE_H  = 15
FONT_SIZE = 10


class DebugOverlay:
    """Toggleable debug HUD with FPS sparkline."""

    def __init__(self) -> None:
        self.visible: bool = False
        self.fps_only: bool = False
        self._frame_times: deque[float] = deque(maxlen=80)
        self._fps: float = 0.0
        self._font: object = None     # py5 font, set via set_font()

    def set_font(self, font) -> None:
        """Cache the py5 font object (call once in setup)."""
        self._font = font

    def toggle(self) -> None:
        self.visible = not self.visible
        if self.visible:
            self.fps_only = False

    def toggle_fps(self) -> None:
        self.fps_only = not self.fps_only
        if self.fps_only:
            self.visible = False

    def update(self, frame_time_ms: float) -> None:
        self._frame_times.append(frame_time_ms)
        if len(self._frame_times) >= 2:
            avg = sum(self._frame_times) / len(self._frame_times)
            self._fps = 1000.0 / avg if avg > 0 else 0.0

    # ── Main draw ──────────────────────────────────────

    def draw(
        self, py5,
        particles: dict[str, int],
        organisms: int, growth_pts: int, seeds: int,
        energy: float, state: str, phase: str,
        hands: list[tuple[float, float]],
        speeds: list[float],
    ) -> None:
        if self.fps_only:
            self._draw_fps_badge(py5)
            return
        if not self.visible:
            return

        py5.push()
        if self._font:
            py5.text_font(self._font)

        py5.text_size(FONT_SIZE)
        rh = self._content_rows(particles, organisms, growth_pts, seeds, hands, speeds)
        panel_h = 24 + rh * LINE_H + 30  # header + rows + sparkline

        # ── Glass panel ──────────────────────────────
        py5.no_stroke()
        py5.fill(*C_BG)
        py5.rect(PANEL_X, PANEL_Y, PANEL_W, panel_h, 6)

        x = PANEL_X + 10
        y = PANEL_Y + 16

        # ── Header ───────────────────────────────────
        py5.fill(*C_HEADER)
        py5.text("The Unseen  v3.5", x, y)
        y += LINE_H + 3

        # ── FPS + Sparkline ──────────────────────────
        self._draw_fps_row(py5, x, y, PANEL_W - 20)
        y += LINE_H + 2

        # ── Divider ──────────────────────────────────
        py5.stroke(*C_DIVIDER)
        py5.stroke_weight(0.5)
        py5.line(x, y, x + PANEL_W - 20, y)
        py5.no_stroke()
        y += 6

        # ── State + Time ─────────────────────────────
        sc = C_STATE.get(state, (200, 200, 200))
        py5.fill(*C_LABEL); py5.text("State", x, y)
        py5.fill(*sc);        py5.text(f"{state}", x + 50, y)
        py5.fill(*C_LABEL); py5.text("Time", x + 130, y)
        py5.fill(*C_VALUE); py5.text(f"{phase}", x + 165, y)
        y += LINE_H

        # ── Particles ────────────────────────────────
        total = sum(particles.values())
        bg = particles.get("background", 0)
        it = particles.get("interaction", 0)
        hl = particles.get("highlight", 0)
        py5.fill(*C_LABEL); py5.text("Particles", x, y)
        py5.fill(*C_VALUE); py5.text(f"{total}", x + 55, y)
        py5.fill(*C_LABEL); py5.text(
            f"BG {bg}  INT {it}  HL {hl}", x + 100, y)
        y += LINE_H

        # ── Organisms ────────────────────────────────
        py5.fill(*C_LABEL); py5.text("Organisms", x, y)
        py5.fill(*C_VALUE)
        py5.text(f"{organisms} orgs  {seeds} seeds  {growth_pts} pts", x + 65, y)
        y += LINE_H

        # ── Energy bar ───────────────────────────────
        py5.fill(*C_LABEL); py5.text("Energy", x, y)
        bar_x, bar_y, bar_w, bar_h = x + 50, y - 9, 100, 10
        ec = C_ENERGY if energy > 30 else C_ENERGY_LO
        py5.fill(*ec, 60);  py5.rect(bar_x, bar_y, bar_w, bar_h, 3)
        py5.fill(*ec, 220); py5.rect(bar_x, bar_y, min(bar_w, energy / 100 * bar_w), bar_h, 3)
        py5.fill(*ec); py5.text(f"{energy:.0f}%", bar_x + bar_w + 6, y)
        y += LINE_H

        # ── Hands ────────────────────────────────────
        if hands:
            for i, (hx, hy) in enumerate(hands):
                spd = speeds[i] if i < len(speeds) else 0.0
                side = "L" if i == 0 or (len(hands) > 1 and hx < py5.width / 2) else "R"
                py5.fill(*C_HAND)
                py5.text(f"Hand {side}  ({hx:4.0f}, {hy:4.0f})  {spd:.3f}", x, y)
                y += LINE_H
        else:
            py5.fill(*C_LABEL); py5.text("Hands  —", x, y)
            y += LINE_H

        # ── FPS sparkline ────────────────────────────
        spark_y = y + 4
        self._draw_sparkline(py5, x, spark_y, PANEL_W - 20, 26)

        # ── Hint ─────────────────────────────────────
        py5.fill(*C_HINT)
        py5.text("D hide  F badge  R release", x + 90, spark_y + 20)

        py5.pop()

    # ── Helpers ────────────────────────────────────────

    def _content_rows(self, particles, organisms, growth_pts, seeds, hands, speeds) -> int:
        rows = 6  # header+fps, divider, state, particles, organisms, energy
        rows += max(1, len(hands)) if hands else 1
        return rows

    def _draw_fps_row(self, py5, x, y, w) -> None:
        fps = self._fps
        avg_ms = 1000.0 / fps if fps > 0 else 0
        fc = C_FPS_OK if fps >= 55 else (C_FPS_WARN if fps >= 30 else C_FPS_BAD)
        py5.fill(*C_LABEL); py5.text("FPS", x, y)
        py5.fill(*fc);       py5.text(f"{fps:.0f}", x + 35, y)
        py5.fill(*C_LABEL); py5.text(f"· {avg_ms:.1f}ms", x + 70, y)

    def _draw_fps_badge(self, py5) -> None:
        """Minimal corner FPS badge."""
        fps = self._fps
        fc = C_FPS_OK if fps >= 55 else (C_FPS_WARN if fps >= 30 else C_FPS_BAD)
        bw, bh = 62, 20
        bx, by = py5.width - bw - 10, 10
        py5.push()
        py5.no_stroke()
        py5.fill(10, 10, 20, 170)
        py5.rect(bx, by, bw, bh, 4)
        py5.fill(*fc)
        if self._font:
            py5.text_font(self._font)
        py5.text_size(FONT_SIZE)
        py5.text(f"FPS {fps:.0f}", bx + 6, by + 13)
        py5.pop()

    def _draw_sparkline(self, py5, x, y, w, h) -> None:
        """Mini FPS sparkline from frame time history."""
        times = list(self._frame_times)
        n = len(times)
        if n < 2:
            return
        max_t = max(times)
        min_t = min(times)
        rng = max(max_t - min_t, 0.5)
        step = w / (n - 1)

        py5.no_fill()
        py5.stroke(80, 200, 120, 120)
        py5.stroke_weight(0.8)
        with py5.begin_shape():
            for i, t in enumerate(times):
                sx = x + i * step
                sy = y + h - (t - min_t) / rng * h
                py5.vertex(sx, sy)
        py5.stroke_weight(1.0)
        py5.no_stroke()
