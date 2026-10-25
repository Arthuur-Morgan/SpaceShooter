import pygame
import math
import random
import sys
from pathlib import Path

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    ASSET_DIR = Path(sys._MEIPASS) / "assets"
else:
    ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"

def get_font(filename, size, fallback_name="Arial"):
    path = ASSET_DIR / filename
    if path.exists():
        try:
            return pygame.font.Font(str(path), size)
        except Exception:
            pass
    return pygame.font.SysFont(fallback_name, size, bold=True)

class FlexibleTabStr(str):
    """String that compares case-insensitively with other strings."""
    def __eq__(self, other):
        if isinstance(other, str):
            return self.lower() == other.lower()
        return super().__eq__(other)
    
    def __hash__(self):
        return hash(self.lower())

class CaseInsensitiveDict(dict):
    """Dictionary supporting case-insensitive key lookups and membership testing."""
    def __getitem__(self, key):
        if super().__contains__(key):
            return super().__getitem__(key)
        for k, v in self.items():
            if str(k).lower() == str(key).lower():
                return v
        raise KeyError(key)

    def __contains__(self, key):
        if super().__contains__(key):
            return True
        return any(str(k).lower() == str(key).lower() for k in self)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self):
        class KeysView:
            def __init__(self, parent):
                self._parent = parent
            def __iter__(self):
                return iter(super(CaseInsensitiveDict, self._parent).keys())
            def __contains__(self, item):
                return item in self._parent
            def __len__(self):
                return len(self._parent)
            def __repr__(self):
                return f"dict_keys({list(self)})"
        return KeysView(self)

