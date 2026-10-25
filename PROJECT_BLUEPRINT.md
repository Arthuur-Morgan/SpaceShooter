# SpaceShooter Project Blueprint

## 1. Game Architecture

### Runtime entry point

| File | Responsibility |
| --- | --- |
| `src/main.py` | Application entry point. Creates display, initializes sound and controllers, runs the 60 FPS loop, enforces strict class caps (no 3-battleship clutter), deploys structured wave formations, renders HUD/combos/streaks/boss overlays, manages high-tech UI transitions to Hangar, Armory, and Settings. |
| `src/hangar_view.py` | Pre-mission Hangar & Armory state (`HANGAR`). Renders animated capital ship docking bay (steam particles, runway lights, observation viewport with parallax stars), 2.5x moving player ship sprite with live engine idle animations, interactive module specification table, inline loadout swap/equip drawer, difficulty cards, and Launch controls. |
| `src/ui_theme.py` | Sci-fi typography suite (`Orbitron`, `Audiowide`, `Chakra Petch`, `Rajdhani`, `Share Tech Mono`), color palettes, cyber buttons with glowing hover states and corner brackets, glass panels, and segmented stat gauges. |
| `src/entities.py` | Gameplay entities: `Player`, `Bullet`, `EnemyBullet`, `Enemy`, `Explosion`, and `CreditOrb`. Features dynamic player tracking (anti-corner-camping), fan-aimed projectile patterns, support healing, boss health bars, and difficulty scaling (damage mitigation, enemy speed, cooldowns, and bullet velocities). |
| `src/adaptive_director.py` | Contextual multi-armed bandit director with progressive threat tiers across 3 distinct fleets and syndicate mixes. Features post-boss anti-collapse (never regresses to Tier 0 patrol) and difficulty-scaled progression pacing and boss cooldowns. |
| `src/asset_loader.py` | Asset loading: player equipment, 25 enemy types across Nautolan, Kla'ed, and Nairan fleets, 15 projectile types, and weapon/feedback audio. |
| `src/background.py` | `ParallaxBackground`, wrapping void and star layers. |
| `src/save_manager.py` | Safe JSON save loading and atomic writes. Preserves progression, settings (difficulty, sensitivity, volume, keybinds), inventory, and director learning values. |

### Active enemy factions

1. **Nautolan Fleet & Swarm**: Asteroid, Scout, Fighter, Bomber, Torpedo Ship, Support Ship, Frigate, Battlecruiser, Dreadnought (Boss 1).
2. **Kla'ed Void Fleet** (CC0 from Foozle/Baldur):
   - `klaed_scout`: High-speed agile interceptor with darting zig-zag strafing.
   - `klaed_fighter`: Twin-plasma interceptor with parallel aimed burst.
   - `klaed_torpedo`: Long-range tracking void torpedoes with predictive lead.
   - `klaed_bomber`: Heavy void bomber with dual area-denial plasma charges.
   - `klaed_support`: Void healer ship with dual ray defenses.
   - `klaed_frigate`: Heavy armed void warship with 4-ray aimed spread.
   - `klaed_battlecruiser`: 128px capital ship firing sweeping void waves.
   - `klaed_dreadnought`: 320-HP **Void Overlord** (Boss 2) with 8-ray sweeping barrage and dual tracking torpedoes.
3. **Nairan Cyber Fleet** (CC0 from Foozle/Baldur FleetPack 2):
   - `nairan_scout`: Agile cyber-recon firing aimed precision bolts.
   - `nairan_fighter`: High-speed interceptor firing dual twin cyber-bolts.
   - `nairan_torpedo`: Long-range warship firing seeking cyber-torpedoes.
   - `nairan_bomber`: Heavy bomber firing high-yield cyber rockets.
   - `nairan_support`: Cyber repair cruiser casting dual defensive laser rays.
   - `nairan_frigate`: Armed assault frigate firing a 3-bolt concentrated fan.
   - `nairan_battlecruiser`: 128px capital vessel with an alternating 3-ray sweep and cyber-torpedo barrage.
   - `nairan_dreadnought`: 350-HP **Cyber Overlord** (Boss 3) firing an 8-ray sweeping barrage, twin cyber-torpedoes, and targeted rocket salvos.

## 2. Carrier Hangar & Mission Deployment System

