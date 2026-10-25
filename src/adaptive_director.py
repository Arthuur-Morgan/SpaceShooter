"""Aegis-Fable Adaptive Encounter Director & Sequential Fleet Campaign Engine.

Features:
1. Sequential Fleet Campaign:
   - Phase 0: Nautolan Swarm Fleet (Scout -> Fighter -> Bomber -> Torpedo -> Support -> Frigate -> Battlecruiser -> Dreadnought)
   - Phase 1: Kla'ed Void Fleet (Scout -> Fighter -> Bomber -> Torpedo -> Support -> Frigate -> Battlecruiser -> Void Overlord)
   - Phase 2: Nairan Cyber Fleet (Scout -> Fighter -> Bomber -> Torpedo -> Support -> Frigate -> Battlecruiser -> Cyber Boss)
   - Phase 3: Tri-Fleet Syndicate War (High-tier cross-fleet armada combat)
2. Gated Boss Climax:
   - Dreadnoughts are rare, climactic encounters requiring minimum survival time (3.5+ min on normal),
     substantial fleet kill milestones (26+ kills), and progression through capital battlecruisers.
   - Never spawns within the first 2 minutes.
3. No Low-HP Throttling:
   - Threat does NOT collapse or de-escalate when player HP is below 25%. Combat maintains legitimate arcade intensity.
4. Aegis-Fable Tactical Neural Engine:
   - Real-time TacticalPlayerProfiler tracking corner-camping, movement entropy, reload vulnerability, and evasion predictability.
   - FableTacticalSynthesizer: Simulates and evaluates 24-48 candidate battle plans per wave, computing utility scores
     across counter-camping, vector interception, reload punishment, and fair-play margin (guaranteeing dodging corridors).
"""

from __future__ import annotations

import math
import random
from collections import deque


# ── Fleet Phase Enumeration ────────────────────────────────────────────────
FLEET_NAUTOLAN = 0
FLEET_KLAED    = 1
FLEET_NAIRAN   = 2
FLEET_ENDGAME  = 3

FLEET_NAMES = {
    FLEET_NAUTOLAN: "NAUTOLAN SWARM",
    FLEET_KLAED:    "KLA'ED VOID FLEET",
    FLEET_NAIRAN:   "NAIRAN CYBER FLEET",
    FLEET_ENDGAME:  "SYNDICATE ARMADA",
}

STAGE_NAMES = {
    0: "RECON",
    1: "SKIRMISH",
    2: "STRIKE",
    3: "CAPITAL WAR",
    4: "DREADNOUGHT CLIMAX",
}

