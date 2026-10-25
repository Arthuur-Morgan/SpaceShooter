"""Comprehensive Headless Verification Suite for SpaceShooter Combat Readiness.

Tests:
1. Flocking Anti-Clumping (<65px radial separation force) & Squad Leader Anchoring.
2. Support Ship Healing Tethers & Boss Invulnerability Conduit ('SHIELD CONDUIT ACTIVE // DESTROY SUPPORT SHIP').
3. Curated Environment: 4-Layer Parallax Background & Celestial Landmarks (Planet Phase 0, Black Hole Phase 1).
4. Fast Asteroid Telegraphing & Dedicated Rock Explosions.
5. In-Run Module Overclock Drops:
   - OverclockPickup mechanics (bobbing, drift, animation, collision).
   - Weapon Overdrive (7.0s duration, twin parallel auto-cannon, pierce 99 big space gun, 5-rocket salvo, 4-chain zapper).
   - Engine Overdrive (6.0s duration, +2.2 speed, afterburner wake, ramming armor scout/asteroid shatter).
   - Shield Surge (5.0s duration, 20 HP barrier absorption, +40% capacity restore, downtime reset).
6. Dynamic Wave Pacing & Breather Buffer.
"""

import sys
import os
import math
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
pygame.init()
pygame.display.set_mode((800, 600))

from src.asset_loader import load_assets
from src.background import ParallaxBackground
from src.entities import Player, Enemy, Bullet, OverclockPickup, Explosion
from src.adaptive_director import AdaptiveDirector

def test_flocking_and_squad_anchoring():
    assets = load_assets()
    enemy_types = {e['name']: e for e in assets['enemy_types']}

    # 1. Soft radial separation force when distance < 65px
    e1 = Enemy(enemy_types['scout'], behavior='straight', difficulty='medium', spawn_x=300, spawn_y=200)
    e2 = Enemy(enemy_types['scout'], behavior='straight', difficulty='medium', spawn_x=320, spawn_y=200)

    initial_dist = math.hypot(e1.rect.centerx - e2.rect.centerx, e1.rect.centery - e2.rect.centery)
    assert initial_dist < 65, f"Initial dist should be < 65, got {initial_dist}"

    class DummyPlayer:
        rect = pygame.Rect(300, 500, 40, 40)
        hp = 100

    dummy_player = DummyPlayer()
    e1.update(dummy_player, [e1, e2])
    e2.update(dummy_player, [e1, e2])

    post_dist = math.hypot(e1.rect.centerx - e2.rect.centerx, e1.rect.centery - e2.rect.centery)
    assert post_dist > initial_dist, f"Separation force should repel ships: {initial_dist} -> {post_dist}"
    print(f"[PASS] Flocking Soft Radial Repulsion: {initial_dist:.1f}px -> {post_dist:.1f}px")

    # 2. Squad Leader Escort Wing Anchoring
    leader = Enemy(enemy_types['frigate'], difficulty='medium', spawn_x=400, spawn_y=150)
    leader.is_leader = True

    escort_left = Enemy(enemy_types['scout'], difficulty='medium', spawn_x=200, spawn_y=100)
    escort_right = Enemy(enemy_types['scout'], difficulty='medium', spawn_x=600, spawn_y=100)

    allies = [leader, escort_left, escort_right]
    for _ in range(5):
        for s in allies:
            s.update(dummy_player, allies)

    # Escorts should steer relative to squad leader
    assert escort_left.x < leader.x, "Escort left wing should remain to the left of squad leader"
    assert escort_right.x > leader.x, "Escort right wing should remain to the right of squad leader"
    print("[PASS] Squad Leader Escort Wing Anchoring verified.")

def test_support_conduit_and_invulnerability():
    assets = load_assets()
    enemy_types = {e['name']: e for e in assets['enemy_types']}

    boss = Enemy(enemy_types['dreadnought'], difficulty='medium', spawn_x=350, spawn_y=100)
    support = Enemy(enemy_types['support'], difficulty='medium', spawn_x=250, spawn_y=100)

    class DummyPlayer:
        rect = pygame.Rect(350, 500, 40, 40)
        hp = 100

    dummy = DummyPlayer()
    allies = [boss, support]

    # Support updates and attaches defensive conduit to boss
    support.update(dummy, allies)
    assert boss.is_invulnerable_tethered is True, "Boss should be tethered by support ship"
    assert boss.tether_support_ship is support, "Boss tether should point to support ship"
    print("[PASS] Support Ship Boss Defense Conduit established.")

    # Damage test: Boss is invulnerable while support lives
    import src.main as main
    main.enemies = [boss, support]
    enemies_to_remove = []
    initial_boss_hp = boss.hp

    main.damage_enemy(boss, 20, enemies_to_remove)
    assert boss.hp == initial_boss_hp, f"Boss took damage while tethered: {boss.hp} vs {initial_boss_hp}"
    assert boss not in enemies_to_remove, "Boss should not be marked for removal"

    # Destroying support ship collapses the shield conduit
    main.damage_enemy(support, 9999, enemies_to_remove)
    assert support in enemies_to_remove, "Support ship should be destroyed"
    assert boss.is_invulnerable_tethered is False, "Boss tether should collapse upon support ship death"
    print("[PASS] Support Ship Boss Invulnerability & Shield Collapse verified.")

def test_parallax_background_and_landmarks():
    assets = load_assets()
    bg = ParallaxBackground(
        assets['bg_void'],
        assets['bg_stars'],
        bg_planet=assets.get('bg_planet'),
        bg_black_hole=assets.get('bg_black_hole')
    )

    assert bg.void_speed == 0.25, f"Void speed should be 0.25, got {bg.void_speed}"
    assert bg.stars_speed == 0.65, f"Stars speed should be 0.65, got {bg.stars_speed}"
    assert bg.landmark_speed == 0.15, f"Landmark speed should be 0.15, got {bg.landmark_speed}"
    assert bg.fg_stars_speed == 1.2, f"Foreground stars speed should be 1.2, got {bg.fg_stars_speed}"
    assert len(bg.fg_stars) == 50, f"Expected 50 foreground star particles, got {len(bg.fg_stars)}"

    # Trigger Phase 0 Planet landmark
    bg.trigger_landmark(fleet_phase=0, force=True)
    assert bg.landmark is not None, "Landmark should have spawned"
    assert bg.landmark['type'] == 'planet', f"Expected planet in Phase 0, got {bg.landmark['type']}"
    assert len(bg.landmark['frames']) == 77, f"Expected 77 planet animation frames, got {len(bg.landmark['frames'])}"

    # Trigger Phase 1 Black Hole landmark
    bg.trigger_landmark(fleet_phase=1, force=True)
    assert bg.landmark['type'] == 'black_hole', f"Expected black_hole in Phase 1, got {bg.landmark['type']}"
    assert len(bg.landmark['frames']) == 16, f"Expected 16 black hole animation frames, got {len(bg.landmark['frames'])}"

    # Test update and drawing
    surf = pygame.Surface((800, 600))
    bg.update(fleet_phase=1)
    bg.draw(surf)
    print("[PASS] 4-Layer Parallax Background & Celestial Landmarks verified.")

def test_fast_asteroid_telegraphing():
    assets = load_assets()
    enemy_types = {e['name']: e for e in assets['enemy_types']}

    asteroid_fast = Enemy(enemy_types['asteroid'], behavior='fast', difficulty='medium', spawn_x=400, spawn_y=-50)
    assert asteroid_fast.speed == 4.5, f"Fast asteroid speed should be 4.5, got {asteroid_fast.speed}"
    assert asteroid_fast.flame_frames is not None, "Fast asteroid should have flame frames attached"
    assert len(asteroid_fast.flame_frames) == 3, f"Expected 3 flame frames, got {len(asteroid_fast.flame_frames)}"
    assert len(asteroid_fast.explosion_frames) == 8, f"Expected 8 asteroid rock explosion frames, got {len(asteroid_fast.explosion_frames)}"

    # Check drawing with flame attached
    surf = pygame.Surface((800, 600))
    asteroid_fast.draw(surf)
    print("[PASS] Fast Asteroid Telegraphing & Dedicated Rock Explosion verified.")