### Flow & Architecture
- **Main Menu**: Direct operational hub. Clicking **"START MISSION"** (or pressing Enter/Space) deploys the pilot immediately into combat.
- **Difficulty Selection**: Dedicated difficulty selector in **Settings** (`EASY`, `MEDIUM`, `HARD`) with automatic persistence and in-flight HUD badges.
- **Hangar Environment**:
  - Distinct mothership docking bay background with steel structural bulkheads, upper reinforced observation bay showing twinkling stars and deep space nebula, sequential animated runway guide lights, and hydraulic steam vents.
  - **Animated Player Spaceship**: Resting on the central docking platform with smooth anti-gravity hovering bobbing, dynamic vertical laser diagnostic scan, and live animated engine idle thruster flames!
  - **Vessel Specifications & Loadout Table**: Side panel displaying equipped Cannon, Propulsion Core, and Shield Matrix with live damage, speed, cooldowns, and segmented Firepower/Mobility/Defense gauges.
  - **Inline Modular Armory Drawer**: "CUSTOMIZE LOADOUT" button opens an interactive equip drawer right inside the hangar, allowing instant swapping and purchasing of weapons, engines, and shields with real-time ship visual updates.
  - **Inspection Bay Controls**: Clean bottom action bar with `[ ? DATABANK ]` and `[ BACK ]` action buttons. Launch controls and difficulty pills are decoupled from the hangar to streamline inspection.

### Difficulty Balancing Matrix

| Setting | Damage Taken | Enemy Speed | Attack Cooldown | Enemy Bullet Speed | Max Enemies | Bonus Score & Credits |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Easy** | 0.65x (-35%) | 0.88x (-12%) | 1.25x (+25% slower) | 0.85x (-15%) | 4 | 1.0x (Standard) |
| **Medium** | 1.00x | 1.00x | 1.00x | 1.00x | 5 | 1.0x (Standard) |
| **Hard** | 1.15x (+15%) | 1.10x (+10%) | 0.85x (-15% faster) | 1.14x (+14%) | 6 | **1.35x (+35% Bonus)** |

### Shop Economy & Module Balancing

Prices are balanced around typical run earnings (~180–270 CR rookie run, ~450–750 CR skirmish, ~1000–2000 CR armada veteran run):

| Category | Module | Price | Role & Pacing |
| :--- | :--- | :--- | :--- |
| **Weapons** | Auto Cannon | **0 CR** | Default kinetic starter cannon |
| | Big Space Gun | **350 CR** | Early high-impact pierce weapon (~1–2 runs) |
| | Rocket Launcher | **650 CR** | Mid-tier auto-locking homing salvo (~2–3 solid runs) |
| | Zapper | **1,100 CR** | Elite arc chain-lightning cannon (Late-game milestone) |
| **Engines** | Base Engine | **0 CR** | Default cruise thruster (5.0 Mach) |
| | Big Pulse Engine | **300 CR** | Entry pulse-dash thruster (5.7 Mach) |
| | Burst Engine | **600 CR** | Tactical afterburner engine (6.5 Mach) |
| | Supercharged Engine | **1,050 CR** | Elite overdrive speed core (7.5 Mach) |
| **Shields** | Front Shield | **280 CR** | Essential starter barrier (30 HP, 10s CD) |
| | Front & Side Shield | **550 CR** | Wide-angle defense matrix (45 HP, 13s CD) |
| | Round Shield | **950 CR** | Full 360° omni-directional bubble (65 HP, 16s CD) |
| | Invincibility Backup | **450 CR** | Consumable 5.0s emergency panic shield ([Q]) |

## 3. Key Combat & Pacing Mechanics

### Dynamic Pacing & Threat Escalation
- Threat tier is driven by BOTH time elapsed and score/kill performance: skilled players encounter higher tiers faster.
- **Post-Boss Anti-Collapse**: When Dreadnought or Overlord is defeated, threat tier does NOT reset to Tier 0. It stays at Tier 3+ (Capital & Armada tiers) so high-intensity action continues.
- Encounter spawn interval tuned to 3.4 seconds for crisp, engaging rhythm.

### Aiming & Tracking (No Corner Camping)
- Heavy ships (`dreadnought`, `klaed_dreadnought`, `battlecruiser`, `klaed_battlecruiser`, `frigate`) dynamically track and hover across the player's active lane instead of oscillating on static sine waves.
- Firing spreads (waves, rays, spinning bullets) calculate the dynamic angle to the player (`math.atan2(dx, dy)`) and center their fans on the player's position, cutting off camping and forcing active maneuvering.