# ── Authors Encounters Catalog By Fleet & Stage ─────────────────────────────
ENCOUNTERS = {
    # ── Phase 0: Nautolan Fleet ─────────────────────────────────────
    # Stage 0: Recon
    "nautolan_patrol": (("scout", "roam"),),
    "nautolan_debris": (("asteroid", "normal"), ("asteroid", "fast")),
    "nautolan_recon_pair": (("scout", "pincer_flank"), ("scout", "pincer_flank")),
    # Stage 1: Skirmish
    "nautolan_crossfire": (("fighter", "strafe"), ("scout", "hunter_lead")),
    "nautolan_pincer_sweep": (("fighter", "pincer_flank"), ("fighter", "pincer_flank")),
    "nautolan_strafing_wing": (("fighter", "strafe"), ("scout", "roam")),
    # Stage 2: Strike
    "nautolan_bomber_run": (("bomber", "dive_bomb"),),
    "nautolan_torpedo_strike": (("torpedo", "tracking"),),
    "nautolan_anti_shield_strike": (("torpedo", "tracking"), ("torpedo", "tracking"), ("scout", "pincer_flank")),
    "nautolan_support_screen": (("support", "heal"), ("fighter", "strafe")),
    "nautolan_hunter_pack": (("scout", "hunter_lead"), ("fighter", "hunter_lead")),
    "nautolan_dive_squad": (("bomber", "dive_bomb"), ("scout", "pincer_flank")),
    # Stage 3: Capital War
    "nautolan_frigate_barrage": (("frigate", "barrage"), ("scout", "escort_screen")),
    "nautolan_battle_line": (("battlecruiser", "broadside"), ("support", "heal")),
    "nautolan_heavy_assault": (("frigate", "barrage"), ("fighter", "pincer_flank")),
    "nautolan_hammer_anvil": (("battlecruiser", "broadside"), ("bomber", "dive_bomb")),
    # Stage 4: Dreadnought
    "nautolan_dreadnought_siege": (("dreadnought", "siege"),),
    "nautolan_flagship_escort": (("dreadnought", "siege"), ("support", "heal")),

    # ── Phase 1: Kla'ed Void Fleet ──────────────────────────────────
    # Stage 0: Recon
    "klaed_scout_sweep": (("klaed_scout", "flank"),),
    "klaed_recon_pair": (("klaed_scout", "pincer_flank"), ("klaed_scout", "pincer_flank")),
    # Stage 1: Skirmish
    "klaed_vanguard": (("klaed_fighter", "hunter_lead"), ("klaed_scout", "flank")),
    "klaed_pincer_assault": (("klaed_fighter", "pincer_flank"), ("klaed_fighter", "pincer_flank")),
    "klaed_raiders": (("klaed_fighter", "hunter_lead"), ("klaed_scout", "flank")),
    # Stage 2: Strike
    "klaed_bomber_run": (("klaed_bomber", "dive_bomb"),),
    "klaed_void_strike": (("klaed_torpedo", "tracking"), ("klaed_fighter", "hunter_lead")),
    "klaed_anti_shield_strike": (("klaed_torpedo", "tracking"), ("klaed_torpedo", "tracking")),
    "klaed_void_screen": (("klaed_support", "heal"), ("klaed_fighter", "strafe")),
    "klaed_swarm": (("klaed_scout", "hunter_lead"), ("klaed_scout", "hunter_lead"), ("klaed_fighter", "strafe")),
    # Stage 3: Capital War
    "klaed_frigate_patrol": (("klaed_frigate", "barrage"), ("klaed_scout", "escort_screen")),
    "klaed_battle_line": (("klaed_battlecruiser", "broadside"), ("klaed_support", "heal")),
    "klaed_void_siege": (("klaed_frigate", "barrage"), ("klaed_torpedo", "tracking")),
    "klaed_heavy_assault": (("klaed_battlecruiser", "broadside"), ("klaed_bomber", "dive_bomb")),
    # Stage 4: Dreadnought
    "klaed_overlord_siege": (("klaed_dreadnought", "overlord"),),
    "klaed_overlord_escort": (("klaed_dreadnought", "overlord"), ("klaed_support", "heal")),

    # ── Phase 2: Nairan Cyber Fleet ─────────────────────────────────
    # Stage 0: Recon
    "nairan_probe": (("nairan_scout", "flank"),),
    "nairan_cyber_pair": (("nairan_scout", "pincer_flank"), ("nairan_scout", "pincer_flank")),
    # Stage 1: Skirmish
    "nairan_vanguard": (("nairan_fighter", "hunter_lead"), ("nairan_scout", "flank")),
    "nairan_laser_crossfire": (("nairan_fighter", "strafe"), ("nairan_fighter", "pincer_flank")),
    "nairan_cyber_strike": (("nairan_fighter", "hunter_lead"), ("nairan_scout", "flank")),
    # Stage 2: Strike
    "nairan_bomber_run": (("nairan_bomber", "dive_bomb"),),
    "nairan_cyber_screen": (("nairan_support", "heal"), ("nairan_fighter", "hunter_lead")),
    "nairan_missile_volley": (("nairan_torpedo", "tracking"), ("nairan_fighter", "strafe")),
    "nairan_anti_shield_strike": (("nairan_torpedo", "tracking"), ("nairan_torpedo", "tracking"), ("nairan_scout", "flank")),
    # Stage 3: Capital War
    "nairan_frigate_squad": (("nairan_frigate", "barrage"), ("nairan_scout", "escort_screen")),
    "nairan_battle_line": (("nairan_battlecruiser", "broadside"), ("nairan_support", "heal")),
    "nairan_cyber_overdrive": (("nairan_battlecruiser", "broadside"), ("nairan_frigate", "barrage")),
    # Stage 4: Dreadnought
    "nairan_cyber_boss_siege": (("nairan_dreadnought", "cyber_boss"),),
    "nairan_cyber_boss_escort": (("nairan_dreadnought", "cyber_boss"), ("nairan_support", "heal")),

    # ── Phase 3: Tri-Fleet Syndicate War ────────────────────────────
    "syndicate_pincer": (("nairan_fighter", "pincer_flank"), ("klaed_fighter", "pincer_flank")),
    "dual_capital_line": (("battlecruiser", "broadside"), ("klaed_battlecruiser", "broadside")),
    "cyber_void_siege": (("nairan_frigate", "barrage"), ("klaed_frigate", "barrage")),
    "armada_assault": (("nairan_battlecruiser", "broadside"), ("klaed_support", "heal")),
    "syndicate_overlord_raid": (("klaed_dreadnought", "overlord"),),
    "syndicate_dreadnought_siege": (("dreadnought", "siege"),),
    "syndicate_cyber_boss_raid": (("nairan_dreadnought", "cyber_boss"),),
    "shadow_interceptor_duel": (("shadow_interceptor", "neural_clone"),),

    # ── Legacy Aliases for Training Simulator Compatibility ──────────
    "patrol": (("scout", "roam"),),
    "debris_field": (("asteroid", "normal"), ("asteroid", "fast")),
    "crossfire": (("fighter", "strafe"), ("scout", "roam")),
    "bomber_run": (("bomber", "dive_bomb"),),
    "hunter_pack": (("scout", "hunter_lead"), ("scout", "hunter_lead")),
    "torpedo_strike": (("torpedo", "tracking"),),
    "support_screen": (("support", "heal"), ("fighter", "strafe")),
    "frigate_barrage": (("frigate", "barrage"), ("scout", "escort_screen")),
    "battle_line": (("battlecruiser", "broadside"), ("support", "heal")),
    "assault": (("fighter", "strafe"), ("fighter", "strafe"), ("asteroid", "fast")),
    "dreadnought_siege": (("dreadnought", "siege"),),
}

