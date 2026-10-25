import pygame
import random
import sys
import math
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import src.entities as entities
from src.entities import Player, Bullet, Enemy, EnemyBullet, Explosion, CreditOrb, OverclockPickup, FloatingText, SparkParticle, get_shared_overlay
from src.background import ParallaxBackground
from src.asset_loader import load_assets, asset_path
from src.save_manager import load_save_data, write_save_data
from src.adaptive_director import AdaptiveDirector, FLEET_NAMES, STAGE_NAMES

pygame.init()
pygame.joystick.init()

fullscreen = True
try:
    display = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
except Exception:
    display = pygame.display.get_surface()
    if display is None:
        display = pygame.display.set_mode((800, 600))
screen = display
SCREEN_WIDTH, SCREEN_HEIGHT = display.get_size()
pygame.display.set_caption("SpaceShooter")
try:
    _icon_p = asset_path("assets/Main Ship - Base - Full health.png")
    if _icon_p.exists():
        pygame.display.set_icon(pygame.image.load(str(_icon_p)))
except Exception:
    pass
clock = pygame.time.Clock()

GAME_WIDTH = 800
GAME_HEIGHT = 600
SCALE_FACTOR = SCREEN_HEIGHT / 600.0
OFFSET_X = (SCREEN_WIDTH - int(GAME_WIDTH * SCALE_FACTOR)) // 2

game_surface = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))

entities.SCREEN_WIDTH = GAME_WIDTH
entities.SCREEN_HEIGHT = GAME_HEIGHT

def get_render_viewport(screen_size, display_size):
    """Calculates uniform aspect-preserving viewport with black pillarbox borders."""
    dw, dh = display_size
    sw, sh = screen_size
    scale = min(dw / sw, dh / sh)
    target_w = int(sw * scale)
    target_h = int(sh * scale)
    offset_x = (dw - target_w) // 2
    offset_y = (dh - target_h) // 2
    return pygame.Rect(offset_x, offset_y, target_w, target_h), scale

save_data = load_save_data()

# Comprehensive Keybind Registry & Category Groupings
KEYBIND_GROUPS = [
    {
        "category": "FLIGHT & PROPULSION",
        "tag": "PROPULSION",
        "color": (0, 240, 255),
        "actions": [
            {"id": "UP", "name": "Thrust Forward", "desc": "Pitch / accelerate upwards", "default": pygame.K_w},
            {"id": "DOWN", "name": "Reverse Thrusters", "desc": "Brake / reverse downwards", "default": pygame.K_s},
            {"id": "LEFT", "name": "Strafe Port", "desc": "Roll / slide left", "default": pygame.K_a},
            {"id": "RIGHT", "name": "Strafe Starboard", "desc": "Roll / slide right", "default": pygame.K_d},
            {"id": "BOOST", "name": "Afterburner Boost", "desc": "Engine dash burst & speed surge", "default": pygame.K_LSHIFT},
        ]
    },
    {
        "category": "COMBAT & COUNTERMEASURES",
        "tag": "TACTICAL",
        "color": (255, 185, 45),
        "actions": [
            {"id": "SHOOT", "name": "Primary Weapon", "desc": "Fire equipped weapon battery", "default": pygame.K_SPACE},
            {"id": "SHIELD", "name": "Energy Barrier", "desc": "Deploy directional shield bubble", "default": pygame.K_e},
            {"id": "FLARE", "name": "Release Flare / Chaff", "desc": "Deploy decoys to break missile locks", "default": pygame.K_f},
            {"id": "RELOAD", "name": "Manual Reload", "desc": "Cycle ammo magazine early", "default": pygame.K_r},
            {"id": "INVINCIBILITY", "name": "Shield Overdrive", "desc": "Deploy emergency invincibility (5s)", "default": pygame.K_q},
            {"id": "PAUSE", "name": "Tactical Pause", "desc": "Pause sortie / system menu", "default": pygame.K_ESCAPE},
        ]
    }
]

_DEFAULT_KEYBINDS = {
    action["id"]: action["default"]
    for group in KEYBIND_GROUPS
    for action in group["actions"]
}

def friendly_key_name(key_code):
    special = {
        pygame.K_SPACE: "SPACE",
        pygame.K_LSHIFT: "L-SHIFT",
        pygame.K_RSHIFT: "R-SHIFT",
        pygame.K_LCTRL: "L-CTRL",
        pygame.K_RCTRL: "R-CTRL",
        pygame.K_LALT: "L-ALT",
        pygame.K_RALT: "R-ALT",
        pygame.K_ESCAPE: "ESC",
        pygame.K_RETURN: "ENTER",
        pygame.K_KP_ENTER: "NUM ENTER",
        pygame.K_TAB: "TAB",
        pygame.K_BACKSPACE: "BKSP",
        pygame.K_CAPSLOCK: "CAPS",
        pygame.K_UP: "UP ARROW",
        pygame.K_DOWN: "DOWN ARROW",
        pygame.K_LEFT: "LEFT ARROW",
        pygame.K_RIGHT: "RIGHT ARROW",
    }
    if key_code in special:
        return special[key_code]
    try:
        name = pygame.key.name(key_code).upper()
        return name if name else f"KEY_{key_code}"
    except Exception:
        return f"KEY_{key_code}"

# Restore persisted keybinds (saved as key-name strings) back to key codes.
_saved_keybinds = save_data.get('keybinds', {})
_restored_keybinds = {}
for _action, _default_key in _DEFAULT_KEYBINDS.items():
    _saved_name = _saved_keybinds.get(_action)
    if not _saved_name and _action == 'BOOST':
        _saved_name = _saved_keybinds.get('ENGINE_ABILITY')
    if not _saved_name and _action == 'FLARE':
        _saved_name = _saved_keybinds.get('CHAFF')
    if _saved_name:
        try:
            _restored_keybinds[_action] = pygame.key.key_code(_saved_name)
        except (ValueError, pygame.error):
            _restored_keybinds[_action] = _default_key
    else:
        _restored_keybinds[_action] = _default_key

CONFIG = {
    'sensitivity': save_data.get('sensitivity', 5),
    'music_volume': save_data.get('music_volume', 0.5),
    'keybinds': _restored_keybinds,
}

assets = load_assets(screen_size=(GAME_WIDTH, GAME_HEIGHT))
background = ParallaxBackground(assets['bg_void'], assets['bg_stars'], bg_planet=assets.get('bg_planet'), bg_black_hole=assets.get('bg_black_hole'), screen_size=(GAME_WIDTH, GAME_HEIGHT))
high_score = save_data['high_score']
current_track_index = save_data['music_track'] % len(assets['bgm_playlist'])
save_data['music_track'] = current_track_index
shop_category = 'weapons'
shop_notice = ''
last_run_credits = 0
director = AdaptiveDirector(save_data.get('adaptive_director'))
enemy_types_by_name = {enemy_type['name']: enemy_type for enemy_type in assets['enemy_types']}

SHOP_ITEMS = {
    'weapons': [
        {'id': 'auto_cannon', 'name': 'Auto Cannon', 'price': 0, 'detail': '20 rounds  |  Rapid fire  |  Reload 1.1s'},
        {'id': 'big_space_gun', 'name': 'Big Space Gun', 'price': 350, 'detail': '5 rounds  |  4 damage  |  Pierces one target  |  Reload 1.8s'},
        {'id': 'rockets', 'name': 'Rocket Launcher', 'price': 650, 'detail': '3-rocket salvo  |  Auto-lock homing  |  Reload 2.1s'},
        {'id': 'zapper', 'name': 'Zapper', 'price': 1100, 'detail': '12 charges  |  Chains up to 2 nearby foes  |  Reload 1.5s'},
    ],
    'engines': [
        {'id': 'base', 'name': 'Base Engine', 'price': 0, 'detail': 'Speed 5.0  |  No active ability'},
        {'id': 'big_pulse', 'name': 'Big Pulse Engine', 'price': 300, 'detail': 'Speed 5.7  |  Pulse dash 0.38s  |  Cooldown 3s - Shift'},
        {'id': 'burst', 'name': 'Burst Engine', 'price': 600, 'detail': 'Speed 6.5  |  Afterburner 1.5s  |  Cooldown 6s - Shift'},
        {'id': 'supercharged', 'name': 'Supercharged Engine', 'price': 1050, 'detail': 'Speed 7.5  |  Rapid fire 2.4s  |  No speed boost  |  Shift - CD 8s'},
    ],
    'shields': [
        {'id': 'front', 'name': 'Front Shield', 'price': 280, 'detail': 'Absorbs 30 damage  |  Cooldown 10s  |  Activate with E'},
        {'id': 'front_side', 'name': 'Front & Side Shield', 'price': 550, 'detail': 'Absorbs 45 damage  |  Cooldown 13s  |  Activate with E'},
        {'id': 'round', 'name': 'Round Shield', 'price': 950, 'detail': 'Absorbs 65 damage  |  Cooldown 16s  |  Activate with E'},
        {'id': 'invincibility', 'name': 'Invincibility Backup', 'price': 450, 'detail': 'One use  |  Q activates 5 seconds'},
    ],
}

from src.ui_theme import UITheme, theme
from src.hangar_view import HangarView
from src.tutorial_controller import TutorialController

theme = UITheme(SCALE_FACTOR)
tutorial_ctrl = TutorialController(assets)

# Scaled typography suite
title_font = theme.title_large
button_font = theme.button
label_font = theme.label
shop_detail_font = theme.mono_small

SPAWN_ENEMY_EVENT = pygame.USEREVENT + 1
pygame.time.set_timer(SPAWN_ENEMY_EVENT, 750)
TRACK_END_EVENT = pygame.USEREVENT + 2

def safe_music_call(method, *args):
    try:
        getattr(pygame.mixer.music, method)(*args)
    except pygame.error:
        # Keep startup and gameplay working when no audio device is available.
        pass

safe_music_call('set_endevent', TRACK_END_EVENT)

safe_music_call('set_volume', CONFIG['music_volume'])
try:
    safe_music_call('load', assets['bgm_playlist'][current_track_index])
    safe_music_call('play')
except pygame.error:
    pass # If the song is missing, just play the game silently instead of crashing! 
state = "MENU"
waiting_for_key = None
keybind_notice = ''
keybind_notice_until = 0

player = None
bullets, enemies, enemy_bullets, explosions, chain_effects = [], [], [], [], []
credit_orbs = []
overclock_pickups = []
last_overclock_drop_time = -18000
floating_texts = []
spark_particles = []
hitstop_until = 0
bomber_hazard_markers = []
active_defense_flares = []
last_busy_screen_time = 0
last_wave_spawn_time = 0
score = 0
game_start_time = 0
asteroid_hits = 0

# ── Feature state variables ────────────────────────────────────────────────
# 1. Combo
combo            = 1
last_kill_time   = 0
combo_label_until= 0
# 3. Boss intro
boss_intro_until = 0
boss_intro_title = 'DREADNOUGHT'
boss_intro_sub   = 'INCOMING'
# 4. Screenshake
shake_until      = 0
shake_intensity  = 0
# 5. Kill streaks
STREAK_MILESTONES= [10, 25, 50, 100]
streak_label     = ''
streak_label_until=0
total_run_kills  = 0
# 6. Per-run stats
run_kills_by_type= {}
run_start_time   = 0
# 7. Adaptive music
music_boosted    = False
# 8. Credit orbs
credit_orbs      = []
# 9. Controller
joysticks        = {}
# 10. Dev overlay
dev_overlay      = False