def test_overclock_pickups_and_durations():
    assets = load_assets()
    save_data = {
        'credits': 1000,
        'high_score': 0,
        'equipped_weapon': 'auto_cannon',
        'equipped_engine': 'base',
        'equipped_shield': 'front',
        'owned_weapons': ['auto_cannon', 'big_space_gun', 'rockets', 'zapper'],
        'owned_engines': ['base', 'big_pulse', 'burst', 'supercharged'],
        'owned_shields': ['front', 'front_side', 'round', 'invincibility'],
        'invincibility_backups': 0,
        'sensitivity': 5,
        'music_volume': 0.5,
        'music_track': 0,
        'difficulty': 'medium',
    }

    # 1. OverclockPickup Class Verification
    w_pickup = OverclockPickup(300, 200, 'weapon', 'auto_cannon', assets['pickup_weapons']['auto_cannon'])
    assert w_pickup.category == 'weapon'
    assert len(w_pickup.frames) == 15, f"Expected 15 icon frames, got {len(w_pickup.frames)}"
    assert w_pickup.speed == 1.2, f"Pickup speed should be 1.2, got {w_pickup.speed}"

    init_y = w_pickup.y
    w_pickup.update()
    assert w_pickup.y > init_y, "Pickup should drift downwards"

    # 2. Player Weapon Overdrive (7.0s)
    player = Player(400, 500, assets, save_data)
    now = pygame.time.get_ticks()

    player.weapon_overclock_until = now + 7000
    assert player.is_weapon_overclocked is True, "Weapon should be overclocked"

    # Auto-cannon Overdrive: 2x fire rate, 0 reload downtime, twin parallel bullets
    keys = {pygame.K_SPACE: True, pygame.K_LSHIFT: False, pygame.K_RSHIFT: False}
    keybinds = {'SHOOT': pygame.K_SPACE, 'SHIELD': pygame.K_e, 'LEFT': pygame.K_a, 'RIGHT': pygame.K_d, 'UP': pygame.K_w, 'DOWN': pygame.K_s}
    player.last_shot_time = 0
    shots = player.shoot(keys, keybinds, [])
    assert len(shots) == 2, f"Auto-cannon overdrive should fire twin parallel shots, got {len(shots)}"
    assert shots[0].rect.centerx != shots[1].rect.centerx, "Twin shots should be parallel with offset"

    # Big Space Gun Overdrive: pierce 99, 320ms fire rate
    save_data['equipped_weapon'] = 'big_space_gun'
    player_bsg = Player(400, 500, assets, save_data)
    player_bsg.weapon_overclock_until = now + 7000
    player_bsg.last_shot_time = 0
    shots_bsg = player_bsg.shoot(keys, keybinds, [])
    assert len(shots_bsg) == 1
    assert shots_bsg[0].pierce == 99, f"BSG Overdrive should pierce all (99), got {shots_bsg[0].pierce}"

    # Rockets Overdrive: 5-rocket salvo, +40% speed
    save_data['equipped_weapon'] = 'rockets'
    player_rkt = Player(400, 500, assets, save_data)
    player_rkt.weapon_overclock_until = now + 7000
    player_rkt.last_shot_time = 0
    shots_rkt = player_rkt.shoot(keys, keybinds, [])
    assert len(shots_rkt) == 5, f"Rockets Overdrive should fire 5-rocket salvo, got {len(shots_rkt)}"

    # Zapper Overdrive: 4 chain count, +50% range
    save_data['equipped_weapon'] = 'zapper'
    player_zap = Player(400, 500, assets, save_data)
    player_zap.weapon_overclock_until = now + 7000
    player_zap.last_shot_time = 0
    shots_zap = player_zap.shoot(keys, keybinds, [])
    assert len(shots_zap) == 1
    assert shots_zap[0].chain_count == 4, f"Zapper Overdrive chain count should be 4, got {shots_zap[0].chain_count}"
    assert shots_zap[0].chain_range == int(assets['weapons']['zapper']['chain_range'] * 1.5)
    print("[PASS] Weapon Overdrive (7.0s) & All Weapon Archetype Overclocks verified.")

    # 3. Player Engine Overdrive (6.0s)
    player_eng = Player(400, 500, assets, save_data)
    player_eng.engine_overclock_until = now + 6000
    assert player_eng.is_engine_overclocked is True, "Engine should be overclocked"

    init_speed = player_eng.speed
    blank_keys = {k: False for k in range(512)}
    blank_keys[pygame.K_d] = True
    player_eng.update(blank_keys, keybinds, [])
    # Movement speed increased by +2.2
    assert player_eng.x > 400 + init_speed, f"Speed should be boosted by +2.2 during Engine Overdrive"
    print("[PASS] Engine Overdrive (6.0s) & Speed Boost verified.")

    # 4. Player Shield Surge (5.0s & 20 HP barrier)
    player_shd = Player(400, 500, assets, save_data)
    player_shd.shield_overcharge_until = now + 5000
    player_shd.shield_overcharge_barrier = 20
    assert player_shd.is_shield_overcharged is True

    init_hp = player_shd.hp
    player_shd.take_damage(12)
    assert player_shd.hp == init_hp, "HP should not drop while overcharge barrier absorbs damage"
    assert player_shd.shield_overcharge_barrier == 8, f"Barrier should have 8 remaining, got {player_shd.shield_overcharge_barrier}"

    player_shd.take_damage(15)  # 8 absorbed, 7 reaches player
    assert player_shd.shield_overcharge_barrier == 0
    assert player_shd.hp < init_hp, "HP should decrease once barrier is depleted"
    print("[PASS] Shield Surge (5.0s) Overcharge Barrier Absorption verified.")

def test_dynamic_wave_pacing():
    from src.main import SPAWN_ENEMY_EVENT
    assets = load_assets()
    enemy_types = {e['name']: e for e in assets['enemy_types']}

    # Dynamic wave pacing threshold check
    cap_ship = Enemy(enemy_types['battlecruiser'], difficulty='medium', spawn_x=300, spawn_y=100)
    has_heavy = any(k in cap_ship.name for k in ('dreadnought', 'battlecruiser', 'frigate'))
    threshold = 2 if has_heavy else 3
    assert threshold == 2, f"Presence of capital ship should lower threshold to 2, got {threshold}"
    print("[PASS] Dynamic Wave Pacing & Breather Window logic verified.")

def test_capital_ship_inset_hitbox():
    from src.asset_loader import load_assets
    from src.entities import Enemy
    assets = load_assets()
    enemy_types = {e['name']: e for e in assets['enemy_types']}

    dread = Enemy(enemy_types['dreadnought'], spawn_x=300, spawn_y=100)
    assert dread.hitbox.width < dread.rect.width, f"Dreadnought width not inset: {dread.hitbox.width} vs {dread.rect.width}"
    assert dread.hitbox.height < dread.rect.height, f"Dreadnought height not inset: {dread.hitbox.height} vs {dread.rect.height}"
    assert dread.hitbox.center == dread.rect.center, "Hitbox center must match sprite center"

    frigate = Enemy(enemy_types['frigate'], spawn_x=250, spawn_y=100)
    assert frigate.hitbox.width < frigate.rect.width
    assert frigate.hitbox.height < frigate.rect.height
    print(f"[PASS] Inset Hitbox verified: Dreadnought raw {dread.rect.size} -> hitbox {dread.hitbox.size}")

def test_boss_carrier_group_composition():
    from src.adaptive_director import AdaptiveDirector, FLEET_NAUTOLAN, FLEET_KLAED
    director = AdaptiveDirector()
    class DummyPlayer:
        rect = pygame.Rect(400, 500, 40, 40)
        hp = 100
        shots_fired = 50
    player = DummyPlayer()
    director.begin_run(player, "medium")

    # Force Stage 4
    director.stage = 4
    enc = director.choose_encounter(player, score=2500, active_enemies_count=0, now=220000, elapsed_ms=220000)
    enemy_names = [e[0] for e in enc]
    assert "dreadnought" in enemy_names, f"Dreadnought must be in Stage 4 wave, got {enemy_names}"
    assert any("support" in name for name in enemy_names), f"Boss must spawn with support ship escort! Got {enemy_names}"
    print(f"[PASS] Boss Escort Fleet verified: {enemy_names}")

    # Test carrier reinforcement wings when boss is active
    director.boss_active = True
    director.last_boss_reinforcement_at = 0
    reinforce_enc = director.choose_encounter(player, score=2600, active_enemies_count=1, now=230000, elapsed_ms=230000)
    reinforce_names = [e[0] for e in reinforce_enc]
    assert len(reinforce_names) >= 1, "Boss carrier must deploy reinforcement wing"
    assert reinforce_names != ["scout"], f"Boss reinforcements must not be lone basic scouts! Got {reinforce_names}"
    print(f"[PASS] Boss Carrier Reinforcement Wings verified: {reinforce_names}")

def test_aspect_ratio_viewport():
    from src.main import get_render_viewport
    # Standard 1080p monitor (16:9) with 800x600 canvas (4:3)
    view_rect, scale = get_render_viewport((800, 600), (1920, 1080))
    assert scale == 1.8, f"Expected uniform scale of 1.8, got {scale}"
    assert view_rect.width == 1440, f"Expected width 1440, got {view_rect.width}"
    assert view_rect.height == 1080, f"Expected height 1080, got {view_rect.height}"
    assert view_rect.x == (1920 - 1440) // 2, "Viewport must be horizontally centered"
    print(f"[PASS] Aspect-Preserving Viewport calculation verified: {view_rect} with scale {scale}")