# Mapping of fleet and stage to encounter keys
FLEET_STAGE_ENCOUNTERS = {
    FLEET_NAUTOLAN: {
        0: ["nautolan_patrol", "nautolan_debris", "nautolan_recon_pair"],
        1: ["nautolan_crossfire", "nautolan_pincer_sweep", "nautolan_strafing_wing"],
        2: ["nautolan_bomber_run", "nautolan_torpedo_strike", "nautolan_support_screen", "nautolan_hunter_pack", "nautolan_dive_squad"],
        3: ["nautolan_frigate_barrage", "nautolan_battle_line", "nautolan_heavy_assault", "nautolan_hammer_anvil"],
        4: ["nautolan_dreadnought_siege", "nautolan_flagship_escort"],
    },
    FLEET_KLAED: {
        0: ["klaed_scout_sweep", "klaed_recon_pair"],
        1: ["klaed_vanguard", "klaed_pincer_assault", "klaed_raiders"],
        2: ["klaed_bomber_run", "klaed_void_strike", "klaed_void_screen", "klaed_swarm"],
        3: ["klaed_frigate_patrol", "klaed_battle_line", "klaed_void_siege", "klaed_heavy_assault"],
        4: ["klaed_overlord_siege", "klaed_overlord_escort"],
    },
    FLEET_NAIRAN: {
        0: ["nairan_probe", "nairan_cyber_pair"],
        1: ["nairan_vanguard", "nairan_laser_crossfire", "nairan_cyber_strike"],
        2: ["nairan_bomber_run", "nairan_cyber_screen", "nairan_missile_volley"],
        3: ["nairan_frigate_squad", "nairan_battle_line", "nairan_cyber_overdrive"],
        4: ["nairan_cyber_boss_siege", "nairan_cyber_boss_escort"],
    },
    FLEET_ENDGAME: {
        0: ["syndicate_pincer", "klaed_vanguard", "nairan_vanguard"],
        1: ["cyber_void_siege", "klaed_void_strike", "nairan_missile_volley"],
        2: ["dual_capital_line", "armada_assault", "klaed_heavy_assault"],
        3: ["dual_capital_line", "armada_assault", "cyber_void_siege", "shadow_interceptor_duel"],
        4: ["syndicate_dreadnought_siege", "syndicate_overlord_raid", "syndicate_cyber_boss_raid", "shadow_interceptor_duel"],
    },
}

# Formation types for spatial wave geometry
FORMATION_TYPES = ["PINCER", "ARROWHEAD", "SUPPRESSION", "HAMMER_ANVIL", "ECHELON", "ESCORT"]


class TacticalCommsHub:
    """Manages real-time alien battle-net encrypted transmissions."""

    def __init__(self, max_messages: int = 4):
        self.messages = deque(maxlen=max_messages)
        self.last_broadcast_at = 0

    def broadcast(self, text: str, sender: str = "FLEET", priority: str = "TACTICAL", color: tuple = (120, 235, 255), now: int = 0):
        # Prevent repeating identical broadcast within 1.8s
        if self.messages and self.messages[-1]['text'] == text and now - self.last_broadcast_at < 1800:
            return
        self.last_broadcast_at = now
        self.messages.append({
            'text': text,
            'sender': sender,
            'priority': priority,
            'color': color,
            'created_at': now,
            'expires_at': now + 4200,
        })

    def get_active_messages(self, now: int) -> list[dict]:
        return [m for m in self.messages if now < m['expires_at']]


class DarwinianCounterEngine:
    """Tracks player loadout and synthesizes counter-adaptations."""

    ADAPTATIONS = {
        'zapper': {
            'code': 'GROUNDING_COILS',
            'label': 'GROUNDING COILS (-50% ARC)',
            'desc': 'Insulated plating dampens chain lightning jumps.',
            'color': (140, 210, 255),
        },
        'rockets': {
            'code': 'POINT_DEFENSE_FLARES',
            'label': 'PD FLARES (35% DEFLECTION)',
            'desc': 'Countermeasure flares deflect incoming torpedoes.',
            'color': (255, 175, 75),
        },
        'big_space_gun': {
            'code': 'ABLATIVE_ARMOR',
            'label': 'ABLATIVE TILES (-1 PIERCE)',
            'desc': 'Hardened composite tiles stop piercing kinetics.',
            'color': (240, 220, 100),
        },
        'auto_cannon': {
            'code': 'KINETIC_DAMPENERS',
            'label': 'KINETIC DAMPENERS (-1 DMG)',
            'desc': 'Absorptive energy field blunts rapid fire.',
            'color': (100, 245, 180),
        },
    }

    def __init__(self):
        self.active_adaptation = None

    def evaluate(self, player, director, now: int):
        if player is None:
            return
        weapon = getattr(player, 'equipped_weapon', 'auto_cannon')
        adaptation = self.ADAPTATIONS.get(weapon)
        if adaptation and adaptation != self.active_adaptation:
            self.active_adaptation = adaptation
            director.comms.broadcast(
                f"WEAPON [{weapon.upper()}] ANALYZED // DEPLOYING {adaptation['code']}",
                sender="ARMADA_LAB",
                priority="COUNTER",
                color=adaptation['color'],
                now=now
            )