def reset_game():
    global player, bullets, enemies, enemy_bullets, explosions, chain_effects, score, game_start_time, asteroid_hits
    global combo, last_kill_time, combo_label_until, boss_intro_until
    global shake_until, shake_intensity, streak_label, streak_label_until
    global total_run_kills, run_kills_by_type, run_start_time, music_boosted, credit_orbs
    global bomber_hazard_markers, active_defense_flares, last_busy_screen_time, last_wave_spawn_time
    global overclock_pickups, last_overclock_drop_time
    global hitstop_until, floating_texts, spark_particles
    player = Player(GAME_WIDTH // 2 - 20, GAME_HEIGHT - 80, assets, save_data)
    engine_speed = assets['engines'][player.equipped_engine]['speed']
    player.speed = max(2, min(15, engine_speed + CONFIG['sensitivity'] - 5))
    bullets, enemies, enemy_bullets, explosions, chain_effects = [], [], [], [], []
    credit_orbs = []
    overclock_pickups = []
    last_overclock_drop_time = -18000
    floating_texts = []
    spark_particles = []
    hitstop_until = 0
    bomber_hazard_markers = []
    active_defense_flares = []
    last_busy_screen_time = 0
    last_wave_spawn_time = 0
    score = 0
    asteroid_hits = 0
    combo = 1
    last_kill_time = 0
    combo_label_until = 0
    boss_intro_until = 0
    shake_until = 0
    shake_intensity = 0
    streak_label = ''
    streak_label_until = 0
    total_run_kills = 0
    run_kills_by_type = {}
    run_start_time = pygame.time.get_ticks()
    music_boosted = False
    game_start_time = pygame.time.get_ticks()
    diff = save_data.get('difficulty', 'medium')
    director.begin_run(player, diff)

def start_tutorial_combat():
    global state, player, bullets, enemies, enemy_bullets, explosions, chain_effects
    global credit_orbs, overclock_pickups, last_overclock_drop_time, floating_texts, spark_particles
    global hitstop_until, bomber_hazard_markers, active_defense_flares
    tutorial_ctrl.reset_tutorial()
    tutorial_ctrl.state = "COMBAT"
    bullets, enemies, enemy_bullets, explosions, chain_effects = [], [], [], [], []
    credit_orbs = []
    overclock_pickups = []
    last_overclock_drop_time = -18000
    floating_texts = []
    spark_particles = []
    hitstop_until = 0
    bomber_hazard_markers = []
    active_defense_flares = []
    training_save = tutorial_ctrl.get_training_save_data(save_data)
    player = Player(GAME_WIDTH // 2 - 20, GAME_HEIGHT - 70, assets, training_save)
    engine_speed = assets['engines'][player.equipped_engine]['speed']
    player.speed = max(2, min(15, engine_speed + CONFIG['sensitivity'] - 5))
    state = "TUTORIAL"

def start_tutorial_session():
    global state
    tutorial_ctrl.state = "INTRO_DIALOGUE"
    tutorial_ctrl.load_script(tutorial_ctrl.INTRO_SCRIPT)
    state = "TUTORIAL_DIALOGUE"

def draw_button(surface, rect, text, font=None, hovered=False, primary=False, color_accent=None):
    theme.draw_cyber_button(surface, rect, text, font or theme.button, hovered=hovered, primary=primary, color_accent=color_accent)

def draw_title(surface):
    title_surf = theme.title_large.render("SPACESHOOTER", True, (0, 240, 255))
    glow_surf = theme.title_large.render("SPACESHOOTER", True, (0, 140, 210))
    cx = SCREEN_WIDTH // 2
    cy = int(100 * SCALE_FACTOR)
    surface.blit(glow_surf, glow_surf.get_rect(center=(cx - 1, cy - 1)))
    surface.blit(glow_surf, glow_surf.get_rect(center=(cx + 1, cy + 1)))
    surface.blit(title_surf, title_surf.get_rect(center=(cx, cy)))
    sub_surf = theme.mono_small.render("— TACTICAL VOID COMBAT —", True, (130, 185, 230))
    surface.blit(sub_surf, sub_surf.get_rect(center=(cx, int(134 * SCALE_FACTOR))))

def get_menu_buttons():
    btn_w = int(260 * SCALE_FACTOR)
    btn_h = int(38 * SCALE_FACTOR)
    btn_x = SCREEN_WIDTH // 2 - btn_w // 2
    btns = {
        "start": pygame.Rect(btn_x, int(170 * SCALE_FACTOR), btn_w, int(42 * SCALE_FACTOR)),
        "hangar": pygame.Rect(btn_x, int(218 * SCALE_FACTOR), btn_w, btn_h),
    }
    y_offset = int(262 * SCALE_FACTOR)
    if not save_data.get("tutorial_completed", False):
        btns["tutorial"] = pygame.Rect(btn_x, y_offset, btn_w, btn_h)
        y_offset += int(44 * SCALE_FACTOR)
    btns["shop"] = pygame.Rect(btn_x, y_offset, btn_w, btn_h)
    y_offset += int(44 * SCALE_FACTOR)
    btns["settings"] = pygame.Rect(btn_x, y_offset, btn_w, btn_h)
    y_offset += int(44 * SCALE_FACTOR)
    btns["keybinds"] = pygame.Rect(btn_x, y_offset, btn_w, btn_h)
    y_offset += int(44 * SCALE_FACTOR)
    btns["quit"] = pygame.Rect(btn_x, y_offset, btn_w, btn_h)
    return btns

def get_settings_buttons():
    cx = SCREEN_WIDTH // 2
    bw = int(50 * SCALE_FACTOR)
    bh = int(44 * SCALE_FACTOR)
    dx_dec = int(210 * SCALE_FACTOR)
    dx_inc = int(160 * SCALE_FACTOR)
    return {
        "sens_decrease": pygame.Rect(cx - dx_dec, int(175 * SCALE_FACTOR), bw, bh),
        "sens_increase": pygame.Rect(cx + dx_inc, int(175 * SCALE_FACTOR), bw, bh),
        "vol_decrease": pygame.Rect(cx - dx_dec, int(240 * SCALE_FACTOR), bw, bh),
        "vol_increase": pygame.Rect(cx + dx_inc, int(240 * SCALE_FACTOR), bw, bh),
        "diff_decrease": pygame.Rect(cx - dx_dec, int(310 * SCALE_FACTOR), bw, bh),
        "diff_increase": pygame.Rect(cx + dx_inc, int(310 * SCALE_FACTOR), bw, bh),
        "song_previous": pygame.Rect(cx - dx_dec, int(410 * SCALE_FACTOR), bw, bh),
        "song_next": pygame.Rect(cx + dx_inc, int(410 * SCALE_FACTOR), bw, bh),
        "back": pygame.Rect(cx - int(100 * SCALE_FACTOR), int(510 * SCALE_FACTOR), int(200 * SCALE_FACTOR), int(46 * SCALE_FACTOR))
    }

def get_keybind_layout():
    cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
    panel_w = min(SCREEN_WIDTH - int(30 * SCALE_FACTOR), int(760 * SCALE_FACTOR))
    panel_h = min(SCREEN_HEIGHT - int(30 * SCALE_FACTOR), int(510 * SCALE_FACTOR))
    panel_rect = pygame.Rect(cx - panel_w // 2, cy - panel_h // 2, panel_w, panel_h)

    pad_x = int(20 * SCALE_FACTOR)
    gap_x = int(16 * SCALE_FACTOR)
    col_w = (panel_w - pad_x * 2 - gap_x) // 2

    col1_x = panel_rect.x + pad_x
    col2_x = col1_x + col_w + gap_x

    header_y = panel_rect.y + int(54 * SCALE_FACTOR)
    header_h = int(24 * SCALE_FACTOR)

    row_start_y = panel_rect.y + int(82 * SCALE_FACTOR)
    row_h = int(45 * SCALE_FACTOR)
    row_gap = int(6 * SCALE_FACTOR)

    rows = {}
    # Column 1 (Flight & Propulsion)
    for i, action_info in enumerate(KEYBIND_GROUPS[0]["actions"]):
        ry = row_start_y + i * (row_h + row_gap)
        rows[action_info["id"]] = pygame.Rect(col1_x, ry, col_w, row_h)

    # Column 2 (Combat & Systems)
    for i, action_info in enumerate(KEYBIND_GROUPS[1]["actions"]):
        ry = row_start_y + i * (row_h + row_gap)
        rows[action_info["id"]] = pygame.Rect(col2_x, ry, col_w, row_h)

    btn_y = panel_rect.y + panel_h - int(52 * SCALE_FACTOR)
    btn_h = int(40 * SCALE_FACTOR)
    btn_w_reset = int(210 * SCALE_FACTOR)
    btn_w_back = int(180 * SCALE_FACTOR)
    spacing = int(20 * SCALE_FACTOR)

    reset_rect = pygame.Rect(cx - btn_w_reset - spacing // 2, btn_y, btn_w_reset, btn_h)
    back_rect = pygame.Rect(cx + spacing // 2, btn_y, btn_w_back, btn_h)

    return {
        "panel": panel_rect,
        "rows": rows,
        "reset": reset_rect,
        "back": back_rect,
        "col1_x": col1_x,
        "col2_x": col2_x,
        "col_w": col_w,
        "header_y": header_y,
        "header_h": header_h,
    }

def get_keybind_rows():
    return get_keybind_layout()["rows"]

def get_keybind_back_rect():
    return get_keybind_layout()["back"]

def get_keybind_reset_rect():
    return get_keybind_layout()["reset"]

def get_pause_buttons():
    cx = SCREEN_WIDTH // 2
    bw = int(200 * SCALE_FACTOR)
    bh = int(50 * SCALE_FACTOR)
    return {
        "resume": pygame.Rect(cx - bw // 2, int(280 * SCALE_FACTOR), bw, bh),
        "restart": pygame.Rect(cx - bw // 2, int(350 * SCALE_FACTOR), bw, bh),
        "menu": pygame.Rect(cx - bw // 2, int(420 * SCALE_FACTOR), bw, bh),
    }

def get_game_over_buttons():
    cx = SCREEN_WIDTH // 2
    bw = int(200 * SCALE_FACTOR)
    bh = int(44 * SCALE_FACTOR)
    spacing = int(10 * SCALE_FACTOR)
    return {
        "restart": pygame.Rect(cx - bw - spacing, int(416 * SCALE_FACTOR), bw, bh),
        "menu": pygame.Rect(cx + spacing, int(416 * SCALE_FACTOR), bw, bh),
    }

def to_game_pos(pos):
    gx = (pos[0] - OFFSET_X) / SCALE_FACTOR
    gy = pos[1] / SCALE_FACTOR
    return (int(round(gx)), int(round(gy)))

def get_shop_tabs():
    cx = SCREEN_WIDTH // 2
    tw = int(190 * SCALE_FACTOR)
    th = int(42 * SCALE_FACTOR)
    gap = int(25 * SCALE_FACTOR)
    total_w = tw * 3 + gap * 2
    start_x = cx - total_w // 2
    return {
        'weapons': pygame.Rect(start_x, int(130 * SCALE_FACTOR), tw, th),
        'engines': pygame.Rect(start_x + tw + gap, int(130 * SCALE_FACTOR), tw, th),
        'shields': pygame.Rect(start_x + (tw + gap) * 2, int(130 * SCALE_FACTOR), tw, th),
    }

def get_shop_item_rect(index):
    cx = SCREEN_WIDTH // 2
    iw = int(640 * SCALE_FACTOR)
    ih = int(68 * SCALE_FACTOR)
    step = int(78 * SCALE_FACTOR)
    base_y = int(185 * SCALE_FACTOR)
    return pygame.Rect(cx - iw // 2, base_y + index * step, iw, ih)

def get_shop_back_rect():
    cx = SCREEN_WIDTH // 2
    bw = int(200 * SCALE_FACTOR)
    bh = int(48 * SCALE_FACTOR)
    return pygame.Rect(cx - bw // 2, int(530 * SCALE_FACTOR), bw, bh)

def item_is_owned(category, item_id):
    owned_key = {'weapons': 'owned_weapons', 'engines': 'owned_engines', 'shields': 'owned_shields'}[category]
    return item_id in save_data[owned_key]

def equipped_item(category):
    return save_data[{'weapons': 'equipped_weapon', 'engines': 'equipped_engine', 'shields': 'equipped_shield'}[category]]

def shop_item_image(category, item_id):
    if category == 'weapons':
        return assets['weapons'][item_id]['frames'][0]
    if category == 'engines':
        return assets['engines'][item_id]['image']
    frames = assets['shields'][item_id]['frames']
    return frames[len(frames) // 2]

def purchase_or_equip(item):
    global shop_notice
    category = shop_category
    item_id = item['id']
    if category == 'shields' and item_id == 'invincibility':
        if save_data['credits'] < item['price']:
            shop_notice = f"Need {item['price'] - save_data['credits']} more credits."
            return
        save_data['credits'] -= item['price']
        save_data['invincibility_backups'] += 1
        shop_notice = f"Invincibility backup purchased. You have {save_data['invincibility_backups']}."
        write_save_data(save_data)
        return
    if item_is_owned(category, item_id):
        key = {'weapons': 'equipped_weapon', 'engines': 'equipped_engine', 'shields': 'equipped_shield'}[category]
        if category == 'shields' and save_data[key] == item_id:
            save_data[key] = None
            shop_notice = 'Shield unequipped.'
            write_save_data(save_data)
            return
        save_data[key] = item_id
        shop_notice = f"{item['name']} equipped."
        write_save_data(save_data)
        return
    if save_data['credits'] < item['price']:
        shop_notice = f"Need {item['price'] - save_data['credits']} more credits."
        return
    owned_key = {'weapons': 'owned_weapons', 'engines': 'owned_engines', 'shields': 'owned_shields'}[category]
    equip_key = {'weapons': 'equipped_weapon', 'engines': 'equipped_engine', 'shields': 'equipped_shield'}[category]
    save_data['credits'] -= item['price']
    save_data[owned_key].append(item_id)
    save_data[equip_key] = item_id
    shop_notice = f"Purchased and equipped {item['name']}."
    write_save_data(save_data)

def handle_hangar_purchase_or_equip(category, item):
    global shop_category, shop_notice
    prev_cat = shop_category
    shop_category = category
    purchase_or_equip(item)
    msg = shop_notice
    shop_category = prev_cat
    return msg

hangar_view = HangarView(assets, SHOP_ITEMS, handle_hangar_purchase_or_equip, screen_size=(SCREEN_WIDTH, SCREEN_HEIGHT))

def change_music(direction):
    global current_track_index
    current_track_index = (current_track_index + direction) % len(assets['bgm_playlist'])
    safe_music_call('load', assets['bgm_playlist'][current_track_index])
    safe_music_call('play')
    save_data['music_track'] = current_track_index
    write_save_data(save_data)

def current_track_name():
    return Path(assets['bgm_playlist'][current_track_index]).stem.replace('_', ' ').title()

def grant_run_credits():
    global last_run_credits
    diff = save_data.get('difficulty', 'medium')
    bonus = 1.35 if diff == 'hard' else 1.0
    last_run_credits = round((score // 2) * bonus)
    save_data['credits'] += last_run_credits
    save_data['adaptive_director'] = director.export()
    write_save_data(save_data)

def damage_enemy(enemy, amount, enemies_to_remove):
    global score, combo, last_kill_time, combo_label_until
    global shake_until, shake_intensity, streak_label, streak_label_until
    global total_run_kills, run_kills_by_type
    global last_overclock_drop_time, overclock_pickups
    global hitstop_until, floating_texts, spark_particles
    if enemy in enemies_to_remove:
        return

    now_d = pygame.time.get_ticks()
    enemy.hit_flash_until = now_d + 35
    for _ in range(random.randint(4, 6)):
        spark_particles.append(SparkParticle(enemy.rect.centerx, enemy.rect.centery))

    # Boss invulnerability tether provided by active Support ship
    if getattr(enemy, 'is_invulnerable_tethered', False):
        supp = getattr(enemy, 'tether_support_ship', None)
        if supp and (not enemies or supp in enemies) and getattr(supp, 'hp', 0) > 0:
            hitstop_until = max(hitstop_until, now_d + 40)
            floating_texts.append(FloatingText(enemy.rect.centerx, enemy.rect.top - 12, "SHIELD CONDUIT ACTIVE", (255, 220, 60)))
            enemy.tether_prompt_until = now_d + 1200
            director.comms.broadcast("SHIELD CONDUIT ACTIVE // DESTROY SUPPORT SHIP", sender="TACTICAL", priority="HIGH", color=(0, 240, 255), now=now_d)
            assets['sfx'].get('deflect', assets['sfx']['player_shoot']).play()
            return
        else:
            enemy.is_invulnerable_tethered = False
            enemy.tether_support_ship = None

    # Shield barrier absorption (Shadow Interceptor)
    if getattr(enemy, 'shield_hp', 0) > 0:
        remaining, broke = enemy.absorb_shield_damage(amount)
        if broke:
            director.comms.broadcast("TARGET BARRIER SHATTERED!", sender="TACTICAL", color=(255, 60, 220), now=pygame.time.get_ticks())
            assets['sfx']['combo'].play()
        if remaining <= 0:
            return
        amount = remaining

    enemy.hp -= amount
    if enemy.hp <= 0:
        enemies_to_remove.append(enemy)
        director.note_enemy_destroyed(enemy.name)
        if enemy.name not in save_data.get('encountered_enemies', []):
            save_data.setdefault('encountered_enemies', []).append(enemy.name)
            write_save_data(save_data)
        now_k = pygame.time.get_ticks()
        if enemy.score_value >= 40:
            hitstop_until = max(hitstop_until, now_k + 75)

        # Boss destruction triggers fleet transition & grand reward
        if enemy.name in ('dreadnought', 'klaed_dreadnought', 'nairan_dreadnought'):
            director.note_boss_destroyed(enemy.name, now_k)
            shake_until = now_k + 850
            shake_intensity = 11
            credit_orbs.append(CreditOrb(enemy.rect.centerx, enemy.rect.centery, 50))
            assets['sfx']['go_good'].play()
        elif enemy.name == 'shadow_interceptor':
            director.comms.broadcast("SHADOW INTERCEPTOR DESTROYED // NEURAL MIRROR PURGED", sender="TACTICAL", priority="CRITICAL", color=(0, 240, 255), now=now_k)
            shake_until = now_k + 700
            shake_intensity = 8
            credit_orbs.append(CreditOrb(enemy.rect.centerx, enemy.rect.centery, 35))
            assets['sfx']['go_good'].play()

        # Support ship destruction collapses allied capital invulnerability conduits!
        if 'support' in enemy.name:
            tether_broke = False
            for ally in enemies:
                if getattr(ally, 'tether_support_ship', None) is enemy or getattr(ally, 'is_invulnerable_tethered', False):
                    ally.is_invulnerable_tethered = False
                    ally.tether_support_ship = None
                    tether_broke = True
            if tether_broke:
                director.comms.broadcast("SUPPORT SHIP DESTROYED // CAPITAL SHIELDS COLLAPSED!", sender="TACTICAL", priority="HIGH", color=(100, 255, 180), now=now_k)
                assets['sfx']['combo'].play()

        # Squad Leader assassination triggers wingmen disarray!
        if getattr(enemy, 'is_leader', False):
            for ally in enemies:
                if ally is not enemy:
                    ally.enter_disarray(2200)
            director.comms.broadcast("SQUAD LEADER LOST! ESCORTS IN DISARRAY!", sender="FLEET_SQUAD", color=(255, 120, 80), now=now_k)

        # ── Feature 1: Combo multiplier ──────────────────────────────────
        if now_k - last_kill_time <= 3000:
            combo = min(combo + 1, 10)
        else:
            combo = 1
        last_kill_time    = now_k
        combo_bonus       = 1.0 + (combo - 1) * 0.1
        diff_bonus        = 1.35 if save_data.get('difficulty', 'medium') == 'hard' else 1.0
        score            += round(enemy.score_value * combo_bonus * diff_bonus)
        if combo >= 2:
            combo_label_until = now_k + 1500
            assets['sfx']['combo'].play()
        # ── Feature 5: Kill-streak milestones ────────────────────────────
        total_run_kills += 1
        run_kills_by_type[enemy.name] = run_kills_by_type.get(enemy.name, 0) + 1
        for milestone in STREAK_MILESTONES:
            if total_run_kills == milestone:
                streak_label       = str(milestone) + ' KILLS!'
                streak_label_until = now_k + 2200
                assets['sfx']['streak'].play()
        # ── Feature 4: Screenshake on heavy kill ─────────────────────────
        if enemy.score_value >= 25:
            shake_until     = now_k + 220
            shake_intensity = 5
        # ── Feature 8: Credit-orb drop ────────────────────────────────────
        if enemy.score_value >= 20:
            credit_orbs.append(CreditOrb(enemy.rect.centerx, enemy.rect.centery,
                                         max(5, enemy.score_value // 5)))

        # ── In-Run Module Overclock Drop (22% chance from heavy enemies, 18s cooldown) ──
        is_heavy = (
            enemy.score_value >= 25 or
            any(k in enemy.name for k in ('battlecruiser', 'dreadnought', 'frigate', 'bomber'))
        )
        if is_heavy and (now_k - last_overclock_drop_time >= 18000) and random.random() < 0.22:
            last_overclock_drop_time = now_k
            p_health_ratio = (player.hp / player.max_hp) if player and player.max_hp else 1.0
            p_shield_low = bool(player and player.shield_data and player.shield_remaining <= 10)
            if p_health_ratio < 0.45 or p_shield_low:
                chosen_cat = random.choices(['shield', 'weapon', 'engine'], weights=[50, 30, 20])[0]
            else:
                chosen_cat = random.choices(['weapon', 'engine', 'shield'], weights=[45, 30, 25])[0]

            if chosen_cat == 'weapon':
                mod_id = player.equipped_weapon if player else 'auto_cannon'
                frames = assets['pickup_weapons'].get(mod_id, assets['pickup_weapons']['auto_cannon'])
            elif chosen_cat == 'engine':
                mod_id = player.equipped_engine if player else 'base'
                frames = assets['pickup_engines'].get(mod_id, assets['pickup_engines']['base'])
            else:
                mod_id = player.equipped_shield if (player and player.equipped_shield) else 'front'
                frames = assets['pickup_shields'].get(mod_id, assets['pickup_shields']['front'])

            overclock_pickups.append(OverclockPickup(enemy.rect.centerx, enemy.rect.centery, chosen_cat, mod_id, frames))
            director.comms.broadcast(f"TACTICAL DROP DETECTED: {chosen_cat.upper()} OVERCLOCK", sender="RECON", color=(255, 200, 60), now=now_k)
        assets['sfx']['explosion'].play()
        explosions.append(Explosion(enemy.rect.centerx, enemy.rect.centery, enemy.explosion_frames))

def record_high_score():
    global high_score, save_data
    if score > high_score:
        high_score = score
        save_data['high_score'] = high_score
        write_save_data(save_data)

running = (__name__ == '__main__')
if running and not save_data.get("tutorial_completed", False):
    state = "BOOT"
    tutorial_ctrl.reset_boot()
while running:
    mouse_pos = pygame.mouse.get_pos()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == TRACK_END_EVENT:
            current_track_index = (current_track_index + 1) % len(assets['bgm_playlist'])
            safe_music_call('load', assets['bgm_playlist'][current_track_index])
            safe_music_call('play')

        # --- TUTORIAL HIJACK ---
        # Only hijack during cold boot and narrative dialogue scenes!
        if state in ("BOOT", "TUTORIAL_DIALOGUE") or (tutorial_ctrl.state in ("INTRO_DIALOGUE", "DEBRIEF_DIALOGUE", "GOODBYE_DIALOGUE") and not save_data.get("tutorial_completed", False)):
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                    if state == "BOOT":
                        start_tutorial_session()
                    else:
                        action = tutorial_ctrl.handle_dialogue_input()
                        if action == "START_COMBAT":
                            start_tutorial_combat()
                        elif action in ("ENTER_HANGAR_TOUR", "GOTO_HANGAR"):
                            state = "HANGAR"
                            hangar_view.mode = "overview"
                            tutorial_ctrl.state = "TOUR"
                            tutorial_ctrl.tour_step = 1
                            tutorial_ctrl.tour_step_started_at = pygame.time.get_ticks()
                        elif action == "GRANT_CREDITS":
                            if not getattr(tutorial_ctrl, 'credits_granted', False):
                                tutorial_ctrl.credits_granted = True
                                save_data["credits"] = save_data.get("credits", 0) + 100
                                write_save_data(save_data)
                                if 'credit_pickup' in assets.get('sfx', {}):
                                    try:
                                        assets['sfx']['credit_pickup'].play()
                                    except Exception:
                                        pass
                        elif action == "END_TUTORIAL":
                            if not getattr(tutorial_ctrl, 'credits_granted', False):
                                tutorial_ctrl.credits_granted = True
                                save_data["credits"] = save_data.get("credits", 0) + 100
                            save_data["tutorial_completed"] = True
                            write_save_data(save_data)
                            tutorial_ctrl.tour_step = 0
                            tutorial_ctrl.state = "DONE"
                elif event.key == pygame.K_ESCAPE:
                    if not getattr(tutorial_ctrl, 'credits_granted', False):
                        tutorial_ctrl.credits_granted = True
                        save_data["credits"] = save_data.get("credits", 0) + 100
                    save_data["tutorial_completed"] = True
                    write_save_data(save_data)
                    tutorial_ctrl.tour_step = 0
                    tutorial_ctrl.state = "DONE"
                    state = "MENU"

            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN, pygame.MOUSEWHEEL):
                continue
        # --- END HIJACK ---
        elif event.type == SPAWN_ENEMY_EVENT and state == "PLAYING":
            now = pygame.time.get_ticks()
            diff = save_data.get('difficulty', 'medium')
            # Difficulty-adjusted enemy cap: Easy=4 (less overwhelming), Med=5, Hard=6
            max_screen_enemies = 4 if diff == 'easy' else (6 if diff == 'hard' else 5)

            # ── Dynamic Wave-Clear Pacing ────────────────────────────────────
            # Cap/elite presence lowers acceptable screen crowding threshold
            cap_ships = ('dreadnought', 'klaed_dreadnought', 'nairan_dreadnought',
                         'battlecruiser', 'klaed_battlecruiser', 'nairan_battlecruiser')
            has_heavy_or_elite = any(
                any(k in e.name for k in ('dreadnought', 'battlecruiser', 'frigate', 'shadow_interceptor'))
                for e in enemies
            )
            wave_threshold = 2 if has_heavy_or_elite else 3

            # Screen busy check: if enemy count is at or above threshold, mark busy and hold spawn
            if len(enemies) >= wave_threshold or len(enemies) >= max_screen_enemies:
                last_busy_screen_time = now
            # Tactical breather window: once screen drops below threshold, require 1.5s breather
            elif last_busy_screen_time > 0 and (now - last_busy_screen_time < 1500):
                pass
            # Inter-wave deployment buffer (minimum 2.2s between new wave deployments)
            elif last_wave_spawn_time > 0 and (now - last_wave_spawn_time < 2200):
                pass
            elif len(enemies) < max_screen_enemies:
                encounter = director.choose_encounter(player, score, len(enemies), now, now - game_start_time)

                # Strict per-class caps to prevent screen clutter (no 3 battleships stacking!):
                cap_ships = ('dreadnought', 'klaed_dreadnought', 'nairan_dreadnought',
                             'battlecruiser', 'klaed_battlecruiser', 'nairan_battlecruiser')
                has_capital = any(e.name in cap_ships for e in enemies)
                frigate_count = sum(1 for e in enemies if 'frigate' in e.name)
                bomber_count  = sum(1 for e in enemies if 'bomber' in e.name)
                torpedo_count = sum(1 for e in enemies if 'torpedo' in e.name)
                support_count = sum(1 for e in enemies if 'support' in e.name)

                # Filter encounter members through strict anti-clutter caps
                approved_members = []
                for enemy_name, behavior in encounter:
                    if len(enemies) + len(approved_members) >= max_screen_enemies:
                        break
                    is_capital = enemy_name in cap_ships
                    if is_capital and (has_capital or any(m[0] in cap_ships for m in approved_members)):
                        continue
                    if 'frigate' in enemy_name and (frigate_count + sum(1 for m in approved_members if 'frigate' in m[0])) >= 2:
                        continue
                    if 'bomber' in enemy_name and (bomber_count + sum(1 for m in approved_members if 'bomber' in m[0])) >= 1:
                        continue
                    if 'torpedo' in enemy_name and (torpedo_count + sum(1 for m in approved_members if 'torpedo' in m[0])) >= 1:
                        continue
                    if 'support' in enemy_name and (support_count + sum(1 for m in approved_members if 'support' in m[0])) >= 1:
                        continue
                    approved_members.append((enemy_name, behavior))

                # Calculate structured wave formation coordinates based on Aegis-Fable formation geometry
                formation = getattr(director, 'last_formation', 'ARROWHEAD')
                num_spawns = len(approved_members)
                for idx, (enemy_name, behavior) in enumerate(approved_members):
                    etype = enemy_types_by_name[enemy_name]
                    ship_w = etype['ship'].get_width()
                    ship_h = etype['ship'].get_height()

                    if enemy_name in ('dreadnought', 'klaed_dreadnought', 'nairan_dreadnought'):
                        # Dreadnought Flagship always commands the central lane
                        sx = GAME_WIDTH // 2 - ship_w // 2
                        sy = -ship_h - 15
                    elif 'support' in enemy_name and (
                        any(any(k in e.name for k in ('dreadnought', 'battlecruiser')) for e in enemies) or
                        any(any(k in m[0] for k in ('dreadnought', 'battlecruiser')) for m in approved_members)
                    ):
                        # Guarantee support ships escorting capital ships spawn cleanly outside the shield on the outer flank
                        cap_in_field = next((e for e in enemies if any(k in e.name for k in ('dreadnought', 'battlecruiser'))), None)
                        cap_cx = cap_in_field.rect.centerx if cap_in_field is not None else (GAME_WIDTH // 2)
                        existing_supps = sum(1 for e in enemies if 'support' in e.name) + sum(1 for m in approved_members[:idx] if 'support' in m[0])
                        flank_side = -1 if (existing_supps % 2 == 0) else 1
                        sx = cap_cx + flank_side * 155 - ship_w // 2
                        sx = max(25, min(GAME_WIDTH - ship_w - 25, sx))
                        sy = -ship_h - 35
                    elif formation == "PINCER" and num_spawns >= 2:
                        # Wide pincer entry to flush corner campers
                        if idx % 2 == 0:
                            sx = 35
                        else:
                            sx = GAME_WIDTH - ship_w - 35
                        sy = -ship_h - (idx * 28)
                    elif formation == "ARROWHEAD" and num_spawns >= 3:
                        # V-Formation (center lead, wings trailing)
                        if idx == 0:
                            sx = GAME_WIDTH * 0.50 - ship_w // 2
                            sy = -ship_h - 10
                        elif idx == 1:
                            sx = GAME_WIDTH * 0.22 - ship_w // 2
                            sy = -ship_h - 55
                        else:
                            sx = GAME_WIDTH * 0.78 - ship_w // 2
                            sy = -ship_h - 55
                    elif formation == "SUPPRESSION" and player is not None and num_spawns >= 2:
                        # Suppression sweep across the player's lateral zone
                        p_center = player.rect.centerx
                        step_x = 130
                        offset = (idx - (num_spawns - 1) / 2) * step_x
                        sx = max(20, min(GAME_WIDTH - ship_w - 20, p_center + offset - ship_w // 2))
                        sy = -ship_h - (idx * 25)
                    elif formation == "HAMMER_ANVIL" and num_spawns >= 2:
                        if idx == 0:
                            sx = GAME_WIDTH // 2 - ship_w // 2
                            sy = -ship_h - 10
                        else:
                            p_side = 70 if (player and player.rect.centerx < GAME_WIDTH // 2) else (GAME_WIDTH - ship_w - 70)
                            sx = p_side
                            sy = -ship_h - 45
                    elif formation == "ESCORT" and num_spawns >= 2:
                        if idx == 0:
                            sx = GAME_WIDTH // 2 - ship_w // 2
                            sy = -ship_h - 10
                        else:
                            side_off = -140 if idx % 2 == 1 else 140
                            sx = max(20, min(GAME_WIDTH - ship_w - 20, GAME_WIDTH // 2 + side_off - ship_w // 2))
                            sy = -ship_h - 35
                    elif num_spawns == 1:
                        sx = GAME_WIDTH // 2 - ship_w // 2
                        sy = -ship_h - 10
                    elif num_spawns == 2:
                        lanes = [GAME_WIDTH * 0.24, GAME_WIDTH * 0.76]
                        sx = lanes[idx] - ship_w // 2
                        sy = -ship_h - (idx * 30)
                    else:
                        step = (GAME_WIDTH - 120) / max(1, num_spawns)
                        sx = 60 + idx * step
                        sy = -ship_h - (idx * 35)

                    new_enemy = Enemy(etype, behavior, spawn_x=sx, spawn_y=sy, difficulty=diff)
                    if idx == 0 and num_spawns >= 2:
                        new_enemy.is_leader = True
                    if enemy_name == 'asteroid':
                        new_enemy.inbound_warning_until = now + 800
                        new_enemy.spawn_lane_x = sx + ship_w // 2
                    enemies.append(new_enemy)

                    # ── Feature 3: Boss intro flash ───────────────────────────────────
                    if enemy_name == 'dreadnought':
                        boss_intro_until = pygame.time.get_ticks() + 2400
                        boss_intro_title = 'DREADNOUGHT'
                        boss_intro_sub   = 'INCOMING'
                        assets['sfx']['boss_alert'].play()
                    elif enemy_name == 'klaed_dreadnought':
                        boss_intro_until = pygame.time.get_ticks() + 2600
                        boss_intro_title = 'VOID OVERLORD'
                        boss_intro_sub   = 'FLEET INVASION'
                        assets['sfx']['boss_alert'].play()
                    elif enemy_name == 'nairan_dreadnought':
                        boss_intro_until = pygame.time.get_ticks() + 2600
                        boss_intro_title = 'NAIRAN DREADNOUGHT'
                        boss_intro_sub   = 'CYBER INVASION'
                        assets['sfx']['boss_alert'].play()

                if approved_members:
                    last_wave_spawn_time = now
                    if len(enemies) >= wave_threshold:
                        last_busy_screen_time = now
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F11:
                fullscreen = not fullscreen
                display = pygame.display.set_mode((0, 0), pygame.FULLSCREEN) if fullscreen else pygame.display.set_mode((800, 600))
                screen = display
                SCREEN_WIDTH, SCREEN_HEIGHT = display.get_size()
                SCALE_FACTOR = SCREEN_HEIGHT / 600.0
                OFFSET_X = (SCREEN_WIDTH - int(GAME_WIDTH * SCALE_FACTOR)) // 2
                theme = UITheme(SCALE_FACTOR)
                title_font = theme.title_large
                button_font = theme.button
                label_font = theme.label
                shop_detail_font = theme.mono_small
                hangar_view = HangarView(assets, SHOP_ITEMS, handle_hangar_purchase_or_equip, screen_size=(SCREEN_WIDTH, SCREEN_HEIGHT))
            elif event.key == pygame.K_F3:
                dev_overlay = not dev_overlay   # Feature 10: toggle dev overlay
            elif state == "BOOT":
                if event.key == pygame.K_ESCAPE:
                    if not save_data.get("tutorial_completed", False):
                        save_data["credits"] = save_data.get("credits", 0) + 100
                    save_data["tutorial_completed"] = True
                    write_save_data(save_data)
                    tutorial_ctrl.state = "DONE"
                    state = "MENU"
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                    start_tutorial_session()
            elif state in ("TUTORIAL", "TUTORIAL_COMBAT"):
                if event.key == pygame.K_ESCAPE:
                    if not save_data.get("tutorial_completed", False):
                        save_data["credits"] = save_data.get("credits", 0) + 100
                    save_data["tutorial_completed"] = True
                    write_save_data(save_data)
                    tutorial_ctrl.state = "DONE"
                    state = "MENU"
                elif event.key == CONFIG['keybinds'].get('RELOAD', pygame.K_r) and player is not None:
                    player.start_reload()
                elif event.key == CONFIG['keybinds'].get('FLARE', CONFIG['keybinds'].get('CHAFF', pygame.K_f)) and player is not None:
                    player.deploy_chaff(now)
            elif state == "MENU" and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                reset_game()
                state = "PLAYING"
            elif state == "HANGAR":
                if event.key == pygame.K_ESCAPE:
                    if tutorial_ctrl.tour_step > 0:
                        tutorial_ctrl.tour_step = 0
                        save_data["tutorial_completed"] = True
                        write_save_data(save_data)
                        state = "MENU"
                    elif hangar_view.mode in ("customize", "encyclopedia"):
                        hangar_view.mode = "overview"
                    else:
                        state = "MENU"
                elif event.key == pygame.K_e:
                    hangar_view.mode = "customize" if hangar_view.mode == "overview" else "overview"
            elif state == "SHOP" and event.key == pygame.K_ESCAPE:
                if tutorial_ctrl.tour_step == 4:
                    tutorial_ctrl.tour_step = 0
                    tutorial_ctrl.state = "GOODBYE_DIALOGUE"
                    tutorial_ctrl.load_script(tutorial_ctrl.GOODBYE_SCRIPT)
                    state = "MENU"
                elif tutorial_ctrl.tour_step > 0:
                    tutorial_ctrl.tour_step = 0
                    tutorial_ctrl.state = "DONE"
                    save_data["tutorial_completed"] = True
                    save_data["credits"] = save_data.get("credits", 0) + 100
                    write_save_data(save_data)
                    state = "MENU"
                else:
                    state = "MENU"
            elif state == "PLAYING" and event.key in (CONFIG['keybinds'].get('PAUSE', pygame.K_ESCAPE), pygame.K_ESCAPE):
                state = "PAUSED"
            elif state == "PLAYING" and event.key == CONFIG['keybinds'].get('RELOAD', pygame.K_r) and player is not None:
                player.start_reload()
            elif state == "PLAYING" and event.key == CONFIG['keybinds'].get('FLARE', CONFIG['keybinds'].get('CHAFF', pygame.K_f)) and player is not None:
                player.deploy_chaff(now)
            elif state == "PLAYING" and event.key == CONFIG['keybinds'].get('INVINCIBILITY', pygame.K_q) and player is not None:
                if save_data['invincibility_backups'] > 0 and not player.emergency_invincible:
                    save_data['invincibility_backups'] -= 1
                    player.activate_invincibility(5000)
                    write_save_data(save_data)
            elif state == "PAUSED":
                if event.key == pygame.K_ESCAPE: state = "PLAYING"
                elif event.key == pygame.K_r: reset_game(); state = "PLAYING"
                elif event.key == pygame.K_m: state = "MENU"
            elif state == "GAME_OVER":
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_r):
                    reset_game()
                    state = "PLAYING"
                elif event.key == pygame.K_ESCAPE:
                    state = "MENU"
            elif state == "KEYBINDS" and event.key == pygame.K_ESCAPE:
                state = "MENU"
            elif state == "WAITING_FOR_KEY":
                if event.key != pygame.K_ESCAPE:
                    old_key = CONFIG['keybinds'].get(waiting_for_key)
                    # Conflict detection: if another action already used this key, swap them!
                    conflict = next((act for act, k in CONFIG['keybinds'].items() if k == event.key and act != waiting_for_key), None)
                    if conflict and old_key:
                        CONFIG['keybinds'][conflict] = old_key
                        save_data.setdefault('keybinds', {})[conflict] = pygame.key.name(old_key)
                        keybind_notice = f"SWAPPED [{friendly_key_name(event.key)}] WITH {conflict}!"
                    else:
                        keybind_notice = f"MAPPED [{friendly_key_name(event.key)}] TO {waiting_for_key}!"

                    CONFIG['keybinds'][waiting_for_key] = event.key
                    save_data.setdefault('keybinds', {})[waiting_for_key] = pygame.key.name(event.key)
                    write_save_data(save_data)
                    keybind_notice_until = pygame.time.get_ticks() + 2500
                    assets['sfx']['combo'].play()
                else:
                    keybind_notice = "REBIND CANCELLED"
                    keybind_notice_until = pygame.time.get_ticks() + 1500
                    assets['sfx']['click'].play()
                waiting_for_key = None
                state = "KEYBINDS"
        # ── Feature 9: controller connect / disconnect ──────────────────
        elif event.type == pygame.JOYDEVICEADDED:
            joy = pygame.joystick.Joystick(event.device_index)
            joysticks[joy.get_instance_id()] = joy
        elif event.type == pygame.JOYDEVICEREMOVED:
            joysticks.pop(event.instance_id, None)
        elif event.type == pygame.JOYBUTTONDOWN:
            if state in ("PLAYING", "TUTORIAL") and player is not None:
                if event.button == 0:   # A / Cross → shield
                    player.activate_shield()
                elif event.button == 4: # LB / L1 → engine ability
                    player.activate_engine_ability()
        elif event.type == pygame.MOUSEWHEEL:
            if state == "HANGAR" and hasattr(hangar_view, 'handle_scroll'):
                hangar_view.handle_scroll(event.y)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            assets['sfx']['click'].play()
            event_pos = event.pos
            if state == "BOOT":
                start_tutorial_session()
            elif state in ("TUTORIAL", "TUTORIAL_COMBAT"):
                if tutorial_ctrl.get_skip_button_rect(SCREEN_WIDTH, SCALE_FACTOR).collidepoint(event_pos):
                    if not save_data.get("tutorial_completed", False):
                        save_data["credits"] = save_data.get("credits", 0) + 100
                    save_data["tutorial_completed"] = True
                    write_save_data(save_data)
                    tutorial_ctrl.state = "DONE"
                    state = "MENU"
            elif state == "MENU":
                buttons = get_menu_buttons()
                if buttons["start"].collidepoint(event_pos):
                    reset_game()
                    state = "PLAYING"
                elif buttons["hangar"].collidepoint(event_pos):
                    state = "HANGAR"
                elif "tutorial" in buttons and buttons["tutorial"].collidepoint(event_pos):
                    start_tutorial_session()
                elif buttons["settings"].collidepoint(event_pos): state = "SETTINGS"
                elif buttons["keybinds"].collidepoint(event_pos): state = "KEYBINDS"
                elif buttons["shop"].collidepoint(event_pos): shop_notice = ''; state = "SHOP"
                elif buttons["quit"].collidepoint(event_pos): running = False
            elif state == "HANGAR":
                action = hangar_view.handle_click(event_pos, save_data)
                if action == "BACK":
                    if tutorial_ctrl.tour_step > 0:
                        tutorial_ctrl.tour_step = 0
                        save_data["tutorial_completed"] = True
                        write_save_data(save_data)
                    state = "MENU"
                elif action == "SAVE_DATA":
                    write_save_data(save_data)
            elif state == "SETTINGS":
                buttons = get_settings_buttons()
                if buttons["sens_decrease"].collidepoint(event_pos):
                    CONFIG['sensitivity'] = max(2, CONFIG['sensitivity'] - 1)
                    save_data['sensitivity'] = CONFIG['sensitivity']
                    write_save_data(save_data)
                    if player: player.speed = CONFIG['sensitivity']
                elif buttons["sens_increase"].collidepoint(event_pos):
                    CONFIG['sensitivity'] = min(15, CONFIG['sensitivity'] + 1)
                    save_data['sensitivity'] = CONFIG['sensitivity']
                    write_save_data(save_data)
                    if player: player.speed = CONFIG['sensitivity']
                elif buttons["vol_decrease"].collidepoint(event_pos):
                    CONFIG['music_volume'] = max(0.0, round(CONFIG['music_volume'] - 0.1, 1))
                    safe_music_call('set_volume', CONFIG['music_volume'])
                    save_data['music_volume'] = CONFIG['music_volume']
                    write_save_data(save_data)
                elif buttons["vol_increase"].collidepoint(event_pos):
                    CONFIG['music_volume'] = min(1.0, round(CONFIG['music_volume'] + 0.1, 1))
                    safe_music_call('set_volume', CONFIG['music_volume'])
                    save_data['music_volume'] = CONFIG['music_volume']
                    write_save_data(save_data)
                elif buttons["diff_decrease"].collidepoint(event_pos):
                    diffs = ["easy", "medium", "hard"]
                    cur_diff = save_data.get('difficulty', 'medium')
                    save_data['difficulty'] = diffs[(diffs.index(cur_diff) - 1) % len(diffs)]
                    write_save_data(save_data)
                elif buttons["diff_increase"].collidepoint(event_pos):
                    diffs = ["easy", "medium", "hard"]
                    cur_diff = save_data.get('difficulty', 'medium')
                    save_data['difficulty'] = diffs[(diffs.index(cur_diff) + 1) % len(diffs)]
                    write_save_data(save_data)
                elif buttons["song_previous"].collidepoint(event_pos): change_music(-1)
                elif buttons["song_next"].collidepoint(event_pos): change_music(1)
                elif buttons["back"].collidepoint(event_pos): state = "MENU"
            elif state == "KEYBINDS":
                kb_layout = get_keybind_layout()
                if kb_layout["back"].collidepoint(event_pos):
                    state = "MENU"
                elif kb_layout["reset"].collidepoint(event_pos):
                    for act, def_k in _DEFAULT_KEYBINDS.items():
                        CONFIG['keybinds'][act] = def_k
                        save_data.setdefault('keybinds', {})[act] = pygame.key.name(def_k)
                    write_save_data(save_data)
                    keybind_notice = "FACTORY DEFAULTS RESTORED"
                    keybind_notice_until = pygame.time.get_ticks() + 2500
                    assets['sfx']['combo'].play()
                else:
                    for action, rect in kb_layout["rows"].items():
                        if rect.collidepoint(event_pos):
                            waiting_for_key = action
                            state = "WAITING_FOR_KEY"
                            assets['sfx']['click'].play()
                            break
            elif state == "SHOP":
                tabs = get_shop_tabs()
                for category, rect in tabs.items():
                    if rect.collidepoint(event_pos):
                        shop_category = category
                        shop_notice = ''
                        break
                if get_shop_back_rect().collidepoint(event_pos):
                    if tutorial_ctrl.tour_step == 4:
                        tutorial_ctrl.tour_step = 0
                        tutorial_ctrl.state = "GOODBYE_DIALOGUE"
                        tutorial_ctrl.load_script(tutorial_ctrl.GOODBYE_SCRIPT)
                        state = "MENU"
                    elif tutorial_ctrl.tour_step > 0:
                        tutorial_ctrl.tour_step = 0
                        tutorial_ctrl.state = "DONE"
                        save_data["tutorial_completed"] = True
                        save_data["credits"] = save_data.get("credits", 0) + 100
                        write_save_data(save_data)
                        state = "MENU"
                    else:
                        state = "MENU"
                else:
                    for index, item in enumerate(SHOP_ITEMS[shop_category]):
                        if get_shop_item_rect(index).collidepoint(event_pos):
                            purchase_or_equip(item)
                            break
            elif state == "PAUSED":
                buttons = get_pause_buttons()
                if buttons['resume'].collidepoint(event_pos): state = "PLAYING"
                elif buttons['restart'].collidepoint(event_pos): reset_game(); state = "PLAYING"
                elif buttons['menu'].collidepoint(event_pos): state = "MENU"
            elif state == "GAME_OVER":
                buttons = get_game_over_buttons()
                if buttons['restart'].collidepoint(event_pos): reset_game(); state = "PLAYING"
                elif buttons['menu'].collidepoint(event_pos): state = "MENU"

    frame_now = pygame.time.get_ticks()
    if state == "PLAYING":
        background.update(getattr(director, 'fleet_phase', 0))
        background.draw(game_surface)
    elif state in ("TUTORIAL", "TUTORIAL_COMBAT"):
        tutorial_ctrl.draw_sim_grid(game_surface, frame_now)
    elif state == "TUTORIAL_DIALOGUE":
        tutorial_ctrl.draw_sim_grid(game_surface, frame_now)
        scaled_bg = pygame.transform.scale(game_surface, (int(GAME_WIDTH * SCALE_FACTOR), SCREEN_HEIGHT))
        display.fill((6, 9, 16))
        display.blit(scaled_bg, (OFFSET_X, 0))
    elif state == "BOOT":
        pass
    else:
        background.update(0)
        background.draw(game_surface)
        scaled_bg = pygame.transform.scale(game_surface, (int(GAME_WIDTH * SCALE_FACTOR), SCREEN_HEIGHT))
        display.fill((11, 15, 25))
        display.blit(scaled_bg, (OFFSET_X, 0))

    if state == "BOOT":
        tutorial_ctrl.draw_boot(display, theme, SCALE_FACTOR, frame_now)
        if tutorial_ctrl.update_boot(frame_now):
            start_tutorial_session()

    elif state == "MENU":
        draw_title(display)
        menu_btns = get_menu_buttons()
        # Start button
        draw_button(display, menu_btns["start"], "START MISSION", theme.button_large,
                    menu_btns["start"].collidepoint(mouse_pos), primary=True, color_accent=theme.CYAN)
        draw_button(display, menu_btns["hangar"], "HANGAR & LOADOUT", theme.button,
                    menu_btns["hangar"].collidepoint(mouse_pos), color_accent=(255, 200, 60))
        if "tutorial" in menu_btns:
            draw_button(display, menu_btns["tutorial"], "TRAINING SIM", theme.button,
                        menu_btns["tutorial"].collidepoint(mouse_pos), color_accent=(100, 240, 180))

        for name, label in [("shop", "Supply Depot"), ("settings", "Settings"), ("keybinds", "Keybinds"), ("quit", "Quit")]:
            rect = menu_btns[name]
            draw_button(display, rect, label, theme.button, rect.collidepoint(mouse_pos))

        best_label = theme.mono.render(f"BEST SCORE: {high_score}", True, (180, 210, 255))
        display.blit(best_label, best_label.get_rect(center=(SCREEN_WIDTH // 2, int(496 * SCALE_FACTOR))))
        wallet = theme.mono.render(f"CREDITS: {save_data['credits']} CR", True, (100, 235, 200))
        display.blit(wallet, wallet.get_rect(center=(SCREEN_WIDTH // 2, int(522 * SCALE_FACTOR))))
        hint = theme.mono_small.render("PRESS ENTER OR CLICK START TO BEGIN MISSION", True, (120, 150, 190))
        display.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, int(554 * SCALE_FACTOR))))

    elif state == "HANGAR":
        hangar_view.draw(display, save_data, mouse_pos)
        if tutorial_ctrl.tour_step in (1, 2, 3):
            if tutorial_ctrl.tour_step == 1 and hangar_view.mode == "customize":
                tutorial_ctrl.tour_step = 2
                tutorial_ctrl.tour_step_started_at = frame_now
            elif tutorial_ctrl.tour_step == 2 and hangar_view.mode == "encyclopedia":
                tutorial_ctrl.tour_step = 3
                tutorial_ctrl.tour_step_started_at = frame_now
            elif tutorial_ctrl.tour_step == 3 and hangar_view.mode != "encyclopedia":
                tutorial_ctrl.tour_step = 4
                tutorial_ctrl.tour_step_started_at = frame_now
                state = "SHOP"
                shop_notice = ''

            if state == "HANGAR":
                tutorial_ctrl.draw_tour_overlay(display, theme, SCALE_FACTOR, hangar_view, None, None, frame_now)

    elif state == "SETTINGS":
        draw_title(display)
        buttons = get_settings_buttons()
        # Sensitivity
        draw_button(display, buttons["sens_decrease"], "-", button_font, buttons["sens_decrease"].collidepoint(mouse_pos))
        draw_button(display, buttons["sens_increase"], "+", button_font, buttons["sens_increase"].collidepoint(mouse_pos))
        sensitivity_label = label_font.render(f"Sensitivity: {CONFIG['sensitivity']}", True, (255, 255, 255))
        display.blit(sensitivity_label, sensitivity_label.get_rect(center=(SCREEN_WIDTH // 2, int(197 * SCALE_FACTOR))))

        # Volume
        draw_button(display, buttons["vol_decrease"], "-", button_font, buttons["vol_decrease"].collidepoint(mouse_pos))
        draw_button(display, buttons["vol_increase"], "+", button_font, buttons["vol_increase"].collidepoint(mouse_pos))
        volume_label = label_font.render(f"Music Vol: {int(CONFIG['music_volume'] * 100)}%", True, (255, 255, 255))
        display.blit(volume_label, volume_label.get_rect(center=(SCREEN_WIDTH // 2, int(262 * SCALE_FACTOR))))

        # Difficulty
        diff = save_data.get('difficulty', 'medium')
        diff_color = (100, 240, 150) if diff == 'easy' else ((255, 105, 90) if diff == 'hard' else (100, 220, 255))
        draw_button(display, buttons["diff_decrease"], "<", button_font, buttons["diff_decrease"].collidepoint(mouse_pos))
        draw_button(display, buttons["diff_increase"], ">", button_font, buttons["diff_increase"].collidepoint(mouse_pos))
        diff_label = label_font.render(f"Difficulty: {diff.upper()}", True, diff_color)
        display.blit(diff_label, diff_label.get_rect(center=(SCREEN_WIDTH // 2, int(332 * SCALE_FACTOR))))
        diff_desc = {
            "easy": "35% Damage Shield Buffer  |  Relaxed Fire  |  Max 4 Enemies",
            "medium": "Balanced Arcade Pacing  |  Full 3-Faction Armada  |  Max 5",
            "hard": "High-Speed Projectiles  |  Max 6  |  +35% Bonus Score & Credits"
        }[diff]
        diff_desc_surf = shop_detail_font.render(diff_desc, True, (170, 195, 225))
        display.blit(diff_desc_surf, diff_desc_surf.get_rect(center=(SCREEN_WIDTH // 2, int(365 * SCALE_FACTOR))))

        # Music
        song_label = label_font.render(current_track_name(), True, (120, 235, 255))
        display.blit(song_label, song_label.get_rect(center=(SCREEN_WIDTH // 2, int(432 * SCALE_FACTOR))))
        draw_button(display, buttons["song_previous"], "<", button_font, buttons["song_previous"].collidepoint(mouse_pos))
        draw_button(display, buttons["song_next"], ">", button_font, buttons["song_next"].collidepoint(mouse_pos))
        draw_button(display, buttons["back"], "Back", button_font, buttons["back"].collidepoint(mouse_pos))

    elif state in ("KEYBINDS", "WAITING_FOR_KEY"):
        now_kb = pygame.time.get_ticks()
        kb_layout = get_keybind_layout()
        panel = kb_layout["panel"]

        # Frosted glass cyber terminal panel
        theme.draw_cyber_panel(display, panel, title="CONTROL MATRIX // FLIGHT KEYBINDINGS", bg_alpha=235)

        # Header Subtitle
        sub_txt = theme.mono_small.render("AEGIS-FABLE TACTICAL INPUT MAPPING  •  CLICK ANY CARD TO REASSIGN", True, (140, 180, 215))
        display.blit(sub_txt, (panel.x + int(24 * SCALE_FACTOR), panel.y + int(28 * SCALE_FACTOR)))

        # Category 1 Header: FLIGHT & PROPULSION
        c1_x = kb_layout["col1_x"]
        h_y = kb_layout["header_y"]
        col_w = kb_layout["col_w"]
        theme.draw_badge(display, c1_x, h_y, "PROPULSION", color=(0, 240, 255))
        c1_title = theme.header_small.render("FLIGHT & PROPULSION", True, (0, 240, 255))
        display.blit(c1_title, (c1_x + int(96 * SCALE_FACTOR), h_y))
        pygame.draw.line(display, (0, 180, 210, 120), (c1_x, h_y + int(22 * SCALE_FACTOR)), (c1_x + col_w, h_y + int(22 * SCALE_FACTOR)), 1)

        # Category 2 Header: COMBAT & TACTICAL
        c2_x = kb_layout["col2_x"]
        theme.draw_badge(display, c2_x, h_y, "TACTICAL", color=(255, 185, 45))
        c2_title = theme.header_small.render("COMBAT & SYSTEMS", True, (255, 185, 45))
        display.blit(c2_title, (c2_x + int(82 * SCALE_FACTOR), h_y))
        pygame.draw.line(display, (210, 150, 35, 120), (c2_x, h_y + int(22 * SCALE_FACTOR)), (c2_x + col_w, h_y + int(22 * SCALE_FACTOR)), 1)

        # Draw Action Cards
        for grp_idx, group in enumerate(KEYBIND_GROUPS):
            accent = group["color"]
            for action_info in group["actions"]:
                act_id = action_info["id"]
                rect = kb_layout["rows"][act_id]
                hovered = rect.collidepoint(mouse_pos) and state == "KEYBINDS"
                is_active_rebind = (waiting_for_key == act_id)

                # Card background & frame
                if is_active_rebind:
                    card_bg = (40, 32, 16)
                    card_border = (255, 215, 60)
                    b_thick = max(1, int(2 * SCALE_FACTOR))
                elif hovered:
                    card_bg = (24, 38, 58)
                    card_border = accent
                    b_thick = max(1, int(2 * SCALE_FACTOR))
                else:
                    card_bg = (14, 20, 30)
                    card_border = (45, 68, 96)
                    b_thick = 1

                pygame.draw.rect(display, card_bg, rect, border_radius=max(2, int(4 * SCALE_FACTOR)))
                pygame.draw.rect(display, card_border, rect, b_thick, border_radius=max(2, int(4 * SCALE_FACTOR)))

                # Action Title
                name_surf = theme.label.render(action_info["name"].upper(), True, (255, 255, 255) if (hovered or is_active_rebind) else (225, 235, 245))
                display.blit(name_surf, (rect.x + int(12 * SCALE_FACTOR), rect.y + int(6 * SCALE_FACTOR)))

                # Action Description
                desc_surf = theme.mono_small.render(action_info["desc"], True, (135, 160, 190))
                display.blit(desc_surf, (rect.x + int(12 * SCALE_FACTOR), rect.y + int(28 * SCALE_FACTOR)))

                # Key Badge on the right
                current_key = CONFIG['keybinds'].get(act_id, action_info["default"])
                key_label = "PRESS KEY..." if is_active_rebind else friendly_key_name(current_key)
                badge_text_surf = theme.mono.render(key_label, True, (255, 230, 60) if is_active_rebind else ((255, 255, 255) if hovered else accent))
                badge_w = max(int(78 * SCALE_FACTOR), badge_text_surf.get_width() + int(16 * SCALE_FACTOR))
                badge_h = int(30 * SCALE_FACTOR)
                badge_rect = pygame.Rect(rect.right - badge_w - int(10 * SCALE_FACTOR), rect.centery - badge_h // 2, badge_w, badge_h)

                badge_bg = (35, 28, 12) if is_active_rebind else ((20, 32, 48) if hovered else (16, 24, 36))
                badge_border = (255, 215, 60) if is_active_rebind else (accent if hovered else (55, 80, 110))
                pygame.draw.rect(display, badge_bg, badge_rect, border_radius=3)
                pygame.draw.rect(display, badge_border, badge_rect, 1, border_radius=3)
                display.blit(badge_text_surf, badge_text_surf.get_rect(center=badge_rect.center))

        # System Telemetry & Secondary Controls Bar
        telem_y = kb_layout["reset"].y - int(34 * SCALE_FACTOR)
        telem_w = panel.width - int(40 * SCALE_FACTOR)
        telem_h = int(24 * SCALE_FACTOR)
        telem_rect = pygame.Rect(panel.x + int(20 * SCALE_FACTOR), telem_y, telem_w, telem_h)
        pygame.draw.rect(display, (10, 16, 26, 180), telem_rect, border_radius=3)
        pygame.draw.rect(display, (36, 52, 74), telem_rect, 1, border_radius=3)

        if keybind_notice and now_kb < keybind_notice_until:
            alpha = min(255, int(255 * (keybind_notice_until - now_kb) / 500))
            notice_surf = theme.label.render(f"[ STATUS ] {keybind_notice}", True, (100, 255, 180))
            notice_surf.set_alpha(alpha)
            display.blit(notice_surf, notice_surf.get_rect(center=telem_rect.center))
        else:
            telem_text = "[ F11 ] FULLSCREEN  •  [ F3 ] DEV OVERLAY  •  [ ARROW KEYS ] ALTERNATE FLIGHT"
            telem_surf = theme.mono_small.render(telem_text, True, (120, 155, 190))
            display.blit(telem_surf, telem_surf.get_rect(center=telem_rect.center))

        # Navigation Buttons
        theme.draw_cyber_button(display, kb_layout["reset"], "RESET DEFAULTS", font=button_font,
                                hovered=kb_layout["reset"].collidepoint(mouse_pos),
                                color_accent=(255, 110, 110))
        theme.draw_cyber_button(display, kb_layout["back"], "BACK TO MENU", font=button_font,
                                hovered=kb_layout["back"].collidepoint(mouse_pos),
                                primary=True)

        # Modal Rebind Overlay when waiting for input
        if state == "WAITING_FOR_KEY" and waiting_for_key:
            modal_backdrop = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            modal_backdrop.fill((0, 0, 0, 190))
            display.blit(modal_backdrop, (0, 0))

            modal_w = min(SCREEN_WIDTH - 40, int(480 * SCALE_FACTOR))
            modal_h = int(210 * SCALE_FACTOR)
            cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
            modal_rect = pygame.Rect(cx - modal_w // 2, cy - modal_h // 2, modal_w, modal_h)

            theme.draw_cyber_panel(display, modal_rect, title="INPUT REBIND PROTOCOL", border_color=(0, 240, 255), bg_alpha=245)

            # Look up action name
            act_name = waiting_for_key
            for g in KEYBIND_GROUPS:
                for a in g["actions"]:
                    if a["id"] == waiting_for_key:
                        act_name = a["name"]
                        break

            m_title = theme.title_small.render(act_name.upper(), True, (0, 240, 255))
            display.blit(m_title, m_title.get_rect(center=(cx, modal_rect.y + int(48 * SCALE_FACTOR))))

            pulse = int(180 + 75 * math.sin(now_kb / 120.0))
            m_prompt = theme.button.render(">>> PRESS ANY KEY TO BIND <<<", True, (255, 235, 60))
            m_prompt.set_alpha(pulse)
            display.blit(m_prompt, m_prompt.get_rect(center=(cx, modal_rect.y + int(105 * SCALE_FACTOR))))

            m_hint = theme.mono_small.render("[ ESC ] CANCEL REBINDING  •  EXISTING BINDS AUTO-SWAP", True, (150, 180, 210))
            display.blit(m_hint, m_hint.get_rect(center=(cx, modal_rect.y + int(160 * SCALE_FACTOR))))

    elif state == "SHOP":
        title = title_font.render("SUPPLY DEPOT", True, (0, 255, 255))
        display.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, int(72 * SCALE_FACTOR))))
        wallet = label_font.render(f"CREDITS: {save_data['credits']}", True, (100, 235, 200))
        display.blit(wallet, wallet.get_rect(topright=(SCREEN_WIDTH // 2 + int(320 * SCALE_FACTOR), int(105 * SCALE_FACTOR))))
        reward_hint = label_font.render("5 CREDITS PER ENEMY", True, (145, 164, 198))
        display.blit(reward_hint, (SCREEN_WIDTH // 2 - int(320 * SCALE_FACTOR), int(103 * SCALE_FACTOR)))
        for category, rect in get_shop_tabs().items():
            selected = category == shop_category
            draw_button(display, rect, category.title(), label_font, selected or rect.collidepoint(mouse_pos))

        for index, item in enumerate(SHOP_ITEMS[shop_category]):
            rect = get_shop_item_rect(index)
            hovered = rect.collidepoint(mouse_pos)
            pygame.draw.rect(display, (23, 35, 61) if not hovered else (31, 54, 78), rect)
            pygame.draw.rect(display, (76, 103, 145) if not hovered else (99, 232, 255), rect, max(1, int(2 * SCALE_FACTOR)))
            preview = shop_item_image(shop_category, item['id'])
            icon_sz = int(52 * SCALE_FACTOR)
            preview = pygame.transform.smoothscale(preview, (icon_sz, icon_sz))
            display.blit(preview, preview.get_rect(center=(rect.x + int(40 * SCALE_FACTOR), rect.centery)))
            name_surface = label_font.render(item['name'], True, (240, 245, 255))
            detail_surface = shop_detail_font.render(item['detail'], True, (145, 164, 198))
            display.blit(name_surface, (rect.x + int(82 * SCALE_FACTOR), rect.y + int(8 * SCALE_FACTOR)))
            display.blit(detail_surface, (rect.x + int(82 * SCALE_FACTOR), rect.y + int(38 * SCALE_FACTOR)))

            if shop_category == 'shields' and item['id'] == 'invincibility':
                status = f"{save_data['invincibility_backups']} BACKUPS  |  BUY {item['price']} CR"
                status_color = (255, 215, 120)
            elif item['id'] == equipped_item(shop_category):
                status = 'REMOVE' if shop_category == 'shields' else 'EQUIPPED'
                status_color = (100, 235, 200)
            elif item_is_owned(shop_category, item['id']):
                status, status_color = 'EQUIP', (120, 220, 255)
            else:
                status, status_color = f"BUY {item['price']} CR", (255, 215, 120)
            status_surface = label_font.render(status, True, status_color)
            display.blit(status_surface, status_surface.get_rect(midright=(rect.right - int(14 * SCALE_FACTOR), rect.centery)))

        notice_surface = label_font.render(shop_notice, True, (255, 205, 125))
        display.blit(notice_surface, notice_surface.get_rect(center=(SCREEN_WIDTH // 2, int(500 * SCALE_FACTOR))))
        back_rect = get_shop_back_rect()
        draw_button(display, back_rect, "Back to Menu", button_font, back_rect.collidepoint(mouse_pos))
        if tutorial_ctrl.tour_step == 4:
            tutorial_ctrl.draw_tour_overlay(display, theme, SCALE_FACTOR, None, get_shop_tabs(), back_rect, frame_now)

    elif state in ("PLAYING", "TUTORIAL", "TUTORIAL_COMBAT") and player is not None:
        now = frame_now
        if frame_now >= hitstop_until:
            keys = pygame.key.get_pressed()
            player.update(keys, CONFIG['keybinds'], enemies)
            if state == "PLAYING":
                director.observe_player(player, pygame.time.get_ticks())
            elif state in ("TUTORIAL", "TUTORIAL_COMBAT"):
                res = tutorial_ctrl.update_tutorial(
                    frame_now, player, enemies, enemy_bullets, overclock_pickups, spark_particles, floating_texts
                )
                if res in ("COMPLETED", "START_TOUR", "COMBAT_CLEARED"):
                    tutorial_ctrl.state = "DEBRIEF_DIALOGUE"
                    tutorial_ctrl.load_script(tutorial_ctrl.DEBRIEF_SCRIPT)
                    state = "TUTORIAL_DIALOGUE"

            # ── Feature 9: controller axis movement ─────────────────────────
            for _joy in joysticks.values():
                _dz = 0.20
                _ax = _joy.get_axis(0) if _joy.get_numaxes() > 0 else 0
                _ay = _joy.get_axis(1) if _joy.get_numaxes() > 1 else 0
                _rt = _joy.get_axis(5) if _joy.get_numaxes() > 5 else -1  # right trigger
                if abs(_ax) > _dz:
                    player.x = max(0, min(player.x + _ax * player.speed,
                                          GAME_WIDTH - player.rect.width))
                if abs(_ay) > _dz:
                    player.y = max(0, min(player.y + _ay * player.speed,
                                          GAME_HEIGHT - player.rect.height))
                player.rect.topleft = (round(player.x), round(player.y))
                if _rt > 0.5:   # right trigger → shoot (handled via key_pressed simulation)
                    pass        # actual firing is key-driven; joystick fire via JOYBUTTONDOWN
            # ── Feature 7: adaptive music intensity ─────────────────────────
            if state == "PLAYING":
                _heavy = any(e.name in ('battlecruiser', 'dreadnought', 'klaed_battlecruiser', 'klaed_dreadnought', 'nairan_battlecruiser', 'nairan_dreadnought') for e in enemies)
                if _heavy and not music_boosted:
                    safe_music_call('set_volume', min(1.0, CONFIG['music_volume'] * 1.45))
                    music_boosted = True
                elif not _heavy and music_boosted:
                    safe_music_call('set_volume', CONFIG['music_volume'])
                    music_boosted = False
            new_bullets = player.shoot(keys, CONFIG['keybinds'], enemies)
            if new_bullets:
                # ── Feature 2: per-weapon sound ─────────────────────────────
                sfx_key = 'shoot_' + player.equipped_weapon
                assets['sfx'].get(sfx_key, assets['sfx']['player_shoot']).play()
                bullets.extend(new_bullets)

            for bullet in bullets: bullet.update(enemies)
            bullets = [b for b in bullets if not b.expired and b.rect.y > -b.rect.height]

            for enemy in enemies: enemy.update(player, enemies)
            # Remove enemies after they leave the playfield to prevent stale
            # collisions and an unbounded list as a run continues.
            enemies = [enemy for enemy in enemies if enemy.rect.top <= GAME_HEIGHT]
            for enemy in enemies:
                new_enemy_bullets = enemy.shoot(assets['enemy_projectiles'], player)
                if new_enemy_bullets:
                    assets['sfx']['enemy_shoot'].play()
                    enemy_bullets.extend(new_enemy_bullets)
                    if 'bomber' in enemy.name:
                        tx = player.rect.centerx if player else enemy.rect.centerx
                        ty = min(GAME_HEIGHT - 60, max(160, player.rect.centery if player else GAME_HEIGHT - 100))
                        bomber_hazard_markers.append({
                            'x': tx,
                            'y': ty,
                            'born': pygame.time.get_ticks(),
                            'duration': 1600,
                            'radius': 52,
                            'damage': 12,
                            'detonated': False
                        })

            # Active Countermeasure: Player Chaff / Decoy Deployment
            if getattr(player, 'chaff_deployed', False):
                player.chaff_deployed = False
                for _ in range(16):
                    spark_particles.append(SparkParticle(
                        player.rect.centerx + random.uniform(-16, 16),
                        player.rect.centery + random.uniform(-12, 12),
                        (255, 185, 45) if random.random() < 0.5 else (100, 240, 255),
                        duration=380
                    ))
                broke_any = False
                for eb in enemy_bullets:
                    if getattr(eb, 'bullet_type', None) in ('sarh_missile', 'shield_buster_torpedo'):
                        eb.bullet_type = "ballistic_lost_lock"
                        broke_any = True
                if broke_any:
                    floating_texts.append(FloatingText(player.rect.centerx, player.rect.top - 20, "CHAFF / FLARES // LOCK BROKEN", (100, 240, 255)))
                else:
                    floating_texts.append(FloatingText(player.rect.centerx, player.rect.top - 20, "DECOY FLARES RELEASED", (255, 205, 75)))
                assets['sfx'].get('spark', assets['sfx']['player_shoot']).play()

            for eb in enemy_bullets: eb.update()
            enemy_bullets = [eb for eb in enemy_bullets if eb.rect.top < GAME_HEIGHT and -eb.rect.width < eb.rect.x < GAME_WIDTH]

            eb_to_remove = []

            # Point-Defense Interception: player bullets can shoot down heavy homing missiles & torpedoes!
            for b in bullets:
                if getattr(b, 'expired', False) or getattr(b, 'deflected', False):
                    continue
                for eb in enemy_bullets:
                    if eb in eb_to_remove:
                        continue
                    if getattr(eb, 'bullet_type', None) in ('sarh_missile', 'shield_buster_torpedo'):
                        if b.rect.colliderect(eb.rect):
                            eb_to_remove.append(eb)
                            exp_frames = assets.get('explosions') or assets['enemy_types'][0]['explosion']
                            explosions.append(Explosion(eb.rect.centerx, eb.rect.centery, exp_frames))
                            floating_texts.append(FloatingText(eb.rect.centerx, eb.rect.centery - 10, "INTERCEPTED! +15", (255, 215, 60)))
                            score += 15
                            if getattr(b, 'pierce', 0) > 0:
                                b.pierce -= 1
                            else:
                                b.expired = True
                            break

            for eb in enemy_bullets:
                if eb.rect.colliderect(player.rect):
                    if not player.is_protected:
                        is_buster = getattr(eb, 'bullet_type', None) == 'shield_buster_torpedo'
                        if is_buster and (player.shield_active or player.is_shield_overcharged):
                            emp_dmg = getattr(eb, 'shield_damage', 45)
                            player.take_damage(emp_dmg)
                            floating_texts.append(FloatingText(player.rect.centerx, player.rect.top - 18, f"EMP SHIELD DISRUPT! -{emp_dmg}", (0, 240, 255)))
                        else:
                            player.take_damage(eb.damage)
                        if getattr(player, 'shield_just_collapsed', False):
                            hitstop_until = max(hitstop_until, frame_now + 60)
                            floating_texts.append(FloatingText(player.rect.centerx, player.rect.top - 32, "SHIELD COLLAPSED!", (255, 60, 60)))
                            player.shield_just_collapsed = False
                    eb_to_remove.append(eb)
            enemy_bullets = [eb for eb in enemy_bullets if eb not in eb_to_remove]

            # Darwinian Point-Defense Flares counter to rockets (evaluated individually per missile)
            if player.equipped_weapon == 'rockets' and getattr(director.counter_engine, 'active_adaptation', None):
                if director.counter_engine.active_adaptation.get('code') == 'POINT_DEFENSE_FLARES':
                    now_fl = pygame.time.get_ticks()
                    for b in bullets:
                        if getattr(b, 'max_range', None) is not None and not getattr(b, 'deflected', False):
                            for e in enemies:
                                if any(k in e.name for k in ('frigate', 'battlecruiser', 'dreadnought')):
                                    if math.hypot(b.x - e.rect.centerx, b.y - e.rect.centery) < 95:
                                        if not hasattr(b, 'evaluated_enemies'):
                                            b.evaluated_enemies = set()
                                        if e not in b.evaluated_enemies:
                                            b.evaluated_enemies.add(e)
                                            if random.random() < 0.35:
                                                b.deflected = True
                                                b.target = None
                                                b.hit_enemies.add(e)
                                                b.vx = random.choice([-7.5, 7.5]) + random.uniform(-1.5, 1.5)
                                                b.vy = random.uniform(-4.5, 0.5)
                                                active_defense_flares.append({
                                                    'start_x': float(e.rect.centerx),
                                                    'start_y': float(e.rect.centery),
                                                    'target_x': float(b.x),
                                                    'target_y': float(b.y),
                                                    'born': now_fl,
                                                    'duration': 260,
                                                    'sparks': [[float(e.rect.centerx), float(e.rect.centery), random.uniform(-2.5, 2.5), random.uniform(-2.5, 2.5)] for _ in range(6)]
                                                })
                                                director.comms.broadcast("POINT-DEFENSE FLARE DEFLECTED TORPEDO", sender="DEFENSE_GRID", color=(255, 175, 75), now=now_fl)
                                                break

            enemies_to_remove = []
            for bullet in bullets:
                if getattr(bullet, 'deflected', False):
                    continue
                for enemy in enemies:
                    if enemy in enemies_to_remove or enemy in bullet.hit_enemies:
                        continue
                    if bullet.rect.colliderect(enemy.hitbox):
                        bullet.hit_enemies.add(enemy)
                        director.note_projectile_hit()

                        # Subsystem targeting check (Port Engine, Starboard Engine, Main Battery)
                        sub_id = enemy.check_subsystem_hit(bullet.rect)
                        if sub_id:
                            just_destroyed = enemy.damage_subsystem(sub_id, bullet.damage)
                            if just_destroyed:
                                sub_name = enemy.subsystems[sub_id]['name']
                                assets['sfx']['combo'].play()
                                director.comms.broadcast(
                                    f"{enemy.name.upper()} {sub_name.upper()} DESTROYED!",
                                    sender="SUBSYSTEM_HIT",
                                    priority="CRITICAL",
                                    color=(255, 215, 60),
                                    now=pygame.time.get_ticks()
                                )
                                sub_rel = enemy.subsystems[sub_id]['rel_rect']
                                explosions.append(Explosion(enemy.rect.x + sub_rel.centerx, enemy.rect.y + sub_rel.centery, enemy.explosion_frames))

                        damage_enemy(enemy, bullet.damage, enemies_to_remove)
                        chain_from = enemy
                        for _ in range(bullet.chain_count):
                            nearby = [candidate for candidate in enemies
                                      if candidate not in enemies_to_remove and candidate not in bullet.hit_enemies
                                      and math.hypot(candidate.rect.centerx - chain_from.rect.centerx,
                                                     candidate.rect.centery - chain_from.rect.centery) <= bullet.chain_range]
                            if not nearby:
                                break
                            chained = min(nearby, key=lambda candidate: math.hypot(
                                candidate.rect.centerx - chain_from.rect.centerx,
                                candidate.rect.centery - chain_from.rect.centery))
                            bullet.hit_enemies.add(chained)
                            director.note_projectile_hit()
                            chain_effects.append((chain_from.rect.center, chained.rect.center, pygame.time.get_ticks()))
                            damage_enemy(chained, max(1, round(bullet.damage * 0.6)), enemies_to_remove)
                            chain_from = chained
                        if bullet.pierce > 0:
                            bullet.pierce -= 1
                        else:
                            bullet.expired = True
                        break

            bullets = [b for b in bullets if not b.expired]
            enemies = [e for e in enemies if e not in enemies_to_remove]
            now = pygame.time.get_ticks()
            chain_effects = [effect for effect in chain_effects if now - effect[2] < 130]

            crashed_enemies = []
            for enemy in enemies:
                if enemy.rect.colliderect(player.rect):
                    # Engine Overdrive Ramming Armor: shatters scouts & asteroids instantly without player damage
                    if player.is_engine_overclocked and (enemy.name in ('scout', 'klaed_scout', 'nairan_scout', 'asteroid') or 'scout' in enemy.name or enemy.name == 'asteroid'):
                        crashed_enemies.append(enemy)
                        exp_frames = enemy.explosion_frames or assets.get('explosions') or assets['enemy_types'][0]['explosion']
                        explosions.append(Explosion(enemy.rect.centerx, enemy.rect.centery, exp_frames))
                        assets['sfx']['explosion'].play()
                        director.note_enemy_destroyed(enemy.name)
                        if enemy.name not in save_data.get('encountered_enemies', []):
                            save_data.setdefault('encountered_enemies', []).append(enemy.name)
                            write_save_data(save_data)
                        score += round(enemy.score_value)
                        continue

                    if not player.is_protected:
                        player.take_damage(enemy.contact_damage)
                        if getattr(player, 'shield_just_collapsed', False):
                            hitstop_until = max(hitstop_until, frame_now + 50)
                            player.shield_just_collapsed = False
                        if enemy.name == 'asteroid': asteroid_hits += 1
                    if enemy.behavior == 'kamikaze':
                        crashed_enemies.append(enemy)
                        explosions.append(Explosion(enemy.rect.centerx, enemy.rect.centery, enemy.explosion_frames))
            enemies = [enemy for enemy in enemies if enemy not in crashed_enemies]

            # ── Feature 8: credit orb update + collection ───────────────────
            for _orb in credit_orbs:
                _orb.update()
            _orbs_collected = []
            for _orb in credit_orbs:
                if _orb.rect.colliderect(player.rect):
                    save_data['credits'] += _orb.value
                    assets['sfx']['credit_pickup'].play()
                    _orbs_collected.append(_orb)
            credit_orbs = [o for o in credit_orbs
                           if not o.is_expired and o not in _orbs_collected]

            # ── In-Run Module Overclock Pickup update + collection ───────────
            for _op in overclock_pickups:
                _op.update()
            _collected_ops = []
            now_oc = pygame.time.get_ticks()
            for _op in overclock_pickups:
                if _op.rect.colliderect(player.rect):
                    _collected_ops.append(_op)
                    assets['sfx']['combo'].play()
                    if _op.category == 'weapon':
                        player.weapon_overclock_until = now_oc + 7000
                        player.is_reloading = False
                        player.ammo = player.magazine_capacity
                        floating_texts.append(FloatingText(player.rect.centerx, player.rect.top - 18, "+WEAPON OVERDRIVE!", (255, 140, 40)))
                        director.comms.broadcast("WEAPON OVERDRIVE ENGAGED [7.0s]", sender="WEAPONS", color=(255, 140, 40), now=now_oc)
                    elif _op.category == 'engine':
                        player.engine_overclock_until = now_oc + 6000
                        player.engine_ready_at = now_oc
                        floating_texts.append(FloatingText(player.rect.centerx, player.rect.top - 18, "+ENGINE OVERDRIVE!", (0, 230, 255)))
                        director.comms.broadcast("ENGINE OVERDRIVE ENGAGED [6.0s] // RAMMING ARMOR ACTIVE", sender="PROPULSION", color=(0, 230, 255), now=now_oc)
                    elif _op.category == 'shield':
                        player.shield_overcharge_until = now_oc + 5000
                        player.shield_overcharge_barrier = 20
                        if player.shield_data:
                            restore_amt = int(player.shield_capacity * 0.40)
                            player.shield_remaining = min(player.shield_capacity, player.shield_remaining + restore_amt)
                            player.shield_ready_at = now_oc
                        else:
                            player.hp = min(player.max_hp, player.hp + 20)
                        floating_texts.append(FloatingText(player.rect.centerx, player.rect.top - 18, "+SHIELD SURGE!", (100, 255, 140)))
                        director.comms.broadcast("SHIELD SURGE ACTIVE [+40% CAP / 20 HP BARRIER]", sender="DEFENSE_GRID", color=(100, 255, 140), now=now_oc)
            overclock_pickups = [p for p in overclock_pickups if not p.is_expired and p not in _collected_ops]

            # Update Bomber Area Denial Hazard Markers
            now = pygame.time.get_ticks()
            for m in bomber_hazard_markers:
                m_elapsed = now - m['born']
                if m_elapsed >= m['duration'] and not m['detonated']:
                    m['detonated'] = True
                    bomb_exp_frames = assets.get('explosions') or enemy_types_by_name['bomber']['explosion']
                    explosions.append(Explosion(m['x'], m['y'], bomb_exp_frames))
                    assets['sfx']['explosion'].play()
                    if player is not None:
                        dist = math.hypot(player.rect.centerx - m['x'], player.rect.centery - m['y'])
                        if dist <= m['radius']:
                            if not player.is_protected:
                                player.take_damage(m['damage'])
                                if getattr(player, 'shield_just_collapsed', False):
                                    hitstop_until = max(hitstop_until, frame_now + 50)
                                    player.shield_just_collapsed = False
                                shake_until = now + 240
                                shake_intensity = 6
            bomber_hazard_markers = [m for m in bomber_hazard_markers if now - m['born'] < m['duration'] + 300]

        if player.hp <= 0:
            if state in ("TUTORIAL", "TUTORIAL_COMBAT"):
                player.hp = 100
            else:
                record_high_score()
                grant_run_credits()
                if score >= 150: assets['sfx']['go_good'].play()
                elif (pygame.time.get_ticks() - game_start_time) < 20000 or asteroid_hits >= 2: assets['sfx']['go_funny'].play()
                else: assets['sfx']['go_fast'].play()
                state = "GAME_OVER"

        for explosion in explosions: explosion.update()
        explosions = [e for e in explosions if not e.is_finished]

        for sp in spark_particles:
            sp.update()
        spark_particles = [sp for sp in spark_particles if sp.life > 0]

        for ft in floating_texts:
            ft.update()
        floating_texts = [ft for ft in floating_texts if not ft.is_expired]

        # Draw Bomber Area Denial Hazard Markers & Point-Defense Flares
        if bomber_hazard_markers or active_defense_flares:
            overlay = get_shared_overlay()
            overlay.fill((0, 0, 0, 0))
            overlay_needed = False

            for m in bomber_hazard_markers:
                m_elapsed = now - m['born']
                if m_elapsed < m['duration']:
                    overlay_needed = True
                    prog = min(1.0, m_elapsed / m['duration'])
                    pulse = int(140 + 80 * math.sin(now / 90.0))
                    pygame.draw.circle(overlay, (255, 30, 20, int(35 + 25 * math.sin(now / 110.0))), (int(m['x']), int(m['y'])), m['radius'])
                    pygame.draw.circle(overlay, (255, 60, 40, pulse), (int(m['x']), int(m['y'])), m['radius'], 2)
                    fuse_r = max(3, int(m['radius'] * (1.0 - prog)))
                    pygame.draw.circle(overlay, (255, 230, 80, 220), (int(m['x']), int(m['y'])), fuse_r, 2)
                    mx, my = int(m['x']), int(m['y'])
                    pygame.draw.line(overlay, (255, 80, 50, 190), (mx - 8, my), (mx + 8, my), 1)
                    pygame.draw.line(overlay, (255, 80, 50, 190), (mx, my - 8), (mx, my + 8), 1)

            for fl in active_defense_flares:
                fl_elapsed = now - fl['born']
                if fl_elapsed < fl['duration'] + 100:
                    overlay_needed = True
                    prog = min(1.0, fl_elapsed / fl['duration'])
                    cx = fl['start_x'] + (fl['target_x'] - fl['start_x']) * prog
                    cy = fl['start_y'] + (fl['target_y'] - fl['start_y']) * prog
                    pygame.draw.line(overlay, (255, 240, 150, 220), (int(fl['start_x']), int(fl['start_y'])), (int(cx), int(cy)), 2)
                    pygame.draw.circle(overlay, (255, 255, 220, 255), (int(cx), int(cy)), 4)
                    pygame.draw.circle(overlay, (255, 170, 40, 190), (int(cx), int(cy)), 7)
                    for sp in fl.get('sparks', []):
                        sp[0] += sp[2]
                        sp[1] += sp[3]
                        s_alpha = max(0, int(220 * (1.0 - prog)))
                        pygame.draw.circle(overlay, (255, 210, 80, s_alpha), (int(sp[0]), int(sp[1])), 2)

            if overlay_needed:
                game_surface.blit(overlay, (0, 0))

            for m in bomber_hazard_markers:
                m_elapsed = now - m['born']
                if m_elapsed < m['duration']:
                    rem_sec = max(0.0, (m['duration'] - m_elapsed) / 1000.0)
                    warn_txt = shop_detail_font.render(f"BLAST ZONE [{rem_sec:.1f}s]", True, (255, 100, 80))
                    game_surface.blit(warn_txt, warn_txt.get_rect(center=(int(m['x']), int(m['y']) - m['radius'] - 10)))

        active_defense_flares = [fl for fl in active_defense_flares if now - fl['born'] < fl['duration'] + 120]

        player.draw(game_surface)
        for obj in bullets + enemies + enemy_bullets + explosions: obj.draw(game_surface)
        for sp in spark_particles:
            sp.draw(game_surface)
        # Telegraph: orange outline on any enemy that is in its attack animation window.
        for enemy in enemies:
            if now < enemy.attack_until:
                pygame.draw.rect(game_surface, (255, 145, 30), enemy.rect.inflate(8, 8), 2)
        for target in player.locked_targets:
            pygame.draw.rect(game_surface, (255, 205, 105), target.rect.inflate(14, 14), 1)

        for start, end, _created in chain_effects:
            pygame.draw.line(game_surface, (95, 235, 255), start, end, 3)
        # ── Feature 8: draw credit orbs & overclock pickups ──────────────
        for _orb in credit_orbs:
            _orb.draw(game_surface)
        for _op in overclock_pickups:
            _op.draw(game_surface)

        # ── Hybrid Scale: Blit 800x600 game surface to native display ──
        display.fill((6, 9, 16))
        scaled_game = pygame.transform.scale(game_surface, (int(GAME_WIDTH * SCALE_FACTOR), SCREEN_HEIGHT))
        shake_x, shake_y = 0, 0
        if frame_now < shake_until:
            shake_x = random.randint(-shake_intensity, shake_intensity)
            shake_y = random.randint(-shake_intensity, shake_intensity)
        display.blit(scaled_game, (OFFSET_X + shake_x, shake_y))

        # Pillarbox Borders
        if OFFSET_X > 0:
            pygame.draw.rect(display, (5, 7, 12), (0, 0, OFFSET_X, SCREEN_HEIGHT))
            pygame.draw.rect(display, (5, 7, 12), (OFFSET_X + int(GAME_WIDTH * SCALE_FACTOR), 0, SCREEN_WIDTH - (OFFSET_X + int(GAME_WIDTH * SCALE_FACTOR)), SCREEN_HEIGHT))
            pygame.draw.line(display, (20, 60, 95), (OFFSET_X, 0), (OFFSET_X, SCREEN_HEIGHT), 2)
            pygame.draw.line(display, (20, 60, 95), (OFFSET_X + int(GAME_WIDTH * SCALE_FACTOR), 0), (OFFSET_X + int(GAME_WIDTH * SCALE_FACTOR), SCREEN_HEIGHT), 2)

        for ft in floating_texts:
            ft.draw(display, label_font, offset=(OFFSET_X + shake_x, shake_y), scale=SCALE_FACTOR)

        # ── Native HD HUD ──
        hp_bar_x = OFFSET_X + int(10 * SCALE_FACTOR)
        hp_bar_y = int(10 * SCALE_FACTOR)
        hp_bar_w = int(200 * SCALE_FACTOR)
        hp_bar_h = int(20 * SCALE_FACTOR)
        pygame.draw.rect(display, (200, 0, 0), (hp_bar_x, hp_bar_y, int(hp_bar_w * max(0, player.hp / player.max_hp)), hp_bar_h))
        pygame.draw.rect(display, (255, 255, 255), (hp_bar_x, hp_bar_y, hp_bar_w, hp_bar_h), max(1, int(3 * SCALE_FACTOR)))

        hud_right = OFFSET_X + int(GAME_WIDTH * SCALE_FACTOR)

        if state in ("TUTORIAL", "TUTORIAL_COMBAT"):
            tutorial_ctrl.draw_tutorial_hud(display, theme, SCALE_FACTOR, CONFIG['keybinds'], friendly_key_name, now)
        else:
            score_label = label_font.render(f"SCORE {score}   BEST {high_score}", True, (220, 235, 255))
            display.blit(score_label, (hud_right - score_label.get_width() - int(14 * SCALE_FACTOR), int(14 * SCALE_FACTOR)))
            # Difficulty HUD badge
            cur_diff = save_data.get('difficulty', 'medium')
            badge_color = (100, 240, 150) if cur_diff == 'easy' else ((255, 105, 90) if cur_diff == 'hard' else (100, 220, 255))
            diff_badge = shop_detail_font.render(f"[{cur_diff.upper()}]", True, badge_color)
            display.blit(diff_badge, (hud_right - score_label.get_width() - diff_badge.get_width() - int(24 * SCALE_FACTOR), int(17 * SCALE_FACTOR)))
            encounter_label = director.encounter_label(now)
            if encounter_label:
                encounter_surface = shop_detail_font.render(encounter_label, True, (255, 215, 120))
                display.blit(encounter_surface, encounter_surface.get_rect(center=(SCREEN_WIDTH // 2, int(22 * SCALE_FACTOR))))

            # Darwinian Counter Adaptation Indicator
            if getattr(director.counter_engine, 'active_adaptation', None):
                ad = director.counter_engine.active_adaptation
                ad_surf = shop_detail_font.render(f"ARMADA DEFENSE: {ad['label']}", True, ad['color'])
                display.blit(ad_surf, ad_surf.get_rect(center=(SCREEN_WIDTH // 2, int(40 * SCALE_FACTOR))))

            # Alien Battle-Net Intercepted Comms Console
            active_comms = director.comms.get_active_messages(now)
            if active_comms:
                line_h = int(16 * SCALE_FACTOR)
                comms_h = len(active_comms) * line_h + int(18 * SCALE_FACTOR)
                comms_w = int(340 * SCALE_FACTOR)
                comms_surf = pygame.Surface((comms_w, comms_h), pygame.SRCALPHA)
                comms_surf.fill((6, 14, 28, 175))
                pygame.draw.rect(comms_surf, (30, 80, 120, 220), (0, 0, comms_w, comms_h), 1, border_radius=4)
                header_txt = shop_detail_font.render("— BATTLE-NET INTERCEPT —", True, (0, 220, 255))
                comms_surf.blit(header_txt, (int(8 * SCALE_FACTOR), int(3 * SCALE_FACTOR)))
                for c_idx, msg in enumerate(active_comms):
                    rem_ms = msg['expires_at'] - now
                    c_alpha = min(255, int(255 * min(1.0, rem_ms / 500)))
                    m_txt = shop_detail_font.render(f"[{msg['sender']}] {msg['text']}", True, msg['color'])
                    m_txt.set_alpha(c_alpha)
                    comms_surf.blit(m_txt, (int(8 * SCALE_FACTOR), int(18 * SCALE_FACTOR) + c_idx * line_h))
                display.blit(comms_surf, (OFFSET_X + int(12 * SCALE_FACTOR), SCREEN_HEIGHT - int(50 * SCALE_FACTOR) - comms_h))

        ammo_color = (255, 205, 110) if player.is_reloading else (230, 240, 255)
        ammo_label = label_font.render(player.reload_status(), True, ammo_color)
        ammo_panel = pygame.Rect(OFFSET_X + int(12 * SCALE_FACTOR), SCREEN_HEIGHT - int(44 * SCALE_FACTOR), ammo_label.get_width() + int(24 * SCALE_FACTOR), int(34 * SCALE_FACTOR))
        pygame.draw.rect(display, (8, 15, 32), ammo_panel, border_radius=5)
        pygame.draw.rect(display, (75, 115, 155), ammo_panel, 1, border_radius=5)
        display.blit(ammo_label, (ammo_panel.x + int(12 * SCALE_FACTOR), ammo_panel.y + int(5 * SCALE_FACTOR)))

        # In-Run Overdrive Timer Badges
        oc_badge_y = SCREEN_HEIGHT - int(74 * SCALE_FACTOR)
        if player.is_shield_overcharged:
            rem = max(0.0, (player.shield_overcharge_until - now) / 1000.0)
            txt = shop_detail_font.render(f"SHIELD SURGE {rem:.1f}s [{player.shield_overcharge_barrier}HP]", True, (100, 255, 140))
            display.blit(txt, (hud_right - txt.get_width() - int(14 * SCALE_FACTOR), oc_badge_y))
            oc_badge_y -= int(18 * SCALE_FACTOR)
        if player.is_engine_overclocked:
            rem = max(0.0, (player.engine_overclock_until - now) / 1000.0)
            txt = shop_detail_font.render(f"ENGINE OVERDRIVE {rem:.1f}s", True, (0, 230, 255))
            display.blit(txt, (hud_right - txt.get_width() - int(14 * SCALE_FACTOR), oc_badge_y))
            oc_badge_y -= int(18 * SCALE_FACTOR)
        if player.is_weapon_overclocked:
            rem = max(0.0, (player.weapon_overclock_until - now) / 1000.0)
            txt = shop_detail_font.render(f"WEAPON OVERDRIVE {rem:.1f}s", True, (255, 140, 40))
            display.blit(txt, (hud_right - txt.get_width() - int(14 * SCALE_FACTOR), oc_badge_y))
            oc_badge_y -= int(18 * SCALE_FACTOR)

        # Compact bottom-right ability indicators
        box_w = int(72 * SCALE_FACTOR)
        box_h = int(40 * SCALE_FACTOR)
        box_y = SCREEN_HEIGHT - int(52 * SCALE_FACTOR)

        shield_box = pygame.Rect(hud_right - box_w - int(12 * SCALE_FACTOR), box_y, box_w, box_h)
        pygame.draw.rect(display, (8, 15, 32), shield_box, border_radius=5)
        shield_icon = pygame.transform.smoothscale(player.emergency_shield_frames[0], (int(30 * SCALE_FACTOR), int(30 * SCALE_FACTOR)))
        display.blit(shield_icon, (shield_box.x + int(4 * SCALE_FACTOR), shield_box.y + int(5 * SCALE_FACTOR)))
        display.blit(shop_detail_font.render(str(save_data['invincibility_backups']), True, (255, 255, 255)), (shield_box.right - int(20 * SCALE_FACTOR), shield_box.y + int(12 * SCALE_FACTOR)))
        if player.emergency_invincible:
            timer_text = f"{max(0, (player.invincibility_until - now) / 1000):.1f}"
            display.blit(shop_detail_font.render(timer_text, True, (100, 235, 255)), (shield_box.x + int(9 * SCALE_FACTOR), shield_box.y - int(15 * SCALE_FACTOR)))

        engine_box = pygame.Rect(shield_box.x - box_w - int(12 * SCALE_FACTOR), box_y, box_w, box_h)
        pygame.draw.rect(display, (8, 15, 32), engine_box, border_radius=5)
        engine_icon = pygame.transform.smoothscale(player.engine_image, (int(34 * SCALE_FACTOR), int(34 * SCALE_FACTOR)))
        display.blit(engine_icon, (engine_box.x + int(2 * SCALE_FACTOR), engine_box.y + int(3 * SCALE_FACTOR)))
        if player.engine_ability:
            if now < player.engine_active_until:
                engine_badge, engine_color = "GO", (100, 235, 200)
            elif now >= player.engine_ready_at:
                engine_badge, engine_color = "OK", (120, 220, 255)
            else:
                engine_badge, engine_color = f"{(player.engine_ready_at - now) / 1000:.0f}", (185, 195, 215)
        else:
            engine_badge, engine_color = "-", (145, 155, 180)
        display.blit(shop_detail_font.render(engine_badge, True, engine_color), (engine_box.right - int(24 * SCALE_FACTOR), engine_box.y + int(12 * SCALE_FACTOR)))

        if player.shield_data:
            active_shield_box = pygame.Rect(engine_box.x - box_w - int(12 * SCALE_FACTOR), box_y, box_w, box_h)
            pygame.draw.rect(display, (8, 15, 32), active_shield_box, border_radius=5)
            pygame.draw.rect(display, (65, 105, 145), active_shield_box, 1, border_radius=5)
            active_shield_icon = pygame.transform.smoothscale(player.shield_frames[0], (int(30 * SCALE_FACTOR), int(30 * SCALE_FACTOR)))
            display.blit(active_shield_icon, (active_shield_box.x + int(3 * SCALE_FACTOR), active_shield_box.y + int(5 * SCALE_FACTOR)))
            if player.shield_active:
                shield_badge, shield_color = str(player.shield_remaining), (100, 235, 255)
            elif player.shield_remaining < player.shield_capacity:
                shield_badge = f"{max(0, (player.shield_ready_at - now) / 1000):.0f}"
                shield_color = (185, 195, 215)
            else:
                shield_badge, shield_color = "E", (120, 220, 255)
            display.blit(shop_detail_font.render(shield_badge, True, shield_color), (active_shield_box.right - int(27 * SCALE_FACTOR), active_shield_box.y + int(12 * SCALE_FACTOR)))

        if state == "PLAYING":
            # ── Feature 1: combo label ───────────────────────────────────────
            if combo >= 2 and now < combo_label_until:
                _alpha  = 255 if combo_label_until - now > 300 else int(255 * (combo_label_until - now) / 300)
                _cs = button_font.render(f"x{combo} COMBO!", True, (255, int(180 + combo * 5), 60))
                _cs.set_alpha(_alpha)
                display.blit(_cs, _cs.get_rect(center=(SCREEN_WIDTH // 2, int(55 * SCALE_FACTOR))))
            # ── Feature 5: streak label ──────────────────────────────────────
            if streak_label and now < streak_label_until:
                _ss = title_font.render(streak_label, True, (255, 220, 60))
                _ss.set_alpha(min(255, int(255 * (streak_label_until - now) / 600)))
                display.blit(_ss, _ss.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
            # ── Feature 3: boss-intro overlay ────────────────────────────────
            if now < boss_intro_until:
                _prog    = 1.0 - max(0, boss_intro_until - now) / 2500
                _flash_a = max(0, int(170 * math.sin(math.pi * _prog)))
                _overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                _overlay.fill((140 if 'VOID' in boss_intro_title else 180, 20, 100 if 'VOID' in boss_intro_title else 20, _flash_a))
                display.blit(_overlay, (0, 0))
                _bt = title_font.render(boss_intro_title, True, (255, 100, 140) if 'VOID' in boss_intro_title else (255, 80, 80))
                _bt.set_alpha(min(255, _flash_a * 2))
                display.blit(_bt, _bt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - int(30 * SCALE_FACTOR))))
                _bs = label_font.render(boss_intro_sub, True, (255, 210, 100))
                _bs.set_alpha(min(255, _flash_a * 2))
                display.blit(_bs, _bs.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + int(28 * SCALE_FACTOR))))

            # ── Fleet Transition Banner overlay ──────────────────────────────
            if now < getattr(director, 'fleet_banner_until', 0):
                rem = director.fleet_banner_until - now
                fade = min(255, int(255 * min(1.0, rem / 800) * min(1.0, (4200 - rem) / 600)))
                b_h = int(94 * SCALE_FACTOR)
                b_surf = pygame.Surface((SCREEN_WIDTH, b_h), pygame.SRCALPHA)
                b_surf.fill((6, 20, 42, int(fade * 0.84)))
                pygame.draw.line(b_surf, (0, 240, 255, fade), (0, 0), (SCREEN_WIDTH, 0), max(1, int(2 * SCALE_FACTOR)))
                pygame.draw.line(b_surf, (0, 240, 255, fade), (0, b_h - 1), (SCREEN_WIDTH, b_h - 1), max(1, int(2 * SCALE_FACTOR)))
                display.blit(b_surf, (0, SCREEN_HEIGHT // 2 - b_h // 2))

                t_surf = title_font.render(director.fleet_banner_title, True, (255, 220, 60))
                t_surf.set_alpha(fade)
                display.blit(t_surf, t_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - int(14 * SCALE_FACTOR))))

                s_surf = label_font.render(director.fleet_banner_sub, True, (120, 235, 255))
                s_surf.set_alpha(fade)
                display.blit(s_surf, s_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + int(20 * SCALE_FACTOR))))

    elif state == "PAUSED" and player is not None:
        scaled_game = pygame.transform.scale(game_surface, (int(GAME_WIDTH * SCALE_FACTOR), SCREEN_HEIGHT))
        display.blit(scaled_game, (OFFSET_X, 0))
        if OFFSET_X > 0:
            pygame.draw.rect(display, (5, 7, 12), (0, 0, OFFSET_X, SCREEN_HEIGHT))
            pygame.draw.rect(display, (5, 7, 12), (OFFSET_X + int(GAME_WIDTH * SCALE_FACTOR), 0, SCREEN_WIDTH - (OFFSET_X + int(GAME_WIDTH * SCALE_FACTOR)), SCREEN_HEIGHT))
            pygame.draw.line(display, (20, 60, 95), (OFFSET_X, 0), (OFFSET_X, SCREEN_HEIGHT), 2)
            pygame.draw.line(display, (20, 60, 95), (OFFSET_X + int(GAME_WIDTH * SCALE_FACTOR), 0), (OFFSET_X + int(GAME_WIDTH * SCALE_FACTOR), SCREEN_HEIGHT), 2)
        dim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dim.fill((5, 8, 22, 190))
        display.blit(dim, (0, 0))
        title = title_font.render("PAUSED", True, (255, 255, 255))
        display.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, int(190 * SCALE_FACTOR))))
        for name, label in [("resume", "Resume"), ("restart", "Restart"), ("menu", "Main Menu")]:
            rect = get_pause_buttons()[name]
            draw_button(display, rect, label, button_font, rect.collidepoint(mouse_pos))
        hint = label_font.render("ESC RESUME  |  R RESTART  |  M MAIN MENU", True, (160, 175, 205))
        display.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, int(500 * SCALE_FACTOR))))

    elif state == "GAME_OVER":
        scaled_game = pygame.transform.scale(game_surface, (int(GAME_WIDTH * SCALE_FACTOR), SCREEN_HEIGHT))
        display.blit(scaled_game, (OFFSET_X, 0))
        if OFFSET_X > 0:
            pygame.draw.rect(display, (5, 7, 12), (0, 0, OFFSET_X, SCREEN_HEIGHT))
            pygame.draw.rect(display, (5, 7, 12), (OFFSET_X + int(GAME_WIDTH * SCALE_FACTOR), 0, SCREEN_WIDTH - (OFFSET_X + int(GAME_WIDTH * SCALE_FACTOR)), SCREEN_HEIGHT))
            pygame.draw.line(display, (20, 60, 95), (OFFSET_X, 0), (OFFSET_X, SCREEN_HEIGHT), 2)
            pygame.draw.line(display, (20, 60, 95), (OFFSET_X + int(GAME_WIDTH * SCALE_FACTOR), 0), (OFFSET_X + int(GAME_WIDTH * SCALE_FACTOR), SCREEN_HEIGHT), 2)
        dim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dim.fill((5, 8, 22, 205))
        display.blit(dim, (0, 0))
        title = title_font.render("GAME OVER", True, (255, 90, 120))
        display.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, int(150 * SCALE_FACTOR))))
        final = label_font.render(f"FINAL SCORE: {score}", True, (255, 255, 255))
        display.blit(final, final.get_rect(center=(SCREEN_WIDTH // 2, int(215 * SCALE_FACTOR))))
        record = label_font.render(f"BEST SCORE: {high_score}", True, (100, 230, 255))
        display.blit(record, record.get_rect(center=(SCREEN_WIDTH // 2, int(248 * SCALE_FACTOR))))
        _cr_label = label_font.render(f"+{last_run_credits} CREDITS  |  WALLET {save_data['credits']}", True, (100, 235, 200))
        display.blit(_cr_label, _cr_label.get_rect(center=(SCREEN_WIDTH // 2, int(280 * SCALE_FACTOR))))
        cur_diff = save_data.get('difficulty', 'medium')
        diff_banner = f"DIFFICULTY: {cur_diff.upper()}" + ("  (+35% HARD BONUS!)" if cur_diff == 'hard' else "")
        diff_banner_color = (100, 240, 150) if cur_diff == 'easy' else ((255, 105, 90) if cur_diff == 'hard' else (100, 220, 255))
        diff_banner_surf = shop_detail_font.render(diff_banner, True, diff_banner_color)
        display.blit(diff_banner_surf, diff_banner_surf.get_rect(center=(SCREEN_WIDTH // 2, int(303 * SCALE_FACTOR))))
        # ── Feature 6: per-run stats ─────────────────────────────────────
        _secs   = max(0, (frame_now - run_start_time) // 1000) if run_start_time else 0
        _mins, _ss = divmod(_secs, 60)
        _acc    = (100 * director.hits // max(1, player.shots_fired)) if player else 0
        _stats  = [
            f"SURVIVED  {_mins}m {_ss:02d}s",
            f"KILLS  {total_run_kills}   ACCURACY  {_acc}%",
        ]
        # Show a compact breakdown of enemy types killed
        _type_parts = []
        _all_types = [
            'nairan_dreadnought', 'klaed_dreadnought', 'dreadnought',
            'nairan_battlecruiser', 'klaed_battlecruiser', 'battlecruiser',
            'nairan_frigate', 'klaed_frigate', 'frigate',
            'nairan_bomber', 'klaed_bomber', 'bomber',
            'nairan_torpedo', 'klaed_torpedo', 'torpedo',
            'nairan_support', 'klaed_support', 'support',
            'nairan_fighter', 'klaed_fighter', 'fighter',
            'nairan_scout', 'klaed_scout', 'scout', 'asteroid'
        ]
        for _ename in _all_types:
            if run_kills_by_type.get(_ename, 0):
                if _ename.startswith('nairan_'):
                    _tag = 'N-' + _ename[7:10].upper()
                elif _ename.startswith('klaed_'):
                    _tag = 'K-' + _ename[6:9].upper()
                else:
                    _tag = _ename[:3].upper()
                _type_parts.append(f"{_tag} {run_kills_by_type[_ename]}")
        if _type_parts:
            _stats.append("  ".join(_type_parts))
        # AI Black Box Tactical Debrief
        debrief = director.generate_debrief(player, score, frame_now)
        deb_w = int(460 * SCALE_FACTOR)
        deb_h = int(76 * SCALE_FACTOR)
        deb_box = pygame.Rect(SCREEN_WIDTH // 2 - deb_w // 2, int(324 * SCALE_FACTOR), deb_w, deb_h)
        deb_surf = pygame.Surface((deb_w, deb_h), pygame.SRCALPHA)
        deb_surf.fill((6, 14, 28, 215))
        pygame.draw.rect(deb_surf, (0, 220, 255, 190), (0, 0, deb_w, deb_h), 1, border_radius=4)
        deb_title = shop_detail_font.render(f"— AI TACTICAL DEBRIEF // [{debrief['archetype']}] —", True, (0, 235, 255))
        deb_surf.blit(deb_title, (int(10 * SCALE_FACTOR), int(5 * SCALE_FACTOR)))
        deb_line1 = shop_detail_font.render(f"VULNERABILITY: {debrief['primary_vulnerability']}", True, (255, 215, 120))
        deb_surf.blit(deb_line1, (int(10 * SCALE_FACTOR), int(23 * SCALE_FACTOR)))
        deb_line2 = shop_detail_font.render(f"ARMADA COUNTER: {debrief['counter_deployed']}  |  PLANS EVAL: {debrief['plans_evaluated']}", True, (170, 205, 240))
        deb_surf.blit(deb_line2, (int(10 * SCALE_FACTOR), int(40 * SCALE_FACTOR)))
        deb_line3 = shop_detail_font.render(f"NOTE: {debrief['note']}", True, (130, 165, 200))
        deb_surf.blit(deb_line3, (int(10 * SCALE_FACTOR), int(57 * SCALE_FACTOR)))
        display.blit(deb_surf, deb_box.topleft)

        for name, label in [("restart", "Play Again"), ("menu", "Main Menu")]:
            rect = get_game_over_buttons()[name]
            draw_button(display, rect, label, button_font, rect.collidepoint(mouse_pos))
        hint = label_font.render("ENTER / R PLAY AGAIN  |  ESC MAIN MENU", True, (160, 175, 205))
        display.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, int(474 * SCALE_FACTOR))))

    # ── Tutorial RPG Dialogue Box Overlay ───────────────────────────────
    if tutorial_ctrl.state in ("INTRO_DIALOGUE", "DEBRIEF_DIALOGUE", "GOODBYE_DIALOGUE", "POST_DIALOGUE"):
        tutorial_ctrl.draw_dialogue_box(display, theme, SCALE_FACTOR, frame_now)

    # ── Feature 10: developer overlay (F3) ──────────────────────────────
    if dev_overlay:
        _ctx  = director._context(player) if player and state == "PLAYING" else "n/a"
        _fleet_name = FLEET_NAMES.get(getattr(director, 'fleet_phase', 0), "UNKNOWN")
        _stage_name = STAGE_NAMES.get(getattr(director, 'stage', 0), "UNKNOWN")
        _boss_status = "ACTIVE" if getattr(director, 'boss_active', False) else ("READY" if getattr(director, 'stage', 0) == 4 else f"STAGE {getattr(director, 'stage', 0)}/4")
        _corridor_pct = int(getattr(director.synthesizer, 'last_corridor_ratio', 0.40) * 100)
        _panic = int(director.profiler.panic_index * 100)
        _flow = int(director.profiler.flow_index * 100)
        _lines = [
            f"FPS {clock.get_fps():.0f}  |  Aegis-Fable Engine v5.1",
            f"Fleet: {_fleet_name} [{_stage_name}]",
            f"Formation: {getattr(director, 'last_formation', 'N/A')}  |  Plans Evaluated: {getattr(director.synthesizer, 'simulated_count', 0)}",
            f"Corridor Fair-Play: {_corridor_pct}% Escape Lane",
            f"Cognitive Index: Panic={_panic}% | Flow={_flow}%",
            f"Boss Gate: {_boss_status}  (Phase Kills: {getattr(director, 'kills_in_phase', 0)})",
            f"Telemetry: {_ctx}",
            f"Active Wave: {director.last_encounter_name}  (Total #{director.total_encounters})",
            f"Enemies: {len(enemies)}/6  |  Total Bosses Defeated: {director.bosses_defeated}",
        ]
        ov_w = int(390 * SCALE_FACTOR)
        line_step = int(18 * SCALE_FACTOR)
        ov_h = len(_lines) * line_step + int(14 * SCALE_FACTOR)
        _bg = pygame.Surface((ov_w, ov_h), pygame.SRCALPHA)
        _bg.fill((0, 0, 0, 190))
        display.blit(_bg, (OFFSET_X + int(4 * SCALE_FACTOR), int(30 * SCALE_FACTOR)))
        for _li, _ln in enumerate(_lines):
            _ls = shop_detail_font.render(_ln, True, (140, 255, 120))
            display.blit(_ls, (OFFSET_X + int(8 * SCALE_FACTOR), int(34 * SCALE_FACTOR) + _li * line_step))

        # Real-time Neural Heatmap Ribbon (Player Flight Corridor)
        if state == "PLAYING" and player:
            lane_w = int(GAME_WIDTH * SCALE_FACTOR)
            _hmap = pygame.Surface((lane_w, int(14 * SCALE_FACTOR)), pygame.SRCALPHA)
            _hmap.fill((10, 25, 45, 110))
            _corr_w = int(lane_w * getattr(director.synthesizer, 'last_corridor_ratio', 0.40))
            _corr_x = (lane_w - _corr_w) // 2
            pygame.draw.rect(_hmap, (0, 240, 255, 60), (_corr_x, 0, _corr_w, int(14 * SCALE_FACTOR)))
            pygame.draw.rect(_hmap, (0, 240, 255, 140), (_corr_x, 0, _corr_w, int(14 * SCALE_FACTOR)), 1)
            px = int(player.rect.centerx * SCALE_FACTOR)
            pygame.draw.circle(_hmap, (255, 220, 60, 220), (px, int(7 * SCALE_FACTOR)), max(2, int(4 * SCALE_FACTOR)))
            display.blit(_hmap, (OFFSET_X, SCREEN_HEIGHT - int(24 * SCALE_FACTOR)))

    pygame.display.flip()
    clock.tick(60)

if __name__ == '__main__':
    pygame.quit()
    sys.exit()