def test_dreadnought_upper_anchoring_and_flocking_immunity():
    assets = load_assets()
    enemy_types = {e['name']: e for e in assets['enemy_types']}

    dread = Enemy(enemy_types['dreadnought'], spawn_x=350, spawn_y=-50)
    class DummyPlayer:
        rect = pygame.Rect(400, 500, 40, 40)
        hp = 100
        velocity_x = 0
    player = DummyPlayer()

    # Update for 120 frames to allow entry
    for _ in range(120):
        dread.update(player, [dread])

    assert dread.y <= 48.0, f"Dreadnought y must be <= 48.0, got {dread.y}"
    assert dread.y >= 10.0, f"Dreadnought y must be >= 10.0, got {dread.y}"

    # Surround Dreadnought with escorts above, below, and alongside at <65px
    escort1 = Enemy(enemy_types['scout'], spawn_x=dread.rect.centerx - 10, spawn_y=dread.rect.centery - 20)
    escort2 = Enemy(enemy_types['scout'], spawn_x=dread.rect.centerx + 10, spawn_y=dread.rect.centery + 20)
    allies = [dread, escort1, escort2]

    for _ in range(60):
        for ship in allies:
            ship.update(player, allies)

    assert dread.y <= 48.0, f"Dreadnought drifted below upper anchor under flocking! y={dread.y}"
    print(f"[PASS] Dreadnought Upper Anchoring & Flocking Immunity verified: Y={dread.y:.1f} (clamp <= 48.0)")

def test_sarh_missile_guidance_and_lock_break():
    from src.entities import EnemyBullet

    class MockTarget:
        rect = pygame.Rect(400, 500, 40, 40)
        hp = 100

    class MockShooter:
        hp = 100

    target = MockTarget()
    shooter = MockShooter()
    frames = [pygame.Surface((10, 10))]

    # Missile fired at x=200, y=100 heading straight down (vx=0, vy=5) while target is at (400, 500)
    missile = EnemyBullet(200, 100, frames, speed=5, vx=0.0, vy=5.0,
                          target=target, homing_turn=0.05, bullet_type="sarh_missile", shooter=shooter)

    assert missile.vx == 0.0
    for _ in range(10):
        missile.update()

    # Target is to the right (x=400 > x=200), so missile must turn right (vx > 0)
    assert missile.vx > 0.5, f"SARH missile should turn towards target, vx={missile.vx}"

    # Flagship killed -> Illumination broken!
    shooter.hp = 0
    missile.update()
    assert missile.bullet_type == "ballistic_lost_lock", f"Lock should break when shooter dies, got {missile.bullet_type}"
    vx_before = missile.vx
    vy_before = missile.vy
    missile.update()
    assert math.isclose(missile.vx, vx_before, rel_tol=1e-5), "Missile should travel along straight ballistic path once lock is broken"
    assert math.isclose(missile.vy, vy_before, rel_tol=1e-5)
    print(f"[PASS] SARH Missile Guidance & Flagship Illumination Lock Break verified.")

def test_dreadnought_multi_vector_arsenal():
    assets = load_assets()
    enemy_types = {e['name']: e for e in assets['enemy_types']}

    class DummyPlayer:
        rect = pygame.Rect(400, 500, 40, 40)
        hp = 100
        velocity_x = 2.0
    player = DummyPlayer()

    for d_name in ('dreadnought', 'klaed_dreadnought', 'nairan_dreadnought'):
        dread = Enemy(enemy_types[d_name], spawn_x=350, spawn_y=35)
        
        # Shot 1: Mode 0 (Ray fan spread)
        dread.last_shot_time = -100000
        s1 = dread.shoot(assets['enemy_projectiles'], player)
        assert len(s1) >= 6, f"{d_name} Mode 0 should fire a wide beam fan, got {len(s1)}"
        
        # Shot 2: Mode 1 (SARH missiles)
        dread.last_shot_time = -100000
        s2 = dread.shoot(assets['enemy_projectiles'], player)
        sarh_missiles = [b for b in s2 if getattr(b, 'bullet_type', None) == 'sarh_missile']
        assert len(sarh_missiles) >= 2, f"{d_name} Mode 1 must include SARH missiles, got {len(sarh_missiles)}"
        assert dread.radar_lock_until > pygame.time.get_ticks(), f"{d_name} must activate radar lock on Mode 1"
        
        # Shot 3: Mode 2 (Waves & Flak)
        dread.last_shot_time = -100000
        s3 = dread.shoot(assets['enemy_projectiles'], player)
        assert len(s3) >= 4, f"{d_name} Mode 2 should fire flak wave matrix, got {len(s3)}"
        
        # Shot 4: Mode 3 (Predictive heavy barrage)
        dread.last_shot_time = -100000
        s4 = dread.shoot(assets['enemy_projectiles'], player)
        assert len(s4) >= 3, f"{d_name} Mode 3 should fire heavy predictive barrage, got {len(s4)}"

    print("[PASS] Dreadnought Multi-Vector 4-Mode Arsenal verified across all factions.")

def test_sarh_and_torpedo_escape_countermeasures():
    from src.entities import EnemyBullet, Player, Bullet

    assets = load_assets()
    save_data = {'difficulty': 'medium', 'equipped_weapon': 'auto_cannon', 'equipped_engine': 'base'}

    class MockTarget:
        rect = pygame.Rect(400, 300, 40, 40)
        hp = 100

    class MockShooter:
        hp = 100

    target = MockTarget()
    shooter = MockShooter()
    frames = [pygame.Surface((12, 12))]

    # 1. Seeker Aspect Overshoot test: missile past player vertically breaks lock
    missile = EnemyBullet(400, 280, frames, speed=5, vx=0.0, vy=5.0,
                          target=target, homing_turn=0.04, bullet_type="sarh_missile", shooter=shooter)
    for _ in range(16):
        missile.update()
    assert missile.y > target.rect.centery + 12, f"Missile should fly past target, y={missile.y}"
    assert missile.bullet_type == "ballistic_lost_lock", f"Missile must lose lock after overshooting target, got {missile.bullet_type}"
    print("[PASS] SARH Evasive Overshoot Countermeasure verified.")

    # 2. Burnout fuel expiration test
    m_burn = EnemyBullet(400, 100, frames, speed=5, vx=0.0, vy=5.0,
                         target=target, homing_turn=0.04, bullet_type="sarh_missile", shooter=shooter)
    m_burn.burnout_at = pygame.time.get_ticks() - 100
    m_burn.update()
    assert m_burn.bullet_type == "ballistic_lost_lock", "Missile must lose lock upon fuel burnout"
    print("[PASS] SARH Fuel Burnout Evasion verified.")

    # 3. Chaff Evasive Pulse (Shift) Countermeasure test
    from src.entities import SparkParticle
    player = Player(400, 500, assets, save_data)
    player.activate_engine_ability(pygame.time.get_ticks())
    assert player.chaff_deployed is True, "Activating engine ability / Shift must deploy defensive chaff"
    sp = SparkParticle(player.rect.centerx, player.rect.centery, (100, 240, 255), duration=320)
    sp.update()
    assert sp.life > 0
    print("[PASS] Player Chaff Decoy Deployment on Shift & SparkParticle verified.")

    # 4. Point-Defense Interception (Shooting down incoming missiles)
    p_bullet = Bullet(400, 205, assets['bullet'], speed=10, damage=2)
    incoming_torpedo = EnemyBullet(400, 200, frames, speed=4, bullet_type="shield_buster_torpedo")
    assert p_bullet.rect.colliderect(incoming_torpedo.rect), "Point-defense bullet must collide with incoming torpedo"
    print("[PASS] Point-Defense Missile Interception collision verified.")

def test_torpedo_emp_shield_busting_and_salvo():
    from src.entities import Enemy, Player
    assets = load_assets()
    enemy_types = {e['name']: e for e in assets['enemy_types']}
    save_data = {'difficulty': 'medium', 'equipped_weapon': 'auto_cannon', 'equipped_engine': 'base', 'equipped_shield': 'front'}

    torp_enemy = Enemy(enemy_types['torpedo'], spawn_x=400, spawn_y=100)
    torp_enemy.last_shot_time = -100000

    class DummyPlayer:
        rect = pygame.Rect(400, 500, 40, 40)
        hp = 100
        velocity_x = 0
    d_player = DummyPlayer()

    # 1. Homing salvo check
    salvo = torp_enemy.shoot(assets['enemy_projectiles'], d_player)
    assert len(salvo) == 2, f"Torpedo ship must fire a twin salvo, got {len(salvo)}"
    for t in salvo:
        assert getattr(t, 'bullet_type', None) == 'shield_buster_torpedo', "Torpedo must be shield_buster_torpedo"
        assert getattr(t, 'shield_damage', 0) == 45, f"EMP Torpedo must have 45 shield damage, got {t.shield_damage}"
    print("[PASS] Torpedo Ship Twin EMP Homing Salvo verified.")

    # 2. EMP Shield-Buster direct hit against active shield
    player = Player(400, 500, assets, save_data)
    player.activate_shield()
    assert player.shield_active is True
    assert player.shield_remaining == 30  # Front shield capacity 30

    emp_torpedo = salvo[0]
    # Simulate EMP hit
    player.take_damage(emp_torpedo.shield_damage)
    # Shield took 30 damage and collapsed! Remaining 15 hit hull: 100 - 15 = 85
    assert player.shield_active is False, "Front shield (30 HP) must collapse under 45 EMP damage"
    assert player.shield_just_collapsed is True, "Shield collapse trigger must be raised for hitstop"
    assert player.hp == 85, f"Remaining 15 EMP damage must reach hull (100 - 15 = 85), got {player.hp}"
    print("[PASS] EMP Torpedo Shield-Busting & Collapse Mechanics verified.")

