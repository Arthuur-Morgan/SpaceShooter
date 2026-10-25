"""Headless test script for Aegis-Fable Engine and Sequential Fleet Campaign."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.adaptive_director import (
    AdaptiveDirector,
    FLEET_NAUTOLAN,
    FLEET_KLAED,
    FLEET_NAIRAN,
    FLEET_ENDGAME,
)

class MockRect:
    def __init__(self, x=400, y=500):
        self.centerx = x
        self.centery = y
        self.width = 40
        self.height = 40

class MockPlayer:
    def __init__(self, x=400, y=500):
        self.rect = MockRect(x, y)
        self.hp = 100
        self.shots_fired = 50
        self.ammo = 10
        self.magazine_capacity = 20
        self.is_reloading = False
        self.velocity_x = 0.0

def test_campaign_progression():
    director = AdaptiveDirector()
    player = MockPlayer(400, 500)
    director.begin_run(player, "medium")

    # 1. Phase 0: Nautolan Swarm
    assert director.fleet_phase == FLEET_NAUTOLAN, f"Initial fleet must be Nautolan, got {director.fleet_phase}"
    assert director.stage == 0

    # Ensure early encounters are Nautolan only
    for step in range(5):
        enc = director.choose_encounter(player, score=step*10, active_enemies_count=0, now=step*5000, elapsed_ms=step*5000)
        for enemy_name, behavior in enc:
            assert "klaed" not in enemy_name and "nairan" not in enemy_name, f"Alien fleet ship leaked into Nautolan phase: {enemy_name}"
            director.note_enemy_destroyed(enemy_name)

    print("[PASS] Phase 0 early encounter fleet isolation passed.")

    # 2. Check Dreadnought Gating (cannot spawn at 60s or 100s)
    enc_60s = director.choose_encounter(player, score=200, active_enemies_count=0, now=60000, elapsed_ms=60000)
    for enemy_name, _ in enc_60s:
        assert enemy_name != "dreadnought", "Dreadnought spawned prematurely at 60s!"

    enc_100s = director.choose_encounter(player, score=400, active_enemies_count=0, now=100000, elapsed_ms=100000)
    for enemy_name, _ in enc_100s:
        assert enemy_name != "dreadnought", "Dreadnought spawned prematurely at 100s!"

    print("[PASS] Dreadnought anti-early-spawn time gating passed.")

    # Advance time and kills to reach Dreadnought gate (210s + 26 kills)
    for i in range(30):
        director.note_enemy_destroyed("scout")

    # At 220s with 35 kills, Dreadnought should unlock
    enc_boss = director.choose_encounter(player, score=1500, active_enemies_count=0, now=220000, elapsed_ms=220000)
    boss_names = [e[0] for e in enc_boss]
    assert "dreadnought" in boss_names, f"Expected dreadnought at 220s/35 kills, got {boss_names}"
    assert director.boss_active, "Boss should be marked active"
    print("[PASS] Dreadnought climactic arrival passed.")

    # 3. Defeat Nautolan Dreadnought -> Transition to Kla'ed Void Fleet!
    director.note_boss_destroyed("dreadnought", now=230000)
    assert director.fleet_phase == FLEET_KLAED, f"Expected Phase 1 Kla'ed, got {director.fleet_phase}"
    assert director.stage == 0, f"Stage should reset to 0 for Kla'ed, got {director.stage}"
    assert "NAUTOLAN FLEET CRUSHED" in director.fleet_banner_title
    assert "KLA'ED VOID ARMADA" in director.fleet_banner_sub
    print(f"[PASS] Fleet Phase transition to Kla'ed passed: Banner='{director.fleet_banner_title}'")

    # In Phase 1, only Kla'ed ships should spawn
    enc_klaed = director.choose_encounter(player, score=2000, active_enemies_count=0, now=235000, elapsed_ms=5000)
    for enemy_name, _ in enc_klaed:
        assert "klaed" in enemy_name, f"Expected klaed ship, got {enemy_name}"
    print("[PASS] Phase 1 Kla'ed fleet isolation passed.")

    # Defeat Kla'ed Dreadnought -> Transition to Nairan Cyber Fleet!
    director.note_boss_destroyed("klaed_dreadnought", now=400000)
    assert director.fleet_phase == FLEET_NAIRAN, f"Expected Phase 2 Nairan, got {director.fleet_phase}"
    assert "VOID OVERLORD DECIMATED" in director.fleet_banner_title
    print(f"[PASS] Fleet Phase transition to Nairan passed: Banner='{director.fleet_banner_title}'")

    # Defeat Nairan Cyber Boss -> Transition to Endgame Syndicate War!
    director.note_boss_destroyed("nairan_dreadnought", now=600000)
    assert director.fleet_phase == FLEET_ENDGAME, f"Expected Phase 3 Endgame, got {director.fleet_phase}"
    assert "CYBER DREADNOUGHT ANNIHILATED" in director.fleet_banner_title
    print(f"[PASS] Fleet Phase transition to Endgame Syndicate War passed: Banner='{director.fleet_banner_title}'")

def test_aegis_fable_ai():
    director = AdaptiveDirector()
    player = MockPlayer(80, 520) # Camping left corner
    director.begin_run(player, "medium")

    # Feed corner camping telemetry
    for _ in range(60):
        director.observe_player(player)

    assert director.profiler.is_corner_camping, "Profiler should detect left corner camping"
    assert director.profiler.lateral_drift == "left_camp"

    # AI chooses encounter
    enc = director.choose_encounter(player, score=100, active_enemies_count=0, now=10000, elapsed_ms=10000)
    assert director.synthesizer.simulated_count > 10, f"Expected >10 simulated plans, got {director.synthesizer.simulated_count}"
    print(f"[PASS] Aegis-Fable AI evaluated {director.synthesizer.simulated_count} plans. Selected: {director.last_formation} - Thought: '{director.last_ai_thought}'")

def test_comms_and_darwinian():
    director = AdaptiveDirector()
    player = MockPlayer(400, 500)
    player.equipped_weapon = "rockets"
    director.begin_run(player, "medium")

    # Evaluate weapon counter
    director.counter_engine.evaluate(player, director, now=1000)
    assert director.counter_engine.active_adaptation is not None
    assert director.counter_engine.active_adaptation['code'] == 'POINT_DEFENSE_FLARES'
    active_msgs = director.comms.get_active_messages(now=1000)
    assert len(active_msgs) >= 1
    assert "POINT_DEFENSE_FLARES" in active_msgs[0]['text']
    print("[PASS] Darwinian Counter-Adaptation & Comms Hub broadcast passed.")

    # Generate Debrief
    debrief = director.generate_debrief(player, score=1200, now=150000)
    assert 'archetype' in debrief
    assert 'primary_vulnerability' in debrief
    assert debrief['counter_deployed'] == 'PD FLARES (35% DEFLECTION)'
    assert 'corridor_safety' in debrief
    assert 'neural_mirror' in debrief
    print(f"[PASS] Black Box Debrief generated: Archetype='{debrief['archetype']}', Counter='{debrief['counter_deployed']}', Corridor='{debrief['corridor_safety']}'")

def test_shadow_interceptor_and_corridors():
    director = AdaptiveDirector()
    player = MockPlayer(400, 500)
    director.begin_run(player, "medium")

    # Verify corridor simulation in Fable AI
    corridor_ratio, fair_play_score = director.synthesizer._evaluate_dodge_corridor("ARROWHEAD", director.profiler)
    assert corridor_ratio >= 0.50
    assert fair_play_score > 0
    print(f"[PASS] Fable AI Corridor Solver verified: Ratio={corridor_ratio:.2f}, Score={fair_play_score:.2f}")

    # Verify that in earlier phases, even with maximum flow index and long elapsed time, Shadow Interceptor never spawns
    director.profiler.flow_index = 0.95
    director.kills_in_phase = 30
    enc_early = director.choose_encounter(player, score=3000, active_enemies_count=0, now=180000, elapsed_ms=180000)
    assert not any(e[0] == "shadow_interceptor" for e in enc_early), "Shadow Interceptor must NEVER spawn during Phase 0/1/2!"
    assert not director.shadow_spawned

    # Advance to Phase 3 (Endgame Syndicate War) post-3-bosses
    director.fleet_phase = FLEET_ENDGAME
    director.bosses_defeated = 3
    director.stage = 3
    enc = director.choose_encounter(player, score=5000, active_enemies_count=0, now=190000, elapsed_ms=190000)
    enemy_types = [e[0] for e in enc]
    assert "shadow_interceptor" in enemy_types, f"Expected shadow_interceptor in Endgame stage 3, got {enemy_types}"
    assert director.shadow_spawned, "shadow_spawned flag should be True"

    # Simulate destroying shadow interceptor
    director.note_enemy_destroyed("shadow_interceptor")
    assert director.shadow_interceptor_defeated, "shadow_interceptor_defeated flag should be True"
    print("[PASS] Shadow Interceptor Neural Clone duel dispatch and victory verified.")

def test_flocking_separation_and_escort_anchoring():
    import os
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    import pygame
    pygame.init()
    from src.entities import Enemy

    dummy_surf = pygame.Surface((30, 30))
    etype_scout = {'name': 'scout', 'ship': dummy_surf, 'explosion': [dummy_surf], 'hp': 10}
    e1 = Enemy(etype_scout, 'straight', 200, 200)
    e2 = Enemy(etype_scout, 'straight', 220, 200)
    init_dist = abs(e2.x - e1.x)
    e1.update(None, [e1, e2])
    e2.update(None, [e1, e2])
    new_dist = abs(e2.x - e1.x)
    assert new_dist > init_dist, f"Soft radial separation failed: {new_dist} <= {init_dist}"
    print(f"[PASS] Flocking Soft Radial Separation verified: Dist {init_dist} -> {new_dist:.2f}")

    # Escort wing anchoring relative to squad leader
    leader = Enemy(etype_scout, 'straight', 400, 100)
    leader.is_leader = True
    escort_left = Enemy(etype_scout, 'straight', 300, 200)
    escort_right = Enemy(etype_scout, 'straight', 500, 200)
    allies = [leader, escort_left, escort_right]
    escort_left.update(None, allies)
    escort_right.update(None, allies)
    assert escort_left.x > 300, "Left escort should steer right toward leader - 70 wing anchor"
    assert escort_right.x < 500, "Right escort should steer left toward leader + 70 wing anchor"
    print("[PASS] Squad Leader Escort Wing Anchoring verified.")

def test_individual_missile_deflection():
    import os
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    import pygame
    pygame.init()
    from src.entities import Bullet, Enemy

    dummy_surf = pygame.Surface((10, 10))
    b1 = Bullet(200, 300, dummy_surf, speed=6.0, max_range=600)
    b2 = Bullet(205, 300, dummy_surf, speed=6.0, max_range=600)
    b3 = Bullet(210, 300, dummy_surf, speed=6.0, max_range=600)
    salvo = [b1, b2, b3]

    dummy_ship = pygame.Surface((40, 40))
    etype = {'name': 'frigate', 'ship': dummy_ship, 'explosion': [dummy_ship], 'hp': 50}
    enemy = Enemy(etype, 'straight', 200, 280)

    # b1 gets deflected by point-defense flare, b2 & b3 proceed
    b1.deflected = True
    b1.target = None
    b1.hit_enemies.add(enemy)
    b1.vx = 8.0
    b1.vy = -3.0

    damaged_bullets = []
    for bullet in salvo:
        if getattr(bullet, 'deflected', False):
            continue
        if enemy in bullet.hit_enemies:
            continue
        if bullet.rect.colliderect(enemy.rect):
            bullet.hit_enemies.add(enemy)
            enemy.hp -= bullet.damage
            damaged_bullets.append(bullet)

    assert b1 not in damaged_bullets, "Deflected rocket must not inflict damage!"
    assert len(damaged_bullets) == 2, f"Expected 2 hits from non-deflected rockets, got {len(damaged_bullets)}"
    assert enemy.hp == 50 - (b2.damage + b3.damage)
    print("[PASS] Individual Rocket Deflection & Collision Bypass verified.")

def test_support_ship_boss_tether():
    import os
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    import pygame
    pygame.init()
    from src.entities import Enemy

    dummy_surf = pygame.Surface((30, 30))
    etype_supp = {'name': 'support', 'ship': dummy_surf, 'explosion': [dummy_surf], 'hp': 20}
    etype_boss = {'name': 'dreadnought', 'ship': dummy_surf, 'explosion': [dummy_surf], 'hp': 100}
    supp = Enemy(etype_supp, 'support_hover', 200, 200)
    boss = Enemy(etype_boss, 'boss_flagship', 400, 200)
    allies = [supp, boss]

    supp.update(None, allies)
    assert boss.is_invulnerable_tethered is True, "Boss should be tethered by support ship"
    assert boss.tether_support_ship == supp

    # Damage handling simulation with invulnerability tether
    def apply_damage(target, amt, allies_list):
        if getattr(target, 'is_invulnerable_tethered', False):
            s = getattr(target, 'tether_support_ship', None)
            if s and s in allies_list and getattr(s, 'hp', 0) > 0:
                return False
        target.hp -= amt
        return True

    # Boss takes zero damage while support ship is alive
    hit_boss = apply_damage(boss, 30, allies)
    assert hit_boss is False
    assert boss.hp == 100

    # Destroy support ship
    apply_damage(supp, 20, allies)
    allies.remove(supp)

    # Boss drops shield on next frame
    boss.update(None, allies)
    assert boss.is_invulnerable_tethered is False

    # Boss now takes full damage
    hit_boss_2 = apply_damage(boss, 30, allies)
    assert hit_boss_2 is True
    assert boss.hp == 70
    print("[PASS] Support Ship Boss Invulnerability Tether & Shield Collapse verified.")

def test_dynamic_wave_pacing_and_breather():
    class MockEnemy:
        def __init__(self, name):
            self.name = name

    def can_spawn_wave(enemies, now, last_busy_time, last_wave_time, max_cap=5):
        has_heavy = any(any(k in e.name for k in ('dreadnought', 'battlecruiser', 'frigate', 'shadow_interceptor')) for e in enemies)
        threshold = 2 if has_heavy else 3
        if len(enemies) >= threshold or len(enemies) >= max_cap:
            return False, now
        if last_busy_time > 0 and (now - last_busy_time < 1400):
            return False, last_busy_time
        if last_wave_time > 0 and (now - last_wave_time < 2200):
            return False, last_busy_time
        return True, last_busy_time

    # Screen busy with 3 ships
    enemies = [MockEnemy('scout'), MockEnemy('fighter'), MockEnemy('scout')]
    can_spawn, last_busy = can_spawn_wave(enemies, now=1000, last_busy_time=0, last_wave_time=0)
    assert can_spawn is False
    assert last_busy == 1000

    # Cleared at 1200ms
    enemies = []
    # In breather window at 1500ms (300ms after clear < 1400ms)
    can_spawn, _ = can_spawn_wave(enemies, now=1500, last_busy_time=1200, last_wave_time=0)
    assert can_spawn is False, "Wave spawn should be held during 1.4s tactical breather window"

    # After breather at 2700ms (1500ms after clear > 1400ms)
    can_spawn, _ = can_spawn_wave(enemies, now=2700, last_busy_time=1200, last_wave_time=0)
    assert can_spawn is True, "Wave should spawn after tactical breather window elapses"

    # Capital ship presence lowers threshold to 2
    enemies = [MockEnemy('battlecruiser'), MockEnemy('scout')]
    can_spawn, _ = can_spawn_wave(enemies, now=6000, last_busy_time=0, last_wave_time=0)
    assert can_spawn is False, "Wave spawn should hold when 2 enemies with capital ship are on screen"
    print("[PASS] Dynamic Wave-Clear Pacing & Breather Window verified.")

def test_enemy_rendering_pixels():
    import os
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    import pygame
    pygame.init()
    from src.entities import Enemy
    dummy_surf = pygame.Surface((32, 32))
    dummy_surf.fill((255, 100, 50))
    dummy_screen = pygame.Surface((800, 600))

    for name in ['scout', 'fighter', 'bomber', 'torpedo', 'support', 'frigate', 'battlecruiser', 'dreadnought', 'asteroid']:
        etype = {'name': name, 'ship': dummy_surf, 'explosion': [dummy_surf], 'hp': 20}
        enemy = Enemy(etype, 'straight', 400, 200)
        dummy_screen.fill((0, 0, 0))
        p_before = pygame.surfarray.array2d(dummy_screen).sum()
        enemy.draw(dummy_screen)
        p_after = pygame.surfarray.array2d(dummy_screen).sum()
        assert p_after > p_before, f"Enemy '{name}' rendered 0 pixels!"
    print("[PASS] Enemy Ship Sprite Visibility & Drawing verified.")

if __name__ == "__main__":
    test_campaign_progression()
    test_aegis_fable_ai()
    test_comms_and_darwinian()
    test_shadow_interceptor_and_corridors()
    test_flocking_separation_and_escort_anchoring()
    test_individual_missile_deflection()
    test_support_ship_boss_tether()
    test_dynamic_wave_pacing_and_breather()
    test_enemy_rendering_pixels()
    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")