class HangarView:
    """A clean, modern, spacious Sci-Fi Hangar & Loadout interface.
    Focuses on comfortable breathing room, sharp typography, and zero clutter."""

    # Restrained modern color palette
    COLOR_BG_TOP = (11, 15, 25)
    COLOR_BG_BOTTOM = (16, 21, 33)
    COLOR_CARD_BG = (18, 25, 38)
    COLOR_CARD_BORDER = (40, 56, 82)
    COLOR_CARD_HOVER = (60, 85, 125)
    
    COLOR_CYAN = (0, 215, 245)
    COLOR_GREEN = (65, 230, 140)
    COLOR_RED = (255, 80, 95)
    COLOR_GOLD = (255, 200, 60)
    COLOR_PURPLE = (195, 85, 255)
    
    TEXT_WHITE = (245, 248, 252)
    TEXT_MUTED = (145, 168, 195)
    TEXT_DIM = (90, 110, 135)

    def __init__(self, assets, shop_items, purchase_callback, screen_size=(800, 600)):
        self.assets = assets
        self.shop_items = shop_items
        self.purchase_callback = purchase_callback
        self.W = screen_size[0]
        self.H = screen_size[1]

        if self.W <= 800 and self.H <= 600:
            self.virtual_w = 800
            self.virtual_h = 600
            self.scale = 1.0
            self.offset_x = 0
        else:
            self.virtual_w = 1024
            self.virtual_h = 640
            self.scale = self.H / 640.0
            self.offset_x = max(0, (self.W - int(1024 * self.scale)) // 2)

        # Razor-sharp native fonts (scaled by self.scale)
        s = self.scale
        def _f(name, sz, fb="Arial"):
            return get_font(name, max(9, int(round(sz * s))), fb)

        self.font_header = _f("Audiowide-Regular.ttf", 20)
        self.font_title = _f("ChakraPetch-Bold.ttf", 16)
        self.font_body = _f("ChakraPetch-Regular.ttf", 13)
        self.font_bold = _f("ChakraPetch-Bold.ttf", 13)
        self.font_small = _f("ChakraPetch-Regular.ttf", 11)
        self.font_badge = _f("Rajdhani-SemiBold.ttf", 13)
        self.font_btn = _f("ChakraPetch-Bold.ttf", 15)

        # Load engine idle frames for live ship animation
        self.engine_idle_frames = self._load_engine_idle_frames()

        # State
        self.mode = "overview"  # "overview", "customize", or "encyclopedia"
        self.custom_tab = "weapons"  # "weapons", "engines", "shields"
        self.notice = ""
        self.notice_timer = 0

        # Calm, subtle background stars
        rng = random.Random(101)
        self.stars = [
            (rng.randint(20, max(21, self.W - 20)), rng.randint(20, max(21, self.H - 20)), rng.randint(100, 200), rng.choice([1, 1, 2]))
            for _ in range(45)
        ]

        # -------------------------------------------------------------
        # STATE & LORE INITIALIZATION
        # -------------------------------------------------------------
        self._encyclopedia_tab = FlexibleTabStr("threats")  # 'threats', 'weapons', 'engines', 'shields'
        self.encyclopedia_sel = "scout"
        self.threat_scroll_y = 0

        # News Ticker Tracking Variables
        self.ticker_x = float(self.offset_x + int(self.virtual_w * self.scale))
        self.current_ticker_idx = 0
        self.last_ticker_time = pygame.time.get_ticks()

        self.ticker_messages = [
            # TACTICAL & LORE
            "DID YOU KNOW: The Aegis-Fable AI tracks your corner-camping habits and will deploy Pincer flanks to flush you out.",
            "BREAKING: Nautolan Swarm activity detected in Sector V. Pilots advised to equip Piercing munitions.",
            "GALACTIC NEWS: Local pilot forgets to reload, panic ensues across the battle-net.",
            "TACTICAL TIP: Support ships project invulnerability tethers onto Capital flagships. Destroy them first!",
            "SYS-ADMIN: Fable AI Corridor Solver ensures you always have a mathematically viable escape route. Probably.",
            "TACTICAL TIP: Engine Overdrive deploys defensive Chaff to break Semi-Active Radar Homing missile locks.",
            "TACTICAL TIP: The Zapper's chain-lightning is highly effective against tightly packed Kla'ed fighter wings.",
            "TACTICAL TIP: Auto Cannons gain zero reload downtime during a Weapon Overdrive. Hold the trigger and sweep.",
            "TACTICAL TIP: Shield Surge overcharge grants a temporary 20-HP barrier. Use it to ram through light debris.",
            "TACTICAL TIP: The Big Space Gun pierces targets naturally, but Overdrive allows it to punch through infinite hulls.",
            "TACTICAL TIP: Torpedo ships paint their targets with a red laser sight 1.2 seconds before firing. Watch your six.",
            "TACTICAL TIP: Nairan Cyber-Bombers drop area-denial blasts. If you see a red holo-circle, evacuate the zone immediately.",
            "TACTICAL TIP: Destroying Capital Ship engines reduces their tracking speed by 40% per thruster.",
            "TACTICAL TIP: Destroying a Dreadnought's Main Battery will cripple its heavy beam sweeps.",
            "TACTICAL TIP: Overclock pickups drop from heavy ships and vanish quickly. Grab them to turn the tide of battle.",
            "TACTICAL TIP: A Round Shield provides 360-degree coverage, but has a long 16-second recharge cycle. Time your activations.",
            "TACTICAL TIP: If your HUD flashes 'SHIELD CONDUIT ACTIVE', stop shooting the Dreadnought and find the Support ship!",
            "TACTICAL TIP: Hard difficulty scales enemy velocity by 10% and speeds up fire rates by 15%. Good luck.",
            "TACTICAL TIP: Kla'ed Torpedoes have fuel limits. Sometimes the best defense is simply outrunning the motor burnout.",
            
            # AEGIS-FABLE AI / META
            "SYS-ADMIN: Telemetry indicates a 34% increase in pilot panic levels. Dispensing virtual calming agents.",
            "SYS-ADMIN: Warning, Darwinian Counter-Engine has adapted to your Rocket Launcher. Expect Point-Defense Flares.",
            "SYS-ADMIN: Movement predictability at 92%. The AI knows exactly where you are going.",
            "SYS-ADMIN: 'Bullet Hell' is a designated training protocol, not a system error. Please stop filing bug reports.",
            "DID YOU KNOW: Aegis-Fable evaluates 48 simulated futures per second. You die in 47 of them.",
            "SYS-ADMIN: Neural Mirror protocol engaged. The Shadow Interceptor is learning your maneuvers.",
            "DID YOU KNOW: The Director will not ease up if your hull is critically damaged. True aces thrive under pressure.",
            "SYS-ADMIN: Lateral drift stabilized. Fable AI confirms pilot is maintaining center lane dominance.",
            "DID YOU KNOW: Hiding in the backline triggers the AI's Hunter Pack subroutine. Nowhere is safe.",
            "SYS-ADMIN: Audio subsystem offline? Unlikely. You just forgot to turn on your speakers.",
            "SYS-ADMIN: Warning. Fable Engine detects high probability of pilot screaming at their monitor.",
            
            # UNIVERSE BUILDING
            "INTEL: The Nautolan Swarm relies on heavy Asteroid cover to mask their approach vectors.",
            "INTEL: Kla'ed Void Overlords utilize multi-vector tachyon beams. Standard shielding may prove insufficient.",
            "INTEL: The Nairan Cyber Fleet's digital pulse flak matrix was originally designed for rapid asteroid mining.",
            "BREAKING: Tri-Fleet Syndicate formally declares war. Expect cross-faction armada deployments in deep space.",
            "INTEL: Kla'ed Frigates use 4-ray void spreads to dictate spatial positioning. Do not get boxed in.",
            "INTEL: Nairan Torpedo Corvettes have been retrofitted with EMP Shield-Disrupter warheads. Evasion is mandatory.",
            "INTEL: Standard Nautolan Battlecruisers measure exactly 128 meters across the bow.",
            "GALACTIC NEWS: Asteroid mining outposts report a 400% increase in rogue fast-moving space debris.",
            "BREAKING: Classified 'Shadow Interceptor' sighted. Eyewitnesses claim its chassis mirrors carrier interceptor specs.",
            
            # CARRIER CHATTER & HUMOR
            "GALACTIC NEWS: Waste-management startup 'SpoonLamp' successfully repurposes carrier scrap into docking bay lighting.",
            "GALACTIC NEWS: Unknown radio frequency intercepted on the battle-net. Sounds like... Atmospheric Drift Phonk?",
            "MARKET WATCH: Credit Orb values fluctuate as Galactic Federation prints more money to fund the Syndicate War.",
            "CARRIER CHATTER: 'Who keeps leaving their empty Wallet app open on the hangar terminal?'",
            "GALACTIC NEWS: Engineers successfully retrofit vintage T-80UK plating onto standard Front Shields.",
            "CARRIER CHATTER: Mechanics report the new Burst Engine sounds exactly like a retro 2000s PC fan.",
            "GALACTIC NEWS: Interstellar Euro Truck simulator championship delayed due to ongoing Kla'ed invasion.",
            "CARRIER CHATTER: Reminder that the docking bay is for interceptors, not recreational Euro-drifting.",
            "DID YOU KNOW: Hangar deck maintenance is performed by automated drones, so please stop dropping credit orbs.",
            "GALACTIC NEWS: Coffee shortage on Carrier Deck 4 leads to a 15% drop in pilot reaction times.",
            "CARRIER CHATTER: To the pilot playing games on the tactical console... please return to your station.",
            "BREAKING: 'Windhawk' system modifications banned from the central flight computer after consecutive crashes.",
            "GALACTIC NEWS: Bicep hypertrophy linked to better flight stick control, according to new Fleet Fitness study.",
            "CARRIER CHATTER: If you see the mechanic, tell him the Rainmeter widgets on the console are leaking memory again.",
            "GALACTIC NEWS: Station chefs replace standard-issue protein paste with authentic Kolkata egg rolls. Morale skyrockets 200%.",
            "DID YOU KNOW: Surviving a Dreadnought siege earns you a 35% bonus to your payout. Try not to spend it all on engine paint."
        ]
        random.shuffle(self.ticker_messages)

        # -------------------------------------------------------------
        # CUSTOM LORE DICTIONARY (26 ENTITIES)
        # -------------------------------------------------------------
        self.encyclopedia_lore = {
            # NAUTOLAN SWARM
            'asteroid': {"class": "Hazard", "role": "Rogue Debris", "desc": "Unaligned rogue space debris. High collision threat. Scanners indicate mineral-rich composition."},
            'scout': {"class": "Light Interceptor", "role": "Recon", "desc": "Relies on speed and erratic roaming to spot targets for the swarm. Low threat alone."},
            'fighter': {"class": "Interceptor", "role": "Vanguard", "desc": "Standard kinetic interceptor. Operates in crossfire formations to overwhelm shields."},
            'bomber': {"class": "Heavy Bomber", "role": "Area Denial", "desc": "Drops unguided, high-yield blast munitions. Avoid its targeted flight path at all costs."},
            'torpedo': {"class": "Artillery Corvette", "role": "Shield Buster", "desc": "Fires twin EMP tracking torpedoes that devour energy barriers. Highly lethal."},
            'support': {"class": "Swarm Tender", "role": "Fleet Defense", "desc": "Projects local repair fields. Can render allied flagships completely invulnerable via tether."},
            'frigate': {"class": "Assault Warship", "role": "Frontline Suppressor", "desc": "Armored frontline warship utilizing spinning lateral kinetic arrays for wide-angle suppression."},
            'battlecruiser': {"class": "Capital Ship", "role": "Heavy Command", "desc": "Projects massive sweeping energy waves. Protects its engines with heavy angled armor."},
            'dreadnought': {"class": "Flagship", "role": "Swarm Apex", "desc": "The Swarm's apex flagship. Features multi-vector tachyon beams and SARH missile barrages."},
            
            # KLA'ED VOID FLEET
            'klaed_scout': {"class": "Void Recon", "role": "Evasion", "desc": "Agile interceptor using zig-zag strafing to evade tracking systems."},
            'klaed_fighter': {"class": "Void Interceptor", "role": "Pincer Attacker", "desc": "Twin-plasma craft executing parallel burst attacks and coordinated pincer maneuvers."},
            'klaed_bomber': {"class": "Void Bomber", "role": "Heavy Payload", "desc": "Drops dual heavy void-bombs designed to obliterate stationary/anchored targets."},
            'klaed_torpedo': {"class": "Void Hunter", "role": "Tracking Artillery", "desc": "Fires hyper-tracking void torpedoes requiring sharp evasive jinking to shake."},
            'klaed_support': {"class": "Void Healer", "role": "Conduit Emitter", "desc": "Emits dual ray defenses and establishes critical shield conduits for Overlords."},
            'klaed_frigate': {"class": "Heavy Void Assault", "role": "Lane Denial", "desc": "Fires a 4-ray aimed spread, effectively cutting off escape corridors."},
            'klaed_battlecruiser': {"class": "Capital Suppressor", "role": "Wave Emitter", "desc": "Fires heavy sweeping void waves capable of clearing entire sectors."},
            'klaed_dreadnought': {"class": "Void Overlord", "role": "Fleet Apex", "desc": "Alternates between 8-ray sweeping barrages and dual tracking void torpedoes."},
            
            # NAIRAN CYBER FLEET
            'nairan_scout': {"class": "Cyber Drone", "role": "Recon", "desc": "Highly evasive drone firing aimed precision bolts to test defenses."},
            'nairan_fighter': {"class": "Cyber Interceptor", "role": "Crossfire", "desc": "High-speed cyber-interceptor generating lethal laser crossfire networks."},
            'nairan_bomber': {"class": "Tactical Bomber", "role": "Area Denial", "desc": "Delivers high-yield explosive rockets to deny sector space."},
            'nairan_torpedo': {"class": "Missile Cruiser", "role": "Tracking Artillery", "desc": "Fires seeking cyber-torpedoes with incredibly high lock-on capabilities."},
            'nairan_support': {"class": "Cyber Repair", "role": "Fleet Defense", "desc": "Casts defensive laser rays and provides absolute flagship shielding."},
            'nairan_frigate': {"class": "Cyber Assault", "role": "Concentrated Fire", "desc": "Concentrates overwhelming firepower into a deadly 3-bolt fan."},
            'nairan_battlecruiser': {"class": "Digital Warship", "role": "Heavy Command", "desc": "Alternates between 3-ray sweeps and relentless cyber-torpedo barrages."},
            'nairan_dreadnought': {"class": "Cyber Boss", "role": "Fleet Apex", "desc": "Apex cybernetic overlord deploying 8-ray fans and quad torpedo matrices."},
            
            # ENDGAME
            'shadow_interceptor': {"class": "Neural Clone", "role": "Mirror Match", "desc": "Matches player velocity, mimics loadouts, and possesses a unique pulsing energy shield."}
        }

        # Keep dedicated list of enemy threat keys for the THREATS encyclopedia tab
        self.threat_keys = list(self.encyclopedia_lore.keys())

        # Define Drop Items & Custom Lore
        self.encyclopedia_lore.update({
            'weapon_overdrive': {"class": "Overclock", "role": "Firepower Surge", "desc": "Overclocks weapon systems for 7.0s. Grants twin-fire, infinite pierce, 5-rocket salvos, or 4-chain lightning based on equipped weapon."},
            'engine_overdrive': {"class": "Overclock", "role": "Mobility Surge", "desc": "Overclocks thrusters for 6.0s. Grants +2.2 Mach speed, afterburner wake, and ramming armor against small craft."},
            'shield_surge': {"class": "Overclock", "role": "Defense Surge", "desc": "Instantly restores 40% capacity and projects a 20 HP overcharge barrier for 5.0s."}
        })

        # Friendly display names for encyclopedia items
        self.enemy_display_names = {
            'asteroid': "Asteroid Debris",
            'scout': "Nautolan Scout",
            'fighter': "Nautolan Fighter",
            'bomber': "Nautolan Bomber",
            'torpedo': "Nautolan Torpedo",
            'support': "Nautolan Support",
            'frigate': "Nautolan Frigate",
            'battlecruiser': "Nautolan Battlecruiser",
            'dreadnought': "Nautolan Dreadnought",
            'klaed_scout': "Kla'ed Scout",
            'klaed_fighter': "Kla'ed Fighter",
            'klaed_bomber': "Kla'ed Bomber",
            'klaed_torpedo': "Kla'ed Torpedo",
            'klaed_support': "Kla'ed Support",
            'klaed_frigate': "Kla'ed Frigate",
            'klaed_battlecruiser': "Kla'ed Battlecruiser",
            'klaed_dreadnought': "Kla'ed Dreadnought",
            'nairan_scout': "Nairan Scout",
            'nairan_fighter': "Nairan Fighter",
            'nairan_bomber': "Nairan Bomber",
            'nairan_torpedo': "Nairan Torpedo",
            'nairan_support': "Nairan Support",
            'nairan_frigate': "Nairan Frigate",
            'nairan_battlecruiser': "Nairan Battlecruiser",
            'nairan_dreadnought': "Nairan Dreadnought",
            'shadow_interceptor': "Shadow Interceptor",
        }

        # Enemy type lookup map from assets
        self.enemy_type_map = {e['name']: e for e in self.assets.get('enemy_types', [])}

    @property
    def encyclopedia_tab(self):
        return self._encyclopedia_tab

    @encyclopedia_tab.setter
    def encyclopedia_tab(self, val):
        self._encyclopedia_tab = FlexibleTabStr(str(val).lower())

    @property
    def selected_encyclopedia_item(self):
        return self.encyclopedia_sel

    @selected_encyclopedia_item.setter
    def selected_encyclopedia_item(self, val):
        self.encyclopedia_sel = val

    def _sc(self, v):
        return int(round(v * self.scale))

    def _sx(self, x):
        return self.offset_x + int(round(x * self.scale))

    def _sy(self, y):
        return int(round(y * self.scale))

    def _load_engine_idle_frames(self):
        frames = {}
        specs = {
            'base': ('Main Ship - Engines - Base Engine - Idle.png', 3),
            'big_pulse': ('Main Ship - Engines - Big Pulse Engine - Idle.png', 4),
            'burst': ('Main Ship - Engines - Burst Engine - Idle.png', 7),
            'supercharged': ('Main Ship - Engines - Supercharged Engine - Idle.png', 4),
        }
        for eid, (fname, count) in specs.items():
            path = ASSET_DIR / fname
            try:
                sheet = pygame.image.load(str(path)).convert_alpha()
                w = sheet.get_width() // count
                h = sheet.get_height()
                frames[eid] = [sheet.subsurface(pygame.Rect(i * w, 0, w, h)) for i in range(count)]
            except Exception:
                if eid in self.assets.get('engines', {}):
                    frames[eid] = [self.assets['engines'][eid]['image']]
                else:
                    frames[eid] = []
        return frames

    def set_notice(self, text):
        self.notice = text
        self.notice_timer = pygame.time.get_ticks() + 2400

    def draw(self, screen, save_data, mouse_pos):
        now = pygame.time.get_ticks()

        # 1. Clean Atmospheric Gradient Background
        self._draw_clean_background(screen, now)

        # 2. Top Minimalist Header
        self._draw_header(screen, save_data)

        # 3. Center-Left Hero Stage (Player Spaceship)
        self._draw_hero_ship(screen, save_data, now)

        # 4. Right Column (Loadout or Customizer)
        if self.mode == "overview":
            self._draw_overview_column(screen, save_data, mouse_pos)
        elif self.mode == "customize":
            self._draw_customize_column(screen, save_data, mouse_pos)

        # 5. Bottom Navigation & Difficulty Bar
        self._draw_bottom_bar(screen, save_data, mouse_pos)

        # 6. Encyclopedia Databank Modal Overlay
        if self.mode == "encyclopedia":
            self._draw_encyclopedia_overlay(screen, save_data, mouse_pos)

        # 7. Eye-Catching Galactic News Ticker (Visible ONLY in Databank mode)
        if self.mode == "encyclopedia":
            self._draw_news_ticker(screen, now)

    # -------------------------------------------------------------
    # 1. CLEAN BACKGROUND
    # -------------------------------------------------------------
    def _draw_clean_background(self, screen, now):
        w, h = screen.get_size()
        
        # Smooth vertical dark gradient
        for y in range(0, h, 4):
            t = y / h
            r = int(self.COLOR_BG_TOP[0] * (1 - t) + self.COLOR_BG_BOTTOM[0] * t)
            g = int(self.COLOR_BG_TOP[1] * (1 - t) + self.COLOR_BG_BOTTOM[1] * t)
            b = int(self.COLOR_BG_TOP[2] * (1 - t) + self.COLOR_BG_BOTTOM[2] * t)
            pygame.draw.rect(screen, (r, g, b), (0, y, w, 4))

        # Soft subtle stars (gentle twinkle)
        if not hasattr(self, 'stars') or not self.stars:
            rng = random.Random(101)
            self.stars = [
                (rng.randint(20, w - 20), rng.randint(20, h - 20), rng.randint(100, 200), rng.choice([1, 1, 2]))
                for _ in range(45)
            ]
        for sx, sy, bright, size in self.stars:
            twinkle = int(bright * (0.8 + 0.2 * math.sin(now * 0.002 + sx)))
            pygame.draw.circle(screen, (twinkle, twinkle, min(255, twinkle + 20)), (sx, sy), size)

    # -------------------------------------------------------------
    # 2. TOP HEADER
    # -------------------------------------------------------------
    def _draw_header(self, screen, save_data):
        # Left Breadcrumb
        title_surf = self.font_header.render("HANGAR // BRIEFING", True, self.COLOR_CYAN)
        screen.blit(title_surf, (self._sx(32), self._sy(22)))

        sub_surf = self.font_small.render("CARRIER DOCKING BAY 04 • VESSEL READY", True, self.TEXT_DIM)
        screen.blit(sub_surf, (self._sx(34), self._sy(46)))

        # Right Wallet Badge
        cr = save_data.get('credits', 0)
        wallet_w = self._sc(140)
        wallet_h = self._sc(30)
        wallet_x = self.offset_x + int(self.virtual_w * self.scale) - wallet_w - self._sc(30)
        wallet_rect = pygame.Rect(wallet_x, self._sy(22), wallet_w, wallet_h)
        pygame.draw.rect(screen, self.COLOR_CARD_BG, wallet_rect, border_radius=self._sc(6))
        pygame.draw.rect(screen, self.COLOR_CARD_BORDER, wallet_rect, 1, border_radius=self._sc(6))

        wallet_surf = self.font_badge.render(f"CREDITS: {cr} CR", True, self.COLOR_GOLD)
        screen.blit(wallet_surf, wallet_surf.get_rect(center=wallet_rect.center))

    # -------------------------------------------------------------
    # 3. CENTER-LEFT HERO SHIP STAGE
    # -------------------------------------------------------------
    def _draw_hero_ship(self, screen, save_data, now):
        rw = self._sc(290)
        rx = self.offset_x + int(self.virtual_w * self.scale) - rw - self._sc(30)
        cx = (self.offset_x + rx) // 2
        cy = self._sy(285)

        # Docking Halo / Magnetic Clamp Ring (Floor)
        pad_w, pad_h = self._sc(190), self._sc(42)
        pad_rect = pygame.Rect(cx - pad_w // 2, cy + self._sc(50), pad_w, pad_h)
        pygame.draw.ellipse(screen, (14, 22, 34), pad_rect)
        pygame.draw.ellipse(screen, (0, 190, 220), pad_rect, max(1, self._sc(2)))
        inner = pad_rect.inflate(-self._sc(40), -self._sc(14))
        pygame.draw.ellipse(screen, (0, 215, 245, 90), inner, 1)

        # Smooth, calm floating hover equation (math.sin)
        hover_offset = math.sin(now * 0.0022) * 6.0 * self.scale
        ship_y = cy + hover_offset

        # Soft drop shadow beneath ship
        shadow_w = int((72 - hover_offset * 1.5) * self.scale)
        shadow_h = max(4, int((20 - hover_offset * 0.6) * self.scale))
        shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 180, 220, 50), (0, 0, shadow_w, shadow_h))
        screen.blit(shadow_surf, (cx - shadow_w // 2, cy + self._sc(54)))

        # Ship Sprite Rendering scaled cleanly
        scale_size = (self._sc(96), self._sc(96))

        # 1. Engine layer with live idle pulse
        eq_engine = save_data.get('equipped_engine', 'base')
        idle_frames = self.engine_idle_frames.get(eq_engine, [])
        if idle_frames:
            eng_img = idle_frames[(now // 110) % len(idle_frames)]
        elif eq_engine in self.assets.get('engines', {}):
            eng_img = self.assets['engines'][eq_engine]['image']
        else:
            eng_img = None
        if eng_img:
            scaled_eng = pygame.transform.scale(eng_img, scale_size)
            screen.blit(scaled_eng, scaled_eng.get_rect(center=(cx, int(ship_y))))

        # 2. Weapon layer
        eq_weapon = save_data.get('equipped_weapon', 'auto_cannon')
        if eq_weapon in self.assets.get('weapons', {}):
            wpn_img = self.assets['weapons'][eq_weapon]['frames'][0]
            scaled_wpn = pygame.transform.scale(wpn_img, scale_size)
            screen.blit(scaled_wpn, scaled_wpn.get_rect(center=(cx, int(ship_y))))

        # 3. Base Hull
        base_img = self.assets.get('player_states', {}).get('full')
        if base_img:
            scaled_base = pygame.transform.scale(base_img, scale_size)
            screen.blit(scaled_base, scaled_base.get_rect(center=(cx, int(ship_y))))

        # 4. Shield Envelope (if equipped)
        eq_shield = save_data.get('equipped_shield')
        if eq_shield and eq_shield in self.assets.get('shields', {}):
            s_frames = self.assets['shields'][eq_shield]['frames']
            if s_frames:
                s_frame = s_frames[(now // 90) % len(s_frames)]
                scaled_shd = pygame.transform.scale(s_frame, (self._sc(120), self._sc(120)))
                screen.blit(scaled_shd, scaled_shd.get_rect(center=(cx, int(ship_y))))

        # Clean Nameplate & Status Pill Under Ship
        name_surf = self.font_title.render("INTERCEPTOR MK-IV", True, self.TEXT_WHITE)
        screen.blit(name_surf, name_surf.get_rect(center=(cx, cy + self._sc(112))))

        status_w, status_h = self._sc(130), self._sc(22)
        status_rect = pygame.Rect(cx - status_w // 2, cy + self._sc(128), status_w, status_h)
        pygame.draw.rect(screen, (16, 26, 36), status_rect, border_radius=status_h // 2)
        pygame.draw.rect(screen, (30, 65, 50), status_rect, 1, border_radius=status_h // 2)
        pygame.draw.circle(screen, self.COLOR_GREEN, (cx - self._sc(45), cy + self._sc(139)), max(2, self._sc(4)))

        status_lbl = self.font_small.render("FLIGHT READY", True, self.COLOR_GREEN)
        screen.blit(status_lbl, (cx - self._sc(34), cy + self._sc(132)))

    # -------------------------------------------------------------
    # 4A. RIGHT COLUMN: OVERVIEW (CLEAN EQUIPMENT CARDS)
    # -------------------------------------------------------------
    def _draw_overview_column(self, screen, panel_save, mouse_pos):
        rw = self._sc(290)
        rx = self.offset_x + int(self.virtual_w * self.scale) - rw - self._sc(30)
        ry = self._sy(70)
        rh = self._sc(435)

        # Frosted glass panel card
        panel_rect = pygame.Rect(rx, ry, rw, rh)
        pygame.draw.rect(screen, self.COLOR_CARD_BG, panel_rect, border_radius=self._sc(8))
        pygame.draw.rect(screen, self.COLOR_CARD_BORDER, panel_rect, 1, border_radius=self._sc(8))

        # Header
        head_surf = self.font_title.render("CURRENT LOADOUT", True, self.COLOR_CYAN)
        screen.blit(head_surf, (rx + self._sc(18), ry + self._sc(16)))

        pygame.draw.line(screen, (28, 38, 55), (rx + self._sc(16), ry + self._sc(42)), (rx + rw - self._sc(16), ry + self._sc(42)), 1)

        # Loadout Module Cards
        eq_wpn = panel_save.get('equipped_weapon', 'auto_cannon')
        eq_eng = panel_save.get('equipped_engine', 'base')
        eq_shd = panel_save.get('equipped_shield')

        wpn_data = self.assets.get('weapons', {}).get(eq_wpn, {})
        eng_data = self.assets.get('engines', {}).get(eq_eng, {})
        shd_data = self.assets.get('shields', {}).get(eq_shd, {}) if eq_shd else None

        card_y = ry + self._sc(54)

        # Card 1: Weapon
        wpn_desc = f"Damage {wpn_data.get('damage', 1)}  •  Rounds {wpn_data.get('magazine', 20)}"
        self._draw_module_card(screen, rx + self._sc(14), card_y, rw - self._sc(28), self._sc(60),
                               "PRIMARY CANNON", wpn_data.get('name', 'Auto Cannon'),
                               wpn_desc, self._get_item_icon('weapons', eq_wpn), self.COLOR_CYAN)
        card_y += self._sc(68)

        # Card 2: Engine
        spd = eng_data.get('speed', 5.0)
        ability = eng_data.get('ability')
        eng_desc = f"Speed {spd:.1f} Mach  •  {ability['name'] if ability else 'Cruiser'}"
        self._draw_module_card(screen, rx + self._sc(14), card_y, rw - self._sc(28), self._sc(60),
                               "PROPULSION CORE", eng_data.get('name', 'Base Engine'),
                               eng_desc, self._get_item_icon('engines', eq_eng), self.COLOR_GREEN)
        card_y += self._sc(68)

        # Card 3: Shield
        if shd_data:
            shd_desc = f"Capacity {shd_data.get('capacity', 30)} HP  •  Auto-Recharge"
            shd_name = shd_data.get('name', 'Front Shield')
            shd_icon = self._get_item_icon('shields', eq_shd)
        else:
            shd_desc = "Standard Hull Armor  •  No Barrier"
            shd_name = "None Equipped"
            shd_icon = None

        self._draw_module_card(screen, rx + self._sc(14), card_y, rw - self._sc(28), self._sc(60),
                               "DEFENSE MATRIX", shd_name,
                               shd_desc, shd_icon, self.COLOR_RED)

        # Action Button below Card 3: [CUSTOMIZE LOADOUT]
        btn_cust = self.get_customize_btn_rect()
        c_hov = btn_cust.collidepoint(mouse_pos)
        self._draw_cyber_btn(screen, btn_cust, "CUSTOMIZE LOADOUT", self.font_btn,
                             hovered=c_hov, border_color=self.COLOR_GOLD, text_color=self.COLOR_GOLD)

        # Performance Meters (Minimalist)
        meter_y = ry + self._sc(304)
        pwr = min(100, (wpn_data.get('damage', 1) * 20) + (wpn_data.get('magazine', 20)))
        spd_val = min(100, int((eng_data.get('speed', 5.0) / 7.5) * 100))
        def_val = 30 + (shd_data.get('capacity', 0) if shd_data else 0)

        self._draw_clean_bar(screen, rx + self._sc(18), meter_y, rw - self._sc(36), "FIREPOWER", pwr, (255, 140, 50))
        self._draw_clean_bar(screen, rx + self._sc(18), meter_y + self._sc(18), rw - self._sc(36), "MOBILITY", spd_val, self.COLOR_GREEN)
        self._draw_clean_bar(screen, rx + self._sc(18), meter_y + self._sc(36), rw - self._sc(36), "DEFENSE", def_val, self.COLOR_CYAN)

    def _draw_module_card(self, screen, x, y, w, h, slot_tag, name, sub_text, icon, accent):
        card_rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(screen, (13, 18, 28), card_rect, border_radius=self._sc(6))
        pygame.draw.rect(screen, (32, 44, 65), card_rect, 1, border_radius=self._sc(6))

        # Accent pip
        pygame.draw.rect(screen, accent, (x, y + self._sc(8), max(2, self._sc(3)), h - self._sc(16)), border_radius=self._sc(2))

        # Icon
        ix = x + self._sc(12)
        if icon:
            scaled = pygame.transform.scale(icon, (self._sc(34), self._sc(34)))
            screen.blit(scaled, (ix, y + (h - self._sc(34)) // 2))
            ix += self._sc(42)

        # Text
        tag_surf = self.font_small.render(slot_tag, True, self.TEXT_DIM)
        name_surf = self.font_bold.render(name, True, self.TEXT_WHITE)
        sub_surf = self.font_body.render(sub_text, True, self.TEXT_MUTED)

        screen.blit(tag_surf, (ix, y + self._sc(6)))
        screen.blit(name_surf, (ix, y + self._sc(21)))
        screen.blit(sub_surf, (ix, y + self._sc(40)))

    def _draw_clean_bar(self, screen, x, y, w, label, val, color):
        lbl = self.font_small.render(label, True, self.TEXT_MUTED)
        screen.blit(lbl, (x, y))

        bar_x = x + self._sc(85)
        bar_w = w - self._sc(85)
        bar_h = max(4, self._sc(7))
        ratio = max(0.0, min(1.0, val / 100.0))

        pygame.draw.rect(screen, (12, 17, 26), (bar_x, y + self._sc(3), bar_w, bar_h), border_radius=self._sc(3))
        if ratio > 0:
            fill_w = max(4, int(bar_w * ratio))
            pygame.draw.rect(screen, color, (bar_x, y + self._sc(3), fill_w, bar_h), border_radius=self._sc(3))

    # -------------------------------------------------------------
    # 4B. RIGHT COLUMN: CUSTOMIZE DRAWER
    # -------------------------------------------------------------
    def _draw_customize_column(self, screen, save_data, mouse_pos):
        rw = self._sc(290)
        rx = self.offset_x + int(self.virtual_w * self.scale) - rw - self._sc(30)
        ry = self._sy(70)
        rh = self._sc(425)

        panel_rect = pygame.Rect(rx, ry, rw, rh)
        pygame.draw.rect(screen, self.COLOR_CARD_BG, panel_rect, border_radius=self._sc(8))
        pygame.draw.rect(screen, self.COLOR_CYAN, panel_rect, 1, border_radius=self._sc(8))

        # Header & Close Button
        head_surf = self.font_title.render("SELECT MODULE", True, self.COLOR_CYAN)
        screen.blit(head_surf, (rx + self._sc(16), ry + self._sc(16)))

        close_btn = self.get_close_customize_btn_rect()
        c_hov = close_btn.collidepoint(mouse_pos)
        self._draw_cyber_btn(screen, close_btn, "DONE", self.font_small, hovered=c_hov, border_color=self.COLOR_RED)

        # Category Tabs
        tabs = self.get_custom_tabs()
        for cat, t_rect in tabs.items():
            is_active = (cat == self.custom_tab)
            t_hov = t_rect.collidepoint(mouse_pos)
            bg = (24, 35, 54) if is_active else ((18, 25, 38) if t_hov else (12, 16, 26))
            border = self.COLOR_CYAN if is_active else (self.COLOR_CARD_BORDER)

            pygame.draw.rect(screen, bg, t_rect, border_radius=self._sc(4))
            pygame.draw.rect(screen, border, t_rect, 1, border_radius=self._sc(4))

            lbl = self.font_bold.render(cat.upper(), True, self.COLOR_CYAN if is_active else self.TEXT_MUTED)
            screen.blit(lbl, lbl.get_rect(center=t_rect.center))

        # Items in this category
        owned_key = {'weapons': 'owned_weapons', 'engines': 'owned_engines', 'shields': 'owned_shields'}[self.custom_tab]
        equip_key = {'weapons': 'equipped_weapon', 'engines': 'equipped_engine', 'shields': 'equipped_shield'}[self.custom_tab]

        owned_list = save_data.get(owned_key, [])
        cur_equipped = save_data.get(equip_key)
        items = self.shop_items.get(self.custom_tab, [])

        item_y = ry + self._sc(86)
        card_h = self._sc(60)
        card_step = self._sc(66)
        for idx, item in enumerate(items):
            item_rect = pygame.Rect(rx + self._sc(12), item_y, rw - self._sc(24), card_h)
            is_hov = item_rect.collidepoint(mouse_pos)
            is_owned = item['id'] in owned_list
            is_equipped = (cur_equipped == item['id'])

            # Background
            bg = (22, 34, 52) if is_equipped else ((20, 28, 44) if is_hov else (13, 18, 28))
            border = self.COLOR_CYAN if is_equipped else (self.COLOR_CARD_BORDER)

            pygame.draw.rect(screen, bg, item_rect, border_radius=self._sc(5))
            pygame.draw.rect(screen, border, item_rect, 1, border_radius=self._sc(5))

            # Icon
            icon = self._get_item_icon(self.custom_tab, item['id'])
            if icon:
                icon_sz = self._sc(30)
                screen.blit(pygame.transform.scale(icon, (icon_sz, icon_sz)), (item_rect.x + self._sc(8), item_rect.y + (card_h - icon_sz) // 2))

            # Name
            name_surf = self.font_bold.render(item['name'], True, self.TEXT_WHITE if is_equipped else self.TEXT_MUTED)
            screen.blit(name_surf, (item_rect.x + self._sc(44), item_rect.y + self._sc(12)))

            # Action Pill Button on right
            pill_w = self._sc(72)
            pill_h = self._sc(24)
            pill_rect = pygame.Rect(item_rect.right - pill_w - self._sc(8), item_rect.centery - pill_h // 2, pill_w, pill_h)
            if is_equipped:
                pygame.draw.rect(screen, (0, 140, 170), pill_rect, border_radius=self._sc(4))
                lbl = self.font_badge.render("EQUIPPED", True, self.TEXT_WHITE)
            elif is_owned:
                pygame.draw.rect(screen, (24, 60, 42), pill_rect, border_radius=self._sc(4))
                pygame.draw.rect(screen, self.COLOR_GREEN, pill_rect, 1, border_radius=self._sc(4))
                lbl = self.font_badge.render("EQUIP", True, self.COLOR_GREEN)
            else:
                can_afford = save_data.get('credits', 0) >= item['price']
                col = self.COLOR_GOLD if can_afford else self.COLOR_RED
                pygame.draw.rect(screen, (32, 28, 18) if can_afford else (28, 16, 20), pill_rect, border_radius=self._sc(4))
                pygame.draw.rect(screen, col, pill_rect, 1, border_radius=self._sc(4))
                lbl = self.font_badge.render(f"{item['price']} CR", True, col)

            screen.blit(lbl, lbl.get_rect(center=pill_rect.center))
            item_y += card_step

        # Feedback notice
        if pygame.time.get_ticks() < self.notice_timer and self.notice:
            msg_surf = self.font_bold.render(self.notice, True, self.COLOR_GOLD)
            screen.blit(msg_surf, (rx + self._sc(16), ry + rh - self._sc(30)))

    # -------------------------------------------------------------
    # 5. BOTTOM BAR: ACTIONS & TERMINAL STATUS
    # -------------------------------------------------------------
    def _draw_bottom_bar(self, screen, save_data, mouse_pos):
        by = self.H - self._sc(72)

        # Subtle System Status Banner on Left
        status_surf = self.font_small.render("HANGAR BAY // LOADOUT CUSTOMIZATION & DATABANK ARCHIVES", True, self.TEXT_DIM)
        screen.blit(status_surf, (self._sx(34), by + self._sc(12)))

        # --- RIGHT: DATABANK & BACK BUTTONS ---
        db_rect = self.get_databank_btn_rect()
        back_rect = self.get_back_rect()

        db_hov = db_rect.collidepoint(mouse_pos)
        back_hov = back_rect.collidepoint(mouse_pos)

        # Databank Button
        self._draw_cyber_btn(screen, db_rect, "[ ? ] DATABANK", self.font_btn,
                             hovered=db_hov, primary=False, border_color=self.COLOR_CYAN,
                             text_color=self.COLOR_CYAN)

        # Back Button
        self._draw_cyber_btn(screen, back_rect, "[ BACK ]", self.font_btn,
                             hovered=back_hov, primary=False, border_color=self.COLOR_CARD_BORDER,
                             text_color=self.TEXT_MUTED)

    # -------------------------------------------------------------
    # 5B. EYE-CATCHING GALACTIC NEWS TICKER
    # -------------------------------------------------------------
    def _draw_news_ticker(self, screen, now):
        dt = max(0.001, min(0.1, (now - self.last_ticker_time) / 1000.0))
        self.last_ticker_time = now

        ticker_h = self._sc(26)
        ticker_y = self.H - ticker_h

        # Solid/semi-transparent background bar across the bottom
        t_bg = pygame.Surface((self.W, ticker_h), pygame.SRCALPHA)
        t_bg.fill((0, 0, 0, 180))
        screen.blit(t_bg, (0, ticker_y))
        pygame.draw.line(screen, (34, 48, 70), (0, ticker_y), (self.W, ticker_y), 1)

        # 1. The Text Scroll:
        self.ticker_x -= (dt * 130.0 * self.scale)

        right_limit = self.offset_x + int(self.virtual_w * self.scale)
        left_limit = self.offset_x

        if self.ticker_messages:
            msg_str = self.ticker_messages[self.current_ticker_idx]
            text_surf = self.font_bold.render(msg_str, True, self.COLOR_GOLD)
            text_w = text_surf.get_width()

            # Cycle message when scrolled completely off-screen
            if self.ticker_x + text_w < left_limit:
                self.ticker_x = float(right_limit)
                self.current_ticker_idx = (self.current_ticker_idx + 1) % len(self.ticker_messages)
                msg_str = self.ticker_messages[self.current_ticker_idx]
                text_surf = self.font_bold.render(msg_str, True, self.COLOR_GOLD)

            clip_rect = pygame.Rect(left_limit, ticker_y, int(self.virtual_w * self.scale), ticker_h)
            screen.set_clip(clip_rect)
            screen.blit(text_surf, (int(self.ticker_x), self.H - self._sc(22)))
            screen.set_clip(None)

        # 2. The Eye-Catching [ DATALINK ] Overlay:
        bg_w = self._sc(130)
        bg_rect = pygame.Rect(self.offset_x, ticker_y, bg_w, ticker_h)
        pygame.draw.rect(screen, self.COLOR_CYAN, bg_rect)
        dl_surf = self.font_btn.render(" [ DATALINK ] ", True, (0, 0, 0))
        screen.blit(dl_surf, dl_surf.get_rect(center=bg_rect.center))
        pygame.draw.line(screen, self.TEXT_WHITE, (bg_rect.right, bg_rect.y), (bg_rect.right, bg_rect.bottom), max(1, self._sc(2)))

    # -------------------------------------------------------------
    # 6. ENCYCLOPEDIA DATABANK MODAL OVERLAY
    # -------------------------------------------------------------
    def _draw_cyber_panel(self, screen, rect, border_color=None, bg_color=(12, 17, 26)):
        border_color = border_color or self.COLOR_CYAN
        rect = pygame.Rect(rect)
        pygame.draw.rect(screen, bg_color, rect, border_radius=self._sc(8))
        pygame.draw.rect(screen, border_color, rect, max(1, self._sc(2)), border_radius=self._sc(8))
        
        # High-tech corner accent notches
        c_len = self._sc(12)
        th = max(1, self._sc(2))
        pygame.draw.line(screen, self.TEXT_WHITE, (rect.x, rect.y + c_len), (rect.x, rect.y), th)
        pygame.draw.line(screen, self.TEXT_WHITE, (rect.x, rect.y), (rect.x + c_len, rect.y), th)
        pygame.draw.line(screen, self.TEXT_WHITE, (rect.right - c_len, rect.y), (rect.right, rect.y), th)
        pygame.draw.line(screen, self.TEXT_WHITE, (rect.right, rect.y), (rect.right, rect.y + c_len), th)
        pygame.draw.line(screen, self.TEXT_WHITE, (rect.x, rect.bottom - c_len), (rect.x, rect.bottom), th)
        pygame.draw.line(screen, self.TEXT_WHITE, (rect.x, rect.bottom), (rect.x + c_len, rect.bottom), th)
        pygame.draw.line(screen, self.TEXT_WHITE, (rect.right - c_len, rect.bottom), (rect.right, rect.bottom), th)
        pygame.draw.line(screen, self.TEXT_WHITE, (rect.right, rect.bottom - c_len), (rect.right, rect.bottom), th)

    def _draw_encyclopedia_overlay(self, screen, save_data, mouse_pos):
        now = pygame.time.get_ticks()

        # Full-screen dim
        dim = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 180))
        screen.blit(dim, (0, 0))

        # Large frosted cyber panel
        panel_rect = self.get_encyclopedia_panel_rect()
        self._draw_cyber_panel(screen, panel_rect, self.COLOR_CYAN)

        # Header Bar within Panel
        header_h = self.get_encyclopedia_header_h()
        pygame.draw.rect(screen, (18, 25, 40), (panel_rect.x, panel_rect.y, panel_rect.w, header_h),
                         border_top_left_radius=self._sc(8), border_top_right_radius=self._sc(8))
        pygame.draw.line(screen, (36, 52, 78), (panel_rect.x, panel_rect.y + header_h),
                         (panel_rect.right, panel_rect.y + header_h), 1)

        # 4 Category Tabs along the top: THREATS, WEAPONS, ENGINES, SHIELDS
        tabs = self.get_encyclopedia_tabs()
        for cat_name, tab_rect in tabs.items():
            is_active = (str(self.encyclopedia_tab).lower() == str(cat_name).lower())
            is_hov = tab_rect.collidepoint(mouse_pos)

            if is_active:
                bg = (24, 40, 64)
                border = self.COLOR_CYAN
                txt_col = self.COLOR_CYAN
            elif is_hov:
                bg = (18, 28, 44)
                border = self.COLOR_CARD_HOVER
                txt_col = self.TEXT_WHITE
            else:
                bg = (13, 19, 30)
                border = self.COLOR_CARD_BORDER
                txt_col = self.TEXT_MUTED

            pygame.draw.rect(screen, bg, tab_rect, border_radius=self._sc(4))
            pygame.draw.rect(screen, border, tab_rect, 1, border_radius=self._sc(4))

            tab_lbl = self.font_bold.render(cat_name.upper(), True, txt_col)
            screen.blit(tab_lbl, tab_lbl.get_rect(center=tab_rect.center))

        # "CLOSE" Button at top right of the panel
        close_rect = self.get_encyclopedia_close_rect()
        c_hov = close_rect.collidepoint(mouse_pos)
        self._draw_cyber_btn(screen, close_rect, "CLOSE", self.font_bold,
                             hovered=c_hov, border_color=self.COLOR_RED if c_hov else self.COLOR_CARD_BORDER,
                             text_color=self.COLOR_RED if c_hov else self.TEXT_MUTED)

        # --- LEFT PANE (LIST) ---
        left_rect = pygame.Rect(panel_rect.x + self._sc(12), panel_rect.y + header_h + self._sc(10), self._sc(240), panel_rect.h - header_h - self._sc(22))
        pygame.draw.rect(screen, (10, 14, 22), left_rect, border_radius=self._sc(6))
        pygame.draw.rect(screen, (28, 40, 60), left_rect, 1, border_radius=self._sc(6))

        # --- RIGHT PANE (HOLOGRAPHIC STAGE) ---
        right_rect = pygame.Rect(left_rect.right + self._sc(12), left_rect.y, panel_rect.right - left_rect.right - self._sc(24), left_rect.h)
        pygame.draw.rect(screen, (12, 17, 27), right_rect, border_radius=self._sc(6))
        pygame.draw.rect(screen, (28, 40, 60), right_rect, 1, border_radius=self._sc(6))

        # Render Selected Tab Content
        if self.encyclopedia_tab == "threats":
            self._draw_threats_list(screen, left_rect, save_data, mouse_pos)
            self._draw_threat_stage_and_dossier(screen, right_rect, save_data, mouse_pos, now, self.encyclopedia_sel)
        else:
            self._draw_modules_list(screen, left_rect, save_data, mouse_pos)
            self._draw_module_stage_and_dossier(screen, right_rect, save_data, mouse_pos, now,
                                                self.encyclopedia_tab.lower(), self.encyclopedia_sel)

    # -------------------------------------------------------------
    # 6A. THREATS LIST (LEFT PANE)
    # -------------------------------------------------------------
    def _draw_threats_list(self, screen, container_rect, save_data, mouse_pos):
        encountered = set(save_data.get('encountered_enemies', []))
        total_threats = len(self.threat_keys)
        disc_count = sum(1 for k in self.threat_keys if k in encountered)

        # List Header
        header_box = pygame.Rect(container_rect.x, container_rect.y, container_rect.w, self._sc(32))
        pygame.draw.rect(screen, (15, 21, 33), header_box, border_top_left_radius=self._sc(6), border_top_right_radius=self._sc(6))
        pygame.draw.line(screen, (28, 40, 60), (header_box.x, header_box.bottom), (header_box.right, header_box.bottom), 1)

        h_surf = self.font_bold.render(f"THREATS ({disc_count}/{total_threats})", True, self.COLOR_CYAN)
        screen.blit(h_surf, (header_box.x + self._sc(10), header_box.y + self._sc(8)))

        # Up / Down Scroll Buttons
        btn_up = self.get_threat_scroll_up_rect()
        btn_dn = self.get_threat_scroll_down_rect()
        u_hov = btn_up.collidepoint(mouse_pos)
        d_hov = btn_dn.collidepoint(mouse_pos)

        pygame.draw.rect(screen, (24, 34, 52) if u_hov else (14, 20, 30), btn_up, border_radius=self._sc(3))
        pygame.draw.rect(screen, self.COLOR_CYAN if u_hov else self.COLOR_CARD_BORDER, btn_up, 1, border_radius=self._sc(3))
        u_txt = self.font_small.render("▲", True, self.COLOR_CYAN if u_hov else self.TEXT_MUTED)
        screen.blit(u_txt, u_txt.get_rect(center=btn_up.center))

        pygame.draw.rect(screen, (24, 34, 52) if d_hov else (14, 20, 30), btn_dn, border_radius=self._sc(3))
        pygame.draw.rect(screen, self.COLOR_CYAN if d_hov else self.COLOR_CARD_BORDER, btn_dn, 1, border_radius=self._sc(3))
        d_txt = self.font_small.render("▼", True, self.COLOR_CYAN if d_hov else self.TEXT_MUTED)
        screen.blit(d_txt, d_txt.get_rect(center=btn_dn.center))

        # Scrollable Viewport
        view_rect = pygame.Rect(container_rect.x + self._sc(4), container_rect.y + self._sc(36), container_rect.w - self._sc(8), container_rect.h - self._sc(42))
        screen.set_clip(view_rect)

        row_h = self._sc(32)
        threat_keys = self.threat_keys
        total_h = len(threat_keys) * row_h
        max_scroll = max(0, total_h - view_rect.h)
        self.threat_scroll_y = max(0, min(max_scroll, self.threat_scroll_y))

        for idx, enemy_key in enumerate(threat_keys):
            row_y = view_rect.y + idx * row_h - self.threat_scroll_y
            if row_y + row_h < view_rect.y or row_y > view_rect.bottom:
                continue

            row_rect = pygame.Rect(view_rect.x + self._sc(2), row_y + self._sc(1), view_rect.w - self._sc(4), row_h - self._sc(2))
            is_sel = (self.encyclopedia_sel == enemy_key)
            is_hov = row_rect.collidepoint(mouse_pos) and view_rect.collidepoint(mouse_pos)
            is_disc = (enemy_key in encountered)

            # Colors
            if is_sel:
                bg = (24, 44, 68)
                border = self.COLOR_CYAN
            elif is_hov:
                bg = (18, 27, 42)
                border = self.COLOR_CARD_HOVER
            else:
                bg = (12, 17, 26)
                border = (25, 36, 52)

            pygame.draw.rect(screen, bg, row_rect, border_radius=self._sc(4))
            pygame.draw.rect(screen, border, row_rect, 1, border_radius=self._sc(4))

            # Faction Color Pip
            if not is_disc:
                pip_col = (110, 40, 50)
                disp_name = "??? CLASSIFIED"
                name_col = (115, 125, 140)
            else:
                if 'klaed' in enemy_key:
                    pip_col = self.COLOR_RED
                elif 'nairan' in enemy_key:
                    pip_col = self.COLOR_CYAN
                elif enemy_key == 'shadow_interceptor':
                    pip_col = self.COLOR_PURPLE
                elif enemy_key == 'asteroid':
                    pip_col = (150, 160, 175)
                else:
                    pip_col = self.COLOR_GOLD

                disp_name = self.enemy_display_names.get(enemy_key, enemy_key.replace('_', ' ').title())
                name_col = self.TEXT_WHITE if is_sel else self.TEXT_MUTED

            pygame.draw.circle(screen, pip_col, (row_rect.x + self._sc(10), row_rect.centery), max(2, self._sc(3)))

            n_surf = self.font_body.render(disp_name, True, name_col)
            screen.blit(n_surf, (row_rect.x + self._sc(20), row_rect.y + self._sc(7)))

        screen.set_clip(None)

    # -------------------------------------------------------------
    # 6B. MODULES LIST (LEFT PANE)
    # -------------------------------------------------------------
    def _draw_modules_list(self, screen, container_rect, save_data, mouse_pos):
        cat_key = self.encyclopedia_tab.lower()
        if cat_key == 'drops':
            items = [
                {'id': 'weapon_overdrive', 'name': 'Weapon Overdrive'},
                {'id': 'engine_overdrive', 'name': 'Engine Overdrive'},
                {'id': 'shield_surge', 'name': 'Shield Surge'}
            ]
        else:
            items = self.shop_items.get(cat_key, [])

        # List Header
        header_box = pygame.Rect(container_rect.x, container_rect.y, container_rect.w, self._sc(32))
        pygame.draw.rect(screen, (15, 21, 33), header_box, border_top_left_radius=self._sc(6), border_top_right_radius=self._sc(6))
        pygame.draw.line(screen, (28, 40, 60), (header_box.x, header_box.bottom), (header_box.right, header_box.bottom), 1)

        headers = {'weapons': 'ARSENAL (4)', 'engines': 'PROPULSION (4)', 'shields': 'DEFENSE (4)', 'drops': 'OVERCLOCKS (3)'}
        h_surf = self.font_bold.render(headers.get(cat_key, "MODULES"), True, self.COLOR_CYAN)
        screen.blit(h_surf, (header_box.x + self._sc(10), header_box.y + self._sc(8)))

        if cat_key in ('weapons', 'engines', 'shields'):
            owned_key = {'weapons': 'owned_weapons', 'engines': 'owned_engines', 'shields': 'owned_shields'}[cat_key]
            equip_key = {'weapons': 'equipped_weapon', 'engines': 'equipped_engine', 'shields': 'equipped_shield'}[cat_key]
            owned_list = save_data.get(owned_key, [])
            cur_equipped = save_data.get(equip_key)
        else:
            owned_list = []
            cur_equipped = None

        start_y = container_rect.y + self._sc(44)
        card_h = self._sc(86)
        card_gap = self._sc(8)

        for idx, item in enumerate(items):
            card_rect = pygame.Rect(container_rect.x + self._sc(8), start_y + idx * (card_h + card_gap), container_rect.w - self._sc(16), card_h)
            is_sel = (self.encyclopedia_sel == item['id'])
            is_hov = card_rect.collidepoint(mouse_pos)
            is_owned = item['id'] in owned_list
            is_equipped = (cur_equipped == item['id'])

            if is_sel:
                bg = (24, 44, 68)
                border = self.COLOR_CYAN
            elif is_hov:
                bg = (18, 27, 42)
                border = self.COLOR_CARD_HOVER
            else:
                bg = (12, 17, 26)
                border = (28, 38, 55)

            pygame.draw.rect(screen, bg, card_rect, border_radius=self._sc(5))
            pygame.draw.rect(screen, border, card_rect, 1, border_radius=self._sc(5))

            # Icon
            icon = self._get_item_icon(cat_key, item['id'])
            if icon:
                icon_sz = self._sc(34)
                screen.blit(pygame.transform.scale(icon, (icon_sz, icon_sz)), (card_rect.x + self._sc(10), card_rect.y + (card_h - icon_sz) // 2))

            # Name
            name_surf = self.font_bold.render(item['name'], True, self.TEXT_WHITE if is_sel else self.TEXT_MUTED)
            screen.blit(name_surf, (card_rect.x + self._sc(52), card_rect.y + self._sc(12)))

            # Status pill
            pill_w = self._sc(90)
            pill_h = self._sc(20)
            pill_rect = pygame.Rect(card_rect.x + self._sc(52), card_rect.y + self._sc(36), pill_w, pill_h)
            if cat_key == 'drops':
                pygame.draw.rect(screen, (20, 45, 60), pill_rect, border_radius=self._sc(3))
                p_lbl = self.font_small.render("OVERCLOCK", True, self.COLOR_GOLD)
            elif is_equipped:
                pygame.draw.rect(screen, (0, 110, 140), pill_rect, border_radius=self._sc(3))
                p_lbl = self.font_small.render("EQUIPPED", True, self.TEXT_WHITE)
            elif is_owned:
                pygame.draw.rect(screen, (20, 50, 35), pill_rect, border_radius=self._sc(3))
                p_lbl = self.font_small.render("OWNED", True, self.COLOR_GREEN)
            else:
                pygame.draw.rect(screen, (32, 26, 18), pill_rect, border_radius=self._sc(3))
                p_lbl = self.font_small.render(f"{item.get('price', 500)} CR", True, self.COLOR_GOLD)
            screen.blit(p_lbl, p_lbl.get_rect(center=pill_rect.center))

    # -------------------------------------------------------------
    # 6C. THREAT HOLOGRAPHIC STAGE & DOSSIER (RIGHT PANE)
    # -------------------------------------------------------------
    def _draw_threat_stage_and_dossier(self, screen, container_rect, save_data, mouse_pos, now, enemy_key):
        is_disc = (enemy_key in save_data.get('encountered_enemies', []))
        enemy_data = self.enemy_type_map.get(enemy_key, {})
        lore = self.encyclopedia_lore.get(enemy_key, {"class": "Threat", "role": "Hostile", "desc": "Unknown hostile signature."})

        cx = container_rect.centerx
        stage_floor_y = container_rect.y + self._sc(134)

        # Holographic Pedestal (Floor)
        pad_w = self._sc(180)
        pad_h = self._sc(34)
        pad_rect = pygame.Rect(cx - pad_w // 2, stage_floor_y, pad_w, pad_h)
        pygame.draw.ellipse(screen, (16, 25, 38), pad_rect)
        pygame.draw.ellipse(screen, (0, 190, 225) if is_disc else (140, 45, 55), pad_rect, max(1, self._sc(2)))
        inner = pad_rect.inflate(-self._sc(36), -self._sc(12))
        pygame.draw.ellipse(screen, (0, 215, 245, 70) if is_disc else (200, 50, 60, 50), inner, 1)

        # Smooth Floating Animation
        hover_offset = math.sin(now * 0.003) * 6.0 * self.scale
        ship_y = (stage_floor_y - self._sc(48)) + hover_offset

        # Drop shadow on pedestal
        shadow_w = int((60 - hover_offset) * self.scale)
        shadow_h = max(4, self._sc(14))
        shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 180, 220, 45) if is_disc else (150, 40, 50, 30), (0, 0, shadow_w, shadow_h))
        screen.blit(shadow_surf, (cx - shadow_w // 2, stage_floor_y + self._sc(8)))

        # Fetch idle_frames[0] of the enemy (fallback to ship)
        idle_frames = enemy_data.get('idle_frames')
        if idle_frames and len(idle_frames) > 0:
            orig_sprite = idle_frames[0]
        else:
            orig_sprite = enemy_data.get('ship')

        if orig_sprite:
            sw, sh = orig_sprite.get_size()
            scale = min(110.0 * self.scale / sw, 110.0 * self.scale / sh, 2.0 * self.scale)
            scaled = pygame.transform.scale(orig_sprite, (max(1, int(sw * scale)), max(1, int(sh * scale))))

            if is_disc:
                # Discovered State: Live full-color sprite
                screen.blit(scaled, scaled.get_rect(center=(cx, int(ship_y))))
            else:
                # Undiscovered State: Pure black silhouette
                silhouette = scaled.copy()
                silhouette.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
                screen.blit(silhouette, silhouette.get_rect(center=(cx, int(ship_y))))

                # Scanning red laser band across the silhouette
                scan_y = int(ship_y - self._sc(35) + (now % 1500) / 1500.0 * self._sc(70))
                pygame.draw.line(screen, (255, 60, 80, 190), (cx - self._sc(45), scan_y), (cx + self._sc(45), scan_y), 1)

        # Divider between stage and dossier
        div_y = stage_floor_y + self._sc(36)
        pygame.draw.line(screen, (28, 40, 60), (container_rect.x + self._sc(16), div_y), (container_rect.right - self._sc(16), div_y), 1)

        # --- DOSSIER PANEL BELOW STAGE ---
        dossier_y = div_y + self._sc(8)

        # Calculate responsive 3-box horizontal dimensions to strictly fit panel margins
        box_margin = self._sc(18)
        box_gap = self._sc(10)
        box_w = (container_rect.w - (box_margin * 2) - (box_gap * 2)) // 3
        box_h = self._sc(46)
        box1_x = container_rect.x + box_margin
        box2_x = box1_x + box_w + box_gap
        box3_x = box2_x + box_w + box_gap

        if not is_disc:
            t_surf = self.font_title.render("CLASSIFIED", True, self.COLOR_RED)
            screen.blit(t_surf, (container_rect.x + self._sc(18), dossier_y))

            sub_surf = self.font_small.render("THREAT SIGNATURE UNVERIFIED // COMBAT ANALYSIS REQUIRED", True, self.TEXT_DIM)
            screen.blit(sub_surf, (container_rect.x + self._sc(18), dossier_y + self._sc(22)))

            # Badges split on two separate vertical lines
            self._draw_info_pill(screen, container_rect.x + self._sc(18), dossier_y + self._sc(44), "CLASS", "???", (120, 50, 60))
            self._draw_info_pill(screen, container_rect.x + self._sc(18), dossier_y + self._sc(70), "ROLE", "???", (120, 50, 60))

            # Stats Cards
            card_y = dossier_y + self._sc(98)
            self._draw_stat_box(screen, box1_x, card_y, box_w, box_h, "HULL HP", "???", self.TEXT_DIM)
            self._draw_stat_box(screen, box2_x, card_y, box_w, box_h, "BOUNTY", "???", self.TEXT_DIM)
            self._draw_stat_box(screen, box3_x, card_y, box_w, box_h, "RAM DMG", "???", self.TEXT_DIM)

            # Lore Box
            lore_rect = pygame.Rect(container_rect.x + self._sc(18), card_y + self._sc(52), container_rect.w - self._sc(36), self._sc(72))
            pygame.draw.rect(screen, (16, 20, 28), lore_rect, border_radius=self._sc(6))
            pygame.draw.rect(screen, (45, 30, 36), lore_rect, 1, border_radius=self._sc(6))
            pygame.draw.rect(screen, self.COLOR_RED, (lore_rect.x, lore_rect.y, max(2, self._sc(4)), lore_rect.h), border_radius=self._sc(2))

            undisc_desc = "Threat signature unverified. Engage in combat to analyze."
            self._draw_wrapped_text(screen, undisc_desc, lore_rect.x + self._sc(14), lore_rect.y + self._sc(14), lore_rect.w - self._sc(28),
                                    self.font_body, self.COLOR_RED, line_spacing=self._sc(18))
        else:
            disp_name = self.enemy_display_names.get(enemy_key, enemy_key.replace('_', ' ').title()).upper()
            t_surf = self.font_title.render(disp_name, True, self.TEXT_WHITE)
            screen.blit(t_surf, (container_rect.x + self._sc(18), dossier_y))

            # Faction subtitle
            if 'klaed' in enemy_key:
                fac_name, fac_col = "KLA'ED VOID FLEET", self.COLOR_RED
            elif 'nairan' in enemy_key:
                fac_name, fac_col = "NAIRAN CYBER OVERLORDS", self.COLOR_CYAN
            elif enemy_key == 'shadow_interceptor':
                fac_name, fac_col = "NEURAL PROTOTYPE MIRROR", self.COLOR_PURPLE
            elif enemy_key == 'asteroid':
                fac_name, fac_col = "UNALIGNED HAZARD", (150, 160, 175)
            else:
                fac_name, fac_col = "NAUTOLAN SWARM FORCES", self.COLOR_GOLD

            sub_surf = self.font_small.render(f"FACTION: {fac_name}", True, fac_col)
            screen.blit(sub_surf, (container_rect.x + self._sc(18), dossier_y + self._sc(22)))

            # Badges split on two separate vertical lines
            self._draw_info_pill(screen, container_rect.x + self._sc(18), dossier_y + self._sc(44), "CLASS", lore.get('class', 'Warship'), self.COLOR_CYAN)
            self._draw_info_pill(screen, container_rect.x + self._sc(18), dossier_y + self._sc(70), "ROLE", lore.get('role', 'Combat'), self.COLOR_GREEN)

            # Stats Cards
            card_y = dossier_y + self._sc(98)
            hp_val = enemy_data.get('hp', 1)
            bounty_val = enemy_data.get('score_value', 10)
            ram_val = enemy_data.get('contact_damage', 10)

            self._draw_stat_box(screen, box1_x, card_y, box_w, box_h, "HULL HP", f"{hp_val} HP", self.COLOR_GREEN)
            self._draw_stat_box(screen, box2_x, card_y, box_w, box_h, "BOUNTY", f"{bounty_val} PTS", self.COLOR_GOLD)
            self._draw_stat_box(screen, box3_x, card_y, box_w, box_h, "RAM DMG", f"{ram_val} DMG", self.COLOR_RED)

            # Lore Box
            lore_rect = pygame.Rect(container_rect.x + self._sc(18), card_y + self._sc(52), container_rect.w - self._sc(36), self._sc(72))
            pygame.draw.rect(screen, (15, 22, 34), lore_rect, border_radius=self._sc(6))
            pygame.draw.rect(screen, (32, 48, 72), lore_rect, 1, border_radius=self._sc(6))
            pygame.draw.rect(screen, self.COLOR_CYAN, (lore_rect.x, lore_rect.y, max(2, self._sc(4)), lore_rect.h), border_radius=self._sc(2))

            self._draw_wrapped_text(screen, lore.get('desc', ''), lore_rect.x + self._sc(14), lore_rect.y + self._sc(14), lore_rect.w - self._sc(28),
                                    self.font_body, self.TEXT_WHITE, line_spacing=self._sc(18))

    # -------------------------------------------------------------
    # 6D. MODULE HOLOGRAPHIC STAGE & DOSSIER (RIGHT PANE)
    # -------------------------------------------------------------
    def _draw_module_stage_and_dossier(self, screen, container_rect, save_data, mouse_pos, now, category, item_id):
        cx = container_rect.centerx
        stage_floor_y = container_rect.y + self._sc(134)

        # Color Accent for Module Category
        cat_colors = {'weapons': self.COLOR_CYAN, 'engines': self.COLOR_GREEN, 'shields': self.COLOR_CYAN, 'drops': self.COLOR_GOLD}
        accent = cat_colors.get(category, self.COLOR_CYAN)

        # Holographic Pedestal
        pad_w = self._sc(180)
        pad_h = self._sc(34)
        pad_rect = pygame.Rect(cx - pad_w // 2, stage_floor_y, pad_w, pad_h)
        pygame.draw.ellipse(screen, (16, 25, 38), pad_rect)
        pygame.draw.ellipse(screen, accent, pad_rect, max(1, self._sc(2)))
        inner = pad_rect.inflate(-self._sc(36), -self._sc(12))
        pygame.draw.ellipse(screen, (*accent[:3], 70), inner, 1)

        # Smooth Floating Animation
        hover_offset = math.sin(now * 0.003) * 6.0 * self.scale
        icon_y = (stage_floor_y - self._sc(48)) + hover_offset

        # Drop shadow on pedestal
        shadow_w = int((60 - hover_offset) * self.scale)
        shadow_h = max(4, self._sc(14))
        shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (*accent[:3], 40), (0, 0, shadow_w, shadow_h))
        screen.blit(shadow_surf, (cx - shadow_w // 2, stage_floor_y + self._sc(8)))

        # Holographic Graphics: Shields (real effects), Drops (animated pickups), Weapons/Engines (spinning pickups)
        if category == 'shields':
            s_frames = self.assets.get('shields', {}).get(item_id, {}).get('frames', [])
            if s_frames:
                img = s_frames[(now // 90) % len(s_frames)]
                target_w = int(img.get_width() * self.scale * 2.5)
                target_h = int(img.get_height() * self.scale * 2.5)
                scaled_img = pygame.transform.smoothscale(img, (target_w, target_h))
                screen.blit(scaled_img, scaled_img.get_rect(center=(cx, int(icon_y))))
            else:
                static_icon = self._get_item_icon(category, item_id)
                if static_icon:
                    scaled_icon = pygame.transform.scale(static_icon, (self._sc(70), self._sc(70)))
                    screen.blit(scaled_icon, scaled_icon.get_rect(center=(cx, int(icon_y))))
        elif category == 'drops':
            drop_pickup_map = {
                'weapon_overdrive': self.assets.get('pickup_weapons', {}).get('auto_cannon', []),
                'engine_overdrive': self.assets.get('pickup_engines', {}).get('burst', []),
                'shield_surge': self.assets.get('pickup_shields', {}).get('round', []),
            }
            p_frames = drop_pickup_map.get(item_id, [])
            if p_frames:
                img = p_frames[(now // 70) % len(p_frames)]
                target_w = int(img.get_width() * self.scale * 2.5)
                target_h = int(img.get_height() * self.scale * 2.5)
                scaled_img = pygame.transform.smoothscale(img, (target_w, target_h))
                screen.blit(scaled_img, scaled_img.get_rect(center=(cx, int(icon_y))))
            else:
                static_icon = self._get_item_icon(category, item_id)
                if static_icon:
                    scaled_icon = pygame.transform.scale(static_icon, (self._sc(80), self._sc(80)))
                    screen.blit(scaled_icon, scaled_icon.get_rect(center=(cx, int(icon_y))))
        else:
            # Animated Spinning Pickup Icon (weapons, engines)
            pickup_dict = self.assets.get('pickup_' + category, {})
            frames = pickup_dict.get(item_id, [])
            if frames:
                cur_frame = frames[(now // 75) % len(frames)]
                scaled_icon = pygame.transform.scale(cur_frame, (self._sc(80), self._sc(80)))
                screen.blit(scaled_icon, scaled_icon.get_rect(center=(cx, int(icon_y))))
            else:
                static_icon = self._get_item_icon(category, item_id)
                if static_icon:
                    scaled_icon = pygame.transform.scale(static_icon, (self._sc(70), self._sc(70)))
                    screen.blit(scaled_icon, scaled_icon.get_rect(center=(cx, int(icon_y))))

        # Divider between stage and dossier
        div_y = stage_floor_y + self._sc(36)
        pygame.draw.line(screen, (28, 40, 60), (container_rect.x + self._sc(16), div_y), (container_rect.right - self._sc(16), div_y), 1)

        # --- DOSSIER PANEL BELOW STAGE ---
        dossier_y = div_y + self._sc(8)

        if category == 'drops':
            drop_names = {
                'weapon_overdrive': 'Weapon Overdrive',
                'engine_overdrive': 'Engine Overdrive',
                'shield_surge': 'Shield Surge',
            }
            item_name = drop_names.get(item_id, item_id.replace('_', ' ').title())
            lore = self.encyclopedia_lore.get(item_id, {})
            desc_text = lore.get('desc', 'In-run combat overclock prototype.')
            stat_lbl, stat_col = "STATUS: IN-RUN COMBAT OVERCLOCK", self.COLOR_GOLD
        else:
            shop_list = self.shop_items.get(category, [])
            item_entry = next((it for it in shop_list if it['id'] == item_id), None)
            item_name = item_entry['name'] if item_entry else item_id.replace('_', ' ').title()
            desc_text = item_entry.get('detail', 'Standard military component.') if item_entry else 'Standard military component.'

            owned_key = {'weapons': 'owned_weapons', 'engines': 'owned_engines', 'shields': 'owned_shields'}.get(category, '')
            equip_key = {'weapons': 'equipped_weapon', 'engines': 'equipped_engine', 'shields': 'equipped_shield'}.get(category, '')
            is_equipped = (save_data.get(equip_key) == item_id) if equip_key else False
            is_owned = item_id in save_data.get(owned_key, []) if owned_key else False

            if is_equipped:
                stat_lbl, stat_col = "STATUS: CURRENTLY EQUIPPED", self.COLOR_CYAN
            elif is_owned:
                stat_lbl, stat_col = "STATUS: IN CARRIER ARMORY", self.COLOR_GREEN
            else:
                price = item_entry['price'] if item_entry else 500
                stat_lbl, stat_col = f"STATUS: CARRIER STORE ({price} CR)", self.COLOR_GOLD

        t_surf = self.font_title.render(item_name.upper(), True, self.TEXT_WHITE)
        screen.blit(t_surf, (container_rect.x + self._sc(18), dossier_y))

        sub_surf = self.font_small.render(stat_lbl, True, stat_col)
        screen.blit(sub_surf, (container_rect.x + self._sc(18), dossier_y + self._sc(22)))

        # Category Spec Badges
        cat_tags = {'weapons': 'SHIP CANNON', 'engines': 'PROPULSION CORE', 'shields': 'DEFENSE MATRIX', 'drops': 'COMBAT SURGE'}
        self._draw_info_pill(screen, container_rect.x + self._sc(18), dossier_y + self._sc(44), "CATEGORY", cat_tags.get(category, "MODULE"), accent)

        # Specific Stats (sourced from self.assets, self.shop_items, and self.encyclopedia_lore)
        card_y = dossier_y + self._sc(74)
        box_margin = self._sc(18)
        box_gap = self._sc(10)
        box_w = (container_rect.w - (box_margin * 2) - (box_gap * 2)) // 3
        box_h = self._sc(46)
        box1_x = container_rect.x + box_margin
        box2_x = box1_x + box_w + box_gap
        box3_x = box2_x + box_w + box_gap

        if category == 'weapons':
            w_data = self.assets.get('weapons', {}).get(item_id, {})
            dmg = w_data.get('damage', 1)
            mag = w_data.get('magazine', 20)
            reload_s = w_data.get('reload_ms', 1100) / 1000.0

            self._draw_stat_box(screen, box1_x, card_y, box_w, box_h, "DAMAGE", f"{dmg} DMG", self.COLOR_CYAN)
            self._draw_stat_box(screen, box2_x, card_y, box_w, box_h, "CAPACITY", f"{mag} RDS", self.COLOR_GOLD)
            self._draw_stat_box(screen, box3_x, card_y, box_w, box_h, "RELOAD", f"{reload_s:.1f} SEC", self.COLOR_GREEN)

        elif category == 'engines':
            e_data = self.assets.get('engines', {}).get(item_id, {})
            spd = e_data.get('speed', 5.0)
            ability = e_data.get('ability')
            ab_name = ability['name'] if ability else "None"
            cd_s = (ability['cooldown'] / 1000.0) if ability else 0.0

            self._draw_stat_box(screen, box1_x, card_y, box_w, box_h, "CRUISE SPEED", f"{spd:.1f} MACH", self.COLOR_GREEN)
            self._draw_stat_box(screen, box2_x, card_y, box_w, box_h, "ABILITY", ab_name, self.COLOR_CYAN)
            self._draw_stat_box(screen, box3_x, card_y, box_w, box_h, "COOLDOWN", f"{cd_s:.1f} SEC", self.COLOR_GOLD)

        elif category == 'shields':
            s_data = self.assets.get('shields', {}).get(item_id, {})
            cap = s_data.get('capacity', 30)
            cd_ms = s_data.get('cooldown_ms', 10000)

            self._draw_stat_box(screen, box1_x, card_y, box_w, box_h, "ABSORPTION", f"{cap} HP", self.COLOR_CYAN)
            self._draw_stat_box(screen, box2_x, card_y, box_w, box_h, "RECHARGE", f"{cd_ms/1000:.0f} SEC", self.COLOR_GREEN)
            self._draw_stat_box(screen, box3_x, card_y, box_w, box_h, "TRIGGER", "KEY [ E ]", self.COLOR_GOLD)

        elif category == 'drops':
            dur_map = {
                'weapon_overdrive': '7.0 SEC',
                'engine_overdrive': '6.0 SEC',
                'shield_surge': '5.0 SEC',
            }
            dur_val = dur_map.get(item_id, '6.0 SEC')

            self._draw_stat_box(screen, box1_x, card_y, box_w, box_h, "DURATION", dur_val, self.COLOR_GOLD)
            self._draw_stat_box(screen, box2_x, card_y, box_w, box_h, "SOURCE", "HEAVY SHIPS", self.COLOR_CYAN)
            self._draw_stat_box(screen, box3_x, card_y, box_w, box_h, "DROP RATE", "22%", self.COLOR_GREEN)

        # Tactical Description Box
        lore_rect = pygame.Rect(container_rect.x + self._sc(18), card_y + self._sc(52), container_rect.w - self._sc(36), self._sc(72))
        pygame.draw.rect(screen, (15, 22, 34), lore_rect, border_radius=self._sc(6))
        pygame.draw.rect(screen, (32, 48, 72), lore_rect, 1, border_radius=self._sc(6))
        pygame.draw.rect(screen, accent, (lore_rect.x, lore_rect.y, max(2, self._sc(4)), lore_rect.h), border_radius=self._sc(2))

        self._draw_wrapped_text(screen, desc_text, lore_rect.x + self._sc(14), lore_rect.y + self._sc(14), lore_rect.w - self._sc(28),
                                self.font_body, self.TEXT_WHITE, line_spacing=self._sc(18))

    # -------------------------------------------------------------
    # UI HELPER: INFO PILL & STAT BOX
    # -------------------------------------------------------------
    def _draw_info_pill(self, screen, x, y, tag, value, accent_color):
        t_surf = self.font_small.render(f"{tag}: ", True, self.TEXT_DIM)
        v_surf = self.font_bold.render(value, True, accent_color)
        w = t_surf.get_width() + v_surf.get_width() + self._sc(16)
        pill_h = self._sc(22)
        pill_rect = pygame.Rect(x, y, w, pill_h)
        pygame.draw.rect(screen, (16, 24, 36), pill_rect, border_radius=pill_h // 2)
        pygame.draw.rect(screen, (32, 46, 68), pill_rect, 1, border_radius=pill_h // 2)
        screen.blit(t_surf, (x + self._sc(8), y + self._sc(4)))
        screen.blit(v_surf, (x + self._sc(8) + t_surf.get_width(), y + self._sc(4)))

    def _draw_stat_box(self, screen, x, y, w, h, label, val_str, val_col):
        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(screen, (14, 20, 30), rect, border_radius=self._sc(5))
        pygame.draw.rect(screen, (28, 40, 60), rect, 1, border_radius=self._sc(5))

        lbl = self.font_small.render(label, True, self.TEXT_DIM)
        val = self.font_bold.render(val_str, True, val_col)

        screen.blit(lbl, (x + self._sc(10), y + self._sc(6)))
        screen.blit(val, (x + self._sc(10), y + self._sc(24)))

    def _draw_wrapped_text(self, screen, text, x, y, max_w, font, color, line_spacing=18):
        line_spacing = self._sc(line_spacing)
        words = text.split(" ")
        lines = []
        cur_line = []
        for word in words:
            test_line = " ".join(cur_line + [word])
            if font.size(test_line)[0] <= max_w:
                cur_line.append(word)
            else:
                if cur_line:
                    lines.append(" ".join(cur_line))
                cur_line = [word]
        if cur_line:
            lines.append(" ".join(cur_line))

        cur_y = y
        for line in lines:
            surf = font.render(line, True, color)
            screen.blit(surf, (x, cur_y))
            cur_y += line_spacing
        return cur_y

    # -------------------------------------------------------------
    # UI BUTTON HELPER (RAZOR SHARP)
    # -------------------------------------------------------------
    def _draw_cyber_btn(self, screen, rect, text, font, hovered=False, primary=False,
                        border_color=None, text_color=None):
        rect = pygame.Rect(rect)
        border_color = border_color or self.COLOR_CARD_BORDER
        text_color = text_color or self.TEXT_WHITE

        if primary:
            bg = (0, 150, 180) if hovered else (12, 42, 60)
            brd = (0, 240, 255)
            txt = (255, 255, 255)
        elif hovered:
            bg = (28, 40, 60)
            brd = (0, 215, 245)
            txt = (255, 255, 255)
        else:
            bg = self.COLOR_CARD_BG
            brd = border_color
            txt = text_color

        b_thick = max(1, self._sc(2)) if (hovered or primary) else max(1, self._sc(1))
        pygame.draw.rect(screen, bg, rect, border_radius=self._sc(6))
        pygame.draw.rect(screen, brd, rect, b_thick, border_radius=self._sc(6))

        t_surf = font.render(text, True, txt)
        screen.blit(t_surf, t_surf.get_rect(center=rect.center))

    def _get_item_icon(self, category, item_id):
        try:
            if category == 'weapons':
                return self.assets['weapons'][item_id]['frames'][0]
            if category == 'engines':
                return self.assets['engines'][item_id]['image']
            if category == 'drops':
                drop_mapping = {
                    'weapon_overdrive': self.assets.get('pickup_weapons', {}).get('auto_cannon', []),
                    'engine_overdrive': self.assets.get('pickup_engines', {}).get('burst', []),
                    'shield_surge': self.assets.get('pickup_shields', {}).get('round', []),
                }
                frames = drop_mapping.get(item_id, [])
                return frames[0] if frames else None
            frames = self.assets['shields'][item_id]['frames']
            return frames[len(frames) // 2]
        except Exception:
            return None

    # -------------------------------------------------------------
    # INTERACTION RECTANGLES
    # -------------------------------------------------------------
    @property
    def btn_back(self):
        return self.get_back_rect()

    def get_back_rect(self):
        w = self._sc(110)
        h = self._sc(40)
        rx = self.offset_x + int(self.virtual_w * self.scale) - self._sc(130)
        y = self.H - self._sc(72)
        return pygame.Rect(rx, y, w, h)

    def get_databank_btn_rect(self):
        w = self._sc(150)
        h = self._sc(40)
        rx = self.offset_x + int(self.virtual_w * self.scale) - self._sc(290)
        y = self.H - self._sc(72)
        return pygame.Rect(rx, y, w, h)

    def get_customize_btn_rect(self):
        rw = self._sc(290)
        rx = self.offset_x + int(self.virtual_w * self.scale) - rw - self._sc(30)
        return pygame.Rect(rx + self._sc(14), self._sy(330), rw - self._sc(28), self._sc(34))

    def get_close_customize_btn_rect(self):
        rw = self._sc(290)
        rx = self.offset_x + int(self.virtual_w * self.scale) - rw - self._sc(30)
        return pygame.Rect(rx + rw - self._sc(70), self._sy(84), self._sc(62), self._sc(24))

    def get_custom_tabs(self):
        rw = self._sc(290)
        rx = self.offset_x + int(self.virtual_w * self.scale) - rw - self._sc(30)
        ry = self._sy(70)
        tw = self._sc(82)
        th = self._sc(26)
        step = self._sc(86)
        return {
            'weapons': pygame.Rect(rx + self._sc(12), ry + self._sc(48), tw, th),
            'engines': pygame.Rect(rx + self._sc(12) + step, ry + self._sc(48), tw, th),
            'shields': pygame.Rect(rx + self._sc(12) + step * 2, ry + self._sc(48), tw, th),
        }

    def get_custom_item_rect(self, index):
        rw = self._sc(290)
        rx = self.offset_x + int(self.virtual_w * self.scale) - rw - self._sc(30)
        return pygame.Rect(rx + self._sc(12), self._sy(156) + index * self._sc(66), rw - self._sc(24), self._sc(60))

    def get_encyclopedia_panel_rect(self):
        pw = int(self.virtual_w * self.scale) - self._sc(140)
        ph = self.H - self._sc(108)
        return pygame.Rect(self.offset_x + self._sc(70), self._sy(36), pw, ph)

    def get_encyclopedia_header_h(self):
        return self._sc(56)

    def get_encyclopedia_close_rect(self):
        panel_rect = self.get_encyclopedia_panel_rect()
        return pygame.Rect(panel_rect.right - self._sc(94), panel_rect.y + self._sc(16), self._sc(82), self._sc(32))

    def get_encyclopedia_tabs(self):
        panel_rect = self.get_encyclopedia_panel_rect()
        start_x = panel_rect.x + self._sc(30)
        tab_y = panel_rect.y + self._sc(16)
        padding_x = self._sc(24)
        tab_h = self._sc(32)
        gap = self._sc(12)

        tabs = CaseInsensitiveDict()
        for cat_key in ["threats", "weapons", "engines", "shields", "drops"]:
            label = cat_key.upper()
            text_w = self.font_bold.size(label)[0]
            tab_w = text_w + padding_x

            tab_rect = pygame.Rect(start_x, tab_y, tab_w, tab_h)
            tabs[cat_key] = tab_rect
            start_x += tab_w + gap

        return tabs

    def get_threat_scroll_up_rect(self):
        panel_rect = self.get_encyclopedia_panel_rect()
        header_h = self.get_encyclopedia_header_h()
        return pygame.Rect(panel_rect.x + self._sc(204), panel_rect.y + header_h + self._sc(16), self._sc(20), self._sc(20))

    def get_threat_scroll_down_rect(self):
        panel_rect = self.get_encyclopedia_panel_rect()
        header_h = self.get_encyclopedia_header_h()
        return pygame.Rect(panel_rect.x + self._sc(226), panel_rect.y + header_h + self._sc(16), self._sc(20), self._sc(20))

    # -------------------------------------------------------------
    # EVENT HANDLING
    # -------------------------------------------------------------
    def handle_scroll(self, delta_y):
        if self.mode == "encyclopedia" and self.encyclopedia_tab == "threats":
            row_h = self._sc(32)
            view_h = self._sc(440)
            max_scroll = max(0, len(self.threat_keys) * row_h - view_h)
            self.threat_scroll_y = max(0, min(max_scroll, self.threat_scroll_y - delta_y * row_h))

    def handle_click(self, pos, save_data):
        # 1. Databank Modal intercepts all clicks when active
        if self.mode == "encyclopedia":
            # Close Button
            if self.get_encyclopedia_close_rect().collidepoint(pos):
                self.mode = "overview"
                return "CLICK"

            # Category Tabs
            for cat_name, t_rect in self.get_encyclopedia_tabs().items():
                if t_rect.collidepoint(pos):
                    if self.encyclopedia_tab != cat_name:
                        self.encyclopedia_tab = FlexibleTabStr(cat_name.lower())
                        if self.encyclopedia_tab == 'threats':
                            self.encyclopedia_sel = 'scout'
                            self.threat_scroll_y = 0
                        elif self.encyclopedia_tab == 'weapons':
                            self.encyclopedia_sel = 'auto_cannon'
                        elif self.encyclopedia_tab == 'engines':
                            self.encyclopedia_sel = 'base'
                        elif self.encyclopedia_tab == 'shields':
                            self.encyclopedia_sel = 'front'
                        elif self.encyclopedia_tab == 'drops':
                            self.encyclopedia_sel = 'weapon_overdrive'
                    return "CLICK"

            # Threat list scroll buttons & items
            if self.encyclopedia_tab == "threats":
                if self.get_threat_scroll_up_rect().collidepoint(pos):
                    self.threat_scroll_y = max(0, self.threat_scroll_y - self._sc(64))
                    return "CLICK"
                if self.get_threat_scroll_down_rect().collidepoint(pos):
                    row_h = self._sc(32)
                    view_h = self._sc(400)
                    max_scroll = max(0, len(self.threat_keys) * row_h - view_h)
                    self.threat_scroll_y = min(max_scroll, self.threat_scroll_y + self._sc(64))
                    return "CLICK"

                # Check Threat item click
                panel_rect = self.get_encyclopedia_panel_rect()
                header_h = self.get_encyclopedia_header_h()
                list_y_start = panel_rect.y + header_h + self._sc(10) + self._sc(36)
                row_h = self._sc(32)
                for idx, enemy_key in enumerate(self.threat_keys):
                    row_y = list_y_start + idx * row_h - self.threat_scroll_y
                    if panel_rect.y + self._sc(90) <= row_y <= panel_rect.bottom - self._sc(40):
                        row_rect = pygame.Rect(panel_rect.x + self._sc(16), row_y, self._sc(224), self._sc(30))
                        if row_rect.collidepoint(pos):
                            self.encyclopedia_sel = enemy_key
                            return "CLICK"

            # Module list click
            else:
                cat_key = self.encyclopedia_tab.lower()
                if cat_key == 'drops':
                    items = [
                        {'id': 'weapon_overdrive', 'name': 'Weapon Overdrive'},
                        {'id': 'engine_overdrive', 'name': 'Engine Overdrive'},
                        {'id': 'shield_surge', 'name': 'Shield Surge'}
                    ]
                else:
                    items = self.shop_items.get(cat_key, [])
                panel_rect = self.get_encyclopedia_panel_rect()
                header_h = self.get_encyclopedia_header_h()
                start_y = panel_rect.y + header_h + self._sc(10) + self._sc(44)
                card_h = self._sc(86)
                card_gap = self._sc(8)
                for idx, item in enumerate(items):
                    card_rect = pygame.Rect(panel_rect.x + self._sc(20), start_y + idx * (card_h + card_gap), self._sc(224), card_h)
                    if card_rect.collidepoint(pos):
                        self.encyclopedia_sel = item['id']
                        return "CLICK"
                        return "CLICK"

            # Click inside panel is absorbed
            if self.get_encyclopedia_panel_rect().collidepoint(pos):
                return "CLICK"

            # Click outside panel closes modal
            self.mode = "overview"
            return "CLICK"

        # 2. Main Hangar Interactions
        # Action Buttons
        if self.get_back_rect().collidepoint(pos):
            return "BACK"
        if self.get_databank_btn_rect().collidepoint(pos):
            self.mode = "encyclopedia"
            return "CLICK"

        # Overview vs Customize
        if self.mode == "overview":
            if self.get_customize_btn_rect().collidepoint(pos):
                self.mode = "customize"
                return "CLICK"
        elif self.mode == "customize":
            if self.get_close_customize_btn_rect().collidepoint(pos):
                self.mode = "overview"
                return "CLICK"

            for cat, t_rect in self.get_custom_tabs().items():
                if t_rect.collidepoint(pos):
                    self.custom_tab = cat
                    return "CLICK"

            items = self.shop_items.get(self.custom_tab, [])
            for idx, item in enumerate(items):
                i_rect = self.get_custom_item_rect(idx)
                if i_rect.collidepoint(pos):
                    msg = self.purchase_callback(self.custom_tab, item)
                    if msg:
                        self.set_notice(msg)
                    return "SAVE_DATA"

        return None
