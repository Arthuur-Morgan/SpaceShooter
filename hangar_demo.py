"""
=====================================================================
  SPACESHOOTER — Cinematic Hangar & Loadout Screen (Standalone Demo)
  Fully self-contained | Downloads assets at runtime | 60 FPS Pygame
=====================================================================
"""

import pygame
import math
import io
import sys
import urllib.request
import urllib.error
import zipfile
import struct
import zlib
import random

# ─────────────────────────────────────────────
#  SCREEN CONSTANTS
# ─────────────────────────────────────────────
SCREEN_W = 1024
SCREEN_H = 640
FPS      = 60
TITLE    = "SpaceShooter — Hangar Briefing"

# ─────────────────────────────────────────────
#  COLOUR PALETTE
# ─────────────────────────────────────────────
C_BG          = (6,  10,  20)
C_PANEL_BG    = (10, 18,  38,  210)   # RGBA
C_BORDER      = (40, 90,  160)
C_ACCENT      = (0,  220, 255)
C_ACCENT_GOLD = (255, 195, 50)
C_TEXT_WHITE  = (235, 245, 255)
C_TEXT_MUTED  = (155, 180, 215)
C_TEXT_DARK   = (80,  110, 150)
C_GREEN       = (55,  230, 140)
C_YELLOW      = (255, 215, 60)
C_RED         = (255, 70,  85)
C_NAVY        = (12,  22,  48)
C_GRID        = (0,   180, 220,  22)  # RGBA
C_CORNER      = (0,   200, 240)

# Difficulty card palette
DIFF_COLORS = {
    "easy":   (55,  230, 140),
    "medium": (0,   210, 255),
    "hard":   (255, 70,  85),
}

# ─────────────────────────────────────────────
#  ASSET DOWNLOAD HELPERS
# ─────────────────────────────────────────────
TIMEOUT = 6   # seconds per request

