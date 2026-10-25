import pygame
import math
import sys
import random

# ---------------------------------------------------------
# CONSTANTS & MODERN SCI-FI PALETTE
# ---------------------------------------------------------
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 640
FPS = 60

# Restrained, modern palette (Dark obsidian with ice-cyan & clean accents)
COLOR_BG_TOP = (11, 15, 25)
COLOR_BG_BOTTOM = (15, 20, 32)
COLOR_CARD_BG = (18, 25, 38)
COLOR_CARD_BORDER = (40, 56, 82)

COLOR_CYAN = (0, 215, 245)
COLOR_GREEN = (65, 230, 140)
COLOR_RED = (255, 80, 95)
COLOR_GOLD = (255, 200, 60)

TEXT_WHITE = (245, 248, 252)
TEXT_MUTED = (145, 168, 195)
TEXT_DIM = (90, 110, 135)

DIFF_COLORS = {
    "EASY": COLOR_GREEN,
    "MEDIUM": COLOR_CYAN,
    "HARD": COLOR_RED
}

# ---------------------------------------------------------
# PROCEDURAL SPACESHIP SPRITE
# ---------------------------------------------------------
def create_player_spaceship(size=120):
    """Draws a clean, sharp sci-fi interceptor sprite."""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = size // 2
    cy = size // 2

    # Engine thruster glow
    for radius, alpha in [(30, 40), (20, 80), (12, 140), (6, 220)]:
        pygame.draw.circle(surf, (0, 215, 245, alpha), (cx, cy + 42), radius)

    # Main hull plating
    hull_pts = [
        (cx, cy - 48),
        (cx + 18, cy - 10),
        (cx + 34, cy + 24),
        (cx + 16, cy + 42),
        (cx, cy + 32),
        (cx - 16, cy + 42),
        (cx - 34, cy + 24),
        (cx - 18, cy - 10),
    ]
    pygame.draw.polygon(surf, (26, 38, 62), hull_pts)
    pygame.draw.polygon(surf, (55, 100, 160), hull_pts, 2)

    # Spine
    spine = [(cx, cy - 44), (cx + 6, cy - 8), (cx + 6, cy + 28), (cx, cy + 34),
             (cx - 6, cy + 28), (cx - 6, cy - 8)]
    pygame.draw.polygon(surf, (38, 62, 105), spine)
    pygame.draw.polygon(surf, COLOR_CYAN, spine, 1)

    # Swept wings
    pygame.draw.polygon(surf, (20, 30, 50), [(cx - 14, cy - 4), (cx - 48, cy + 26), (cx - 34, cy + 42), (cx - 12, cy + 24)])
    pygame.draw.polygon(surf, (45, 80, 135), [(cx - 14, cy - 4), (cx - 48, cy + 26), (cx - 34, cy + 42), (cx - 12, cy + 24)], 1)

    pygame.draw.polygon(surf, (20, 30, 50), [(cx + 14, cy - 4), (cx + 48, cy + 26), (cx + 34, cy + 42), (cx + 12, cy + 24)])
    pygame.draw.polygon(surf, (45, 80, 135), [(cx + 14, cy - 4), (cx + 48, cy + 26), (cx + 34, cy + 42), (cx + 12, cy + 24)], 1)

    # Cannons
    for gx in [cx - 28, cx + 28]:
        pygame.draw.rect(surf, (14, 22, 36), (gx - 2, cy - 22, 5, 28))
        pygame.draw.rect(surf, COLOR_CYAN, (gx - 2, cy - 22, 5, 28), 1)

    # Cockpit visor
    pygame.draw.ellipse(surf, (0, 220, 255), (cx - 9, cy - 32, 18, 24))
    pygame.draw.ellipse(surf, (200, 245, 255), (cx - 6, cy - 30, 12, 12))

    # Dual thrusters
    for tx in [cx - 12, cx + 12]:
        pygame.draw.rect(surf, (60, 85, 120), (tx - 4, cy + 36, 8, 10))
        pygame.draw.rect(surf, (0, 255, 240), (tx - 4, cy + 36, 8, 10), 1)

    return surf

