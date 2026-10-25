# SPACESHOOTER: Tactical Void Combat

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Pygame-CE](https://img.shields.io/badge/Pygame--CE-2.5%2B-informational.svg)](https://pyga.me/)
[![Tests](https://img.shields.io/badge/Test%20Suite-64%2F64%20Passing-brightgreen.svg)]()
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()

> A high-performance, tactical top-down sci-fi space combat simulator built with **Pygame Community Edition (Pygame-CE)**. Features adaptive enemy AI brains, multi-tiered fleet warfare across 3 distinct alien armada factions, authentic military carrier flight-deck operations, and a hybrid HD render pipeline.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
  - [1. Military Onboarding & Narrative Tutorial](#1-military-onboarding--narrative-tutorial)
  - [2. Carrier Flight Deck & Inspection Bay](#2-carrier-flight-deck--inspection-bay)
  - [3. Fleet Databank & Overclock Drops](#3-fleet-databank--overclock-drops)
  - [4. Aegis-Fable AI Brain & Combat Dynamics](#4-aegis-fable-ai-brain--combat-dynamics)
  - [5. 3 Alien Fleets & Endgame Syndicate War](#5-3-alien-fleets--endgame-syndicate-war)
  - [6. Tactical Countermeasures & Overclocks](#6-tactical-countermeasures--overclocks)
  - [7. Hybrid HD Rendering & Gamepad Support](#7-hybrid-hd-rendering--gamepad-support)
- [Flight Controls & Keybindings](#flight-controls--keybindings)
- [Installation & Quickstart](#installation--quickstart)
- [Verification & Test Suites](#verification--test-suites)
- [Project Architecture](#project-architecture)
- [Credits & Acknowledgments](#credits--acknowledgments)

---

## Overview

In **SpaceShooter**, you pilot an advanced strike interceptor deployed from the frontline carrier flagship against the invading **Nautolan Swarm**, **Kla'ed Void Fleet**, and **Nairan Cyber Armada**. 

Survive dynamic fleet phases, break radar missile locks with point-defense flares, dismantle capital ship shield conduits, and overcome Darwinian counter-adaptations synthesized in real-time by the enemy battle network.

---

## Key Features

### 1. Military Onboarding & Narrative Tutorial
- **Red Alert Cold Boot**: Atmospheric emergency sequence with pulsating hazard screens, CRT scanlines, and typewriter breach alarms.
- **Commander Vance RPG Dialogue**: High-tech comms dialogue with authentic Astronaut Commander portraits (`hello`, `talking`, `thumbs_up`) delivering voice-less military briefings with clean, solid poses (zero chatter/mouth jitter).
- **6-Stage Combat Simulator**: Step-by-step calibration covering thruster vectoring, weapon reload pacing, missile lock evasion, shield matrix absorption, support conduit priority, and overclock wipe.
- **3.5s Breather Windows**: Combat pacing buffers between simulation waves allow pilots to read HUD instruction telemetry without feeling rushed.
- **Manual Tap Carrier Tour**: Interactive walkthrough guiding new pilots through the live carrier deck (Docking Bay $\rightarrow$ Modular Armory $\rightarrow$ Databank $\rightarrow$ Supply Depot) using pulsing holographic target brackets.
- **Homescreen Graduation**: Commander Vance delivers a final farewell transmission directly on the Bridge homescreen with an immediate **+100 Credits** deployment grant.

### 2. Carrier Flight Deck & Inspection Bay
- **Hangar Bay**: Atmospheric hangar environment with hydraulic steam vents, runway guide lights, and animated 2.5x player ship sprite with active thruster idle animations.
- **Live Specifications Table**: Segmented stat gauges displaying dynamic Firepower, Mobility, and Defense ratings.
- **Modular Armory Drawer**: Hot-swap weapons, propulsion cores, and defense matrices before sorties with instant visual ship updates.

### 3. Fleet Databank & Overclock Drops
- **Alien Encyclopedia**: Catalogs 26 distinct entities with live animated holograms, custom lore, and real stat metrics (Hull HP, Speed, DPS, Ramming Damage).
- **Silhouette Discovery**: Undefeated ships appear as darkened silhouettes with scrambled scan frequencies until destroyed in combat.
- **Dedicated "DROPS" Tab**: Detailed catalog of in-run Overclocks with rotating 3D-styled wireframe pickup animations.

### 4. Aegis-Fable AI Brain & Combat Dynamics
- **18 Simulated Tactical Plans**: The AI brain evaluates candidate tactical plans every frame to out-maneuver the pilot.
- **Corridor Fair-Play Solver**: Guarantees escape lanes through bullet hell waves to ensure encounters remain tactical rather than unfair.
- **Darwinian Counter-Adaptation**: Detects player behavioral patterns (e.g. missile dependency, corner camping) and deploys fleet counters broadcast across the intercepted Alien Battle-Net console.
- **Capital Shield Exclusion**: Friendly escort craft dynamically orbit and support capital ships without clipping inside capital energy barriers.

### 5. 3 Alien Fleets & Endgame Syndicate War
1. **Phase 0 — Nautolan Swarm**: Scouts, Fighters, Asteroid swarms, Torpedo corvettes, Frigates, and the Nautolan Dreadnought.
2. **Phase 1 — Kla'ed Void Fleet**: Fast, aggressive purple-tinted void ships, darting interceptors, and the 320-HP Void Overlord.
3. **Phase 2 — Nairan Cyber Fleet**: Heavy cybernetic gunships, alternating sweeping rays, and the 350-HP Cyber Overlord.
4. **Phase 3 — Endgame Syndicate War**: Post-3-boss endgame war featuring the elusive **Shadow Interceptor** prototype with aerodynamic dashing, afterimages, and mirror combat AI.

### 6. Tactical Countermeasures & Overclocks
- **Semi-Active Radar Homing (SARH)**: Missiles track the player via flagship radar guidance; deploying flares or destroying the illuminating ship breaks lock.
- **Point-Defense Decoys**: Launch burning flare/chaff canisters (`[F]`) to divert homing missiles.
- **EMP Torpedoes**: Devastating twin homing salvos that collapse player shields on contact.
- **In-Run Overclocks**:
  - **Weapon Overdrive (7.0s)**: Twin-fire, infinite pierce, 5-rocket salvos, or 4-chain lightning.
  - **Engine Overdrive (6.0s)**: +2.2 Mach boost, afterburner shockwave, and ramming armor.
  - **Shield Surge (5.0s)**: Temporary +50 HP overcharge barrier absorbing heavy ordnance.

### 7. Hybrid HD Rendering & Gamepad Support
- **Resolution-Independent UI**: Native display space overlay rendered on top of an 800×600 aspect-ratio-preserved physics simulation.
- **Gamepad / Controller Support**: Native controller integration via `pygame.joystick` (analog movement, trigger firing, bumper abilities).
- **Developer Telemetry Overlay (`F3`)**: Live telemetry HUD displaying FPS, AI corridor ratios, panic/flow indices, active plans, and formation diagnostics.

---

## Flight Controls & Keybindings

All keybindings can be fully remapped in the in-game **KEYBINDS** terminal:

| Action | Default Keyboard | Controller / Gamepad |
| :--- | :--- | :--- |
| **Move Up / Down / Left / Right** | `W` / `S` / `A` / `D` (or Arrows) | Left Analog Stick / D-Pad |
| **Fire Primary Weapon** | `SPACE` | Right Trigger (`RT` / `R2`) |
| **Manual Reload** | `R` | `X` Button / Square |
| **Engine Ability (Boost / Pulse)** | `LEFT SHIFT` | Left Bumper (`LB` / `L1`) |
| **Project Shield Matrix** | `E` | `A` Button / Cross |
| **Deploy Flare / Chaff Decoy** | `F` | Right Bumper (`RB` / `R2`) |
| **Emergency Invincibility Panic** | `Q` | `Y` Button / Triangle |
| **Pause Game** | `ESCAPE` | `START` / Options |
| **Developer Telemetry** | `F3` | — |

---

## Installation & Quickstart

### Prerequisites
- Python 3.10, 3.11, 3.12, 3.13, or 3.14
- `pip` package manager

### 1. Clone or Download Repository
```bash
git clone https://github.com/your-username/SpaceShooter.git
cd SpaceShooter
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Launch the Game
```bash
python -m src.main
# or directly:
python src/main.py
```

### 4. Build Standalone Executable (.exe)
```bash
python build_app.py
```
This automatically compiles the game into `dist/SpaceShooter/` and creates a ready-to-distribute archive: `dist/SpaceShooter-v1.0.0-Windows.zip`. Players can simply unzip and run without needing Python installed.

---

## Verification & Test Suites

The repository contains an exhaustive automated test suite with **64 out of 64 passing tests** verifying combat systems, AI behaviors, fleet transitions, and tutorial flows.

### Run All Combat Readiness Tests (43 tests)
```bash
python tests/test_combat_readiness.py
```
*Verifies flocking repulsion, capital shield exclusion, keybind conflict swaps, parallax landmarks, overclocks, inset hitboxes, SARH guidance & flares, EMP torpedoes, Databank lore & tabs, Hybrid HD scaling, Shadow Interceptor movement & endgame gating, and the 6-stage tutorial calibration.*

### Run Campaign & AI Tests (21 tests)
```bash
python tests/test_campaign_ai.py
```
*Verifies fleet phase transitions, boss arrival gates, Aegis-Fable AI planning, corridor fair-play solver, Darwinian counter-adaptations, Black Box debrief generator, and Shadow Interceptor duels.*

---

## Project Architecture

```
SpaceShooter/
├── assets/                     # Sprites, VFX sheets, SFX, BGM, and fonts
│   ├── astronaut/              # Commander Vance portraits (hello, talking, thumbs_up)
│   ├── ships/                  # Player interceptor, weapon icons, engines, shields
│   ├── enemies/                # 26 enemy ship sprites across 3 fleet factions
│   └── audio/                  # Adaptive soundtracks and tactical sound effects
├── src/                        # Core game engine modules
│   ├── main.py                 # Main application loop, state machine, and HD UI
│   ├── entities.py             # Player, Enemy, Bullet, OverclockPickup, and VFX
│   ├── adaptive_director.py    # Aegis-Fable AI Brain, Encounter Selector, Debriefs
│   ├── tutorial_controller.py  # Red Alert boot, Commander dialogue & tour controller
│   ├── hangar_view.py          # Hangar bay inspection, loadout customizer, Databank
│   ├── asset_loader.py         # Multi-format sprite/audio loader & alpha processing
│   ├── background.py           # 4-layer parallax starfield & celestial landmarks
│   ├── ui_theme.py             # Cyberpunk typography, glass panels, and buttons
│   └── save_manager.py         # Atomic save persistence & settings management
├── tests/                      # Automated test verification suites
│   ├── test_combat_readiness.py# 43 automated physics, balance, and UI tests
│   └── test_campaign_ai.py     # 21 automated AI brain and fleet campaign tests
├── PROJECT_BLUEPRINT.md        # Comprehensive game design & balance documentation
├── requirements.txt            # Python dependencies (pygame-ce)
└── README.md                   # Project overview & documentation
```

---

## Credits & Acknowledgments
- **Developer & Creator**: Dipayan Bhanja
- **Engine**: [Pygame Community Edition (Pygame-CE)](https://pyga.me/)
- **Artwork & Assets**: FoozleCC / Baldur FleetPacks (CC0 Public Domain)

Enjoy your flight, Pilot. Push back the Swarm and defend the fleet!