### Screen Visibility & Formations
- Maximum active screen enemies capped at 5.
- Maximum 1 heavy capital ship (`dreadnought` or `battlecruiser`) at any time.
- Strict class limits (max 2 frigates, max 1 bomber, max 1 torpedo, max 1 support) prevent overlapping visual clutter.
- Formations deployed automatically based on encounter size:
  - Solo flagship: center entry.
  - 2-ship: Pincer / Dual Flanker on outer lanes.
  - 3-ship: Arrowhead / V-Formation (center lead, staggered wings).
  - 4-ship: Staggered echelon with non-overlapping lanes.

## 4. Military Onboarding & Narrative Calibration

- **Red Alert Cold Boot Sequence**:
  - Dark red/black pulsating emergency hazard screen (`math.sin(now / 300.0)`) with CRT scanlines and 4 critical breach alarms (~9.8s).
  - Typewriter cadence at 55ms/char with 2.2s line delays. Pressing `[SPACE]` skips immediately to Commander Vance's briefing; `[ESC]` skips the tutorial entirely.
- **Commander Vance Dialogue Engine**:
  - Comms box with authentic Astronaut Commander portraits (`hello`, `talking`, `thumbs_up`) with solid poses (no mouth jitter).
  - Word-wrapped dialogue and spacebar-driven narrative progression.
- **6-Stage Combat Simulator**:
  - Stage 1: Thruster Vectoring (3 holographic waypoints).
  - Stage 2: Weapon Calibration & Reload Pacing (hold shoot, manual reload with `[R]`).
  - Stage 3: SARH Missile Lock Evasion (incoming radar missile; deploy flare `[F]` or afterburner `[Shift]` to break lock).
  - Stage 4: Defense Matrix Absorption (activate shield `[E]` to absorb wave bullets).
  - Stage 5: Support Ship Tether Priority (destroy support ship to collapse flagship invulnerability).
  - Stage 6: Overclock Collection & Graduation (collect weapon overclock for twin-fire wipeout).
  - **3.5s Breather Windows**: Inserted between stages (`combat_delay_until`) so pilots can read HUD instructions without being overwhelmed.
  - **Hull Safety Net**: Emergency nanite repair restores hull to 100 HP if player drops below 25 HP.
- **Interactive Carrier Deck Tour**:
  - Replaces automated slideshows with manual tapping. Pulsing holographic target brackets guide the player to click:
    1. Hangar Overview $\rightarrow$ `[ CUSTOMIZE LOADOUT ]`
    2. Modular Armory $\rightarrow$ `[ ? DATABANK ]`
    3. Threat Encyclopedia $\rightarrow$ `[ CLOSE ]`
    4. Supply Depot $\rightarrow$ `[ Back to Menu ]`
- **Homescreen Graduation & Grant**:
  - Returning to the Bridge triggers Vance's final transmission, awarding a **+100 Credits** deployment grant with live wallet chime and counter update.

## 5. Fleet Databank & In-Run Overclocks

- **26 Decoded Entities**: Full fleet database including Nautolan, Kla'ed, and Nairan craft with custom lore, animated holograms, and real performance metrics.
- **Dynamic Tab Widths**: Fluidly calculated tab widths with 12px gaps across `THREATS`, `WEAPONS`, `ENGINES`, `SHIELDS`, and `DROPS`.
- **Dedicated "DROPS" Tab**:
  - **Weapon Overdrive (7.0s)**: Twin-fire kinetic, infinite pierce railgun, 5-rocket salvos, or 4-chain lightning.
  - **Engine Overdrive (6.0s)**: +2.2 Mach boost, afterburner shockwave, and ramming armor.
  - **Shield Surge (5.0s)**: +50 HP overcharge barrier absorbing incoming projectiles.

## 6. Aegis-Fable AI Brain & Syndicate Warfare

- **18 Tactical Plans**: The Aegis-Fable AI engine simulates 18 candidate fleet movement/firing plans every frame, selecting optimal actions based on utility scores.
- **Corridor Fair-Play Solver**: Calculates escape lane ratios through bullet barrages to maintain fair-play standards.
- **Darwinian Counter-Adaptations**: Intercepts player habits and deploys Armada Defense countermeasures (e.g. PD Flares, Anti-Shield Torpedoes, Mirror Interceptors) broadcast to the Alien Battle-Net Comms Console.
- **Shadow Interceptor Endgame Gating**:
  - Gated strictly to Phase 3 (Endgame Syndicate War) after all 3 fleet bosses (Nautolan, Kla'ed, Nairan) have been defeated.
  - Features smooth aerodynamic velocity decay (`dash_vx *= 0.88`), afterimages, flocking separation exemption, and reactive lateral mirror jinking.