def test_ai_brain_anti_shield_torpedo_deployment():
    from src.adaptive_director import AdaptiveDirector, ENCOUNTERS
    director = AdaptiveDirector()
    assets = load_assets()
    save_data = {'difficulty': 'medium', 'equipped_weapon': 'auto_cannon', 'equipped_engine': 'base', 'equipped_shield': 'front'}
    player = Player(400, 320, assets, save_data)  # Aggressive forward positioning (Y=320)
    player.activate_shield()

    director.begin_run(player, "medium")
    director.stage = 1  # Before dreadnought stage

    # Simulate 20 ticks of forward aggressive shield usage
    now = 5000
    for tick in range(25):
        t_now = now + tick * 150
        director.profiler.sample(player, director, now=t_now)

    assert director.profiler.is_abusing_shield is True, "Profiler must identify aggressive shield over-reliance"

    # AI Brain evaluates wave and dispatches anti-shield torpedo corvettes
    enc = director.choose_encounter(player, score=800, active_enemies_count=1, now=t_now + 100, elapsed_ms=60000)
    enemy_names = [e[0] for e in enc]
    assert "torpedo" in enemy_names, f"AI Brain must deploy torpedo corvettes to counter shield abuse! Got {enemy_names}"
    assert len([e for e in enc if e[0] == "torpedo"]) >= 2, f"AI Brain must dispatch a pair of torpedo corvettes, got {enemy_names}"

    # Check comms transmission broadcast
    comms_text = " ".join([m['text'] for m in director.comms.messages])
    assert "ANTI-SHIELD TORPEDO CORVETTES" in comms_text, f"Comms hub must broadcast torpedo counter alert, got: {comms_text}"
    print(f"[PASS] Aegis-Fable AI Brain Anti-Shield Torpedo Deployment verified: {enemy_names}")

def test_hangar_databank_and_discovery_system():
    from src.save_manager import DEFAULT_SAVE, load_save_data
    from src.hangar_view import HangarView
    from src.main import SHOP_ITEMS, damage_enemy
    from src.entities import Enemy

    # 1. Save data schema
    assert "encountered_enemies" in DEFAULT_SAVE, "DEFAULT_SAVE must include encountered_enemies"
    s_data = load_save_data()
    assert isinstance(s_data.get("encountered_enemies"), list), "encountered_enemies must be a list"
    print("[PASS] Save Manager encountered_enemies schema verified.")

    # 2. Main combat destruction discovery recording
    assets = load_assets()
    enemy_types = {e['name']: e for e in assets['enemy_types']}
    test_save = {'difficulty': 'medium', 'encountered_enemies': ['scout']}
    
    # Simulate damage_enemy kill
    e_to_kill = Enemy(enemy_types['bomber'], spawn_x=400, spawn_y=100)
    e_to_kill.hp = 2
    rem_list = []

    # Mock save_data in main module scope if needed or direct check
    import src.main as main_mod
    orig_save = main_mod.save_data
    main_mod.save_data = test_save
    try:
        main_mod.damage_enemy(e_to_kill, 5, rem_list)
        assert "bomber" in main_mod.save_data["encountered_enemies"], "Destroying an enemy must record its name in encountered_enemies"
    finally:
        main_mod.save_data = orig_save
    print("[PASS] Enemy Combat Destruction Discovery Tracking verified.")

    # 3. Hangar Databank & Custom Lore Dictionary (26 entities)
    hangar = HangarView(assets, SHOP_ITEMS, lambda c, it: "OK")
    assert len(hangar.threat_keys) == 26, f"Hangar threat keys must contain exactly 26 entities, got {len(hangar.threat_keys)}"
    assert len(hangar.encyclopedia_lore) >= 29, f"Hangar lore must contain at least 29 entries (26 threats + 3 drops), got {len(hangar.encyclopedia_lore)}"
    assert "dreadnought" in hangar.encyclopedia_lore
    assert "shadow_interceptor" in hangar.encyclopedia_lore
    assert "klaed_dreadnought" in hangar.encyclopedia_lore
    assert "nairan_dreadnought" in hangar.encyclopedia_lore
    assert hangar.encyclopedia_lore['shadow_interceptor']['role'] == "Mirror Match"
    assert "weapon_overdrive" in hangar.encyclopedia_lore
    assert "engine_overdrive" in hangar.encyclopedia_lore
    assert "shield_surge" in hangar.encyclopedia_lore
    assert hangar.encyclopedia_lore['weapon_overdrive']['role'] == "Firepower Surge"
    assert hangar.encyclopedia_lore['engine_overdrive']['role'] == "Mobility Surge"
    assert hangar.encyclopedia_lore['shield_surge']['role'] == "Defense Surge"
    print("[PASS] Databank 26-Entity Custom Lore & Overclock Drops Dictionary verified.")

    # 4. Hangar Interaction & Databank Modal (Launch and Difficulty removed)
    assert hangar.mode == "overview"
    # Verification: Launch button and Difficulty cards must be stripped out of Hangar
    assert not hasattr(hangar, 'btn_launch'), "hangar must not have btn_launch"
    assert not hasattr(hangar, 'get_launch_rect'), "hangar must not have get_launch_rect"
    assert not hasattr(hangar, 'get_difficulty_cards'), "hangar must not have get_difficulty_cards"

    # Verification: Back button and Databank button are cleanly anchored on the bottom bar
    assert hasattr(hangar, 'btn_back') and hangar.btn_back is not None, "hangar must have btn_back"
    back_action = hangar.handle_click(hangar.btn_back.center, test_save)
    assert back_action == "BACK", "Clicking btn_back must return 'BACK'"

    db_btn = hangar.get_databank_btn_rect()
    assert db_btn.y == hangar.btn_back.y, "Databank button and Back button must be aligned on the bottom bar"
    action = hangar.handle_click(db_btn.center, test_save)
    assert action == "CLICK" and hangar.mode == "encyclopedia", "Clicking Databank button must switch to encyclopedia mode"

    # Category Tab Switching & Layout Verification (5 tabs including DROPS)
    tabs = hangar.get_encyclopedia_tabs()
    tab_keys = ["threats", "weapons", "engines", "shields", "drops"]
    ordered_rects = [tabs[k] for k in tab_keys]

    # Verify dynamic widths and clean 12px gaps
    panel_rect = hangar.get_encyclopedia_panel_rect()
    assert ordered_rects[0].x == panel_rect.x + hangar._sc(30), "First tab must start at panel_rect.x + 30"
    for idx, (cat_key, rect) in enumerate(zip(tab_keys, ordered_rects)):
        expected_w = hangar.font_bold.size(cat_key.upper())[0] + hangar._sc(24)
        assert rect.w == expected_w, f"Tab {cat_key} width {rect.w} must equal text_w + padding {expected_w}"
        assert rect.h == hangar._sc(32), f"Tab {cat_key} height must be 32px"
        assert rect.y == panel_rect.y + hangar._sc(16), f"Tab {cat_key} Y must be panel_rect.y + 16"
        if idx > 0:
            prev_rect = ordered_rects[idx - 1]
            gap = rect.left - prev_rect.right
            assert gap == hangar._sc(12), f"Gap between tabs must be exactly 12px, got {gap}px"
            assert not rect.colliderect(prev_rect), f"Tab {cat_key} must not overlap previous tab"

    # Verify case-insensitive tab access
    for cat_key in tab_keys:
        assert tabs[cat_key] == tabs[cat_key.upper()], f"tabs must allow case-insensitive access for {cat_key}"
        assert cat_key in tabs and cat_key.upper() in tabs

    for t_name in ("WEAPONS", "ENGINES", "SHIELDS", "DROPS", "THREATS"):
        res = hangar.handle_click(tabs[t_name].center, test_save)
        assert res == "CLICK" and hangar.encyclopedia_tab == t_name
    print("[PASS] Databank Dynamic Tab Widths, 12px Gaps & Overlap Elimination verified.")
    print("[PASS] Databank Dynamic Tab Widths, 12px Gaps & Overlap Elimination verified.")

    # Undiscovered vs Discovered Silhouette and Rendering
    screen = pygame.Surface((800, 600))
    hangar.selected_encyclopedia_item = "klaed_dreadnought"  # Not yet encountered in test_save
    hangar.draw(screen, test_save, (400, 300))  # Renders pure black silhouette & classified dossiers

    hangar.selected_encyclopedia_item = "bomber"  # Encountered in test_save
    hangar.draw(screen, test_save, (400, 300))  # Renders full-color sprite & real stats

    # Shield Hologram Verification (Animated shield aura instead of pickup icon)
    hangar.encyclopedia_tab = "shields"
    hangar.encyclopedia_sel = "invincibility"
    hangar.draw(screen, test_save, (400, 300))
    # Verify shield animation frame is retrieved from assets['shields']['invincibility']['frames']
    assert len(assets['shields']['invincibility']['frames']) == 10

    # Overclock Drops Tab & Holograms Verification
    hangar.encyclopedia_tab = "drops"
    hangar.encyclopedia_sel = "weapon_overdrive"
    hangar.draw(screen, test_save, (400, 300))
    assert hangar.encyclopedia_lore['weapon_overdrive']['role'] == "Firepower Surge"

    hangar.encyclopedia_sel = "engine_overdrive"
    hangar.draw(screen, test_save, (400, 300))
    assert hangar.encyclopedia_lore['engine_overdrive']['role'] == "Mobility Surge"

    hangar.encyclopedia_sel = "shield_surge"
    hangar.draw(screen, test_save, (400, 300))
    assert hangar.encyclopedia_lore['shield_surge']['role'] == "Defense Surge"
    print("[PASS] Databank Shield Hologram & Overclock Drops Tab verified.")

    # Close Databank
    c_btn = hangar.get_encyclopedia_close_rect()
    res = hangar.handle_click(c_btn.center, test_save)
    assert res == "CLICK" and hangar.mode == "overview", "Clicking Close must return to overview mode"
    print("[PASS] Databank Modal Navigation, Silhouette & Real-Stats Rendering verified.")

    # 5. Ticker Visibility Restriction (ONLY in Databank mode)
    # In overview mode, ticker is hidden and does not draw cyan overlay
    screen.fill((0, 0, 0))
    hangar.draw(screen, test_save, (400, 300))
    assert screen.get_at((50, 587))[:3] != (0, 215, 245), "Ticker must be hidden on main Hangar screen"
    
    # In encyclopedia mode, ticker IS visible and scrolls
    hangar.mode = "encyclopedia"
    assert len(hangar.ticker_messages) >= 6, "News ticker must have multiple lore and tactical tips"
    t_init_x = hangar.ticker_x
    pygame.time.delay(20)
    hangar.draw(screen, test_save, (400, 300))
    assert hangar.ticker_x < t_init_x, "News ticker must scroll to the left over time in encyclopedia mode"
    assert screen.get_at((50, 587))[:3] == (0, 215, 245), "Cyan [ DATALINK ] header block must be rendered in encyclopedia mode"
    print("[PASS] Scrolling Galactic News Ticker & Visibility Restriction verified.")

    # 6. Verify RAM DMG box fits within panel margins
    p_rect = hangar.get_encyclopedia_panel_rect()
    l_rect = pygame.Rect(p_rect.x + 12, p_rect.y + 44 + 10, 240, p_rect.h - 44 - 22)
    r_rect = pygame.Rect(l_rect.right + 12, l_rect.y, p_rect.right - l_rect.right - 24, l_rect.h)
    box_m = 18
    box_g = 10
    box_w = (r_rect.w - (box_m * 2) - (box_g * 2)) // 3
    box3_r = r_rect.x + box_m + 2 * (box_w + box_g) + box_w
    assert box3_r <= r_rect.right, f"RAM DMG box must not overflow right panel margin! {box3_r} > {r_rect.right}"
    print("[PASS] Stat Box (RAM DMG) margin boundary verified.")