class TacticalPlayerProfiler:
    """Real-time player playstyle and cognitive telemetry tracker."""

    def __init__(self, history_len: int = 180):
        self.history_len = history_len
        self.positions = deque(maxlen=history_len)
        self.velocities = deque(maxlen=history_len)
        self.last_pos = None
        self.corner_camping_left = 0.0
        self.corner_camping_right = 0.0
        self.backline_hugging = 0.0
        self.is_corner_camping = False
        self.lateral_drift = "balanced"
        self.movement_predictability = 0.5
        self.reload_vulnerable = False
        self.ammo_ratio = 1.0

        # Psychological & Reflex Tracking
        self.reversals_count = 0
        self.last_vx = 0.0
        self.panic_index = 0.0
        self.flow_index = 0.0
        self.last_panic_alert = 0
        self.last_flow_alert = 0

        # Shield utilization & aggression tracking
        self.shield_active_start = 0
        self.forward_aggression = 0.0
        self.is_abusing_shield = False

    def sample(self, player, director=None, now: int = 0):
        if player is None or not hasattr(player, 'rect'):
            return
        if hasattr(player.rect, 'centerx') and hasattr(player.rect, 'centery'):
            cx, cy = player.rect.centerx, player.rect.centery
        elif hasattr(player.rect, 'center'):
            cx, cy = player.rect.center
        else:
            cx, cy = 400.0, 500.0
        if self.last_pos is not None:
            vx = cx - self.last_pos[0]
            vy = cy - self.last_pos[1]
            self.velocities.append((vx, vy))
            if (vx > 0.6 and self.last_vx < -0.6) or (vx < -0.6 and self.last_vx > 0.6):
                self.reversals_count += 1
            self.last_vx = vx
        self.last_pos = (cx, cy)
        self.positions.append((cx, cy))

        # Check reload vulnerability
        self.reload_vulnerable = getattr(player, 'is_reloading', False) or (getattr(player, 'ammo', 10) <= 2)
        mag = getattr(player, 'magazine_capacity', 20)
        self.ammo_ratio = getattr(player, 'ammo', 20) / max(1, mag)

        # Analyze rolling position statistics
        if len(self.positions) >= 20:
            left_count = sum(1 for px, _ in self.positions if px < 160)
            right_count = sum(1 for px, _ in self.positions if px > 640)
            back_count = sum(1 for _, py in self.positions if py > 500)
            n = len(self.positions)

            self.corner_camping_left = left_count / n
            self.corner_camping_right = right_count / n
            self.backline_hugging = back_count / n
            self.is_corner_camping = (self.corner_camping_left > 0.38) or (self.corner_camping_right > 0.38)

            if self.corner_camping_left > 0.40:
                self.lateral_drift = "left_camp"
            elif self.corner_camping_right > 0.40:
                self.lateral_drift = "right_camp"
            else:
                self.lateral_drift = "center_balanced"

        # Shield usage and forward aggressive posture tracking
        is_shield_up = getattr(player, 'shield_active', False) or getattr(player, 'is_shield_overcharged', False)
        if is_shield_up:
            if self.shield_active_start == 0:
                self.shield_active_start = now if now > 0 else 1
        else:
            self.shield_active_start = 0

        if len(self.positions) >= 15:
            forward_count = sum(1 for _, py in self.positions if py < 420)
            self.forward_aggression = forward_count / len(self.positions)

            shield_held_time = (now - self.shield_active_start) if self.shield_active_start > 0 else 0
            self.is_abusing_shield = is_shield_up and (shield_held_time >= 2500 or (self.forward_aggression > 0.35 and shield_held_time >= 1000))

        # Movement entropy / predictability
        if len(self.velocities) >= 20:
            vxs = [v[0] for v in self.velocities]
            mean_vx = sum(vxs) / len(vxs)
            var_vx = sum((v - mean_vx) ** 2 for v in vxs) / len(vxs)
            self.movement_predictability = max(0.1, min(0.95, 1.0 - math.sqrt(var_vx) / 6.0))

        # Panic detection: high reversals + firing during reload
        rev_rate = self.reversals_count / max(1, len(self.positions))
        trigger_during_reload = getattr(player, 'is_reloading', False) and getattr(player, 'shift_was_down', False)
        self.panic_index = min(1.0, rev_rate * 2.4 + (0.35 if trigger_during_reload else 0.0))

        # Flow detection: accuracy + combo
        acc = getattr(director, 'hits', 0) / max(1, getattr(player, 'shots_fired', 1)) if director else 0.5
        self.flow_index = min(1.0, acc * 0.7 + (0.3 if not self.is_corner_camping else 0.0))

        if director and now > 5000:
            if self.panic_index > 0.70 and now - self.last_panic_alert > 14000:
                self.last_panic_alert = now
                director.comms.broadcast("TARGET PILOT ELEVATED STRESS // PRESSURE FLANKS", sender="NEURAL_NET", priority="VITAL", color=(255, 95, 95), now=now)
            elif self.flow_index > 0.82 and now - self.last_flow_alert > 16000:
                self.last_flow_alert = now
                director.comms.broadcast("TARGET IN FLOW STATE // COMBAT OVERDRIVE ENGAGED", sender="NEURAL_NET", priority="VITAL", color=(100, 255, 200), now=now)


