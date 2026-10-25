import math
import pygame
from src.entities import Enemy, EnemyBullet, OverclockPickup, FloatingText

class TutorialController:
    BOOT_LINES = [
        ("CRITICAL ALERT // SECTOR 04 BREACH DETECTED", (255, 60, 60)),
        ("ENVIRONMENTAL INTEGRITY COMPROMISED...", (255, 60, 60)),
        ("EVACUATION PROTOCOLS FAILED.", (255, 60, 60)),
        ("WAKING INTERCEPTOR PILOT...", (255, 200, 50)),
    ]

    # Script Format: (Pose, Name, Text, Auto-Trigger Action)
    INTRO_SCRIPT = [
        ("hello", "COMMANDER VANCE", "Wake up, Rookie. I'm Commander Vance. The Nautolan Swarm just breached our perimeter.", None),
        ("talking", "COMMANDER VANCE", "Environmental alarms are blaring. We don't have time for a standard briefing.", None),
        ("talking", "COMMANDER VANCE", "I'm dumping your consciousness straight into the VR Calibration deck. Get ready.", "START_COMBAT"),
    ]

    DEBRIEF_SCRIPT = [
        ("thumbs_up", "COMMANDER VANCE", "Excellent work in the simulator. Your reflexes are sharp.", None),
        ("talking", "COMMANDER VANCE", "Now let's head to the Hangar deck to inspect your Interceptor's hardpoints and ship facilities.", "ENTER_HANGAR_TOUR"),
    ]
    POST_SCRIPT = DEBRIEF_SCRIPT

    GOODBYE_SCRIPT = [
        ("thumbs_up", "COMMANDER VANCE", "You're ready for active duty, Pilot. I've transferred a 100 Credit deployment grant to your account.", "GRANT_CREDITS"),
        ("thumbs_up", "COMMANDER VANCE", "Push back the Swarm and defend the fleet. Best of luck out there. Vance out.", "END_TUTORIAL"),
    ]

    def __init__(self, assets):
        self.assets = assets
        self.enemy_types = {e['name']: e for e in assets['enemy_types']}
        
        # Dialogue State
        self.script = []
        self.script_idx = 0
        self.char_idx = 0.0
        self.typing_speed = 30.0  # chars per second
        self.boot_duration = len(self.BOOT_LINES) * 2200 + 1000
        self.credits_granted = False
        
        self.reset_boot()
        self.reset_tutorial()

    def get_training_save_data(self, base_save: dict) -> dict:
        sim_save = dict(base_save)
        sim_save['equipped_weapon'] = 'auto_cannon'
        sim_save['equipped_engine'] = 'burst'
        sim_save['equipped_shield'] = 'front'
        sim_save['difficulty'] = 'easy'
        return sim_save

    def reset_boot(self):
        self.state = "BOOT"
        self.boot_started_at = pygame.time.get_ticks()
        self.boot_duration = len(self.BOOT_LINES) * 2200 + 1000
        self.last_beep_line = -1

    def reset_tutorial(self, now: int = 0):
        self.step = 1
        self.combat_delay_until = 0
        self.completed = False
        self.grid_scroll_y = 0.0
        self.waypoints = [[200, 420, 38, False], [600, 420, 38, False], [400, 480, 38, False]]
        self.step_spawned = False
        self.reloaded_in_step2 = False
        self.evaded_in_step3 = False
        self.shield_used_in_step4 = False
        self.pickup_collected_in_step6 = False
        self.final_wave_spawned = False
        self.tour_step = 0
        self.tour_step_started_at = 0
        self.credits_granted = False

    def load_script(self, script_data):
        self.script = script_data
        self.script_idx = 0
        self.char_idx = 0.0

    def handle_dialogue_input(self) -> str | None:
        """Called when SPACE is pressed during dialogue."""
        if not self.script or self.script_idx >= len(self.script):
            return None
        
        pose, name, text, action = self.script[self.script_idx]
        if self.char_idx < len(text):
            # Skip typing immediately
            self.char_idx = float(len(text))
            return None
        else:
            # Advance script
            self.script_idx += 1
            self.char_idx = 0.0
            if 'click' in self.assets.get('sfx', {}):
                try:
                    self.assets['sfx']['click'].play()
                except Exception:
                    pass
            return action

    def update_boot(self, now: int) -> bool:
        elapsed = now - self.boot_started_at
        line_idx = elapsed // 2200  # Extremely slow pacing (2.2s per line)
        if line_idx > self.last_beep_line and line_idx < len(self.BOOT_LINES):
            self.last_beep_line = line_idx
            if 'click' in self.assets.get('sfx', {}):
                try:
                    self.assets['sfx']['click'].play()
                except Exception:
                    pass
        if elapsed >= self.boot_duration:
            self.state = "INTRO_DIALOGUE"
            self.load_script(self.INTRO_SCRIPT)
            return True
        return False

    def draw_boot(self, display: pygame.Surface, theme, scale: float, now: int):
        W, H = display.get_size()
        elapsed = max(0, now - self.boot_started_at)
        
        # Red Emergency Pulse
        pulse = int(50 + 40 * math.sin(now / 300.0))
        display.fill((pulse, 5, 5))

        for y in range(0, H, max(2, int(4 * scale))):
            pygame.draw.line(display, (20, 5, 5), (0, y), (W, y), 1)

        alert_pulse = int(140 + 70 * math.sin(now / 250.0))
        pygame.draw.rect(display, (alert_pulse, 20, 20), (0, 0, W, H), max(2, int(4 * scale)))

        y_cursor = H // 2 - int(100 * scale)
        for idx, (text, color) in enumerate(self.BOOT_LINES):
            line_start = idx * 2200
            if elapsed >= line_start:
                chars = min(len(text), max(1, int((elapsed - line_start) / 55)))  # Slower typing
                shown = f"> {text[:chars]}"
                surf = theme.mono.render(shown, True, color)
                display.blit(surf, (W // 2 - int(300 * scale), y_cursor))
            y_cursor += int(50 * scale)

        skip_font = getattr(theme, 'small', getattr(theme, 'body_small', theme.mono_small))
        skip_s = skip_font.render("PRESS [SPACE] TO CONTINUE", True, (220, 80, 80))
        display.blit(skip_s, skip_s.get_rect(center=(W // 2, H - int(50 * scale))))

    def draw_dialogue_box(self, display, theme, scale, now):
        """Renders the Commander Dialogue UI."""
        if not self.script or self.script_idx >= len(self.script):
            return
        pose, name, text, action = self.script[self.script_idx]
        
        # Typing progression
        if self.char_idx < len(text):
            self.char_idx += self.typing_speed * (1/60.0)

        W, H = display.get_size()
        panel_w = int(740 * scale)
        panel_h = int(145 * scale)
        px = (W - panel_w) // 2
        py = H - panel_h - int(35 * scale)
        rect = pygame.Rect(px, py, panel_w, panel_h)

        # Background
        surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        surf.fill((10, 15, 25, 240))
        display.blit(surf, rect.topleft)
        pygame.draw.rect(display, (0, 225, 255), rect, max(1, int(2 * scale)), border_radius=int(6 * scale))

        # Astronaut Portrait
        port_sz = int(120 * scale)
        port_rect = pygame.Rect(px + int(12 * scale), py + int(12 * scale), port_sz, port_sz)
        pygame.draw.rect(display, (20, 30, 45), port_rect, border_radius=int(4 * scale))
        
        portrait = self.assets.get('astronaut', {}).get(pose, self.assets.get('astronaut', {}).get('hello'))
        if portrait:
            try:
                p_scaled = pygame.transform.smoothscale(portrait, (port_sz, port_sz))
                display.blit(p_scaled, port_rect)
            except Exception:
                pass
        pygame.draw.rect(display, (0, 225, 255), port_rect, 1, border_radius=int(4 * scale))

        # Text
        name_s = theme.button.render(name, True, (255, 205, 70))
        display.blit(name_s, (px + port_sz + int(24 * scale), py + int(14 * scale)))
        
        display_text = text[:int(self.char_idx)]
        
        # Word Wrap implementation
        words = display_text.split()
        lines = []
        curr = ""
        max_w = panel_w - port_sz - int(45 * scale)
        body_font = getattr(theme, 'body', getattr(theme, 'body_small', theme.mono))
        for w in words:
            test_line = (curr + " " + w) if curr else w
            if body_font.size(test_line)[0] < max_w:
                curr = test_line
            else:
                if curr:
                    lines.append(curr)
                curr = w
        if curr:
            lines.append(curr)
        
        ly = py + int(46 * scale)
        for l in lines:
            ls = body_font.render(l.strip(), True, (235, 245, 255))
            display.blit(ls, (px + port_sz + int(24 * scale), ly))
            ly += int(22 * scale)

        # Press Space Prompt
        if self.char_idx >= len(text):
            blink = int(155 + 100 * math.sin(now / 150.0))
            small_font = getattr(theme, 'small', getattr(theme, 'mono_small', body_font))
            pmpt = small_font.render("PRESS [SPACE]", True, (0, blink, blink))
            display.blit(pmpt, (px + panel_w - int(135 * scale), py + panel_h - int(24 * scale)))

    def update_combat_sim(self, now: int, player, enemies: list, enemy_bullets: list,
                          overclock_pickups: list, spark_particles: list, floating_texts: list) -> str | None:
        if self.completed:
            return "COMBAT_CLEARED"

        self.grid_scroll_y = (self.grid_scroll_y + 1.8) % 40.0

        if getattr(player, 'hp', 100) <= 25:
            player.hp = 100
            floating_texts.append(FloatingText(player.rect.centerx, player.rect.top - 10, "SIM HULL RESTORED", (55, 235, 145)))

        if now < self.combat_delay_until:
            return None  # BREATHER PAUSE

        if self.step == 1:
            all_cleared = True
            for wp in self.waypoints:
                if not wp[3]:
                    dist = math.hypot(player.rect.centerx - wp[0], player.rect.centery - wp[1])
                    if dist <= wp[2] + 18:
                        wp[3] = True
                        if 'credit_pickup' in self.assets.get('sfx', {}):
                            self.assets['sfx']['credit_pickup'].play()
                        floating_texts.append(FloatingText(wp[0], wp[1], "WAYPOINT LOCKED", (0, 240, 255)))
                    else:
                        all_cleared = False
            if all_cleared:
                self._advance_step(now, enemies, enemy_bullets, overclock_pickups)

        elif self.step == 2:
            if not self.step_spawned:
                self.step_spawned = True
                for sx in (260, 540):
                    drone = Enemy(self.enemy_types['scout'], behavior='straight', spawn_x=sx, spawn_y=140, difficulty='easy')
                    drone.speed = 0.0
                    drone.shoot_cooldown = 999999
                    drone.hp = 3
                    drone.max_hp = 3
                    enemies.append(drone)
            if getattr(player, 'is_reloading', False):
                self.reloaded_in_step2 = True
            if len(enemies) == 0 and (self.reloaded_in_step2 or getattr(player, 'shots_fired', 0) >= 4):
                self._advance_step(now, enemies, enemy_bullets, overclock_pickups)

        elif self.step == 3:
            if not self.step_spawned:
                self.step_spawned = True
                corvette = Enemy(self.enemy_types['torpedo'], behavior='straight', spawn_x=380, spawn_y=90, difficulty='easy')
                corvette.speed = 0.0
                corvette.shoot_cooldown = 999999
                corvette.hp = 6
                corvette.max_hp = 6
                enemies.append(corvette)
                proj_frames = self.assets['enemy_projectiles']['rocket']
                enemy_bullets.append(EnemyBullet(
                    corvette.rect.centerx, corvette.rect.bottom, proj_frames,
                    speed=3.4, damage=10, vx=0.0, vy=3.4,
                    target=player, homing_turn=0.04, bullet_type="sarh_missile", shooter=corvette
                ))

            if getattr(player, 'chaff_deployed', False) or getattr(player, 'engine_uses', 0) > 0:
                self.evaded_in_step3 = True
                for eb in enemy_bullets:
                    if getattr(eb, 'bullet_type', '') == 'sarh_missile':
                        eb.bullet_type = 'ballistic_lost_lock'

            if self.evaded_in_step3 and len(enemies) == 0:
                self._advance_step(now, enemies, enemy_bullets, overclock_pickups)

        elif self.step == 4:
            if not getattr(player, 'shield_active', False) and getattr(player, 'shield_remaining', 0) < getattr(player, 'shield_capacity', 30):
                player.shield_remaining = player.shield_capacity
                player.shield_ready_at = 0

            if not self.step_spawned or len(enemy_bullets) == 0:
                self.step_spawned = True
                proj_frames = self.assets['enemy_projectiles']['wave']
                for offset in (-70, 0, 70):
                    bx = max(60, min(740, player.rect.centerx + offset))
                    enemy_bullets.append(EnemyBullet(bx, 60, proj_frames, speed=4.2, damage=8))

            if getattr(player, 'shield_active', False) and getattr(player, 'shield_remaining', 0) < getattr(player, 'shield_capacity', 30):
                self.shield_used_in_step4 = True

            if self.shield_used_in_step4:
                self._advance_step(now, enemies, enemy_bullets, overclock_pickups)

        elif self.step == 5:
            if not self.step_spawned:
                self.step_spawned = True
                flagship = Enemy(self.enemy_types['frigate'], behavior='barrage', spawn_x=370, spawn_y=90, difficulty='easy')
                flagship.speed = 0.0
                flagship.hp = 10
                flagship.max_hp = 10
                flagship.shoot_cooldown = 999999
                tender = Enemy(self.enemy_types['support'], behavior='heal', spawn_x=210, spawn_y=90, difficulty='easy')
                tender.speed = 0.0
                tender.hp = 5
                tender.max_hp = 5
                tender.shoot_cooldown = 999999
                flagship.is_invulnerable_tethered = True
                flagship.tether_support_ship = tender
                tender.shield_conduit_target = flagship
                enemies.extend([flagship, tender])

            if len(enemies) == 0:
                self._advance_step(now, enemies, enemy_bullets, overclock_pickups)

        elif self.step == 6:
            if not self.step_spawned:
                self.step_spawned = True
                overclock_pickups.append(OverclockPickup(
                    player.rect.centerx, max(120, player.rect.centery - 160),
                    'weapon', 'auto_cannon', self.assets['pickup_weapons']['auto_cannon']
                ))

            if getattr(player, 'is_weapon_overclocked', False):
                self.pickup_collected_in_step6 = True
                if not self.final_wave_spawned:
                    self.final_wave_spawned = True
                    for sx in (220, 400, 580):
                        d = Enemy(self.enemy_types['fighter'], behavior='straight', spawn_x=sx, spawn_y=110, difficulty='easy')
                        d.speed = 0.4
                        d.hp = 4
                        d.max_hp = 4
                        enemies.append(d)

            if self.final_wave_spawned and len(enemies) == 0:
                self.completed = True
                self.state = "DEBRIEF_DIALOGUE"
                self.load_script(self.DEBRIEF_SCRIPT)
                return "COMBAT_CLEARED"

        return None

    # Compatibility alias
    update_tutorial = update_combat_sim

    def draw_pulsing_highlight(self, display: pygame.Surface, rect: pygame.Rect, color: tuple, now: int, scale: float):
        """Draws a pulsing holographic target bracket around an interactive button."""
        if not rect:
            return
        pulse = 0.5 + 0.5 * math.sin(now * 0.007)
        alpha = int(140 + 115 * pulse)
        gw = rect.width + int(12 * scale)
        gh = rect.height + int(12 * scale)
        glow_surf = pygame.Surface((gw, gh), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (*color[:3], alpha), glow_surf.get_rect(), max(2, int(3 * scale)), border_radius=int(6 * scale))
        bx = rect.x - int(6 * scale)
        by = rect.y - int(6 * scale)
        display.blit(glow_surf, (bx, by))

        # Corner target brackets
        blen = int(10 * scale)
        c_col = (255, 255, 255)
        # Top-left
        pygame.draw.line(display, c_col, (bx, by), (bx + blen, by), 2)
        pygame.draw.line(display, c_col, (bx, by), (bx, by + blen), 2)
        # Top-right
        pygame.draw.line(display, c_col, (bx + gw, by), (bx + gw - blen, by), 2)
        pygame.draw.line(display, c_col, (bx + gw, by), (bx + gw, by + blen), 2)
        # Bottom-left
        pygame.draw.line(display, c_col, (bx, by + gh), (bx + blen, by + gh), 2)
        pygame.draw.line(display, c_col, (bx, by + gh), (bx, by + gh - blen), 2)
        # Bottom-right
        pygame.draw.line(display, c_col, (bx + gw, by + gh), (bx + gw - blen, by + gh), 2)
        pygame.draw.line(display, c_col, (bx + gw, by + gh), (bx + gw, by + blen), 2)

    def draw_commander_box(self, display: pygame.Surface, theme, scale: float, title: str, text: str,
                           started_at: int, now: int, pose='talking', y_pos=None, x_pos=None, box_w=None):
        """Renders an authentic holographic comms transmission with Astronaut Commander."""
        W, H = display.get_size()
        box_w = box_w or int(660 * scale)
        box_h = int(142 * scale)
        x_pos = x_pos if x_pos is not None else (W - box_w) // 2
        y_pos = y_pos if y_pos is not None else H - int(155 * scale)

        rect = pygame.Rect(x_pos, y_pos, box_w, box_h)
        surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        surf.fill((8, 16, 32, 235))
        display.blit(surf, rect.topleft)

        accent_color = (255, 205, 70) if pose == 'thumbs_up' else (0, 225, 255)
        pygame.draw.rect(display, accent_color, rect, max(1, int(2 * scale)), border_radius=int(8 * scale))

        astros = self.assets.get('astronaut', {})
        portrait = astros.get(pose, astros.get('hello'))

        port_sz = int(112 * scale)
        if portrait:
            try:
                scaled_port = pygame.transform.smoothscale(portrait, (port_sz, port_sz))
                port_rect = pygame.Rect(x_pos + int(14 * scale), y_pos + int(14 * scale), port_sz, port_sz)
                pygame.draw.rect(display, (12, 24, 46), port_rect, border_radius=int(6 * scale))
                display.blit(scaled_port, port_rect.topleft)
                pygame.draw.rect(display, accent_color, port_rect, 1, border_radius=int(6 * scale))
            except Exception:
                pass

        # Text rendering
        tx = x_pos + port_sz + int(24 * scale)
        ty = y_pos + int(14 * scale)
        avail_w = box_w - port_sz - int(38 * scale)

        # Title
        t_font = getattr(theme, 'button', getattr(theme, 'mono_bold', theme.mono))
        title_surf = t_font.render(title, True, accent_color)
        display.blit(title_surf, (tx, ty))

        # Body text with word wrap
        body_font = getattr(theme, 'body', getattr(theme, 'mono', theme.button))
        words = text.split()
        lines = []
        curr = ""
        for w in words:
            test_line = (curr + " " + w) if curr else w
            if body_font.size(test_line)[0] < avail_w:
                curr = test_line
            else:
                if curr:
                    lines.append(curr)
                curr = w
        if curr:
            lines.append(curr)

        ly = ty + int(32 * scale)
        for l in lines:
            ls = body_font.render(l.strip(), True, (235, 245, 255))
            display.blit(ls, (tx, ly))
            ly += int(20 * scale)

    def draw_tour_overlay(self, display: pygame.Surface, theme, scale: float, hangar_view,
                          shop_tabs: dict | None, shop_back_rect: pygame.Rect | None, now: int):
        """Draws non-blocking Commander speech box and button spotlights during the manual tap Carrier tour."""
        W, H = display.get_size()
        if self.tour_step == 1 and hangar_view:
            # Tour Step 1: Hangar Overview
            cust_btn = hangar_view.get_customize_btn_rect()
            if cust_btn:
                self.draw_pulsing_highlight(display, cust_btn, (255, 205, 60), now, scale)
            title = "CARRIER TOUR 1/4 // DOCKING BAY & SPECS"
            text = "This is your Hangar bay. The right panel shows your Interceptor's live Firepower, Mobility, and Defense ratings. Tap or click [ CUSTOMIZE LOADOUT ] to inspect your hardpoints."
            self.draw_commander_box(
                display, theme, scale, title, text,
                self.tour_step_started_at, now, pose='talking',
                x_pos=int(24 * scale), y_pos=H - int(155 * scale), box_w=int(640 * scale)
            )

        elif self.tour_step == 2 and hangar_view:
            # Tour Step 2: Modular Armory Drawer
            db_btn = hangar_view.get_databank_btn_rect()
            if db_btn:
                self.draw_pulsing_highlight(display, db_btn, (0, 230, 255), now, scale)
            title = "CARRIER TOUR 2/4 // MODULAR ARMORY DRAWER"
            text = "Here you can hot-swap owned Weapons, Engines, and Defense Matrices before a sortie. Next, tap or click [ ? DATABANK ] at the bottom to open Fleet Intelligence."
            self.draw_commander_box(
                display, theme, scale, title, text,
                self.tour_step_started_at, now, pose='talking',
                x_pos=int(24 * scale), y_pos=H - int(155 * scale), box_w=int(640 * scale)
            )

        elif self.tour_step == 3 and hangar_view:
            # Tour Step 3: Threat Encyclopedia & Datalink
            close_btn = hangar_view.get_encyclopedia_close_rect()
            if close_btn:
                self.draw_pulsing_highlight(display, close_btn, (255, 90, 110), now, scale)
            title = "CARRIER TOUR 3/4 // THREAT ENCYCLOPEDIA & DATALINK"
            text = "Every enemy ship you destroy in combat is decoded here with hull HP, role, and weak points. Watch the bottom ticker for AI tips! Tap or click [ CLOSE ] to proceed to the Supply Depot."
            self.draw_commander_box(
                display, theme, scale, title, text,
                self.tour_step_started_at, now, pose='talking',
                x_pos=int(24 * scale), y_pos=H - int(155 * scale), box_w=int(640 * scale)
            )

        elif self.tour_step == 4:
            # Tour Step 4: Supply Depot / Shop
            if shop_tabs:
                for tab_rect in shop_tabs.values():
                    self.draw_pulsing_highlight(display, tab_rect, (0, 230, 255), now, scale)
            if shop_back_rect:
                self.draw_pulsing_highlight(display, shop_back_rect, (255, 205, 60), now, scale)

            title = "CARRIER TOUR 4/4 // SUPPLY DEPOT"
            text = "Welcome to the Supply Depot! Spend combat Credits here on Piercing Guns, Homing Rockets, Burst Engines, and Shields. Tap or click [ Back to Menu ] to return to the Bridge."
            self.draw_commander_box(
                display, theme, scale, title, text,
                self.tour_step_started_at, now, pose='talking',
                x_pos=(W - int(660 * scale)) // 2, y_pos=H - int(155 * scale), box_w=int(660 * scale)
            )

    def _advance_step(self, now: int, enemies: list, enemy_bullets: list, overclock_pickups: list):
        enemies.clear()
        enemy_bullets.clear()
        overclock_pickups.clear()
        self.step += 1
        self.combat_delay_until = now + 3500  # 3.5 SECOND BREATHER PAUSE
        self.step_spawned = False
        if 'combo' in self.assets.get('sfx', {}):
            try:
                self.assets['sfx']['combo'].play()
            except Exception:
                pass

    def draw_sim_grid(self, game_surface: pygame.Surface, now: int):
        game_surface.fill((6, 12, 24))
        for x in range(0, 800, 40):
            col = (0, 75, 110) if x % 160 == 0 else (0, 38, 62)
            pygame.draw.line(game_surface, col, (x, 0), (x, 600), 1)
        for y_base in range(0, 640, 40):
            y = int((y_base + self.grid_scroll_y) % 600)
            col = (0, 75, 110) if y_base % 160 == 0 else (0, 38, 62)
            pygame.draw.line(game_surface, col, (0, y), (800, y), 1)

        if self.step == 1 and now >= self.combat_delay_until:
            pulse = int(6 * math.sin(now * 0.006))
            for wx, wy, wr, cleared in self.waypoints:
                if not cleared:
                    pygame.draw.circle(game_surface, (0, 230, 255), (wx, wy), wr + pulse, 2)
                    pygame.draw.circle(game_surface, (55, 235, 145), (wx, wy), 6)

    def draw_combat_hud(self, display, theme, scale, keybinds, friendly_key_fn, now):
        if now < self.combat_delay_until:
            return  # Don't draw instructions during the breather pause
            
        k_up, k_left, k_down, k_right = map(friendly_key_fn, (keybinds.get('UP', pygame.K_w), keybinds.get('LEFT', pygame.K_a), keybinds.get('DOWN', pygame.K_s), keybinds.get('RIGHT', pygame.K_d)))
        k_shoot = friendly_key_fn(keybinds.get('SHOOT', pygame.K_SPACE))
        k_reload = friendly_key_fn(keybinds.get('RELOAD', pygame.K_r))
        k_boost = friendly_key_fn(keybinds.get('BOOST', pygame.K_LSHIFT))
        k_flare = friendly_key_fn(keybinds.get('FLARE', pygame.K_f))
        k_shield = friendly_key_fn(keybinds.get('SHIELD', pygame.K_e))

        prompts = {
            1: ("STEP 1/6 // THRUSTER VECTORING", f"Navigate through the 3 glowing waypoints using [{k_up}/{k_left}/{k_down}/{k_right}]."),
            2: ("STEP 2/6 // WEAPON CALIBRATION", f"Hold [{k_shoot}] to destroy targets. Press [{k_reload}] to manual reload."),
            3: ("STEP 3/6 // MISSILE EVASION", f"Incoming Missile! Press [{k_flare}] (Flare) or [{k_boost}] (Afterburner) to break lock!"),
            4: ("STEP 4/6 // DEFENSE MATRIX", f"Press [{k_shield}] to project your Shield and absorb incoming fire."),
            5: ("STEP 5/6 // TETHER PRIORITY", "Destroy the left Support Ship FIRST to drop the Flagship's invulnerable shield!"),
            6: ("STEP 6/6 // OVERCLOCK SURGE", "Collect the Overclock Pickup for Twin-Fire Overdrive and wipe out the squad!"),
        }

        title, desc = prompts.get(self.step, ("", ""))
        W, H = display.get_size()
        panel_w = int(660 * scale)
        panel_h = int(86 * scale)
        px = (W - panel_w) // 2
        py = int(14 * scale)
        rect = pygame.Rect(px, py, panel_w, panel_h)

        surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        surf.fill((10, 18, 34, 225))
        display.blit(surf, rect.topleft)
        pygame.draw.rect(display, (0, 225, 255), rect, max(1, int(2 * scale)), border_radius=int(6 * scale))

        t_surf = theme.button.render(title, True, (0, 225, 255))
        d_surf = theme.body.render(desc, True, (235, 245, 255))
        display.blit(t_surf, (px + int(18 * scale), py + int(12 * scale)))
        display.blit(d_surf, (px + int(18 * scale), py + int(42 * scale)))

        # Skip Tutorial button
        skip_rect = self.get_skip_button_rect(W, scale)
        s_surf = pygame.Surface((skip_rect.width, skip_rect.height), pygame.SRCALPHA)
        s_surf.fill((20, 25, 40, 200))
        display.blit(s_surf, skip_rect.topleft)
        pygame.draw.rect(display, (220, 80, 80), skip_rect, max(1, int(1 * scale)), border_radius=int(4 * scale))
        skip_txt = getattr(theme, 'mono_small', getattr(theme, 'small', theme.body)).render("[ ESC / SKIP ]", True, (255, 120, 120))
        display.blit(skip_txt, skip_txt.get_rect(center=skip_rect.center))

    # Compatibility alias
    draw_tutorial_hud = draw_combat_hud

    def get_skip_button_rect(self, screen_w: int, scale: float) -> pygame.Rect:
        bw = int(190 * scale)
        bh = int(34 * scale)
        return pygame.Rect(screen_w - bw - int(24 * scale), int(18 * scale), bw, bh)