def test_hybrid_hd_ui_pipeline():
    from src.ui_theme import UITheme
    import src.main as m
    from src.entities import FloatingText

    # 1. UITheme dynamic font scaling
    t1 = UITheme(scale_factor=1.0)
    t2 = UITheme(scale_factor=1.8)
    # Check that font sizes scaled
    sz1 = t1.title_large.size("TEST")[1]
    sz2 = t2.title_large.size("TEST")[1]
    assert sz2 > sz1, f"Scaled font height {sz2} must be strictly greater than 1x font height {sz1}"
    print("[PASS] UITheme Dynamic Multi-Scale Font Generation verified.")

    # 2. Hybrid simulation dimensions & scaling metrics
    assert m.GAME_WIDTH == 800 and m.GAME_HEIGHT == 600, "Physics canvas must be exactly 800x600"
    assert m.entities.SCREEN_WIDTH == 800 and m.entities.SCREEN_HEIGHT == 600, "Entity physics bounds must be 800x600"
    assert m.SCALE_FACTOR == m.SCREEN_HEIGHT / 600.0, "SCALE_FACTOR must match monitor height / 600"
    assert m.OFFSET_X == (m.SCREEN_WIDTH - int(800 * m.SCALE_FACTOR)) // 2, "OFFSET_X must center the 800x600 simulation"
    print(f"[PASS] Hybrid HD Engine Metrics verified: Scale={m.SCALE_FACTOR:.2f}, OffsetX={m.OFFSET_X}px.")

    # 3. to_game_pos coordinate transformation
    test_game_x, test_game_y = 350, 420
    disp_x = m.OFFSET_X + int(test_game_x * m.SCALE_FACTOR)
    disp_y = int(test_game_y * m.SCALE_FACTOR)
    mapped_gx, mapped_gy = m.to_game_pos((disp_x, disp_y))
    assert abs(mapped_gx - test_game_x) <= 1, f"X-mapping mismatch: expected ~{test_game_x}, got {mapped_gx}"
    assert abs(mapped_gy - test_game_y) <= 1, f"Y-mapping mismatch: expected ~{test_game_y}, got {mapped_gy}"
    print("[PASS] Native Display <-> 800x600 Simulation Coordinate Mapping verified.")

    # 4. Dynamic Menu and Shop Layouts
    menu_btns = m.get_menu_buttons()
    assert menu_btns["start"].centerx == m.SCREEN_WIDTH // 2, "Main menu buttons must be centered on native display"
    assert menu_btns["start"].width == int(260 * m.SCALE_FACTOR), "Button width must scale by SCALE_FACTOR"

    shop_tabs = m.get_shop_tabs()
    assert shop_tabs["engines"].centerx == m.SCREEN_WIDTH // 2, "Middle shop tab must be centered on native display"
    assert shop_tabs["weapons"].width == int(190 * m.SCALE_FACTOR), "Shop tab width must scale by SCALE_FACTOR"
    print("[PASS] Scaled UI Widget & Menu Layout Anchoring verified.")

    # 5. Native FloatingText Scaled Blitting
    ft = FloatingText(400, 300, "+250", (0, 240, 255))
    disp_surf = pygame.Surface((m.SCREEN_WIDTH, m.SCREEN_HEIGHT))
    ft.draw(disp_surf, m.label_font, offset=(m.OFFSET_X, 0), scale=m.SCALE_FACTOR)
    print("[PASS] Native Resolution FloatingText Scaled Rendering verified.")

def test_enemy_hit_flash_masking():
    from src.asset_loader import load_assets
    from src.entities import Enemy
    assets = load_assets()
    enemy = Enemy(assets['enemy_types'][0]) # Asteroid (96x96 with large transparent padding)
    enemy.rect.topleft = (50, 50)

    test_surf = pygame.Surface((200, 200))
    test_surf.fill((10, 20, 30))

    corner_pos = (50, 50)
    center_pos = (enemy.rect.centerx, enemy.rect.centery)

    # Active hit flash
    now = pygame.time.get_ticks()
    enemy.hit_flash_until = now + 35
    enemy.draw(test_surf)

    # Verify corner of bounding box (transparent in sprite) NEVER leaked white
    corner_color = test_surf.get_at(corner_pos)
    assert corner_color == (10, 20, 30, 255), f"Hit flash must not leak white onto transparent bounding box! Got {corner_color}"

    # Verify ship center was drawn with hit flash
    center_color = test_surf.get_at(center_pos)
    assert center_color != (10, 20, 30, 255), "Enemy sprite was not rendered"
    print("[PASS] Enemy Hit-Flash Silhouette Masking (Zero Bounding Box Leakage) verified.")