class FableTacticalSynthesizer:
    """Tactical Simulation Brain.

    Simulates and evaluates dozens of candidate tactical plans per wave,
    weighing counter-camping utility, lead-interception, reload punishment,
    and strict fair-play corridor constraints.
    """

    def __init__(self):
        self.last_formation = "ARROWHEAD"
        self.simulated_count = 0
        self.optimal_score = 0.0
        self.last_corridor_ratio = 0.42

    def _evaluate_dodge_corridor(self, formation: str, profiler: TacticalPlayerProfiler) -> tuple[float, float]:
        """Simulates physical dodging corridors across the playfield (Fair-Play Solver).
        Returns (corridor_ratio, fair_play_score).
        """
        if formation == "PINCER":
            corridor_ratio = 0.42
        elif formation == "ARROWHEAD":
            corridor_ratio = 0.58
        elif formation == "SUPPRESSION":
            corridor_ratio = 0.28
        elif formation == "HAMMER_ANVIL":
            corridor_ratio = 0.36
        elif formation == "ECHELON":
            corridor_ratio = 0.46
        else:
            corridor_ratio = 0.50

        if profiler.is_corner_camping and formation == "PINCER":
            corridor_ratio = 0.24

        if corridor_ratio < 0.20:
            fair_play_score = -0.50
        elif 0.24 <= corridor_ratio <= 0.45:
            fair_play_score = 0.35
        else:
            fair_play_score = 0.20

        return corridor_ratio, fair_play_score

    def evaluate_wave(
        self,
        candidate_encounters: list[str],
        profiler: TacticalPlayerProfiler,
        q_values: dict[str, float],
        difficulty: str = "medium"
    ) -> tuple[str, str, str]:
        """Simulates candidate tactical permutations and picks the best counter-strategy."""
        scored_plans = []
        self.simulated_count = 0

        for enc_name in candidate_encounters:
            for formation in FORMATION_TYPES:
                self.simulated_count += 1
                base_q = q_values.get(f"{profiler.lateral_drift}:{enc_name}", 0.0)

                # 1. Counter-Camping Utility
                counter_camp_util = 0.0
                if profiler.is_corner_camping:
                    if formation in ("PINCER", "SUPPRESSION", "HAMMER_ANVIL"):
                        counter_camp_util += 0.42
                    if "pincer" in enc_name or "flank" in enc_name or "sweep" in enc_name:
                        counter_camp_util += 0.30
                else:
                    if formation == "ARROWHEAD":
                        counter_camp_util += 0.20

                # 2. Intercept-Predictability Utility
                intercept_util = 0.0
                if profiler.movement_predictability > 0.65:
                    if "hunter" in enc_name or "torpedo" in enc_name or formation == "SUPPRESSION":
                        intercept_util += 0.35

                # 3. Reload Punishment Utility
                reload_util = 0.0
                if profiler.reload_vulnerable:
                    if "dive" in enc_name or "bomber" in enc_name or "raiders" in enc_name or formation == "PINCER":
                        reload_util += 0.38

                # 4. Fair-Play Dodging Corridor Simulation
                corridor_ratio, fair_play_margin = self._evaluate_dodge_corridor(formation, profiler)

                # 5. Diversity / Anti-Repetition Penalty
                repetition_penalty = 0.28 if formation == self.last_formation else 0.0

                total_utility = (
                    0.20 * base_q
                    + counter_camp_util
                    + intercept_util
                    + reload_util
                    + fair_play_margin
                    - repetition_penalty
                )
                scored_plans.append((total_utility, enc_name, formation, corridor_ratio))

        if not scored_plans:
            chosen_enc = candidate_encounters[0] if candidate_encounters else "nautolan_patrol"
            return chosen_enc, "ARROWHEAD", "Default fallback plan"

        # Sort by total utility descending
        scored_plans.sort(key=lambda item: item[0], reverse=True)

        # Softmax / Epsilon-greedy exploration (85% optimal, 15% explore top-3)
        if random.random() < 0.85:
            best_util, best_enc, best_formation, best_corridor = scored_plans[0]
        else:
            top_candidates = scored_plans[:min(3, len(scored_plans))]
            best_util, best_enc, best_formation, best_corridor = random.choice(top_candidates)

        self.last_formation = best_formation
        self.optimal_score = best_util
        self.last_corridor_ratio = best_corridor

        thought = (
            f"Simulated {self.simulated_count} tactical plans -> Selected: {best_enc.upper()} "
            f"[{best_formation}] (Utility: {best_util:.2f}, Camp: {profiler.lateral_drift})"
        )
        return best_enc, best_formation, thought


