import pygame
import math
import sys
from pathlib import Path

# Paths and assets
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    ASSET_DIR = Path(sys._MEIPASS) / "assets"
else:
    ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"

def get_font_path(filename):
    p = ASSET_DIR / filename
    return str(p) if p.exists() else None

class UITheme:
    """Manages high-tech sci-fi typography, color palettes, and polished UI widget renderers."""
    
    # Modern Sci-Fi Color Palette
    CYAN = (0, 240, 255)
    CYAN_DIM = (0, 150, 180)
    CYAN_DARK = (15, 38, 55)
    
    AMBER = (255, 185, 45)
    GREEN = (65, 240, 145)
    GREEN_DIM = (30, 130, 75)
    RED = (255, 75, 95)
    RED_DIM = (140, 35, 45)
    GOLD = (255, 215, 65)
    
    TEXT_WHITE = (245, 250, 255)
    TEXT_MUTED = (160, 185, 215)
    TEXT_DARK = (90, 115, 145)
    
    PANEL_BG = (12, 18, 30)
    PANEL_BORDER = (45, 90, 140)
    PANEL_BORDER_LIGHT = (70, 140, 210)

    def __init__(self, scale_factor=1.0):
        self.scale_factor = scale_factor
        def s(pt):
            return max(8, int(round(pt * scale_factor)))

        # Load fonts with graceful fallbacks
        p_orbitron = get_font_path("Orbitron-Bold.ttf")
        p_audiowide = get_font_path("Audiowide-Regular.ttf")
        p_chakra_b = get_font_path("ChakraPetch-Bold.ttf")
        p_chakra_r = get_font_path("ChakraPetch-Regular.ttf")
        p_rajdhani = get_font_path("Rajdhani-SemiBold.ttf")
        p_sharetech = get_font_path("ShareTechMono-Regular.ttf")
        p_pixelta = get_font_path("Pixelta.ttf")

        # Title font (Orbitron)
        try:
            self.title_large = pygame.font.Font(p_orbitron, s(52))
            self.title = pygame.font.Font(p_orbitron, s(38))
            self.title_small = pygame.font.Font(p_orbitron, s(28))
        except Exception:
            self.title_large = pygame.font.SysFont(None, s(56))
            self.title = pygame.font.SysFont(None, s(42))
            self.title_small = pygame.font.SysFont(None, s(30))

        # Header font (Audiowide)
        try:
            self.header = pygame.font.Font(p_audiowide, s(24))
            self.header_small = pygame.font.Font(p_audiowide, s(18))
        except Exception:
            self.header = pygame.font.SysFont(None, s(26))
            self.header_small = pygame.font.SysFont(None, s(20))

        # UI / Button fonts (Chakra Petch Bold)
        try:
            self.button = pygame.font.Font(p_chakra_b, s(20))
            self.button_large = pygame.font.Font(p_chakra_b, s(24))
            self.button_small = pygame.font.Font(p_chakra_b, s(16))
            self.label = pygame.font.Font(p_chakra_b, s(18))
            self.label_large = pygame.font.Font(p_chakra_b, s(22))
        except Exception:
            self.button = pygame.font.SysFont(None, s(24))
            self.button_large = pygame.font.SysFont(None, s(28))
            self.button_small = pygame.font.SysFont(None, s(18))
            self.label = pygame.font.SysFont(None, s(20))
            self.label_large = pygame.font.SysFont(None, s(24))

        # Body / Details (Chakra Petch Regular)
        try:
            self.body = pygame.font.Font(p_chakra_r, s(15))
            self.body_small = pygame.font.Font(p_chakra_r, s(13))
        except Exception:
            self.body = pygame.font.SysFont(None, s(16))
            self.body_small = pygame.font.SysFont(None, s(14))
        self.small = self.body_small

        # Stats & Numbers (Rajdhani)
        try:
            self.stat_large = pygame.font.Font(p_rajdhani, s(26))
            self.stat = pygame.font.Font(p_rajdhani, s(20))
            self.stat_small = pygame.font.Font(p_rajdhani, s(16))
        except Exception:
            self.stat_large = pygame.font.SysFont(None, s(28))
            self.stat = pygame.font.SysFont(None, s(22))
            self.stat_small = pygame.font.SysFont(None, s(18))

        # Tech telemetry & Monospace (Share Tech Mono)
        try:
            self.mono = pygame.font.Font(p_sharetech, s(15))
            self.mono_small = pygame.font.Font(p_sharetech, s(12))
        except Exception:
            self.mono = pygame.font.SysFont(None, s(16))
            self.mono_small = pygame.font.SysFont(None, s(13))

    def draw_cyber_button(self, surface, rect, text, font=None, hovered=False, primary=False, color_accent=None, disabled=False):
        """Draw a sleek futuristic button with chamfered cyber corners and glowing hover state."""
        font = font or self.button
        rect = pygame.Rect(rect)
        
        # Color resolution
        if disabled:
            bg_color = (20, 24, 32)
            border_color = (50, 60, 75)
            text_color = (100, 115, 135)
        elif color_accent:
            border_color = color_accent if hovered else tuple(max(30, int(c * 0.75)) for c in color_accent)
            bg_color = tuple(min(255, int(c * 0.28) + 15) for c in color_accent) if hovered else (18, 26, 38)
            text_color = (255, 255, 255) if hovered else color_accent
        elif primary:
            border_color = (0, 255, 240) if hovered else (0, 200, 220)
            bg_color = (15, 60, 78) if hovered else (12, 38, 52)
            text_color = (255, 255, 255) if hovered else (180, 245, 255)
        else:
            border_color = self.CYAN if hovered else (75, 115, 160)
            bg_color = (22, 42, 64) if hovered else (16, 24, 38)
            text_color = (255, 255, 255) if hovered else (200, 220, 245)

        # Main background box
        pygame.draw.rect(surface, bg_color, rect, border_radius=4)
        
        # Glow edge on hover or primary
        if hovered and not disabled:
            glow_surf = pygame.Surface((rect.width + 4, rect.height + 4), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (*border_color[:3], 60), (0, 0, rect.width + 4, rect.height + 4), border_radius=6)
            surface.blit(glow_surf, (rect.x - 2, rect.y - 2))

        # Main border
        border_width = max(1, int(2 * self.scale_factor)) if (hovered or primary) else max(1, int(1 * self.scale_factor))
        pygame.draw.rect(surface, border_color, rect, border_width, border_radius=max(2, int(4 * self.scale_factor)))
        
        # Sci-Fi corner tick marks
        corner_len = min(max(4, int(6 * self.scale_factor)), rect.width // 6, rect.height // 6)
        if not disabled:
            # Top-left corner tick
            pygame.draw.line(surface, border_color, (rect.x, rect.y + corner_len), (rect.x, rect.y), max(1, int(2 * self.scale_factor)))
            pygame.draw.line(surface, border_color, (rect.x, rect.y), (rect.x + corner_len, rect.y), max(1, int(2 * self.scale_factor)))
            # Bottom-right corner tick
            pygame.draw.line(surface, border_color, (rect.right - 1, rect.bottom - 1 - corner_len), (rect.right - 1, rect.bottom - 1), max(1, int(2 * self.scale_factor)))
            pygame.draw.line(surface, border_color, (rect.right - 1 - corner_len, rect.bottom - 1), (rect.right - 1, rect.bottom - 1), max(1, int(2 * self.scale_factor)))

        # Text rendering
        text_surf = font.render(text, True, text_color)
        surface.blit(text_surf, text_surf.get_rect(center=rect.center))

    def draw_cyber_panel(self, surface, rect, title=None, border_color=None, bg_alpha=220):
        """Draw a darkened semi-transparent glass panel with sci-fi framing and header tab."""
        rect = pygame.Rect(rect)
        border_color = border_color or self.PANEL_BORDER
        
        # Translucent glass backing
        glass = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        glass.fill((*self.PANEL_BG[:3], bg_alpha))
        surface.blit(glass, rect.topleft)
        
        # Outline
        pygame.draw.rect(surface, border_color, rect, max(1, int(1 * self.scale_factor)))
        
        # Glowing cyber corners
        c_len = max(6, int(10 * self.scale_factor))
        accent = (0, 210, 240)
        c_thick = max(1, int(2 * self.scale_factor))
        # Top-left
        pygame.draw.line(surface, accent, (rect.x, rect.y), (rect.x + c_len, rect.y), c_thick)
        pygame.draw.line(surface, accent, (rect.x, rect.y), (rect.x, rect.y + c_len), c_thick)
        # Top-right
        pygame.draw.line(surface, accent, (rect.right - 1 - c_len, rect.y), (rect.right - 1, rect.y), c_thick)
        pygame.draw.line(surface, accent, (rect.right - 1, rect.y), (rect.right - 1, rect.y + c_len), c_thick)
        # Bottom-left
        pygame.draw.line(surface, accent, (rect.x, rect.bottom - 1), (rect.x + c_len, rect.bottom - 1), c_thick)
        pygame.draw.line(surface, accent, (rect.x, rect.bottom - 1 - c_len), (rect.x, rect.bottom - 1), c_thick)
        # Bottom-right
        pygame.draw.line(surface, accent, (rect.right - 1 - c_len, rect.bottom - 1), (rect.right - 1, rect.bottom - 1), c_thick)
        pygame.draw.line(surface, accent, (rect.right - 1, rect.bottom - 1 - c_len), (rect.right - 1, rect.bottom - 1), c_thick)

        # Title bar if provided
        if title:
            t_surf = self.header_small.render(title, True, self.CYAN)
            tab_width = t_surf.get_width() + int(24 * self.scale_factor)
            tab_h = max(18, int(22 * self.scale_factor))
            tab_rect = pygame.Rect(rect.x + int(14 * self.scale_factor), rect.y - int(12 * self.scale_factor), tab_width, tab_h)
            pygame.draw.rect(surface, self.PANEL_BG, tab_rect)
            pygame.draw.rect(surface, border_color, tab_rect, 1)
            surface.blit(t_surf, (rect.x + int(26 * self.scale_factor), rect.y - int(10 * self.scale_factor)))

    def draw_stat_bar(self, surface, x, y, width, height, current_val, max_val, color=None, label="", stat_text=""):
        """Draw a segmented high-tech telemetry gauge with smooth visual fill."""
        color = color or self.CYAN
        ratio = max(0.0, min(1.0, current_val / max(1.0, max_val)))
        
        # Label & value display
        if label or stat_text:
            lbl_surf = self.body_small.render(label, True, self.TEXT_MUTED)
            val_str = stat_text if stat_text else f"{int(current_val)}/{int(max_val)}"
            val_surf = self.stat_small.render(val_str, True, color)
            surface.blit(lbl_surf, (x, y - int(16 * self.scale_factor)))
            surface.blit(val_surf, (x + width - val_surf.get_width(), y - int(16 * self.scale_factor)))

        # Background slot
        slot_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(surface, (14, 20, 30), slot_rect)
        pygame.draw.rect(surface, (45, 65, 88), slot_rect, 1)
        
        # Fill
        fill_w = round((width - 4) * ratio)
        if fill_w > 0:
            fill_rect = pygame.Rect(x + 2, y + 2, fill_w, height - 4)
            pygame.draw.rect(surface, color, fill_rect)
            # Segment ticks
            step = max(8, int(16 * self.scale_factor))
            for sx in range(x + 2 + step, x + 2 + fill_w, step):
                pygame.draw.line(surface, (10, 16, 25), (sx, y + 2), (sx, y + height - 3), 1)

    def draw_badge(self, surface, x, y, text, font=None, color=None, border=True):
        """Draw an alert or difficulty badge."""
        font = font or self.mono_small
        color = color or self.CYAN
        t_surf = font.render(text, True, color)
        pad_x, pad_y = 6, 2
        bg_rect = pygame.Rect(x, y, t_surf.get_width() + pad_x * 2, t_surf.get_height() + pad_y * 2)
        
        # Dark fill with slight tint
        bg_tint = tuple(min(255, int(c * 0.25)) for c in color[:3])
        pygame.draw.rect(surface, bg_tint, bg_rect, border_radius=3)
        if border:
            pygame.draw.rect(surface, color, bg_rect, 1, border_radius=3)
        surface.blit(t_surf, (x + pad_x, y + pad_y))
        return bg_rect

# Global singleton instance for easy import
theme = UITheme()