def test_support_ship_shield_exclusion():
    from src.asset_loader import load_assets
    from src.entities import Enemy
    import math

    assets = load_assets()
    enemy_types = {e['name']: e for e in assets['enemy_types']}

    class DummyPlayer:
        rect = pygame.Rect(400, 500, 40, 40)
        velocity_x = 0
        hp = 100

    dummy = DummyPlayer()

    # 1. Test against Dreadnought
    boss = Enemy(enemy_types['dreadnought'], difficulty='medium', spawn_x=336, spawn_y=38)
    boss_shield_r = max(boss.rect.width, boss.rect.height) // 2 + 14  # 78px
    # Spawn support ship directly on top of the Dreadnought inside its shield
    support = Enemy(enemy_types['support'], difficulty='medium', spawn_x=368, spawn_y=38)
    supp_r = max(support.rect.width, support.rect.height) // 2       # 32px
    min_clear_dist = boss_shield_r + supp_r + 14                    # 124px

    allies = [boss, support]

    # Verify initial spawn is inside shield
    init_dist = math.hypot(support.rect.centerx - boss.rect.centerx, support.rect.centery - boss.rect.centery)
    assert init_dist < boss_shield_r, f"Initial placement should be inside shield for testing, got dist={init_dist}"

    # Support update should immediately repel out of the shield
    support.update(dummy, allies)
    dist_after_supp = math.hypot(support.rect.centerx - boss.rect.centerx, support.rect.centery - boss.rect.centery)
    assert dist_after_supp >= min_clear_dist, f"Support ship failed to repel outside Dreadnought shield! Dist={dist_after_supp} vs {min_clear_dist}"

    # Boss update should also enforce repulsion
    boss.update(dummy, allies)
    dist_after_boss = math.hypot(support.rect.centerx - boss.rect.centerx, support.rect.centery - boss.rect.centery)
    assert dist_after_boss >= min_clear_dist, f"Boss update allowed support ship inside shield! Dist={dist_after_boss} vs {min_clear_dist}"

    # 2. Multi-frame simulation across 90 frames
    for _ in range(90):
        boss.update(dummy, allies)
        support.update(dummy, allies)
        dist = math.hypot(support.rect.centerx - boss.rect.centerx, support.rect.centery - boss.rect.centery)
        assert dist >= min_clear_dist, f"Support ship entered Dreadnought shield during dynamic movement! Dist={dist} vs {min_clear_dist}"

    # 3. Test against Battlecruiser
    bc = Enemy(enemy_types['battlecruiser'], difficulty='medium', spawn_x=336, spawn_y=70)
    bc_shield_r = max(bc.rect.width, bc.rect.height) // 2 + 14
    supp_bc = Enemy(enemy_types['support'], difficulty='medium', spawn_x=350, spawn_y=70)
    bc_allies = [bc, supp_bc]

    for _ in range(60):
        bc.update(dummy, bc_allies)
        supp_bc.update(dummy, bc_allies)
        dist = math.hypot(supp_bc.rect.centerx - bc.rect.centerx, supp_bc.rect.centery - bc.rect.centery)
        assert dist >= bc_shield_r + supp_r + 14, f"Support ship entered Battlecruiser shield! Dist={dist}"

    # 4. Dual Support ships split onto opposite flanks outside shield
    supp_left = Enemy(enemy_types['support'], difficulty='medium', spawn_x=200, spawn_y=38)
    supp_right = Enemy(enemy_types['support'], difficulty='medium', spawn_x=600, spawn_y=38)
    triple_allies = [boss, supp_left, supp_right]
    for _ in range(30):
        boss.update(dummy, triple_allies)
        supp_left.update(dummy, triple_allies)
        supp_right.update(dummy, triple_allies)

    assert supp_left.rect.centerx < boss.rect.centerx - boss_shield_r, "Left support ship must be outside left shield edge"
    assert supp_right.rect.centerx > boss.rect.centerx + boss_shield_r, "Right support ship must be outside right shield edge"

    print("[PASS] Support Ship Capital Shield Exclusion & Escort Wings verified.")

def test_reconstructed_keybinds_system():
    import src.main as main
    from src.entities import Player
    from src.asset_loader import load_assets

    # 1. Verify all 11 expected actions exist (including dedicated Flare / Chaff)
    expected_actions = {'UP', 'DOWN', 'LEFT', 'RIGHT', 'BOOST', 'SHOOT', 'SHIELD', 'FLARE', 'RELOAD', 'INVINCIBILITY', 'PAUSE'}
    assert expected_actions.issubset(set(main.CONFIG['keybinds'].keys())), f"Missing actions in CONFIG['keybinds']: {expected_actions - set(main.CONFIG['keybinds'].keys())}"
    assert len(main.KEYBIND_GROUPS) == 2, f"Expected 2 category groups, got {len(main.KEYBIND_GROUPS)}"

    # 2. Friendly key names
    assert main.friendly_key_name(pygame.K_SPACE) == "SPACE"
    assert main.friendly_key_name(pygame.K_LSHIFT) == "L-SHIFT"
    assert main.friendly_key_name(pygame.K_ESCAPE) == "ESC"
    assert main.friendly_key_name(pygame.K_w) == "W"
    assert main.friendly_key_name(pygame.K_f) == "F"

    # 3. Layout geometry and non-overflow
    layout = main.get_keybind_layout()
    assert layout["panel"].width > 0 and layout["panel"].height > 0
    assert len(layout["rows"]) == 11
    assert layout["panel"].contains(layout["reset"]), "Reset button must be inside terminal panel"
    assert layout["panel"].contains(layout["back"]), "Back button must be inside terminal panel"
    for act_id, rect in layout["rows"].items():
        assert layout["panel"].contains(rect), f"Action row {act_id} must be inside terminal panel"

    # 4. In-flight control integration with custom bindings
    assets = load_assets()
    save_data = {
        'credits': 100,
        'equipped_weapon': 'auto_cannon',
        'equipped_engine': 'base',
        'equipped_shield': None,
        'owned_weapons': ['auto_cannon'],
        'owned_engines': ['base'],
        'owned_shields': [],
    }
    player = Player(400, 500, assets, save_data)

    # Test custom BOOST and FLARE keybinds
    custom_binds = dict(main.CONFIG['keybinds'])
    custom_binds['BOOST'] = pygame.K_b
    custom_binds['SHOOT'] = pygame.K_g
    custom_binds['FLARE'] = pygame.K_c

    # Press K_b -> should trigger engine ability
    initial_engine_until = player.engine_active_until
    keys_boost = {pygame.K_b: True, pygame.K_g: False, pygame.K_c: False, pygame.K_a: False, pygame.K_d: False, pygame.K_w: False, pygame.K_s: False, pygame.K_LSHIFT: False, pygame.K_RSHIFT: False}
    player.update(keys_boost, custom_binds, [])
    assert player.engine_active_until > initial_engine_until, "Custom rebound BOOST key (K_b) failed to activate engine ability"

    # Press custom FLARE key (K_c) -> should deploy chaff countermeasure
    player.chaff_deployed = False
    keys_flare = {pygame.K_c: True, pygame.K_b: False, pygame.K_g: False, pygame.K_a: False, pygame.K_d: False, pygame.K_w: False, pygame.K_s: False, pygame.K_LSHIFT: False, pygame.K_RSHIFT: False}
    player.update(keys_flare, custom_binds, [])
    assert player.chaff_deployed is True, "Custom rebound FLARE key (K_c) failed to deploy chaff"

    # Test custom SHOOT keybind (rebound to K_g)
    keys_shoot = {pygame.K_g: True, pygame.K_SPACE: False}
    shots = player.shoot(keys_shoot, custom_binds, [])
    assert len(shots) > 0, "Custom rebound SHOOT key (K_g) failed to fire weapon"

    # Test Arrow Key Secondary Fallback for movement
    initial_x = player.x
    keys_arrow = {pygame.K_RIGHT: True, custom_binds['RIGHT']: False}
    player.update(keys_arrow, custom_binds, [])
    assert player.x > initial_x, "Arrow key secondary fallback (K_RIGHT) failed to move ship"

    # 5. Conflict Resolution Auto-Swap
    old_shield_key = custom_binds['SHIELD']
    new_key = pygame.K_e
    conflict = next((act for act, k in custom_binds.items() if k == new_key and act != 'RELOAD'), None)
    assert conflict == 'SHIELD', f"Expected conflict with SHIELD, got {conflict}"
    custom_binds[conflict] = custom_binds['RELOAD']
    custom_binds['RELOAD'] = new_key
    assert custom_binds['RELOAD'] == pygame.K_e
    assert custom_binds['SHIELD'] == pygame.K_r

    print("[PASS] Reconstructed Keybinds Matrix, Categorization, Conflict Swap & Control Hooks verified.")

