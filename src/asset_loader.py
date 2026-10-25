import pygame
import os
import sys
from pathlib import Path

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    PROJECT_ROOT = Path(sys._MEIPASS)
else:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent

def asset_path(filename):
    return PROJECT_ROOT / filename

def load_sound(path):
    class DummySound:
        def play(self): pass
        def set_volume(self, vol): pass
    if not os.path.exists(path): return DummySound()
    try: return pygame.mixer.Sound(path)
    except Exception: return DummySound()

def slice_spritesheet(path, num_frames):
    try:
        if num_frames < 1:
            raise ValueError("num_frames must be at least 1")
        sheet = pygame.image.load(str(path))
        try:
            sheet = sheet.convert_alpha()
        except pygame.error:
            pass
        w, h = sheet.get_size()
        fw = w // num_frames
        if fw < 1:
            raise ValueError("spritesheet is narrower than its frame count")
        return [sheet.subsurface((i * fw, 0, fw, h)).copy() for i in range(num_frames)]
    except Exception:
        surf = pygame.Surface((32, 32))
        surf.fill((255, 0, 255))
        return [surf] * num_frames

def load_image(path):
    try:
        img = pygame.image.load(str(path))
        try:
            return img.convert_alpha()
        except pygame.error:
            return img
    except Exception:
        surf = pygame.Surface((32, 32))
        surf.fill((255, 0, 255))
        return surf

def load_enemy_image(path):
    """Nautolan source art faces upward; enemies approach from the top."""
    return pygame.transform.rotate(load_image(path), 180)

def load_enemy_frames(path, frame_count):
    return [pygame.transform.rotate(frame, 180) for frame in slice_spritesheet(path, frame_count)]

def _strip_outer_white_background(surf: pygame.Surface) -> pygame.Surface:
    w, h = surf.get_size()
    clean = pygame.Surface((w, h), pygame.SRCALPHA)
    clean.blit(surf, (0, 0))
    visited = bytearray(w * h)
    from collections import deque
    q = deque()
    for x in range(w):
        q.append((x, 0))
        q.append((x, h - 1))
    for y in range(h):
        q.append((0, y))
        q.append((w - 1, y))
    while q:
        cx, cy = q.popleft()
        idx = cy * w + cx
        if visited[idx]:
            continue
        visited[idx] = 1
        r, g, b, a = clean.get_at((cx, cy))
        if a > 0 and r > 230 and g > 230 and b > 230:
            clean.set_at((cx, cy), (0, 0, 0, 0))
            if cx > 0: q.append((cx - 1, cy))
            if cx < w - 1: q.append((cx + 1, cy))
            if cy > 0: q.append((cx, cy - 1))
            if cy < h - 1: q.append((cx, cy + 1))
    return clean

def _create_fallback_astronaut_portrait(pose='hello') -> pygame.Surface:
    surf = pygame.Surface((160, 160), pygame.SRCALPHA)
    pygame.draw.circle(surf, (15, 30, 55), (80, 80), 65)
    pygame.draw.circle(surf, (220, 235, 255), (80, 75), 52)
    pygame.draw.ellipse(surf, (20, 45, 80), (45, 50, 70, 50))
    pygame.draw.ellipse(surf, (255, 195, 45), (52, 58, 56, 32))
    if pose == 'thumbs_up':
        pygame.draw.circle(surf, (220, 235, 255), (135, 110), 16)
        pygame.draw.rect(surf, (220, 235, 255), (128, 85, 14, 25), border_radius=4)
    elif pose == 'talking':
        pygame.draw.ellipse(surf, (15, 30, 55), (70, 72, 20, 12))
    return surf