# ---------------------------------------------------------
# UI BUTTON HELPER
# ---------------------------------------------------------
def draw_button(screen, rect, text, font, hovered=False, primary=False, border_col=None, text_col=None):
    rect = pygame.Rect(rect)
    border_col = border_col or COLOR_CARD_BORDER
    text_col = text_col or TEXT_WHITE

    if primary:
        bg = (0, 145, 175) if hovered else (12, 42, 60)
        brd = COLOR_CYAN
        txt = (255, 255, 255)
    elif hovered:
        bg = (26, 38, 58)
        brd = (0, 215, 245)
        txt = (255, 255, 255)
    else:
        bg = COLOR_CARD_BG
        brd = border_col
        txt = text_col

    pygame.draw.rect(screen, bg, rect, border_radius=6)
    pygame.draw.rect(screen, brd, rect, 2 if (hovered or primary) else 1, border_radius=6)

    # Anti-aliased sharp font render
    t_surf = font.render(text, True, txt)
    screen.blit(t_surf, t_surf.get_rect(center=rect.center))

# ---------------------------------------------------------
# MAIN HANGAR APPLICATION
# ---------------------------------------------------------
def main():
    pygame.init()
    pygame.display.set_caption("SpaceShooter — Modern Hangar & Loadout")
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    # Razor-sharp standard system fonts
    font_header = pygame.font.SysFont("Arial", 22, bold=True)
    font_card_title = pygame.font.SysFont("Arial", 16, bold=True)
    font_bold = pygame.font.SysFont("Arial", 14, bold=True)
    font_body = pygame.font.SysFont("Arial", 13, bold=False)
    font_small = pygame.font.SysFont("Arial", 11, bold=False)
    font_btn = pygame.font.SysFont("Arial", 15, bold=True)
    font_badge = pygame.font.SysFont("Arial", 13, bold=True)

    ship_sprite = create_player_spaceship(120)

    # Calm stars
    rng = random.Random(42)
    stars = [(rng.randint(20, SCREEN_WIDTH - 20), rng.randint(20, SCREEN_HEIGHT - 120),
              rng.randint(90, 200), rng.choice([1, 1, 2])) for _ in range(50)]

    # State
    selected_difficulty = "MEDIUM"
    hover_time = 0.0

    # Layout
    ship_cx = 280
    ship_base_y = 300

    panel_x = 590
    panel_y = 75
    panel_w = 400
    panel_h = 445

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        hover_time += dt
        now = pygame.time.get_ticks()
        mouse_pos = pygame.mouse.get_pos()

        # -----------------------------------------------------
        # EVENT HANDLING
        # -----------------------------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    print(f"Deploying on {selected_difficulty}!")
                elif event.key in (pygame.K_1, pygame.K_KP1):
                    selected_difficulty = "EASY"
                elif event.key in (pygame.K_2, pygame.K_KP2):
                    selected_difficulty = "MEDIUM"
                elif event.key in (pygame.K_3, pygame.K_KP3):
                    selected_difficulty = "HARD"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Check Difficulty Buttons
                diff_rects = {
                    "EASY": pygame.Rect(40, 550, 120, 36),
                    "MEDIUM": pygame.Rect(170, 550, 120, 36),
                    "HARD": pygame.Rect(300, 550, 120, 36),
                }
                for diff_k, r in diff_rects.items():
                    if r.collidepoint(event.pos):
                        selected_difficulty = diff_k

                # Action Buttons
                launch_btn_r = pygame.Rect(SCREEN_WIDTH - 380, 545, 230, 44)
                back_btn_r = pygame.Rect(SCREEN_WIDTH - 135, 545, 95, 44)
                if launch_btn_r.collidepoint(event.pos):
                    print(f"Launch Mission: [{selected_difficulty}]")
                elif back_btn_r.collidepoint(event.pos):
                    running = False

        # -----------------------------------------------------
        # 1. CLEAN ATMOSPHERIC BACKGROUND
        # -----------------------------------------------------
        for y in range(0, SCREEN_HEIGHT, 4):
            t = y / SCREEN_HEIGHT
            r = int(COLOR_BG_TOP[0] * (1 - t) + COLOR_BG_BOTTOM[0] * t)
            g = int(COLOR_BG_TOP[1] * (1 - t) + COLOR_BG_BOTTOM[1] * t)
            b = int(COLOR_BG_TOP[2] * (1 - t) + COLOR_BG_BOTTOM[2] * t)
            pygame.draw.rect(screen, (r, g, b), (0, y, SCREEN_WIDTH, 4))

        for sx, sy, bright, sz in stars:
            twinkle = int(bright * (0.85 + 0.15 * math.sin(now * 0.002 + sx)))
            pygame.draw.circle(screen, (twinkle, twinkle, min(255, twinkle + 20)), (sx, sy), sz)

        # -----------------------------------------------------
        # 2. TOP HEADER BAR
        # -----------------------------------------------------
        title_surf = font_header.render("HANGAR // BRIEFING", True, COLOR_CYAN)
        screen.blit(title_surf, (40, 24))

        sub_surf = font_small.render("CARRIER DOCKING BAY 04 • VESSEL READY", True, TEXT_DIM)
        screen.blit(sub_surf, (42, 50))

        # Wallet Badge
        wallet_r = pygame.Rect(SCREEN_WIDTH - 200, 24, 160, 32)
        pygame.draw.rect(screen, COLOR_CARD_BG, wallet_r, border_radius=6)
        pygame.draw.rect(screen, COLOR_CARD_BORDER, wallet_r, 1, border_radius=6)
        wallet_surf = font_badge.render("CREDITS: 350 CR", True, COLOR_GOLD)
        screen.blit(wallet_surf, wallet_surf.get_rect(center=wallet_r.center))

        # -----------------------------------------------------
        # 3. HERO SPACESHIP (CALM SINE-WAVE HOVER)
        # -----------------------------------------------------
        pad_rect = pygame.Rect(ship_cx - 110, ship_base_y + 55, 220, 48)
        pygame.draw.ellipse(screen, (14, 22, 34), pad_rect)
        pygame.draw.ellipse(screen, (0, 190, 220), pad_rect, 2)
        inner_pad = pad_rect.inflate(-44, -16)
        pygame.draw.ellipse(screen, (0, 215, 245, 90), inner_pad, 1)

        # Smooth, calm floating hover equation
        hover_displacement = math.sin(hover_time * 2.0) * 6.5
        current_ship_y = ship_base_y + hover_displacement

        # Dynamic shadow
        sh_w = int(80 - hover_displacement * 1.5)
        sh_h = int(22 - hover_displacement * 0.5)
        sh_surf = pygame.Surface((sh_w, sh_h), pygame.SRCALPHA)
        pygame.draw.ellipse(sh_surf, (0, 180, 220, 50), (0, 0, sh_w, sh_h))
        screen.blit(sh_surf, (ship_cx - sh_w // 2, ship_base_y + 60))

        # Ship sprite
        screen.blit(ship_sprite, ship_sprite.get_rect(center=(ship_cx, int(current_ship_y))))

        # Nameplate & status
        name_s = font_card_title.render("INTERCEPTOR MK-IV", True, TEXT_WHITE)
        screen.blit(name_s, name_s.get_rect(center=(ship_cx, ship_base_y + 124)))

        status_r = pygame.Rect(ship_cx - 70, ship_base_y + 144, 140, 24)
        pygame.draw.rect(screen, (16, 26, 36), status_r, border_radius=12)
        pygame.draw.rect(screen, (30, 65, 50), status_r, 1, border_radius=12)
        pygame.draw.circle(screen, COLOR_GREEN, (ship_cx - 48, ship_base_y + 156), 4)
        stat_s = font_small.render("FLIGHT READY", True, COLOR_GREEN)
        screen.blit(stat_s, (ship_cx - 36, ship_base_y + 149))

        # -----------------------------------------------------
        # 4. RIGHT COLUMN: SPACIOUS EQUIPMENT CARDS & SPECS
        # -----------------------------------------------------
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        pygame.draw.rect(screen, COLOR_CARD_BG, panel_rect, border_radius=8)
        pygame.draw.rect(screen, COLOR_CARD_BORDER, panel_rect, 1, border_radius=8)

        p_head = font_card_title.render("CURRENT LOADOUT", True, COLOR_CYAN)
        screen.blit(p_head, (panel_x + 22, panel_y + 18))
        pygame.draw.line(screen, (28, 38, 55), (panel_x + 20, panel_y + 46), (panel_x + panel_w - 20, panel_y + 46), 1)

        # 3 Clean Module Cards
        modules = [
            ("[PRIMARY WEAPON]", "Rocket Launcher", "3-Rocket Salvo • Auto-Lock Homing", COLOR_GOLD),
            ("[PROPULSION CORE]", "Burst Engine", "Speed 6.5 Mach • Afterburner Dash", COLOR_GREEN),
            ("[DEFENSE MATRIX]", "Front Shield", "Absorbs 30 HP • 10s Auto-Recharge", COLOR_CYAN),
        ]
        card_y = panel_y + 56
        for tag, name, desc, accent in modules:
            c_rect = pygame.Rect(panel_x + 18, card_y, panel_w - 36, 60)
            pygame.draw.rect(screen, (13, 18, 28), c_rect, border_radius=6)
            pygame.draw.rect(screen, (32, 44, 65), c_rect, 1, border_radius=6)

            pygame.draw.rect(screen, accent, (c_rect.x, c_rect.y + 8, 3, c_rect.height - 16), border_radius=2)

            t_tag = font_small.render(tag, True, TEXT_DIM)
            t_name = font_bold.render(name, True, TEXT_WHITE)
            t_desc = font_body.render(desc, True, TEXT_MUTED)

            screen.blit(t_tag, (c_rect.x + 16, c_rect.y + 6))
            screen.blit(t_name, (c_rect.x + 16, c_rect.y + 22))
            screen.blit(t_desc, (c_rect.x + 16, c_rect.y + 40))

            card_y += 68

        # Change Loadout Button (Cleanly lowered below module 3)
        btn_cust = pygame.Rect(panel_x + 20, card_y + 12, panel_w - 40, 36)
        c_hov = btn_cust.collidepoint(mouse_pos)
        draw_button(screen, btn_cust, "CHANGE LOADOUT", font_btn, hovered=c_hov, border_col=COLOR_GOLD, text_col=COLOR_GOLD)

        # Performance Meters
        meter_y = card_y + 66
        meters = [
            ("FIREPOWER", 75, (255, 140, 50)),
            ("MOBILITY", 85, COLOR_GREEN),
            ("DEFENSE", 60, COLOR_CYAN),
        ]
        for m_lbl, m_val, m_col in meters:
            lbl_s = font_small.render(m_lbl, True, TEXT_MUTED)
            screen.blit(lbl_s, (panel_x + 24, meter_y))

            bar_x = panel_x + 120
            bar_w = panel_w - 150
            bar_h = 8
            pygame.draw.rect(screen, (12, 17, 26), (bar_x, meter_y + 3, bar_w, bar_h), border_radius=4)
            fill_w = int(bar_w * (m_val / 100.0))
            pygame.draw.rect(screen, m_col, (bar_x, meter_y + 3, fill_w, bar_h), border_radius=4)

            meter_y += 26

        # -----------------------------------------------------
        # 5. BOTTOM BAR: DIFFICULTY PILLS & ACTION BUTTONS
        # -----------------------------------------------------
        diff_lbl = font_small.render("MISSION THREAT LEVEL", True, TEXT_DIM)
        screen.blit(diff_lbl, (42, 530))

        diff_rects = {
            "EASY": pygame.Rect(40, 550, 120, 36),
            "MEDIUM": pygame.Rect(170, 550, 120, 36),
            "HARD": pygame.Rect(300, 550, 120, 36),
        }
        for d_key, r in diff_rects.items():
            is_active = (selected_difficulty == d_key)
            is_hov = r.collidepoint(mouse_pos)
            col = DIFF_COLORS[d_key]

            if is_active:
                bg = tuple(min(255, int(c * 0.28) + 18) for c in col)
                brd = col
                txt_c = TEXT_WHITE
            elif is_hov:
                bg = (24, 34, 52)
                brd = (70, 95, 140)
                txt_c = TEXT_WHITE
            else:
                bg = COLOR_CARD_BG
                brd = COLOR_CARD_BORDER
                txt_c = TEXT_MUTED

            pygame.draw.rect(screen, bg, r, border_radius=5)
            pygame.draw.rect(screen, brd, r, 1, border_radius=5)
            t_s = font_bold.render(d_key, True, col if is_active else txt_c)
            screen.blit(t_s, t_s.get_rect(center=r.center))

        # Single Clean 1-Line Subtitle
        subtitles = {
            "EASY": "35% Damage Shield Buffer  •  Relaxed Enemy Fire  •  Max 4 Ships",
            "MEDIUM": "Standard Fleet Armada  •  Balanced Threat  •  Max 5 Ships",
            "HARD": "High-Velocity Munitions  •  Max 6 Ships  •  +35% BONUS CREDITS & SCORE",
        }
        sub_t = font_body.render(subtitles[selected_difficulty], True, DIFF_COLORS[selected_difficulty])
        screen.blit(sub_t, (42, 594))

        # Action Buttons
        launch_btn_r = pygame.Rect(SCREEN_WIDTH - 380, 545, 230, 44)
        back_btn_r = pygame.Rect(SCREEN_WIDTH - 135, 545, 95, 44)

        l_hov = launch_btn_r.collidepoint(mouse_pos)
        b_hov = back_btn_r.collidepoint(mouse_pos)

        draw_button(screen, launch_btn_r, "LAUNCH MISSION", font_btn, hovered=l_hov, primary=True)
        draw_button(screen, back_btn_r, "[ BACK ]", font_btn, hovered=b_hov, primary=False, text_col=TEXT_MUTED)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