def _fetch(url: str) -> bytes | None:
    """Download a URL to bytes; returns None on any failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.read()
    except Exception as e:
        print(f"[ASSET] fetch failed: {e}")
        return None


def load_font_from_url(url: str, size: int) -> pygame.font.Font | None:
    """
    Download a TTF (or first TTF inside a ZIP) and return a pygame.font.Font.
    Returns None on failure so callers can fall back to SysFont.
    """
    raw = _fetch(url)
    if raw is None:
        return None
    try:
        # If it looks like a ZIP, extract the first .ttf inside
        if raw[:2] == b"PK":
            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                ttf_names = [n for n in zf.namelist() if n.lower().endswith(".ttf")]
                if not ttf_names:
                    return None
                raw = zf.read(ttf_names[0])
        return pygame.font.Font(io.BytesIO(raw), size)
    except Exception as e:
        print(f"[FONT] parse failed: {e}")
        return None


def load_image_from_url(url: str) -> pygame.Surface | None:
    """Download a PNG/JPG and decode into a pygame.Surface. Returns None on failure."""
    raw = _fetch(url)
    if raw is None:
        return None
    try:
        return pygame.image.load(io.BytesIO(raw)).convert()
    except Exception as e:
        print(f"[IMAGE] parse failed: {e}")
        return None


# ─────────────────────────────────────────────
#  PROCEDURAL FALLBACK ASSETS
# ─────────────────────────────────────────────

def make_hangar_background(w: int, h: int) -> pygame.Surface:
    """
    Generate a wide (2× screen width) cinematic space-hangar background
    programmatically when the network image cannot be downloaded.
    """
    BG_W = w * 2
    surf = pygame.Surface((BG_W, h))

    # Deep space gradient — top to bottom
    for y in range(h):
        t   = y / h
        r   = int(8  + t * 6)
        g   = int(10 + t * 8)
        b   = int(22 + t * 18)
        pygame.draw.line(surf, (r, g, b), (0, y), (BG_W, y))

    # Distant star field
    rng = random.Random(42)
    for _ in range(340):
        sx     = rng.randint(0, BG_W - 1)
        sy     = rng.randint(0, h // 2)
        radius = rng.choice([1, 1, 1, 2])
        bright = rng.randint(160, 255)
        pygame.draw.circle(surf, (bright, bright, min(255, bright + 20)), (sx, sy), radius)

    # Nebula blobs
    nebula = pygame.Surface((BG_W, h), pygame.SRCALPHA)
    for cx, cy, col, rad in [
        (BG_W // 5,     h // 3,  (55, 25, 110, 60),  180),
        (BG_W * 3 // 5, h // 4,  (15, 45, 120, 70),  220),
        (BG_W * 4 // 5, h // 2,  (80, 20, 100, 50),  160),
    ]:
        tmp = pygame.Surface((rad * 2, rad * 2), pygame.SRCALPHA)
        for step in range(rad, 0, -4):
            alpha = int(col[3] * (1 - step / rad))
            pygame.draw.circle(tmp, (*col[:3], alpha), (rad, rad), step)
        nebula.blit(tmp, (cx - rad, cy - rad))
    surf.blit(nebula, (0, 0))

    # Hangar deck floor with perspective converging lines
    vanish_x = BG_W // 2
    vanish_y = h // 2 + 60
    FLOOR_LINES = 18
    for i in range(FLOOR_LINES + 1):
        t     = i / FLOOR_LINES
        bx    = int(t * BG_W)
        alpha = int(40 + 80 * abs(0.5 - t) * 2)
        pygame.draw.line(surf, (0, 160, 210, alpha), (bx, h), (vanish_x, vanish_y), 1)

    # Horizontal deck grid lines
    for dy in range(vanish_y + 10, h, 28):
        y_frac = (dy - vanish_y) / (h - vanish_y)
        pygame.draw.line(surf, (0, 160, 210, int(25 * y_frac)), (0, dy), (BG_W, dy), 1)

    # Giant structural hangar girders (left and right columns)
    GIRDER_PAIRS = [(80, 120), (BG_W - 120, BG_W - 80)]
    for lx, rx in GIRDER_PAIRS:
        pygame.draw.rect(surf, (22, 35, 58), pygame.Rect(lx, 0, rx - lx, h))
        pygame.draw.rect(surf, (35, 60, 90), pygame.Rect(lx, 0, 3, h))
        pygame.draw.rect(surf, (35, 60, 90), pygame.Rect(rx, 0, 3, h))
        # Cross-bracing
        for brace_y in range(80, h, 100):
            pygame.draw.line(surf, (40, 75, 115), (lx, brace_y), (rx, brace_y + 40), 2)
            pygame.draw.line(surf, (40, 75, 115), (rx, brace_y), (lx, brace_y + 40), 2)

    # Platform under ship
    plat_rect = pygame.Rect(BG_W // 2 - 130, h // 2 + 90, 260, 45)
    pygame.draw.ellipse(surf, (18, 30, 52), plat_rect)
    pygame.draw.ellipse(surf, (0, 180, 215), plat_rect, 2)
    inner = plat_rect.inflate(-60, -18)
    pygame.draw.ellipse(surf, (0, 215, 255, 120), inner, 1)

    # Runway approach lights
    for i, rx in enumerate(range(BG_W // 2 - 90, BG_W // 2 + 100, 36)):
        color = (0, 240, 255) if i % 3 == 0 else (20, 90, 120)
        pygame.draw.circle(surf, color, (rx, h // 2 + 148), 5)

    # Caution stripes along hangar deck edge
    for sx in range(0, BG_W, 24):
        stripe = pygame.Surface((12, 14), pygame.SRCALPHA)
        stripe.fill((220, 175, 40, 180))
        surf.blit(stripe, (sx, h // 2 + 115))
        stripe2 = pygame.Surface((12, 14), pygame.SRCALPHA)
        stripe2.fill((18, 18, 22, 180))
        surf.blit(stripe2, (sx + 12, h // 2 + 115))

    return surf


def make_spaceship_sprite(size: int = 96) -> pygame.Surface:
    """
    Procedurally draw a sleek sci-fi interceptor sprite viewed from above.
    """
    s = size
    surf = pygame.Surface((s, s), pygame.SRCALPHA)
    cx, cy = s // 2, s // 2

    # Engine exhaust glow beneath hull
    glow = pygame.Surface((s, s), pygame.SRCALPHA)
    for r, a in [(34, 50), (24, 90), (15, 130), (8, 180)]:
        pygame.draw.circle(glow, (0, 180, 255, a), (cx, cy + 34), r)
    surf.blit(glow, (0, 0))

    # Main hull — elongated diamond body
    hull_pts = [
        (cx,         cy - 42),   # nose tip
        (cx + 18,    cy - 10),
        (cx + 28,    cy + 20),
        (cx + 14,    cy + 36),
        (cx,         cy + 42),   # tail center
        (cx - 14,    cy + 36),
        (cx - 28,    cy + 20),
        (cx - 18,    cy - 10),
    ]
    pygame.draw.polygon(surf, (32, 48, 82),  hull_pts)
    pygame.draw.polygon(surf, (55, 90, 140), hull_pts, 2)

    # Hull centre stripe
    stripe_pts = [
        (cx,         cy - 42),
        (cx + 6,     cy - 12),
        (cx + 6,     cy + 28),
        (cx,         cy + 42),
        (cx - 6,     cy + 28),
        (cx - 6,     cy - 12),
    ]
    pygame.draw.polygon(surf, (48, 80, 140),  stripe_pts)
    pygame.draw.polygon(surf, (80, 180, 255), stripe_pts, 1)

    # Left wing
    lwing = [(cx - 10, cy - 4), (cx - 42, cy + 22), (cx - 30, cy + 38), (cx - 8, cy + 22)]
    pygame.draw.polygon(surf, (24, 40, 72), lwing)
    pygame.draw.polygon(surf, (50, 80, 130), lwing, 1)

    # Right wing
    rwing = [(cx + 10, cy - 4), (cx + 42, cy + 22), (cx + 30, cy + 38), (cx + 8, cy + 22)]
    pygame.draw.polygon(surf, (24, 40, 72), rwing)
    pygame.draw.polygon(surf, (50, 80, 130), rwing, 1)

    # Cannon barrels
    for bx in [cx - 24, cx + 24]:
        pygame.draw.rect(surf, (0, 200, 240), pygame.Rect(bx - 2, cy - 36, 4, 22))

    # Cockpit canopy
    pygame.draw.ellipse(surf, (0, 190, 255, 200), pygame.Rect(cx - 9, cy - 30, 18, 26))
    pygame.draw.ellipse(surf, (120, 240, 255, 120), pygame.Rect(cx - 6, cy - 28, 12, 14))

    # Engine nozzle pair
    for ex in [cx - 10, cx + 10]:
        pygame.draw.rect(surf, (60, 100, 160), pygame.Rect(ex - 4, cy + 34, 8, 10))
        pygame.draw.rect(surf, (0, 220, 255),  pygame.Rect(ex - 4, cy + 34, 8, 10), 1)

    return surf


# ─────────────────────────────────────────────
#  TEXT WRAPPING ENGINE
# ─────────────────────────────────────────────

def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    """
    Splits *text* into a list of lines that each fit within *max_width* pixels.
    Words are never broken mid-character — only at spaces.
    """
    words  = text.split()
    lines  = []
    current = ""

    for word in words:
        probe = (current + " " + word).strip()
        if font.size(probe)[0] <= max_width:
            current = probe
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines


def render_wrapped(surface: pygame.Surface, text: str, font: pygame.font.Font,
                   color: tuple, rect: pygame.Rect, line_gap: int = 4) -> int:
    """
    Render wrapped text inside *rect*, returning the Y position after the last line.
    Text is clipped to the rect; each line is anti-aliased.
    """
    lines   = wrap_text(text, font, rect.width)
    y       = rect.top
    h_line  = font.get_height()

    for line in lines:
        if y + h_line > rect.bottom:
            break   # Don't overflow the designated panel box
        surf = font.render(line, True, color)
        surface.blit(surf, (rect.left, y))
        y += h_line + line_gap

    return y


# ─────────────────────────────────────────────
#  UI PRIMITIVE HELPERS
# ─────────────────────────────────────────────

def draw_cyber_panel(dest: pygame.Surface, rect: pygame.Rect,
                     bg_color: tuple = C_PANEL_BG, border_color: tuple = C_BORDER,
                     corner_color: tuple = C_CORNER, corner_len: int = 14) -> None:
    """
    Draw a sleek semi-transparent panel with sci-fi corner ticks.
    Uses SRCALPHA surface for clean blending.
    """
    panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    panel.fill(bg_color)
    dest.blit(panel, rect.topleft)

    # Outer border
    pygame.draw.rect(dest, border_color, rect, 1)

    # Corner accent ticks
    for (ox, oy), (dx1, dy1), (dx2, dy2) in [
        (rect.topleft,     (corner_len, 0),  (0, corner_len)),
        (rect.topright,    (-corner_len, 0), (0, corner_len)),
        (rect.bottomleft,  (corner_len, 0),  (0, -corner_len)),
        (rect.bottomright, (-corner_len, 0), (0, -corner_len)),
    ]:
        p = (ox, oy)
        pygame.draw.line(dest, corner_color, p, (ox + dx1, oy + dy1), 2)
        pygame.draw.line(dest, corner_color, p, (ox + dx2, oy + dy2), 2)


def draw_cyber_button(dest: pygame.Surface, rect: pygame.Rect, label: str,
                      font: pygame.font.Font, hovered: bool = False,
                      accent: tuple = C_ACCENT) -> None:
    """Render a chamfered-corner cyber button with hover glow."""
    c = 5  # chamfer size

    bg_col  = tuple(min(255, int(v * 0.32) + 12) for v in accent) if hovered else C_NAVY
    brd_col = accent if hovered else C_BORDER

    # Background polygon (chamfered corners)
    pts = [
        (rect.left + c, rect.top),
        (rect.right - c, rect.top),
        (rect.right, rect.top + c),
        (rect.right, rect.bottom - c),
        (rect.right - c, rect.bottom),
        (rect.left + c, rect.bottom),
        (rect.left, rect.bottom - c),
        (rect.left, rect.top + c),
    ]
    pygame.draw.polygon(dest, bg_col, pts)
    pygame.draw.polygon(dest, brd_col, pts, 2 if hovered else 1)

    # Hover glow layer
    if hovered:
        glow_s = pygame.Surface((rect.width + 8, rect.height + 8), pygame.SRCALPHA)
        glow_a = (*accent[:3], 55)
        pygame.draw.rect(glow_s, glow_a, (0, 0, rect.width + 8, rect.height + 8), border_radius=6)
        dest.blit(glow_s, (rect.left - 4, rect.top - 4))

    # Label
    txt_col = (255, 255, 255) if hovered else C_TEXT_MUTED
    t_surf  = font.render(label, True, txt_col)
    dest.blit(t_surf, t_surf.get_rect(center=rect.center))


def draw_segmented_bar(dest: pygame.Surface, x: int, y: int,
                       w: int, h: int, ratio: float,
                       fill_color: tuple, seg_count: int = 18) -> None:
    """Draw a segmented progress bar (like a ship stat gauge)."""
    # Background track
    pygame.draw.rect(dest, (14, 22, 38), (x, y, w, h))
    pygame.draw.rect(dest, C_BORDER, (x, y, w, h), 1)

    fill_w = max(0, int((w - 2) * min(1.0, ratio)))
    if fill_w > 0:
        pygame.draw.rect(dest, fill_color, (x + 1, y + 1, fill_w, h - 2))

    # Segment ticks
    seg_w = (w - 2) / seg_count
    for i in range(1, seg_count):
        sx = int(x + 1 + i * seg_w)
        pygame.draw.line(dest, (8, 14, 26), (sx, y + 1), (sx, y + h - 2), 1)


# ─────────────────────────────────────────────
#  PARTICLE SYSTEM  (hangar steam vents)
# ─────────────────────────────────────────────

class Particle:
    __slots__ = ("x", "y", "vx", "vy", "size", "life", "max_life")

    def __init__(self, x: float, y: float):
        rng         = random.random
        self.x      = x + (rng() - 0.5) * 30
        self.y      = float(y)
        self.vx     = (rng() - 0.5) * 0.5
        self.vy     = -(0.7 + rng() * 0.8)
        self.size   = 3 + rng() * 5
        self.max_life = 55 + int(rng() * 40)
        self.life   = self.max_life

    def update(self):
        self.x    += self.vx
        self.y    += self.vy
        self.size += 0.08
        self.life -= 1

    def draw(self, dest: pygame.Surface, origin_x: int):
        """Draw, respecting the parallax-panned origin_x offset."""
        if self.life <= 0:
            return
        alpha = int(95 * self.life / self.max_life)
        r     = max(1, int(self.size))
        s     = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (155, 210, 255, alpha), (r, r), r)
        dest.blit(s, (int(self.x) - origin_x - r, int(self.y) - r))


class ParticleSystem:
    def __init__(self):
        self.particles: list[Particle] = []
        self._next_emit = 0

    def update(self, now: int, vent_positions: list[tuple[int, int]]):
        if now >= self._next_emit:
            for vx, vy in vent_positions:
                self.particles.append(Particle(vx, vy))
            self._next_emit = now + 100

        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.life > 0]

    def draw(self, dest: pygame.Surface, pan_x: int):
        for p in self.particles:
            p.draw(dest, pan_x)


# ─────────────────────────────────────────────
#  MAIN HANGAR SCREEN CLASS
# ─────────────────────────────────────────────

class HangarScreen:
    """
    Self-contained cinematic Hangar & Loadout customisation screen.

    * Downloads a high-quality sci-fi background & font at startup.
    * Falls back to procedural art if offline or fetch fails.
    * Manages camera pan, ship hover, particles, UI panels, and buttons.
    """

    # URLs ─────────────────────────────────────────────────────────────────
    # Orbitron Bold — classic angular sci-fi display typeface (Google Fonts CDN)
    FONT_URL = ("https://raw.githubusercontent.com/google/fonts/main/ofl/"
                "orbitron/Orbitron%5Bwght%5D.ttf")

    # Chakra Petch Bold — sharp high-tech UI label font (Google Fonts CDN)
    FONT_BOLD_URL = ("https://raw.githubusercontent.com/google/fonts/main/ofl/"
                     "chakrapetch/ChakraPetch-Bold.ttf")

    # Placeholder for a cinematic space hangar image from Unsplash (1920×1080)
    # This is a real public CDN URL — no auth required.
    BG_URL = ("https://images.unsplash.com/photo-1451187580459-43490279c0fa"
              "?w=1920&auto=format&fit=crop&q=80")

    def __init__(self, screen: pygame.Surface, clock: pygame.time.Clock):
        self.screen = screen
        self.clock  = clock
        self.W, self.H = screen.get_size()

        self._load_assets()
        self._build_layout()
        self._init_state()

    # ── Asset Loading ──────────────────────────────────────────────────────

    def _load_assets(self):
        print("[HANGAR] Fetching fonts …")
        self.font_head  = self._try_font(self.FONT_URL,      36)
        self.font_body  = self._try_font(self.FONT_BOLD_URL, 15)
        self.font_small = self._try_font(self.FONT_BOLD_URL, 12)
        self.font_btn   = self._try_font(self.FONT_URL,      17)
        self.font_stat  = self._try_font(self.FONT_BOLD_URL, 13)

        print("[HANGAR] Fetching background …")
        raw_bg = load_image_from_url(self.BG_URL)
        if raw_bg:
            # Scale to wide panoramic strip (2× screen width) for pan effect
            self.bg = pygame.transform.scale(raw_bg, (self.W * 2, self.H))
            print("[HANGAR] Background loaded from internet.")
        else:
            self.bg = make_hangar_background(self.W, self.H)
            print("[HANGAR] Using procedural background (offline/failed).")

        self.ship_img = make_spaceship_sprite(110)

    def _try_font(self, url: str, size: int) -> pygame.font.Font:
        """Try to download a WOFF2 font; fall back to Arial / system font."""
        raw = _fetch(url)
        if raw:
            try:
                # pygame-ce can load most font formats including woff2
                return pygame.font.Font(io.BytesIO(raw), size)
            except Exception:
                pass
        # Graceful fallback chain
        for name in ("Arial", "Segoe UI", "DejaVu Sans", "FreeSans", None):
            try:
                return pygame.font.SysFont(name, size, bold=False)
            except Exception:
                continue
        return pygame.font.Font(None, size)

    # ── Layout ────────────────────────────────────────────────────────────

    def _build_layout(self):
        W, H  = self.W, self.H
        PAD   = 20
        BOTTOM_H = 74
        PANEL_Y  = 10
        PANEL_H  = H - BOTTOM_H - PANEL_Y - PAD

        # Left panel — Tactical Threat Protocol (difficulty)
        LP_W = int(W * 0.31)
        self.rect_left = pygame.Rect(PAD, PANEL_Y, LP_W, PANEL_H)

        # Right panel — Vessel Specs
        RP_W = int(W * 0.31)
        self.rect_right = pygame.Rect(W - PAD - RP_W, PANEL_Y, RP_W, PANEL_H)

        # Bottom action buttons
        BPAD     = 16
        BTN_H    = 46
        BTN_ROWS = H - BOTTOM_H + (BOTTOM_H - BTN_H) // 2
        BTN_W    = 220
        btn_total_w = BTN_W * 3 + BPAD * 2
        btn_start_x = (W - btn_total_w) // 2

        self.btn_launch = pygame.Rect(btn_start_x,              BTN_ROWS, BTN_W, BTN_H)
        self.btn_custom = pygame.Rect(btn_start_x + BTN_W + BPAD, BTN_ROWS, BTN_W, BTN_H)
        self.btn_back   = pygame.Rect(btn_start_x + (BTN_W + BPAD) * 2, BTN_ROWS, BTN_W, BTN_H)

    # ── State ─────────────────────────────────────────────────────────────

    def _init_state(self):
        self.pan_x        = 0.0       # horizontal panorama scroll (pixels)
        self.pan_speed    = 0.22      # pixels per frame
        self.pan_dir      = 1         # +1 right, -1 left
        self.t            = 0.0       # running time accumulator (seconds)
        self.selected_diff = "medium"
        self.hovered_btn   = None
        self.particles     = ParticleSystem()
        self.running       = True

        # Steam vent positions (in background-space x, screen-space y)
        bg_cx = self.W             # approximate ship centre in bg-space
        self.vents = [
            (bg_cx - 100, self.H // 2 + 100),
            (bg_cx + 100, self.H // 2 + 100),
        ]

        # Ship hover parameters
        self.ship_hover_amp   = 9.0   # pixels amplitude
        self.ship_hover_speed = 1.4   # radians per second
        self.ship_base_y      = self.H // 2 - 40  # rest centre Y

    # ── Main Loop ─────────────────────────────────────────────────────────

    def run(self) -> str:
        """
        Run the hangar screen until the player picks an action.
        Returns one of: 'launch', 'customize', 'back'
        """
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.t += dt

            action = self._handle_events()
            if action:
                return action

            self._update(dt)
            self._draw()
            pygame.display.flip()

        return "back"

    # ── Event Handling ────────────────────────────────────────────────────

    def _handle_events(self) -> str | None:
        mouse = pygame.mouse.get_pos()
        self.hovered_btn = None
        for btn, key in [(self.btn_launch, "launch"),
                         (self.btn_custom, "customize"),
                         (self.btn_back,   "back")]:
            if btn.collidepoint(mouse):
                self.hovered_btn = key

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "back"
                if event.key == pygame.K_RETURN:
                    return "launch"
                if event.key in (pygame.K_1, pygame.K_KP1):
                    self.selected_diff = "easy"
                if event.key in (pygame.K_2, pygame.K_KP2):
                    self.selected_diff = "medium"
                if event.key in (pygame.K_3, pygame.K_KP3):
                    self.selected_diff = "hard"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                if self.btn_launch.collidepoint(pos):
                    return "launch"
                if self.btn_custom.collidepoint(pos):
                    return "customize"
                if self.btn_back.collidepoint(pos):
                    return "back"
                # Difficulty cards
                for key, rect in self._diff_card_rects().items():
                    if rect.collidepoint(pos):
                        self.selected_diff = key

        return None

    # ── Update ────────────────────────────────────────────────────────────

    def _update(self, dt: float):
        # Horizontal panorama ping-pong
        bg_w   = self.bg.get_width()
        max_pan = bg_w - self.W
        self.pan_x += self.pan_speed * self.pan_dir
        if self.pan_x >= max_pan:
            self.pan_x = float(max_pan)
            self.pan_dir = -1
        elif self.pan_x <= 0:
            self.pan_x = 0.0
            self.pan_dir = 1

        # Particles
        now = pygame.time.get_ticks()
        self.particles.update(now, self.vents)

    # ── Drawing ───────────────────────────────────────────────────────────

    def _draw(self):
        s = self.screen

        # ── 1. Scrolling Cinematic Background ───────────────────────────
        s.blit(self.bg, (-int(self.pan_x), 0))

        # Subtle CRT vignette overlay (darkens the outer screen edges)
        self._draw_vignette()

        # Steam particles (drawn in world-space, translated by pan)
        self.particles.draw(s, int(self.pan_x))

        # ── 2. Floating Spaceship ────────────────────────────────────────
        hover_y = self.ship_base_y + math.sin(self.t * self.ship_hover_speed) * self.ship_hover_amp
        ship_cx = self.W // 2

        # Drop-shadow / glow beneath ship
        glow_r = 56
        glow_s = pygame.Surface((glow_r * 2, glow_r // 2), pygame.SRCALPHA)
        pygame.draw.ellipse(glow_s, (0, 180, 255, 55), (0, 0, glow_r * 2, glow_r // 2))
        s.blit(glow_s, (ship_cx - glow_r, int(hover_y) + 48))

        # Ship sprite
        s.blit(self.ship_img, self.ship_img.get_rect(center=(ship_cx, int(hover_y))))

        # Holographic scan beam
        self._draw_scan_beam(ship_cx, int(hover_y))

        # ── 3. UI Panels ─────────────────────────────────────────────────
        self._draw_left_panel()
        self._draw_right_panel()

        # ── 4. Bottom Bar ─────────────────────────────────────────────────
        self._draw_bottom_bar()

        # ── 5. Top Title Bar ─────────────────────────────────────────────
        self._draw_title_bar()

    def _draw_vignette(self):
        """Draw a radial dark vignette at the screen edges."""
        vig = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        for r in range(min(self.W, self.H) // 2, 0, -6):
            progress = 1.0 - r / (min(self.W, self.H) // 2)
            a        = int(progress * progress * 145)
            pygame.draw.circle(vig, (0, 0, 0, a),
                               (self.W // 2, self.H // 2), r, 6)
        self.screen.blit(vig, (0, 0))

    def _draw_scan_beam(self, cx: int, ship_y: int):
        """Vertical holographic scan beam crossing the ship periodically."""
        phase = (self.t % 4.5)
        if phase < 3.0:
            beam_y = ship_y - 60 + int((phase / 3.0) * 120)
            bw     = 115
            beam   = pygame.Surface((bw, 4), pygame.SRCALPHA)
            beam.fill((0, 230, 255, 120))
            self.screen.blit(beam, (cx - bw // 2, beam_y))
            # Glow centre line
            gline = pygame.Surface((bw, 1), pygame.SRCALPHA)
            gline.fill((200, 245, 255, 200))
            self.screen.blit(gline, (cx - bw // 2, beam_y + 1))

    def _draw_title_bar(self):
        """Top-of-screen SPACESHOOTER title with subtitle."""
        cx = self.W // 2

        # Glow pass
        glow_surf = self.font_head.render("SPACESHOOTER", True, (0, 120, 195))
        for ox, oy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            self.screen.blit(glow_surf, glow_surf.get_rect(center=(cx + ox, 28 + oy)))

        # Main title
        t_surf = self.font_head.render("SPACESHOOTER", True, C_ACCENT)
        self.screen.blit(t_surf, t_surf.get_rect(center=(cx, 28)))

        # Subtitle
        sub_surf = self.font_small.render("— CARRIER HANGAR  ·  PRE-MISSION BRIEFING —", True, C_TEXT_DARK)
        self.screen.blit(sub_surf, sub_surf.get_rect(center=(cx, 50)))

    # ── Left Panel: Tactical Threat Protocol ─────────────────────────────

    def _diff_card_rects(self) -> dict[str, pygame.Rect]:
        """Returns the clickable rects for the three difficulty cards."""
        r     = self.rect_left
        PAD   = 10
        CARD_H = 76
        HEADER_RESERVE = 56   # space consumed by panel title
        y0    = r.top + HEADER_RESERVE

        cards = {}
        for i, key in enumerate(("easy", "medium", "hard")):
            card_r = pygame.Rect(
                r.left + PAD,
                y0 + i * (CARD_H + 8),
                r.width - PAD * 2,
                CARD_H,
            )
            cards[key] = card_r
        return cards

    def _draw_left_panel(self):
        r   = self.rect_left
        PAD = 10
        draw_cyber_panel(self.screen, r)

        # Panel title
        t = self.font_body.render("TACTICAL THREAT PROTOCOL", True, C_ACCENT)
        self.screen.blit(t, (r.left + PAD, r.top + PAD))
        pygame.draw.line(self.screen, C_BORDER,
                         (r.left + PAD, r.top + 34),
                         (r.right - PAD, r.top + 34), 1)

        # Difficulty cards
        DIFF_DATA = [
            ("easy",   "RECON — EASY",
             "35% reduced incoming damage. Slower enemy projectiles. "
             "Maximum 4 simultaneous contacts on the battlefield."),
            ("medium", "SORTIE — MEDIUM",
             "Standard arcade fleet scaling across all three rival factions. "
             "Full 5-enemy cap. Balanced for seasoned pilots."),
            ("hard",   "INVASION — HARD",
             "15% bonus incoming damage. High-velocity rounds. 6 concurrent "
             "enemies. Earns +35% Score and Credits on mission completion."),
        ]

        for (key, title, desc), card_r in zip(DIFF_DATA, self._diff_card_rects().values()):
            is_sel = (key == self.selected_diff)
            col    = DIFF_COLORS[key]

            # Card background
            bg_col = tuple(min(255, int(c * 0.22) + 14) for c in col)
            card_bg = pygame.Surface((card_r.width, card_r.height), pygame.SRCALPHA)
            card_bg.fill((*bg_col, 210))
            self.screen.blit(card_bg, card_r.topleft)
            pygame.draw.rect(self.screen, col if is_sel else C_BORDER, card_r, 2 if is_sel else 1)

            # Active indicator pip
            pip_col = col if is_sel else (55, 75, 105)
            pygame.draw.circle(self.screen, pip_col,
                               (card_r.left + 14, card_r.centery - 8), 5)

            # Title
            t_surf = self.font_stat.render(title, True, col if is_sel else C_TEXT_WHITE)
            self.screen.blit(t_surf, (card_r.left + 28, card_r.top + 8))

            # Description wrapped inside card bounds
            desc_rect = pygame.Rect(
                card_r.left + 28,
                card_r.top + 28,
                card_r.width - 36,
                card_r.height - 32,
            )
            render_wrapped(self.screen, desc, self.font_small,
                           C_TEXT_MUTED if not is_sel else (210, 235, 255),
                           desc_rect, line_gap=3)

        # Keyboard shortcut hint
        hint = self.font_small.render("Press  1 / 2 / 3  to select protocol", True, C_TEXT_DARK)
        self.screen.blit(hint, (r.left + PAD, r.bottom - 22))

    # ── Right Panel: Vessel Specifications & Loadout ──────────────────────

    def _draw_right_panel(self):
        r   = self.rect_right
        PAD = 11
        draw_cyber_panel(self.screen, r)

        # Panel title
        t = self.font_body.render("VESSEL SPECIFICATIONS", True, C_ACCENT)
        self.screen.blit(t, (r.left + PAD, r.top + PAD))
        pygame.draw.line(self.screen, C_BORDER,
                         (r.left + PAD, r.top + 34), (r.right - PAD, r.top + 34), 1)

        y = r.top + 44

        # ── Module slots ──────────────────────────────────────────────────
        MODULES = [
            {
                "slot":  "[PRIMARY CANNON]",
                "name":  "Rocket Launcher",
                "col":   (255, 145, 45),
                "stats": [
                    ("Salvo",    "3 Rockets",  0.75),
                    ("Guidance", "Auto-Lock",  1.00),
                    ("Reload",   "2.1 s",      0.70),
                ],
                "desc": (
                    "Fires a three-rocket spread with autonomous homing. "
                    "High burst damage. Ideal for mid-range capital threats."
                ),
            },
            {
                "slot":  "[PROPULSION CORE]",
                "name":  "Burst Engine",
                "col":   (55, 230, 140),
                "stats": [
                    ("Speed",     "6.5 Mach",  0.87),
                    ("Skill",     "Afterburner", 1.00),
                    ("CD",        "6 s",        0.62),
                ],
                "desc": (
                    "Afterburner active for 1.5 s, granting ×1.9 velocity. "
                    "Enables rapid repositioning against flanking fighters."
                ),
            },
            {
                "slot":  "[DEFENSE MATRIX]",
                "name":  "Round Shield",
                "col":   (80, 185, 255),
                "stats": [
                    ("Capacity", "65 HP",    1.00),
                    ("Cooldown", "16 s",     0.55),
                    ("Coverage", "360°",     1.00),
                ],
                "desc": (
                    "Full-surround barrier absorbing up to 65 damage. "
                    "Activate with [E]. Regenerates automatically after cooldown."
                ),
            },
        ]

        for mod in MODULES:
            col = mod["col"]
            # Module header row
            slot_s = self.font_small.render(mod["slot"], True, col)
            name_s = self.font_body.render(mod["name"], True, C_TEXT_WHITE)
            self.screen.blit(slot_s, (r.left + PAD, y))
            y += slot_s.get_height() + 2
            self.screen.blit(name_s, (r.left + PAD, y))
            y += name_s.get_height() + 5

            # Stat gauges
            bar_w = r.width - PAD * 2 - 85
            for stat_label, stat_val, ratio in mod["stats"]:
                lbl_s  = self.font_small.render(stat_label, True, C_TEXT_MUTED)
                val_s  = self.font_small.render(stat_val,   True, col)
                self.screen.blit(lbl_s, (r.left + PAD, y + 1))
                draw_segmented_bar(self.screen, r.left + PAD + 65, y + 1,
                                   bar_w - 50, 10, ratio, col)
                self.screen.blit(val_s, (r.right - PAD - val_s.get_width(), y))
                y += 16

            # Wrapped description box
            desc_rect = pygame.Rect(r.left + PAD, y + 4, r.width - PAD * 2, 42)
            desc_bg   = pygame.Surface((desc_rect.width, desc_rect.height), pygame.SRCALPHA)
            desc_bg.fill((14, 24, 46, 180))
            self.screen.blit(desc_bg, desc_rect.topleft)
            pygame.draw.rect(self.screen, C_BORDER, desc_rect, 1)
            render_wrapped(self.screen, mod["desc"], self.font_small,
                           C_TEXT_MUTED, desc_rect.inflate(-6, -4), line_gap=2)
            y += desc_rect.height + 12

            # Divider
            pygame.draw.line(self.screen, (35, 60, 100),
                             (r.left + PAD, y),
                             (r.right - PAD, y), 1)
            y += 10

    # ── Bottom Action Bar ─────────────────────────────────────────────────

    def _draw_bottom_bar(self):
        # Separator line
        pygame.draw.line(self.screen, C_BORDER,
                         (0, self.H - 74), (self.W, self.H - 74), 1)

        diff_col = DIFF_COLORS.get(self.selected_diff, C_ACCENT)
        BUTTONS = [
            (self.btn_launch, "LAUNCH MISSION", C_ACCENT),
            (self.btn_custom, "CUSTOMIZE LOADOUT", C_ACCENT_GOLD),
            (self.btn_back,   "[ BACK ]",             C_TEXT_MUTED),
        ]
        # Override launch button colour to reflect threat colour
        BUTTONS[0] = (self.btn_launch, "LAUNCH MISSION", diff_col)

        BTN_KEY = {id(self.btn_launch): "launch",
                   id(self.btn_custom): "customize",
                   id(self.btn_back):   "back"}

        for btn_r, label, accent in BUTTONS:
            hov = (self.hovered_btn == BTN_KEY.get(id(btn_r)))
            draw_cyber_button(self.screen, btn_r, label, self.font_btn,
                              hovered=hov, accent=accent)

        # Keyboard hints
        hint = self.font_small.render(
            "ENTER — Launch    E — Equip / Swap    ESC — Back",
            True, C_TEXT_DARK,
        )
        self.screen.blit(hint, hint.get_rect(center=(self.W // 2, self.H - 14)))


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

def main():
    pygame.init()
    pygame.display.set_caption(TITLE)
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.RESIZABLE)
    clock  = pygame.time.Clock()

    hangar = HangarScreen(screen, clock)
    result = hangar.run()

    print(f"\n[HANGAR] Player selected: {result.upper()}")
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