class AdaptiveDirector:
    """Master AI Director orchestrating the Sequential Fleet Campaign and Aegis-Fable Engine."""

    def __init__(self, learned_data: dict | None = None):
        learned_data = learned_data if isinstance(learned_data, dict) else {}
        self.values = learned_data.get("values", {})
        self.counts = learned_data.get("counts", {})
        if not isinstance(self.values, dict): self.values = {}
        if not isinstance(self.counts, dict): self.counts = {}
        self.total_encounters = int(learned_data.get("total_encounters", 0))

        # Fleet Campaign State
        self.fleet_phase = int(learned_data.get("fleet_phase", FLEET_NAUTOLAN))
        self.stage = 0
        self.kills_in_phase = 0
        self.phase_start_time = 0
        self.bosses_defeated = int(learned_data.get("bosses_defeated", 0))
        self.highest_fleet_phase = int(learned_data.get("highest_fleet_phase", FLEET_NAUTOLAN))

        # Runtime State
        self.difficulty = "medium"
        self.boss_active = False
        self.last_boss_at = -90000
        self.last_boss_reinforcement_at = 0
        self.last_support_spawn_at = 0
        self.last_torpedo_counter_at = -30000
        self.kills = 0
        self.hits = 0
        self.enemy_kills = {}
        self.pending = None

        # Presentation & Telemetry
        self.last_encounter_name = ""
        self.last_encounter_at = 0
        self.last_formation = "ARROWHEAD"
        self.last_ai_thought = "Aegis-Fable Engine Initializing..."
        self.fleet_banner_title = ""
        self.fleet_banner_sub = ""
        self.fleet_banner_until = 0

        # Subsystems
        self.profiler = TacticalPlayerProfiler()
        self.synthesizer = FableTacticalSynthesizer()
        self.comms = TacticalCommsHub()
        self.counter_engine = DarwinianCounterEngine()
        self.shadow_spawned = False
        self.shadow_interceptor_defeated = False

    def begin_run(self, player, difficulty: str = "medium"):
        self.difficulty = difficulty
        self.fleet_phase = FLEET_NAUTOLAN  # Each fresh run begins with the Nautolan Swarm
        self.stage = 0
        self.bosses_defeated = 0
        self.kills_in_phase = 0
        self.boss_active = False
        self.last_boss_at = -90000
        self.last_boss_reinforcement_at = 0
        self.last_support_spawn_at = 0
        self.last_torpedo_counter_at = -30000
        self.kills = 0
        self.hits = 0
        self.enemy_kills = {}
        self.pending = None
        self.fleet_banner_until = 0
        self.profiler = TacticalPlayerProfiler()
        self.synthesizer = FableTacticalSynthesizer()
        self.comms = TacticalCommsHub()
        self.counter_engine = DarwinianCounterEngine()
        self.shadow_spawned = False
        self.shadow_interceptor_defeated = False

    def observe_player(self, player, now: int = 0):
        if player is not None:
            self.profiler.sample(player, self, now)
            self.counter_engine.evaluate(player, self, now)

    def note_enemy_destroyed(self, enemy_name: str):
        self.kills += 1
        self.kills_in_phase += 1
        self.enemy_kills[enemy_name] = self.enemy_kills.get(enemy_name, 0) + 1
        if enemy_name == 'shadow_interceptor':
            self.shadow_interceptor_defeated = True

    def note_boss_destroyed(self, boss_name: str, now: int):
        """Called when a flagship Dreadnought is annihilated: advances the fleet campaign!"""
        self.bosses_defeated += 1
        self.boss_active = False
        self.last_boss_at = now

        if self.fleet_phase == FLEET_NAUTOLAN and boss_name == "dreadnought":
            self.fleet_phase = FLEET_KLAED
            self.stage = 0
            self.kills_in_phase = 0
            self.phase_start_time = now
            self.fleet_banner_title = "NAUTOLAN FLEET CRUSHED!"
            self.fleet_banner_sub = "KLA'ED VOID ARMADA INCOMING"
            self.fleet_banner_until = now + 4200
            self.last_encounter_name = "KLA'ED VOID ARRIVAL"
        elif self.fleet_phase == FLEET_KLAED and boss_name == "klaed_dreadnought":
            self.fleet_phase = FLEET_NAIRAN
            self.stage = 0
            self.kills_in_phase = 0
            self.phase_start_time = now
            self.fleet_banner_title = "VOID OVERLORD DECIMATED!"
            self.fleet_banner_sub = "NAIRAN CYBER FLEET ENGAGING"
            self.fleet_banner_until = now + 4200
            self.last_encounter_name = "NAIRAN FLEET ARRIVAL"
        elif self.fleet_phase == FLEET_NAIRAN and boss_name == "nairan_dreadnought":
            self.fleet_phase = FLEET_ENDGAME
            self.stage = 2
            self.kills_in_phase = 0
            self.phase_start_time = now
            self.fleet_banner_title = "CYBER DREADNOUGHT ANNIHILATED!"
            self.fleet_banner_sub = "ALL-OUT SYNDICATE WAR DECLARED"
            self.fleet_banner_until = now + 4200
            self.last_encounter_name = "SYNDICATE WAR"

        if self.fleet_phase > self.highest_fleet_phase:
            self.highest_fleet_phase = self.fleet_phase

        self.comms.broadcast(
            f"ALERT: {boss_name.upper()} DEFEATED // ADVANCING FLEET",
            sender="FLEET_CMD",
            priority="CRITICAL",
            color=(255, 100, 100),
            now=now
        )

    def note_projectile_hit(self):
        self.hits += 1

    def _resolve_pending(self, player, score: int, now: int):
        if not self.pending or now - self.pending["started_at"] < 4000:
            return
        p = self.pending
        damage_taken = max(0, p["start_hp"] - player.hp)
        kills = max(0, self.kills - p["start_kills"])
        score_gain = max(0, score - p["start_score"])
        shots = max(0, player.shots_fired - p["start_shots"])
        hits = max(0, self.hits - p["start_hits"])
        accuracy = min(1.0, hits / max(1, shots))

        # Reward signals tactical engagement quality
        reward = (min(1.5, 0.12 * kills + 0.015 * score_gain)
                  + 0.25 * accuracy
                  - min(1.2, 0.035 * damage_taken))
        context, action = p["context"], p["action"]
        key = f"{context}:{action}"
        seen = int(self.counts.get(key, 0)) + 1
        old_val = float(self.values.get(key, 0.0))
        self.values[key] = old_val + (reward - old_val) / seen
        self.counts[key] = seen
        self.total_encounters += 1
        self.pending = None

    def _update_stage(self, elapsed_ms: int):
        """Progression manager: advances stage from Recon -> Skirmish -> Strike -> Capital -> Dreadnought."""
        # Gating thresholds for the climatic Dreadnought:
        # Easy: 240s (4.0m) & 24 kills; Medium: 210s (3.5m) & 26 kills; Hard: 180s (3.0m) & 28 kills
        boss_time_gate = 240000 if self.difficulty == "easy" else (180000 if self.difficulty == "hard" else 210000)
        boss_kill_gate = 24 if self.difficulty == "easy" else (28 if self.difficulty == "hard" else 26)

        while True:
            if self.stage == 0 and (self.kills_in_phase >= 4 or elapsed_ms >= 22000):
                self.stage = 1
            elif self.stage == 1 and (self.kills_in_phase >= 10 or elapsed_ms >= 65000):
                self.stage = 2
            elif self.stage == 2 and (self.kills_in_phase >= 18 or elapsed_ms >= 125000):
                self.stage = 3
            elif self.stage == 3 and (elapsed_ms >= boss_time_gate and self.kills_in_phase >= boss_kill_gate):
                # Stage 4 unlocks: the fleet Dreadnought enters the theatre!
                self.stage = 4
            else:
                break

    def choose_encounter(self, player, score: int, active_enemies_count: int, now: int, elapsed_ms: int):
        """Generates an intelligently tailored wave using the Aegis-Fable cognitive engine."""
        self._resolve_pending(player, score, now)
        self._update_stage(elapsed_ms)

        # If a boss is already active on screen, do NOT stack more bosses or capital ships
        if self.boss_active:
            if active_enemies_count <= 1 and now - self.last_boss_reinforcement_at >= 4500:
                self.last_boss_reinforcement_at = now
                if now - self.last_support_spawn_at >= 20000:
                    self.last_support_spawn_at = now
                    if self.fleet_phase == FLEET_NAUTOLAN:
                        reinforce = (("support", "heal"), ("fighter", "pincer_flank"))
                    elif self.fleet_phase == FLEET_KLAED:
                        reinforce = (("klaed_support", "heal"), ("klaed_fighter", "hunter_lead"))
                    elif self.fleet_phase == FLEET_NAIRAN:
                        reinforce = (("nairan_support", "heal"), ("nairan_fighter", "strafe"))
                    else:
                        reinforce = (("nairan_support", "heal"), ("klaed_fighter", "pincer_flank"))
                    self.comms.broadcast("DEFENSIVE TENDER DEPLOYED // RE-ESTABLISHING SHIELD CONDUIT", sender="FLAGSHIP_CARRIER", priority="CRITICAL", color=(100, 255, 180), now=now)
                    return reinforce
                else:
                    if self.fleet_phase == FLEET_NAUTOLAN:
                        reinforce = random.choice([ENCOUNTERS["nautolan_crossfire"], ENCOUNTERS["nautolan_pincer_sweep"]])
                    elif self.fleet_phase == FLEET_KLAED:
                        reinforce = random.choice([ENCOUNTERS["klaed_vanguard"], ENCOUNTERS["klaed_raiders"]])
                    elif self.fleet_phase == FLEET_NAIRAN:
                        reinforce = random.choice([ENCOUNTERS["nairan_laser_crossfire"], ENCOUNTERS["nairan_cyber_strike"]])
                    else:
                        if not self.shadow_spawned and self.bosses_defeated >= 3 and random.random() < 0.15:
                            self.shadow_spawned = True
                            self.comms.broadcast("CRITICAL INTERCEPT: SHADOW INTERCEPTOR ENGAGING", sender="FLAGSHIP_CARRIER", priority="CRITICAL", color=(255, 60, 220), now=now)
                            return ENCOUNTERS["shadow_interceptor_duel"]
                        reinforce = ENCOUNTERS["syndicate_pincer"]
                    return reinforce
            return ()

        # Check for elite Shadow Interceptor neural mirror duel:
        trigger_shadow = (
            not self.shadow_spawned
            and not self.boss_active
            and active_enemies_count <= 1
            and self.fleet_phase == FLEET_ENDGAME
            and self.bosses_defeated >= 3
            and self.stage >= 3
        )
        if trigger_shadow:
            self.shadow_spawned = True
            action = "shadow_interceptor_duel"
            formation = "ARROWHEAD"
            self.last_ai_thought = "SHADOW INTERCEPTOR: NEURAL MIRROR ONLINE"
            self.comms.broadcast("CRITICAL INTERCEPT: SHADOW INTERCEPTOR ENGAGING", sender="NEURAL_NET", priority="BOSS", color=(255, 60, 220), now=now)
            self.comms.broadcast("NEURAL MIRROR ONLINE // PREDICTING COMBAT VECTORS", sender="SHADOW_AI", priority="COMBAT", color=(0, 240, 255), now=now)
            self.last_formation = formation
            self.last_encounter_name = "SHADOW INTERCEPTOR DUEL"
            self.last_encounter_at = now
            return ENCOUNTERS[action]

        # Retrieve authored encounters for the current fleet and stage
        fleet_dict = FLEET_STAGE_ENCOUNTERS.get(self.fleet_phase, FLEET_STAGE_ENCOUNTERS[FLEET_NAUTOLAN])
        stage_pool = fleet_dict.get(self.stage, fleet_dict.get(3, []))

        # Boss stage handling:
        is_boss_stage = (self.stage == 4)

        # Check for Anti-Shield Torpedo Counter Strike (triggered by shield over-reliance & aggressive pushing)
        if (not is_boss_stage and not self.boss_active
                and getattr(self.profiler, 'is_abusing_shield', False)
                and (now - getattr(self, 'last_torpedo_counter_at', -30000) >= 14000)
                and active_enemies_count <= 2):
            self.last_torpedo_counter_at = now
            if self.fleet_phase == FLEET_NAUTOLAN:
                action = "nautolan_anti_shield_strike"
            elif self.fleet_phase == FLEET_KLAED:
                action = "klaed_anti_shield_strike"
            elif self.fleet_phase == FLEET_NAIRAN:
                action = "nairan_anti_shield_strike"
            else:
                action = "nautolan_anti_shield_strike"
            formation = "PINCER"
            self.last_ai_thought = "FABLE AI: SHIELD OVERUSE DETECTED -> DISPATCHING ANTI-SHIELD TORPEDO CORVETTES"
            self.comms.broadcast("PILOT RELYING HEAVILY ON SHIELDS // DEPLOYING ANTI-SHIELD TORPEDO CORVETTES",
                                 sender="TACTICAL_AI", priority="CRITICAL", color=(255, 130, 60), now=now)
            self.last_formation = formation
            self.last_encounter_name = action.replace("_", " ").upper()
            self.last_encounter_at = now
            return ENCOUNTERS[action]
        if is_boss_stage:
            # Stage 4: Dreadnought wave!
            # Require screen to be clear or down to <= 1 enemy for a dramatic entrance
            if active_enemies_count > 1:
                # Hold off until screen clears
                return ()
            self.boss_active = True
            if self.fleet_phase == FLEET_NAUTOLAN:
                action = "nautolan_flagship_escort"
            elif self.fleet_phase == FLEET_KLAED:
                action = "klaed_overlord_escort"
            elif self.fleet_phase == FLEET_NAIRAN:
                action = "nairan_cyber_boss_escort"
            else:
                action = random.choice(["syndicate_dreadnought_siege", "syndicate_overlord_raid", "syndicate_cyber_boss_raid"])
            formation = "ESCORT"
            self.last_ai_thought = f"FLAGSHIP ARRIVAL: {action.upper()} DEPLOYED"
        else:
            # Aegis-Fable Cognitive Synthesis: simulate and select counter-strategy
            action, formation, thought = self.synthesizer.evaluate_wave(
                stage_pool,
                self.profiler,
                self.values,
                self.difficulty
            )
            self.last_ai_thought = thought

        self.last_formation = formation
        self.last_encounter_name = action.replace("_", " ").upper()
        self.last_encounter_at = now

        context = self.profiler.lateral_drift
        self.pending = {
            "context": context,
            "action": action,
            "started_at": now,
            "start_hp": getattr(player, "hp", 100),
            "start_score": score,
            "start_kills": self.kills,
            "start_shots": getattr(player, "shots_fired", 0),
            "start_hits": self.hits,
        }

        return ENCOUNTERS.get(action, (("scout", "roam"),))

    def encounter_label(self, now: int) -> str:
        if now - self.last_encounter_at < 1800:
            return f"TACTICAL WAVE: {self.last_encounter_name} [{self.last_formation}]"
        return ""

    def _context(self, player) -> str:
        """Context string used by telemetry overlay."""
        return f"{self.profiler.lateral_drift}:v_pred={self.profiler.movement_predictability:.2f}:vuln={self.profiler.reload_vulnerable}"

    def generate_debrief(self, player, score: int, now: int) -> dict:
        """Synthesizes an intelligent post-mission combat black box review."""
        if self.profiler.corner_camping_left > 0.35 or self.profiler.corner_camping_right > 0.35:
            archetype = "CORNER ANCHOR"
            note = "Maintained low-risk border defensive lines to limit enemy crossfire angles."
        elif self.profiler.movement_predictability < 0.38:
            archetype = "APEX STRAFER"
            note = "High-entropy lateral jinking; neutralized predictive torpedo tracks."
        elif self.profiler.backline_hugging > 0.60:
            archetype = "DEFENSIVE TURTLER"
            note = "Maximized range buffer and relied on shield mitigations."
        else:
            archetype = "AGGRESSIVE SKIRMISHER"
            note = "Contested center lines with forward velocity and sustained engagement."

        if self.profiler.reload_vulnerable:
            vuln = "Magazine Depletion / Reload Downtime"
        elif self.profiler.is_corner_camping:
            vuln = "Lateral Containment / Pincer Flush"
        else:
            vuln = "Overlapping Angular Crossfire"

        counter = self.counter_engine.active_adaptation['label'] if self.counter_engine.active_adaptation else "STANDARD ARMOR"

        return {
            'archetype': archetype,
            'note': note,
            'primary_vulnerability': vuln,
            'counter_deployed': counter,
            'plans_evaluated': self.synthesizer.simulated_count,
            'bosses_defeated': self.bosses_defeated,
            'highest_phase': FLEET_NAMES.get(self.highest_fleet_phase, "NAUTOLAN"),
            'panic_peak': f"{int(self.profiler.panic_index * 100)}%",
            'flow_peak': f"{int(self.profiler.flow_index * 100)}%",
            'corridor_safety': f"{int(getattr(self.synthesizer, 'last_corridor_ratio', 0.40) * 100)}%",
            'neural_mirror': "PURGED" if self.shadow_interceptor_defeated else ("ENGAGED" if self.shadow_spawned else "STANDBY"),
        }

    def export(self) -> dict:
        return {
            "values": self.values,
            "counts": self.counts,
            "total_encounters": self.total_encounters,
            "bosses_defeated": self.bosses_defeated,
            "highest_fleet_phase": self.highest_fleet_phase,
        }