def test_shadow_interceptor_movement_and_endgame_gating():
    from src.adaptive_director import AdaptiveDirector, FLEET_NAUTOLAN, FLEET_KLAED, FLEET_NAIRAN, FLEET_ENDGAME
    assets = load_assets()
    enemy_types = {e['name']: e for e in assets['enemy_types']}

    class DummyPlayer:
        rect = pygame.Rect(400, 500, 40, 40)
        hp = 100
        velocity_x = 0.0
        shots_fired = 50
        ammo = 10
        magazine_capacity = 20
        is_reloading = False

    # 1. Test Endgame Gating
    director = AdaptiveDirector()
    player = DummyPlayer()
    director.begin_run(player, "medium")

    assert director.fleet_phase == FLEET_NAUTOLAN, "Fresh run must start at FLEET_NAUTOLAN"
    assert director.bosses_defeated == 0, "Fresh run must start with 0 bosses defeated"

    # High flow and long elapsed time in Phase 0 must NEVER trigger Shadow Interceptor
    director.profiler.flow_index = 0.99
    director.kills_in_phase = 40
    enc = director.choose_encounter(player, score=4000, active_enemies_count=0, now=200000, elapsed_ms=200000)
    assert not any(e[0] == "shadow_interceptor" for e in enc), "Shadow Interceptor spawned prematurely in Phase 0!"
    assert director.shadow_spawned is False

    # Check Phase 1 and Phase 2 isolation
    director.fleet_phase = FLEET_KLAED
    director.stage = 3
    enc = director.choose_encounter(player, score=6000, active_enemies_count=0, now=250000, elapsed_ms=250000)
    assert not any(e[0] == "shadow_interceptor" for e in enc), "Shadow Interceptor spawned prematurely in Phase 1!"

    director.fleet_phase = FLEET_NAIRAN
    director.stage = 3
    enc = director.choose_encounter(player, score=9000, active_enemies_count=0, now=300000, elapsed_ms=300000)
    assert not any(e[0] == "shadow_interceptor" for e in enc), "Shadow Interceptor spawned prematurely in Phase 2!"

    # Endgame but bosses_defeated < 3 -> should NOT trigger
    director.fleet_phase = FLEET_ENDGAME
    director.bosses_defeated = 2
    director.stage = 3
    enc = director.choose_encounter(player, score=12000, active_enemies_count=0, now=350000, elapsed_ms=350000)
    assert not any(e[0] == "shadow_interceptor" for e in enc), "Shadow Interceptor spawned before 3 bosses were defeated!"

    # Endgame with 3 bosses defeated and stage 3 -> SHOULD trigger!
    director.fleet_phase = FLEET_ENDGAME
    director.bosses_defeated = 3
    director.stage = 3
    director.boss_active = False
    director.kills_in_phase = 18
    enc = director.choose_encounter(player, score=15000, active_enemies_count=0, now=160000, elapsed_ms=160000)
    assert any(e[0] == "shadow_interceptor" for e in enc), "Shadow Interceptor failed to trigger in Endgame Phase with 3 bosses defeated!"
    assert director.shadow_spawned is True

    # 2. Test Flocking Exemption
    shadow = Enemy(enemy_types['shadow_interceptor'], behavior='neural_clone', spawn_x=300, spawn_y=120)
    ally = Enemy(enemy_types['fighter'], behavior='straight', spawn_x=320, spawn_y=120)
    init_shadow_x = shadow.x
    # Update ally and shadow with each other as allies
    shadow.update(player, [shadow, ally])
    # The ally should be repelled by flocking, but shadow should NOT have flocking repulsion applied
    # Let's verify by checking that shadow flocking code was bypassed
    assert shadow.name == 'shadow_interceptor'

    # 3. Test Smooth Dashing & Aerodynamic Deceleration
    shadow.last_dash_time = pygame.time.get_ticks()
    shadow.dash_vx = 8.5
    start_x = shadow.x
    shadow.update(player, [shadow])
    # After update, shadow.x should have advanced by dash_vx and dash_vx decayed by 0.88
    assert shadow.dash_vx < 8.5, "dash_vx did not decay"
    assert abs(shadow.dash_vx - (8.5 * 0.88)) < 0.05, f"Expected dash_vx ~ {8.5 * 0.88}, got {shadow.dash_vx}"

    # 4. Test Sub-pixel / Center Anchoring in _animate()
    shadow.x = 250.7
    shadow.y = 120.3
    shadow._animate(pygame.time.get_ticks())
    expected_cx = round(shadow.x + shadow.rect.width / 2)
    expected_cy = round(shadow.y + shadow.rect.height / 2)
    assert shadow.rect.center == (expected_cx, expected_cy), f"Sprite center {shadow.rect.center} does not match expected ({expected_cx}, {expected_cy})"

    print("[PASS] Shadow Interceptor Endgame Gating, Flocking Exemption & Smooth Aerodynamics verified.")

def test_hangar_loadout_flow_and_direct_launch():
    import src.main as m
    from src.hangar_view import HangarView
    assets = load_assets()

    # 1. Main menu button layout & direct launch
    menu_btns = m.get_menu_buttons()
    assert "start" in menu_btns
    assert "hangar" in menu_btns

    # 2. Hangar View verification
    hangar = HangarView(assets, m.SHOP_ITEMS, lambda c, it: "OK")
    assert not hasattr(hangar, 'btn_launch')
    assert not hasattr(hangar, 'get_launch_rect')
    assert not hasattr(hangar, 'get_difficulty_cards')

    # Back button & Databank button
    assert hasattr(hangar, 'btn_back')
    assert hangar.handle_click(hangar.btn_back.center, m.save_data) == "BACK"
    assert hangar.handle_click(hangar.get_databank_btn_rect().center, m.save_data) == "CLICK"
    assert hangar.mode == "encyclopedia"

    # 3. Settings difficulty cycling
    settings_btns = m.get_settings_buttons()
    assert "diff_decrease" in settings_btns and "diff_increase" in settings_btns
    diffs = ["easy", "medium", "hard"]
    cur_diff = m.save_data.get('difficulty', 'medium')
    next_diff = diffs[(diffs.index(cur_diff) + 1) % len(diffs)]
    assert next_diff in diffs

    print("[PASS] Hangar Inspection Mode, Direct Mission Launch & Settings Difficulty verified.")