def load_astronaut_portrait(filename: str, pose='hello') -> pygame.Surface:
    paths = [
        asset_path(f"assets/{filename}"),
        asset_path(filename),
    ]
    found_path = next((p for p in paths if os.path.exists(p)), None)
    if not found_path:
        return _create_fallback_astronaut_portrait(pose)
    try:
        raw = pygame.image.load(str(found_path))
        surf = pygame.Surface(raw.get_size(), pygame.SRCALPHA)
        surf.blit(raw, (0, 0))
        scaled = pygame.transform.smoothscale(surf, (160, 160))
        return _strip_outer_white_background(scaled)
    except Exception:
        return _create_fallback_astronaut_portrait(pose)

def load_assets(screen_size=(800, 600)):
    try:
        pygame.mixer.init()
    except pygame.error:
        # Audio devices are optional; the game remains playable without sound.
        pass
    # ── Curated Environment Assets (Foozle 2DS0015) ─────────────────────
    void_path = asset_path('assets/environment/bg_void.png')
    if not os.path.exists(void_path):
        void_path = asset_path('assets/bg_void.png')
    stars_path = asset_path('assets/environment/bg_stars.png')
    if not os.path.exists(stars_path):
        stars_path = asset_path('assets/bg_stars.png')

    sw, sh = screen_size
    try:
        void_orig = load_image(void_path)
        stars_orig = load_image(stars_path)
        void_w = int(void_orig.get_width() * (sh / max(1, void_orig.get_height())))
        stars_w = int(stars_orig.get_width() * (sh / max(1, stars_orig.get_height())))
        bg_void = pygame.transform.scale(void_orig, (max(sw, void_w), sh))
        bg_stars = pygame.transform.scale(stars_orig, (max(sw, stars_w), sh))
    except Exception:
        bg_void = pygame.Surface((sw, sh))
        bg_stars = pygame.Surface((sw, sh))

    # Celestial Landmarks (Drifting down at 0.15 speed)
    planet_path = asset_path('assets/environment/Earth-Like planet.png')
    bg_planet_frames = slice_spritesheet(planet_path, 77)
    bg_planet = [pygame.transform.smoothscale(f, (150, 150)) for f in bg_planet_frames]

    black_hole_path = asset_path('assets/environment/black_hole.png')
    bg_black_hole_frames = slice_spritesheet(black_hole_path, 16)
    bg_black_hole = [pygame.transform.smoothscale(f, (220, 220)) for f in bg_black_hole_frames]

    # Asteroid Flame & Rock Explosion
    flame_path = asset_path('assets/environment/Asteroid - Flame.png')
    asteroid_flame = slice_spritesheet(flame_path, 3)

    rock_exp_path = asset_path('assets/environment/Asteroid 01 - Explode.png')
    asteroid_explosion = slice_spritesheet(rock_exp_path, 8)

    # ── Curated Pickups (Foozle 2DS0016) ─────────────────────────────────
    pickup_weapons = {
        'auto_cannon': slice_spritesheet(asset_path('assets/pickups/pickup_auto_cannon.png'), 15),
        'big_space_gun': slice_spritesheet(asset_path('assets/pickups/pickup_big_space_gun.png'), 15),
        'rockets': slice_spritesheet(asset_path('assets/pickups/pickup_rockets.png'), 15),
        'zapper': slice_spritesheet(asset_path('assets/pickups/pickup_zapper.png'), 15),
    }
    pickup_engines = {
        'base': slice_spritesheet(asset_path('assets/pickups/pickup_engine_base.png'), 15),
        'big_pulse': slice_spritesheet(asset_path('assets/pickups/pickup_engine_big_pulse.png'), 15),
        'burst': slice_spritesheet(asset_path('assets/pickups/pickup_engine_burst.png'), 15),
        'supercharged': slice_spritesheet(asset_path('assets/pickups/pickup_engine_supercharged.png'), 15),
    }
    pickup_shields = {
        'front': slice_spritesheet(asset_path('assets/pickups/pickup_shield_front.png'), 15),
        'front_side': slice_spritesheet(asset_path('assets/pickups/pickup_shield_front_side.png'), 15),
        'round': slice_spritesheet(asset_path('assets/pickups/pickup_shield_round.png'), 15),
        'invincibility': slice_spritesheet(asset_path('assets/pickups/pickup_shield_invincibility.png'), 15),
    }

    # Synthesize The Shadow Interceptor (Neural Mirror Clone)
    player_ship_base = load_image(asset_path('assets/player.png'))
    shadow_surf = pygame.transform.rotate(player_ship_base, 180).copy()
    shadow_tint = pygame.Surface(shadow_surf.get_size(), pygame.SRCALPHA)
    shadow_tint.fill((190, 50, 240, 255))
    shadow_surf.blit(shadow_tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    pygame.draw.circle(shadow_surf, (0, 240, 255, 180), (shadow_surf.get_width() // 2, shadow_surf.get_height() // 2), 4, 1)

    weapon_specs = {
        'auto_cannon': {'name': 'Auto Cannon', 'frames': 7, 'projectile': 'Auto cannon bullet', 'projectile_frames': 4, 'cooldown': 140, 'speed': 10, 'damage': 1, 'magazine': 20, 'reload_ms': 1100},
        'big_space_gun': {'name': 'Big Space Gun', 'frames': 12, 'projectile': 'Big Space Gun', 'projectile_frames': 10, 'cooldown': 520, 'speed': 9, 'damage': 4, 'magazine': 5, 'reload_ms': 1750, 'pierce': 1},
        'rockets': {'name': 'Rocket Launcher', 'frames': 17, 'projectile': 'Rocket', 'projectile_frames': 3, 'cooldown': 750, 'speed': 7, 'damage': 4, 'magazine': 9, 'reload_ms': 2100, 'salvo': 3, 'lock_range': 430},
        'zapper': {'name': 'Zapper', 'frames': 14, 'projectile': 'Zapper', 'projectile_frames': 8, 'cooldown': 280, 'speed': 10, 'damage': 2, 'magazine': 12, 'reload_ms': 1450, 'chain_range': 125, 'chain_count': 2},
    }
    weapons = {}
    for item_id, spec in weapon_specs.items():
        weapons[item_id] = {
            **spec,
            'frames': slice_spritesheet(asset_path(f"assets/Main Ship - Weapons - {spec['name'].replace('Rocket Launcher', 'Rockets')}.png"), spec['frames']),
            'projectile': slice_spritesheet(asset_path(f"assets/Main ship weapon - Projectile - {spec['projectile']}.png"), spec['projectile_frames'])[0],
        }

    engines = {
        'base': {'name': 'Base Engine', 'image': load_image(asset_path('assets/Main Ship - Engines - Base Engine.png')), 'speed': 5, 'ability': None},
        'big_pulse': {'name': 'Big Pulse Engine', 'image': load_image(asset_path('assets/Main Ship - Engines - Big Pulse Engine.png')), 'speed': 5.7, 'ability': {'name': 'Pulse Dash', 'duration': 380, 'cooldown': 3000, 'speed_multiplier': 3.0, 'fire_rate_multiplier': 1.0}},
        'burst': {'name': 'Burst Engine', 'image': load_image(asset_path('assets/Main Ship - Engines - Burst Engine.png')), 'speed': 6.5, 'ability': {'name': 'Afterburner', 'duration': 1500, 'cooldown': 6000, 'speed_multiplier': 1.9, 'fire_rate_multiplier': 1.0}},
        'supercharged': {'name': 'Supercharged Engine', 'image': load_image(asset_path('assets/Main Ship - Engines - Supercharged Engine.png')), 'speed': 7.5, 'ability': {'name': 'Overdrive', 'duration': 2400, 'cooldown': 8000, 'speed_multiplier': 1.0, 'fire_rate_multiplier': 0.45}},
    }

    shields = {
        'front': {'name': 'Front Shield', 'frames': slice_spritesheet(asset_path('assets/Main Ship - Shields - Front Shield.png'), 10), 'capacity': 30, 'cooldown_ms': 10000},
        'front_side': {'name': 'Front & Side Shield', 'frames': slice_spritesheet(asset_path('assets/Main Ship - Shields - Front and Side Shield.png'), 6), 'capacity': 45, 'cooldown_ms': 13000},
        'round': {'name': 'Round Shield', 'frames': slice_spritesheet(asset_path('assets/Main Ship - Shields - Round Shield.png'), 12), 'capacity': 65, 'cooldown_ms': 16000},
        'invincibility': {'name': 'Invincibility Shield', 'frames': slice_spritesheet(asset_path('assets/Main Ship - Shields - Invincibility Shield.png'), 10), 'mitigation': 1.0},
    }

    music_names = [
        'bgm_1.mp3', 'bgm_2.mp3', 'BRACE_FOR_IMPACT.mp3', 'Cataclysm_at_Midnight.mp3',
        'G_Force_Rampage.mp3', 'Gravity_Burn.mp3', 'Intercepting_The_Fleet.mp3',
        'Interceptor_Glide.mp3', 'Kinetic_Breach.mp3', 'Starfire_Interceptor.mp3',
        'Through_the_Amber_Haze.mp3', 'Velocity_Lock.mp3',
    ]

    return {
        'player_states': {
            'full': load_image(asset_path('assets/Main Ship - Base - Full health.png')),
            'slight': load_image(asset_path('assets/Main Ship - Base - Slight damage.png')),
            'damaged': load_image(asset_path('assets/Main Ship - Base - Damaged.png')),
            'very_damaged': load_image(asset_path('assets/Main Ship - Base - Very damaged.png')),
        },
        'weapons': weapons,
        'engines': engines,
        'shields': shields,
        'bullet': load_image(asset_path('assets/bullet.png')),
        'enemy_projectiles': {
            'bullet': slice_spritesheet(asset_path('assets/Nautolan - Bullet.png'), 8),
            'bomb': slice_spritesheet(asset_path('assets/Nautolan - Bomb.png'), 16),
            'rocket': slice_spritesheet(asset_path('assets/Nautolan - Rocket.png'), 3),
            'spinning': slice_spritesheet(asset_path('assets/Nautolan - Spinning Bullet.png'), 8),
            'ray': slice_spritesheet(asset_path('assets/Nautolan - Ray.png'), 6),
            'wave': slice_spritesheet(asset_path('assets/Nautolan - Wave.png'), 6),
            # Kla'ed void fleet projectiles
            'klaed_bullet': slice_spritesheet(asset_path("assets/Kla'ed - Bullet.png"), 1),
            'klaed_big_bullet': slice_spritesheet(asset_path("assets/Kla'ed - Big Bullet.png"), 2),
            'klaed_ray': slice_spritesheet(asset_path("assets/Kla'ed - Ray.png"), 4),
            'klaed_torpedo': slice_spritesheet(asset_path("assets/Kla'ed - Torpedo.png"), 3),
            'klaed_wave': slice_spritesheet(asset_path("assets/Kla'ed - Wave.png"), 6),
            # Nairan cyber fleet projectiles
            'nairan_bolt': slice_spritesheet(asset_path("assets/Nairan - Bolt.png"), 5),
            'nairan_ray': slice_spritesheet(asset_path("assets/Nairan - Ray.png"), 4),
            'nairan_rocket': slice_spritesheet(asset_path("assets/Nairan - Rocket.png"), 3),
            'nairan_torpedo': slice_spritesheet(asset_path("assets/Nairan - Torpedo.png"), 3),
        },
        'bg_void': bg_void,
        'bg_stars': bg_stars,
        'sfx': {
            # Generic fallback shoot (used as auto-cannon sound)
            'player_shoot': load_sound(asset_path('assets/autocanon_gunshot.mp3')),
            # Per-weapon shoot sounds
            'shoot_auto_cannon':   load_sound(asset_path('assets/autocanon_gunshot.mp3')),
            'shoot_big_space_gun': load_sound(asset_path('assets/sfx_big_space_gun.wav')),
            'shoot_rockets':       load_sound(asset_path('assets/sfx_rockets.wav')),
            'shoot_zapper':        load_sound(asset_path('assets/sfx_zapper.wav')),
            # Feedback sounds
            'boss_alert':    load_sound(asset_path('assets/sfx_boss_alert.wav')),
            'combo':         load_sound(asset_path('assets/sfx_combo.wav')),
            'credit_pickup': load_sound(asset_path('assets/sfx_credit_pickup.wav')),
            'streak':        load_sound(asset_path('assets/sfx_streak.wav')),
            # Existing sounds
            'enemy_shoot': load_sound(asset_path('assets/enemy_laser.wav')),
            'explosion': load_sound(asset_path('assets/explosion.wav')),
            'click': load_sound(asset_path('assets/mouse_click.wav')),
            'go_funny': load_sound(asset_path('assets/funny_system_breakdown.wav')),
            'go_fast': load_sound(asset_path('assets/fast_game_over.wav')),
            'go_good': load_sound(asset_path('assets/space_shooter_dead.wav')),
        },
        'bgm_playlist': [asset_path(f'assets/{name}') for name in music_names],
        'enemy_types': [
            {'name': 'asteroid', 'hp': 5, 'score_value': 10, 'ship': load_image(asset_path('assets/asteroid.png')), 'explosion': asteroid_explosion, 'flame': asteroid_flame},
            {'name': 'scout', 'hp': 2, 'score_value': 10, 'ship': load_image(asset_path('assets/alien_scout.png')), 'explosion': slice_spritesheet(asset_path('assets/alien_scout_explosion.png'), 9)},
            {'name': 'fighter', 'hp': 3, 'score_value': 15, 'ship': load_image(asset_path('assets/alien_fighter.png')), 'explosion': slice_spritesheet(asset_path('assets/alien_fighter_explosion.png'), 9)},
            {'name': 'bomber', 'hp': 10, 'score_value': 25, 'ship': load_enemy_frames(asset_path('assets/Nautolan Ship - Bomber.png'), 10)[0], 'idle_frames': [load_enemy_frames(asset_path('assets/Nautolan Ship - Bomber.png'), 10)[0]], 'attack_frames': load_enemy_frames(asset_path('assets/Nautolan Ship - Bomber.png'), 10), 'explosion': slice_spritesheet(asset_path('assets/explosion.png'), 8), 'contact_damage': 12},
            {'name': 'torpedo', 'hp': 8, 'score_value': 25, 'ship': load_enemy_image(asset_path('assets/Nautolan Ship - Torpedo Ship.png')), 'idle_frames': [load_enemy_image(asset_path('assets/Nautolan Ship - Torpedo Ship.png'))], 'attack_frames': load_enemy_frames(asset_path('assets/Nautolan Ship - Torpedo Ship - Weapons.png'), 16), 'attack_overlay': True, 'explosion': slice_spritesheet(asset_path('assets/explosion.png'), 8), 'contact_damage': 14},
            {'name': 'support', 'hp': 7, 'score_value': 20, 'ship': load_enemy_frames(asset_path('assets/Nautolan Ship - Support.png'), 8)[0], 'idle_frames': [load_enemy_frames(asset_path('assets/Nautolan Ship - Support.png'), 8)[0]], 'attack_frames': load_enemy_frames(asset_path('assets/Nautolan Ship - Support.png'), 8), 'explosion': slice_spritesheet(asset_path('assets/explosion.png'), 8), 'contact_damage': 8},
            {'name': 'frigate', 'hp': 18, 'score_value': 35, 'ship': load_enemy_image(asset_path('assets/Nautolan Ship - Frigate - Base.png')), 'idle_frames': [load_enemy_image(asset_path('assets/Nautolan Ship - Frigate - Base.png'))], 'attack_frames': load_enemy_frames(asset_path('assets/Nautolan Ship - Frigate - Weapons.png'), 9), 'attack_overlay': True, 'explosion': slice_spritesheet(asset_path('assets/explosion.png'), 8), 'contact_damage': 18},
            {'name': 'battlecruiser', 'hp': 42, 'score_value': 60, 'ship': load_enemy_image(asset_path('assets/Nautolan Ship - Battlecruiser - Base.png')), 'idle_frames': [load_enemy_image(asset_path('assets/Nautolan Ship - Battlecruiser - Base.png'))], 'attack_frames': load_enemy_frames(asset_path('assets/Nautolan Ship - Battlecruiser - Weapons.png'), 9), 'attack_overlay': True, 'explosion': slice_spritesheet(asset_path('assets/explosion.png'), 8), 'contact_damage': 25},
            {'name': 'dreadnought', 'hp': 260, 'score_value': 150, 'ship': load_enemy_image(asset_path('assets/Nautolan Ship - Dreadnought - Base.png')), 'idle_frames': [load_enemy_image(asset_path('assets/Nautolan Ship - Dreadnought - Base.png'))], 'attack_frames': load_enemy_frames(asset_path('assets/Nautolan Ship - Dreadnought - Weapons.png'), 35), 'attack_overlay': True, 'explosion': slice_spritesheet(asset_path('assets/explosion.png'), 8), 'contact_damage': 35},
            # ── Kla'ed Void Fleet ───────────────────────────────────────────────
            {'name': 'klaed_scout', 'hp': 3, 'score_value': 15,
             'ship': load_enemy_image(asset_path("assets/Kla'ed - Scout - Base.png")),
             'idle_frames': [load_enemy_image(asset_path("assets/Kla'ed - Scout - Base.png"))],
             'attack_frames': load_enemy_frames(asset_path("assets/Kla'ed - Scout - Weapons.png"), 6),
             'attack_overlay': True,
             'explosion': load_enemy_frames(asset_path("assets/Kla'ed - Scout - Destruction.png"), 10),
             'contact_damage': 6},
            {'name': 'klaed_fighter', 'hp': 5, 'score_value': 20,
             'ship': load_enemy_image(asset_path("assets/Kla'ed - Fighter - Base.png")),
             'idle_frames': [load_enemy_image(asset_path("assets/Kla'ed - Fighter - Base.png"))],
             'attack_frames': load_enemy_frames(asset_path("assets/Kla'ed - Fighter - Weapons.png"), 6),
             'attack_overlay': True,
             'explosion': load_enemy_frames(asset_path("assets/Kla'ed - Fighter - Destruction.png"), 9),
             'contact_damage': 8},
            {'name': 'klaed_torpedo', 'hp': 12, 'score_value': 30,
             'ship': load_enemy_image(asset_path("assets/Kla'ed - Torpedo Ship - Base.png")),
             'idle_frames': [load_enemy_image(asset_path("assets/Kla'ed - Torpedo Ship - Base.png"))],
             'attack_frames': load_enemy_frames(asset_path("assets/Kla'ed - Torpedo Ship - Weapons.png"), 16),
             'attack_overlay': True,
             'explosion': load_enemy_frames(asset_path("assets/Kla'ed - Torpedo Ship - Destruction.png"), 10),
             'contact_damage': 14},
            {'name': 'klaed_bomber', 'hp': 16, 'score_value': 35,
             'ship': load_enemy_image(asset_path("assets/Kla'ed - Bomber - Base.png")),
             'idle_frames': [load_enemy_image(asset_path("assets/Kla'ed - Bomber - Base.png"))],
             'attack_frames': [load_enemy_image(asset_path("assets/Kla'ed - Bomber - Base.png"))],
             'explosion': load_enemy_frames(asset_path("assets/Kla'ed - Bomber - Destruction.png"), 8),
             'contact_damage': 16},
            {'name': 'klaed_support', 'hp': 10, 'score_value': 25,
             'ship': load_enemy_image(asset_path("assets/Kla'ed - Support ship - Base.png")),
             'idle_frames': [load_enemy_image(asset_path("assets/Kla'ed - Support ship - Base.png"))],
             'attack_frames': [load_enemy_image(asset_path("assets/Kla'ed - Support ship - Base.png"))],
             'explosion': load_enemy_frames(asset_path("assets/Kla'ed - Support ship - Destruction.png"), 10),
             'contact_damage': 10},
            {'name': 'klaed_frigate', 'hp': 26, 'score_value': 50,
             'ship': load_enemy_image(asset_path("assets/Kla'ed - Frigate - Base.png")),
             'idle_frames': [load_enemy_image(asset_path("assets/Kla'ed - Frigate - Base.png"))],
             'attack_frames': load_enemy_frames(asset_path("assets/Kla'ed - Frigate - Weapons.png"), 6),
             'attack_overlay': True,
             'explosion': load_enemy_frames(asset_path("assets/Kla'ed - Frigate - Destruction.png"), 9),
             'contact_damage': 20},
            {'name': 'klaed_battlecruiser', 'hp': 65, 'score_value': 90,
             'ship': load_enemy_image(asset_path("assets/Kla'ed - Battlecruiser - Base.png")),
             'idle_frames': [load_enemy_image(asset_path("assets/Kla'ed - Battlecruiser - Base.png"))],
             'attack_frames': load_enemy_frames(asset_path("assets/Kla'ed - Battlecruiser - Weapons.png"), 30),
             'attack_overlay': True,
             'explosion': load_enemy_frames(asset_path("assets/Kla'ed - Battlecruiser - Destruction.png"), 14),
             'contact_damage': 30},
            {'name': 'klaed_dreadnought', 'hp': 320, 'score_value': 250,
             'ship': load_enemy_image(asset_path("assets/Kla'ed - Dreadnought - Base.png")),
             'idle_frames': [load_enemy_image(asset_path("assets/Kla'ed - Dreadnought - Base.png"))],
             'attack_frames': load_enemy_frames(asset_path("assets/Kla'ed - Dreadnought - Weapons.png"), 60),
             'attack_overlay': True,
             'explosion': load_enemy_frames(asset_path("assets/Kla'ed - Dreadnought - Destruction.png"), 12),
             'contact_damage': 40},
            # ── Nairan Cyber Fleet ──────────────────────────────────────────────
            {'name': 'nairan_scout', 'hp': 4, 'score_value': 15,
             'ship': load_enemy_image(asset_path("assets/Nairan - Scout - Base.png")),
             'idle_frames': [load_enemy_image(asset_path("assets/Nairan - Scout - Base.png"))],
             'attack_frames': load_enemy_frames(asset_path("assets/Nairan - Scout - Weapons.png"), 6),
             'attack_overlay': True,
             'explosion': load_enemy_frames(asset_path("assets/Nairan - Scout - Destruction.png"), 16),
             'contact_damage': 6},
            {'name': 'nairan_fighter', 'hp': 6, 'score_value': 20,
             'ship': load_enemy_image(asset_path("assets/Nairan - Fighter - Base.png")),
             'idle_frames': [load_enemy_image(asset_path("assets/Nairan - Fighter - Base.png"))],
             'attack_frames': load_enemy_frames(asset_path("assets/Nairan - Fighter - Weapons.png"), 28),
             'attack_overlay': True,
             'explosion': load_enemy_frames(asset_path("assets/Nairan - Fighter - Destruction.png"), 18),
             'contact_damage': 8},
            {'name': 'nairan_torpedo', 'hp': 14, 'score_value': 30,
             'ship': load_enemy_image(asset_path("assets/Nairan - Torpedo Ship - Base.png")),
             'idle_frames': [load_enemy_image(asset_path("assets/Nairan - Torpedo Ship - Base.png"))],
             'attack_frames': load_enemy_frames(asset_path("assets/Nairan - Torpedo Ship - Weapons.png"), 12),
             'attack_overlay': True,
             'explosion': load_enemy_frames(asset_path("assets/Nairan - Torpedo Ship - Destruction.png"), 16),
             'contact_damage': 14},
            {'name': 'nairan_bomber', 'hp': 18, 'score_value': 35,
             'ship': load_enemy_image(asset_path("assets/Nairan - Bomber - Base.png")),
             'idle_frames': [load_enemy_image(asset_path("assets/Nairan - Bomber - Base.png"))],
             'attack_frames': [load_enemy_image(asset_path("assets/Nairan - Bomber - Base.png"))],
             'explosion': load_enemy_frames(asset_path("assets/Nairan - Bomber - Destruction.png"), 16),
             'contact_damage': 16},
            {'name': 'nairan_support', 'hp': 12, 'score_value': 25,
             'ship': load_enemy_image(asset_path("assets/Nairan - Support Ship - Base.png")),
             'idle_frames': [load_enemy_image(asset_path("assets/Nairan - Support Ship - Base.png"))],
             'attack_frames': [load_enemy_image(asset_path("assets/Nairan - Support Ship - Base.png"))],
             'explosion': load_enemy_frames(asset_path("assets/Nairan - Support Ship - Destruction.png"), 16),
             'contact_damage': 10},
            {'name': 'nairan_frigate', 'hp': 30, 'score_value': 50,
             'ship': load_enemy_image(asset_path("assets/Nairan - Frigate - Base.png")),
             'idle_frames': [load_enemy_image(asset_path("assets/Nairan - Frigate - Base.png"))],
             'attack_frames': load_enemy_frames(asset_path("assets/Nairan - Frigate - Weapons.png"), 5),
             'attack_overlay': True,
             'explosion': load_enemy_frames(asset_path("assets/Nairan - Frigate - Destruction.png"), 16),
             'contact_damage': 22},
            {'name': 'nairan_battlecruiser', 'hp': 75, 'score_value': 100,
             'ship': load_enemy_image(asset_path("assets/Nairan - Battlecruiser - Base.png")),
             'idle_frames': [load_enemy_image(asset_path("assets/Nairan - Battlecruiser - Base.png"))],
             'attack_frames': load_enemy_frames(asset_path("assets/Nairan - Battlecruiser - Weapons.png"), 9),
             'attack_overlay': True,
             'explosion': load_enemy_frames(asset_path("assets/Nairan - Battlecruiser - Destruction.png"), 18),
             'contact_damage': 30},
            {'name': 'nairan_dreadnought', 'hp': 350, 'score_value': 280,
             'ship': load_enemy_image(asset_path("assets/Nairan - Dreadnought - Base.png")),
             'idle_frames': [load_enemy_image(asset_path("assets/Nairan - Dreadnought - Base.png"))],
             'attack_frames': load_enemy_frames(asset_path("assets/Nairan - Dreadnought - Weapons.png"), 34),
             'attack_overlay': True,
             'explosion': load_enemy_frames(asset_path("assets/Nairan - Dreadnought - Destruction.png"), 18),
             'contact_damage': 45},
            # ── The Shadow Interceptor (Neural Clone Mirror Match) ───────────
            {'name': 'shadow_interceptor', 'hp': 130, 'score_value': 300,
             'ship': shadow_surf,
             'idle_frames': [shadow_surf],
             'attack_frames': [shadow_surf],
             'explosion': slice_spritesheet(asset_path('assets/explosion.png'), 8),
             'contact_damage': 20},
        ],
        'bg_void': bg_void,
        'bg_stars': bg_stars,
        'bg_planet': bg_planet,
        'bg_black_hole': bg_black_hole,
        'asteroid_flame': asteroid_flame,
        'asteroid_explosion': asteroid_explosion,
        'pickup_weapons': pickup_weapons,
        'pickup_engines': pickup_engines,
        'pickup_shields': pickup_shields,
        'explosions': slice_spritesheet(asset_path('assets/explosion.png'), 8),
        'astronaut': {
            'hello': load_astronaut_portrait('astronaut hello.png', 'hello'),
            'talking': load_astronaut_portrait('astronaut talking.png', 'talking'),
            'thumbs_up': load_astronaut_portrait('astronaut thumbs up.png', 'thumbs_up'),
        },
    }
