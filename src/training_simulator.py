"""Offline synthetic AI-player training for the adaptive encounter director.

This is intentionally separate from Pygame and never touches save_data.json.
It simulates several player policies to pre-train a profile that can be
reviewed before importing it into the live game.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

from src.adaptive_director import AdaptiveDirector


RISK = {
    "patrol": 0.06, "debris_field": 0.13, "crossfire": 0.17,
    "bomber_run": 0.20, "hunter_pack": 0.23, "torpedo_strike": 0.27,
    "support_screen": 0.25, "frigate_barrage": 0.32, "battle_line": 0.38,
    "assault": 0.35, "dreadnought_siege": 0.48,
}

WEAPON_ADVANTAGE = {
    "auto_cannon": {"patrol", "hunter_pack", "crossfire"},
    "rockets": {"battle_line", "dreadnought_siege", "torpedo_strike"},
    "zapper": {"hunter_pack", "support_screen", "assault"},
    "big_space_gun": {"frigate_barrage", "battle_line", "dreadnought_siege"},
}


@dataclass
class Rect:
    center: tuple[float, float] = (400.0, 500.0)

    @property
    def centerx(self):
        return self.center[0]

    @property
    def centery(self):
        return self.center[1]


@dataclass
class SimulatedPlayer:
    equipped_weapon: str
    movement: float
    accuracy: float
    ability_rate: float
    hp: float = 100.0
    shots_fired: int = 0
    engine_uses: int = 0
    shield_uses: int = 0
    rect: Rect = None

    def __post_init__(self):
        self.rect = Rect()


PLAYSTYLES = (
    ("mobile_rockets", "rockets", 3.2, 0.66, 0.42),
    ("anchored_autocannon", "auto_cannon", 0.45, 0.72, 0.12),
    ("mobile_zapper", "zapper", 2.8, 0.62, 0.36),
    ("precision_big_gun", "big_space_gun", 1.1, 0.78, 0.20),
)


def action_name(encounter):
    names = {name for name, _behavior in encounter}
    if "dreadnought" in names:
        return "dreadnought_siege"
    if "battlecruiser" in names:
        return "battle_line"
    if "frigate" in names:
        return "frigate_barrage"
    if "support" in names:
        return "support_screen"
    if "torpedo" in names:
        return "torpedo_strike"
    if "bomber" in names:
        return "bomber_run"
    if names == {"asteroid"}:
        return "debris_field"
    if names == {"fighter", "scout"}:
        return "crossfire"
    if len(encounter) > 1:
        return "hunter_pack"
    return "patrol"


def run_training(seed=17, runs_per_style=12, steps_per_run=72):
    random.seed(seed)
    director = AdaptiveDirector()
    summaries = {name: {"runs": 0, "kills": 0, "damage": 0.0, "encounters": 0} for name, *_ in PLAYSTYLES}

    for name, weapon, movement, accuracy, ability_rate in PLAYSTYLES:
        for _run in range(runs_per_style):
            player = SimulatedPlayer(weapon, movement, accuracy, ability_rate)
            player.rect.center = (260.0, 500.0)
            director.begin_run(player)
            score = 0
            now = 0
            total_damage = 0.0
            total_kills = 0

            for step in range(steps_per_run):
                player.rect.center = (400 + ((step * movement) % 280) - 140, 500)
                if random.random() < ability_rate * 0.12:
                    player.engine_uses += 1
                if random.random() < ability_rate * 0.07:
                    player.shield_uses += 1
                director.observe_player(player)
                encounter = director.choose_encounter(player, score, 0, now, now)
                action = action_name(encounter)

                shots = max(2, round(9 + accuracy * 12))
                hit_ratio = max(0.05, min(0.98, random.gauss(accuracy, 0.09)))
                if action in WEAPON_ADVANTAGE[weapon]:
                    hit_ratio = min(0.98, hit_ratio + 0.13)
                hits = round(shots * hit_ratio)
                player.shots_fired += shots
                for _ in range(hits):
                    director.note_projectile_hit()

                kill_chance = min(0.95, hit_ratio + (0.16 if action in WEAPON_ADVANTAGE[weapon] else 0.0))
                kills = sum(random.random() < kill_chance for _enemy in encounter)
                for enemy_name, _behavior in encounter[:kills]:
                    director.note_enemy_destroyed(enemy_name)
                score += kills * 10

                risk = RISK[action] * (1.0 - min(0.48, movement * 0.09))
                risk *= 1.0 - min(0.22, (player.engine_uses + player.shield_uses) * 0.012)
                damage = max(0.0, random.gauss(risk * 13, 1.3))
                # The offline model represents a stream of independent combat
                # samples. Recovery keeps the dataset from collapsing into one
                # low-health context after a long synthetic session.
                player.hp = min(100.0, max(48.0, player.hp - damage + 1.8))
                total_damage += damage
                total_kills += kills
                now += 4500

            # Resolve the final pending encounter without selecting a new one.
            director._resolve_pending(player, score, now + 4500)
            summaries[name]["runs"] += 1
            summaries[name]["kills"] += total_kills
            summaries[name]["damage"] += total_damage
            summaries[name]["encounters"] += steps_per_run

    return director.export(), summaries


def write_results(output_dir):
    profile, summaries = run_training()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "adaptive_director_training.json").write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")

    ranked = sorted(profile["values"].items(), key=lambda item: item[1], reverse=True)[:12]
    lines = ["# Adaptive Director Offline Training Results", "", "Synthetic AI-player simulation; this does not modify `save_data.json`.", "", "## Dataset", "", "- Seed: 17", "- Playstyles: 4", "- Runs per playstyle: 12", "- Encounter decisions: 3,456", "", "## AI-player summaries", "", "| Playstyle | Encounters | Average kills/run | Average damage/run |", "| --- | ---: | ---: | ---: |"]
    for name, result in summaries.items():
        lines.append(f"| {name} | {result['encounters']} | {result['kills'] / result['runs']:.1f} | {result['damage'] / result['runs']:.1f} |")
    lines.extend(["", "## Highest learned context/action values", "", "| Context and encounter | Learned value | Samples |", "| --- | ---: | ---: |"])
    for key, value in ranked:
        lines.append(f"| {key} | {value:.3f} | {profile['counts'].get(key, 0)} |")
    lines.extend(["", "## Interpretation", "", "Higher values identify encounter choices that produced kills and score with manageable damage for that synthetic player context. The exported JSON profile is intentionally separate so it can be inspected or imported later without overwriting live player learning."])
    (output_dir / "adaptive_director_training_results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return profile, summaries


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    write_results(project_root.parent / "outputs")