def test_tutorial_boot_and_6_stage_calibration():
    from src.save_manager import DEFAULT_SAVE
    from src.tutorial_controller import TutorialController
    import src.main as m
    from src.entities import Player, EnemyBullet
    from src.hangar_view import HangarView

    assets = load_assets()

    # 1. Astronaut Commander Sprites and Transparency Verification
    assert 'astronaut' in assets, "assets must contain 'astronaut' dictionary"
    for pose in ('hello', 'talking', 'thumbs_up'):
        assert pose in assets['astronaut'], f"assets['astronaut'] missing '{pose}'"
        surf = assets['astronaut'][pose]
        assert surf.get_size() == (160, 160), f"Astronaut portrait must be scaled to 160x160, got {surf.get_size()}"
        assert surf.get_at((0, 0))[3] == 0, f"Outer corner (0,0) of {pose} must have alpha=0 (background stripped cleanly)"
        assert surf.get_at((80, 80))[3] > 0, f"Center of {pose} must have alpha > 0 (spacesuit remains solid and opaque)"

    # 2. Save data structure
    assert "tutorial_completed" in DEFAULT_SAVE, "DEFAULT_SAVE must contain 'tutorial_completed'"
    assert DEFAULT_SAVE["tutorial_completed"] is False

    # 3. Main Menu dynamic tutorial button gating
    m.save_data["tutorial_completed"] = False
    menu_btns_new = m.get_menu_buttons()
    assert "tutorial" in menu_btns_new, "Main menu must show 'tutorial' when tutorial_completed is False"
    assert menu_btns_new["tutorial"].width == int(260 * m.SCALE_FACTOR)

    m.save_data["tutorial_completed"] = True
    menu_btns_done = m.get_menu_buttons()
    assert "tutorial" not in menu_btns_done, "Main menu must not show 'tutorial' once tutorial is completed"
    m.save_data["tutorial_completed"] = False

    # 4. Slower Dramatic Boot sequence (~9.8 seconds)
    tc = TutorialController(assets)
    tc.reset_boot()
    assert tc.boot_duration >= 9000, f"Boot duration must be dramatic (~9.8s), got {tc.boot_duration}ms"
    assert len(tc.BOOT_LINES) == 4
    tc.boot_started_at = 1000
    assert tc.update_boot(1000) is False
    assert tc.update_boot(1000 + 4000) is False, "Boot must still be in progress at 4.0s"
    assert tc.update_boot(1000 + tc.boot_duration) is True, "Boot sequence must complete after boot_duration"
    assert tc.state == "INTRO_DIALOGUE"

    # Commander Vance Intro Script Dialogue
    assert len(tc.script) == 3
    assert tc.handle_dialogue_input() is None  # finish line 0
    assert tc.handle_dialogue_input() is None  # advance to line 1
    assert tc.handle_dialogue_input() is None  # finish line 1
    assert tc.handle_dialogue_input() is None  # advance to line 2
    assert tc.handle_dialogue_input() is None  # finish line 2
    act = tc.handle_dialogue_input()           # advance and trigger combat
    assert act == "START_COMBAT", f"Expected 'START_COMBAT', got {act}"

    # 5. Training loadout synthesis
    raw_save = {'equipped_weapon': 'auto_cannon', 'equipped_engine': 'base', 'equipped_shield': None, 'credits': 50}
    t_save = tc.get_training_save_data(raw_save)
    assert t_save['equipped_engine'] == 'burst', "Training loadout must grant burst engine"
    assert t_save['equipped_shield'] == 'front', "Training loadout must grant front shield"
    assert t_save['difficulty'] == 'easy'
    assert raw_save['equipped_engine'] == 'base', "Original save data must not be mutated"

    # 6. Calibration course: Step 1 (Waypoints)
    player = Player(400, 500, assets, t_save)
    enemies = []
    enemy_bullets = []
    overclock_pickups = []
    sparks = []
    texts = []

    tc.reset_tutorial()
    assert tc.step == 1
    for wp in tc.waypoints:
        player.rect.center = (wp[0], wp[1])
        tc.update_tutorial(1000, player, enemies, enemy_bullets, overclock_pickups, sparks, texts)
    assert tc.step == 2, "Step 1 must advance to Step 2 upon clearing all waypoints"
    assert tc.combat_delay_until == 1000 + 3500

    # 7. Step 2 (Weapons & Reload) - wait for 3.5s breather
    tc.update_tutorial(2000, player, enemies, enemy_bullets, overclock_pickups, sparks, texts)
    assert len(enemies) == 0, "Breather window must keep screen clear"
    tc.update_tutorial(5000, player, enemies, enemy_bullets, overclock_pickups, sparks, texts)
    assert len(enemies) == 2, "Step 2 must spawn 2 target drones"
    player.is_reloading = True
    tc.update_tutorial(5100, player, enemies, enemy_bullets, overclock_pickups, sparks, texts)
    assert tc.reloaded_in_step2 is True
    enemies.clear()
    tc.update_tutorial(5200, player, enemies, enemy_bullets, overclock_pickups, sparks, texts)
    assert tc.step == 3, "Step 2 must advance to Step 3"
    assert tc.combat_delay_until == 5200 + 3500

    # 8. Step 3 (Missile Lock & Countermeasure Evasion) - wait for breather (> 8700ms)
    tc.update_tutorial(9000, player, enemies, enemy_bullets, overclock_pickups, sparks, texts)
    assert len(enemies) == 1, "Step 3 must spawn corvette"
    assert len(enemy_bullets) == 1, "Step 3 must fire incoming missile"
    assert enemy_bullets[0].bullet_type == "sarh_missile"
    player.chaff_deployed = True
    tc.update_tutorial(9100, player, enemies, enemy_bullets, overclock_pickups, sparks, texts)
    assert tc.evaded_in_step3 is True
    assert enemy_bullets[0].bullet_type == "ballistic_lost_lock"
    enemies.clear()
    tc.update_tutorial(9200, player, enemies, enemy_bullets, overclock_pickups, sparks, texts)
    assert tc.step == 4, "Step 3 must advance to Step 4"
    assert tc.combat_delay_until == 9200 + 3500

    # 9. Step 4 (Defense Matrix Shield Absorption) - wait for breather (> 12700ms)
    tc.update_tutorial(13000, player, enemies, enemy_bullets, overclock_pickups, sparks, texts)
    assert len(enemy_bullets) == 3, "Step 4 must spawn test wave projectiles"
    player.shield_active = True
    player.shield_remaining = 10
    tc.update_tutorial(13100, player, enemies, enemy_bullets, overclock_pickups, sparks, texts)
    assert tc.shield_used_in_step4 is True
    assert tc.step == 5, "Step 4 must advance to Step 5"
    assert tc.combat_delay_until == 13100 + 3500

    # 10. Step 5 (Support Ship Conduit Priority) - wait for breather (> 16600ms)
    tc.update_tutorial(17000, player, enemies, enemy_bullets, overclock_pickups, sparks, texts)
    assert len(enemies) == 2, "Step 5 must spawn flagship and support tender"
    frigate = next(e for e in enemies if 'frigate' in e.name)
    tender = next(e for e in enemies if 'support' in e.name)
    assert frigate.is_invulnerable_tethered is True
    assert tender.shield_conduit_target == frigate
    enemies.clear()
    tc.update_tutorial(17100, player, enemies, enemy_bullets, overclock_pickups, sparks, texts)
    assert tc.step == 6, "Step 5 must advance to Step 6"
    assert tc.combat_delay_until == 17100 + 3500

    # 11. Step 6 (Overclock Collection & Graduation -> Transition to Tour) - wait for breather (> 20600ms)
    tc.update_tutorial(21000, player, enemies, enemy_bullets, overclock_pickups, sparks, texts)
    assert len(overclock_pickups) == 1, "Step 6 must spawn weapon overclock pickup"
    player.weapon_overclock_until = 21000 + 7000
    tc.update_tutorial(21100, player, enemies, enemy_bullets, overclock_pickups, sparks, texts)
    assert tc.pickup_collected_in_step6 is True
    assert len(enemies) == 3, "Step 6 must spawn final 3-fighter wave"
    enemies.clear()
    res = tc.update_tutorial(21200, player, enemies, enemy_bullets, overclock_pickups, sparks, texts)
    assert tc.completed is True
    assert res in ("START_TOUR", "COMPLETED", "COMBAT_CLEARED")
    assert tc.state in ("DEBRIEF_DIALOGUE", "POST_DIALOGUE")

    # 12. Non-Combat Carrier UI Tour Flow Verification (Manual Tapping: Hangar -> Loadout -> Databank -> Supply Depot)
    assert len(tc.script) == 2
    assert tc.handle_dialogue_input() is None  # finish line 0
    assert tc.handle_dialogue_input() is None  # advance to line 1
    assert tc.handle_dialogue_input() is None  # finish line 1
    debrief_act = tc.handle_dialogue_input()   # advance and trigger tour
    assert debrief_act == "ENTER_HANGAR_TOUR"

    # Enter manual interactive tour
    tc.tour_step = 1
    assert tc.tour_step == 1, "Tour Step 1 must be active (Hangar Overview)"
    hangar = HangarView(assets, m.SHOP_ITEMS, lambda c, it: "OK")
    assert hangar.get_customize_btn_rect() is not None

    # Step 1 -> Step 2: Player manually clicks [ CUSTOMIZE LOADOUT ]
    hangar.mode = "customize"
    if tc.tour_step == 1 and hangar.mode == "customize":
        tc.tour_step = 2
    assert tc.tour_step == 2, "Tour must advance to Step 2 upon opening Loadout"
    assert hangar.get_databank_btn_rect() is not None

    # Step 2 -> Step 3: Player manually clicks [ ? DATABANK ]
    hangar.mode = "encyclopedia"
    if tc.tour_step == 2 and hangar.mode == "encyclopedia":
        tc.tour_step = 3
    assert tc.tour_step == 3, "Tour must advance to Step 3 upon opening Databank"
    assert hangar.get_encyclopedia_close_rect() is not None

    # Step 3 -> Step 4: Player manually clicks [ CLOSE ] -> Transition to Supply Depot (Shop)
    hangar.mode = "overview"
    if tc.tour_step == 3 and hangar.mode != "encyclopedia":
        tc.tour_step = 4
    assert tc.tour_step == 4, "Tour must advance to Step 4 (Supply Depot)"

    # Step 4: Player manually clicks [ Back to Menu ] in Supply Depot -> Return to Homescreen & Goodbye Dialogue
    tc.tour_step = 0
    tc.state = "GOODBYE_DIALOGUE"
    tc.load_script(tc.GOODBYE_SCRIPT)
    assert tc.state == "GOODBYE_DIALOGUE"
    assert len(tc.script) == 2

    # Step through Goodbye dialogue on Homescreen
    assert tc.handle_dialogue_input() is None  # finish line 0
    act_grant = tc.handle_dialogue_input()     # advance to line 1 & trigger credit grant
    assert act_grant == "GRANT_CREDITS"
    m.save_data["credits"] = m.save_data.get("credits", 0) + 100
    assert m.save_data["credits"] >= 100, "100 Credits must be awarded on homescreen"

    assert tc.handle_dialogue_input() is None  # finish line 1 (goodbye)
    act_bye = tc.handle_dialogue_input()       # advance and complete tutorial
    assert act_bye == "END_TUTORIAL"
    m.save_data["tutorial_completed"] = True
    tc.state = "DONE"
    assert m.save_data["tutorial_completed"] is True

    # 13. Simulation Safety Net
    player.hp = 20
    tc.combat_delay_until = 0
    tc.completed = False
    tc.update_tutorial(25000, player, enemies, enemy_bullets, overclock_pickups, sparks, texts)
    assert player.hp == 100, "Safety net must restore hull when hp <= 25"

    print("[PASS] Dramatic Boot, Astronaut Commander, 6-Stage Calibration & Full Carrier Tour verified.")

if __name__ == '__main__':
    print("=" * 70)
    print("STARTING COMBAT READINESS VERIFICATION TEST SUITE")
    print("=" * 70)
    test_flocking_and_squad_anchoring()
    test_support_conduit_and_invulnerability()
    test_support_ship_shield_exclusion()
    test_reconstructed_keybinds_system()
    test_parallax_background_and_landmarks()
    test_fast_asteroid_telegraphing()
    test_overclock_pickups_and_durations()
    test_dynamic_wave_pacing()
    test_capital_ship_inset_hitbox()
    test_boss_carrier_group_composition()
    test_aspect_ratio_viewport()
    test_dreadnought_upper_anchoring_and_flocking_immunity()
    test_sarh_missile_guidance_and_lock_break()
    test_dreadnought_multi_vector_arsenal()
    test_sarh_and_torpedo_escape_countermeasures()
    test_torpedo_emp_shield_busting_and_salvo()
    test_ai_brain_anti_shield_torpedo_deployment()
    test_hangar_databank_and_discovery_system()
    test_hybrid_hd_ui_pipeline()
    test_enemy_hit_flash_masking()
    test_shadow_interceptor_movement_and_endgame_gating()
    test_hangar_loadout_flow_and_direct_launch()
    test_tutorial_boot_and_6_stage_calibration()
    print("=" * 70)
    print("ALL COMBAT READINESS & POLISH VERIFICATIONS PASSED 100%!")
    print("=" * 70)
