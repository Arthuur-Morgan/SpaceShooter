import pygame
import random
import math

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

_shared_overlay_surf = None

def get_shared_overlay():
    global _shared_overlay_surf
    if _shared_overlay_surf is None or _shared_overlay_surf.get_size() != (SCREEN_WIDTH, SCREEN_HEIGHT):
        _shared_overlay_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    return _shared_overlay_surf

class Player:
    def __init__(self, x, y, assets, save_data=None):
        self.width = 40
        self.height = 40
        self.rect = pygame.Rect(x, y, self.width, self.height)
        self.x, self.y = float(self.rect.x), float(self.rect.y)
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        save_data = save_data or {}
        self.difficulty = save_data.get('difficulty', 'medium')
        self.equipped_weapon = save_data.get('equipped_weapon', 'auto_cannon')
        self.equipped_engine = save_data.get('equipped_engine', 'base')
        self.equipped_shield = save_data.get('equipped_shield')
        if self.equipped_weapon not in assets['weapons']:
            self.equipped_weapon = 'auto_cannon'
        if self.equipped_engine not in assets['engines']:
            self.equipped_engine = 'base'
        if self.equipped_shield not in assets['shields']:
            self.equipped_shield = None
        self.weapon_data = assets['weapons'][self.equipped_weapon]
        self.weapon_frames = self.weapon_data['frames']
        self.bullet_image = self.weapon_data['projectile']
        self.engine_image = assets['engines'][self.equipped_engine]['image']
        self.engine_data = assets['engines'][self.equipped_engine]
        self.engine_ability = self.engine_data['ability']
        self.engine_active_until = 0
        self.engine_ready_at = 0
        self.shift_was_down = False
        self.speed = assets['engines'][self.equipped_engine]['speed']
        self.shield_frames = assets['shields'][self.equipped_shield]['frames'] if self.equipped_shield else []
        self.emergency_shield_frames = assets['shields']['invincibility']['frames']
        self.shield_data = assets['shields'][self.equipped_shield] if self.equipped_shield else None
        self.shield_capacity = self.shield_data['capacity'] if self.shield_data else 0
        self.shield_remaining = self.shield_capacity
        self.shield_active = False
        self.shield_ready_at = 0
        self.shield_was_down = True
        self.max_hp = 100
        self.hp = 100
        self.invulnerable = False
        self.invulnerable_duration = 1000 
        self.last_hit_time = 0
        self.ship_states = assets['player_states']
        self.base_image = self.ship_states['full']
        self.shoot_cooldown = self.weapon_data['cooldown']
        self.last_shot_time = 0
        self.magazine_capacity = self.weapon_data['magazine']
        self.ammo = self.magazine_capacity
        self.is_reloading = False
        self.reload_started = 0
        self.invincibility_until = 0
        self.locked_targets = []
        self.current_frame = 0
        self.is_animating = False
        self.frame_duration = 40
        self.last_frame_time = 0
        self.shots_fired = 0
        self.damage_events = 0
        self.engine_uses = 0
        self.shield_uses = 0
        self.shield_just_collapsed = False
        # In-Run Module Overclock Telemetry
        self.weapon_overclock_until = 0
        self.engine_overclock_until = 0
        self.shield_overcharge_until = 0
        self.shield_overcharge_barrier = 0
        self.afterburner_particles = []
        self.chaff_deployed = False

    @property
    def is_weapon_overclocked(self):
        return pygame.time.get_ticks() < self.weapon_overclock_until

    @property
    def is_engine_overclocked(self):
        return pygame.time.get_ticks() < self.engine_overclock_until

    @property
    def is_shield_overcharged(self):
        return pygame.time.get_ticks() < self.shield_overcharge_until and self.shield_overcharge_barrier > 0

    def take_damage(self, amount):
        if not self.is_protected:
            # 1. Shield Surge Overcharge Barrier (absorbs up to 20 bonus damage)
            if self.is_shield_overcharged:
                if amount <= self.shield_overcharge_barrier:
                    self.shield_overcharge_barrier -= amount
                    return
                else:
                    amount -= self.shield_overcharge_barrier
                    self.shield_overcharge_barrier = 0

            self.damage_events += 1
            # Difficulty-based damage scaling
            if self.difficulty == 'easy':
                scaled_amt = amount * 0.65  # 35% damage mitigation on Easy
            elif self.difficulty == 'hard':
                scaled_amt = amount * 1.15  # 15% more damage on Hard
            else:
                scaled_amt = amount
            damage = max(1, round(scaled_amt))
            if self.shield_active:
                absorbed = min(damage, self.shield_remaining)
                self.shield_remaining -= absorbed
                damage -= absorbed
                if self.shield_remaining <= 0:
                    self.shield_remaining = 0
                    self.shield_active = False
                    self.shield_ready_at = pygame.time.get_ticks() + self.shield_data['cooldown_ms']
                    self.shield_just_collapsed = True
            self.hp -= damage
            self.invulnerable = True
            self.last_hit_time = pygame.time.get_ticks()
            if self.hp < 0: self.hp = 0

    def update(self, keys, keybinds, enemies=()):
        now = pygame.time.get_ticks()
        previous_x, previous_y = self.x, self.y
        if self.invulnerable and (now - self.last_hit_time > self.invulnerable_duration):
            self.invulnerable = False

        # Only recharge when shield is not active and capacity has been spent.
        if (self.shield_data and not self.shield_active
                and self.shield_remaining < self.shield_capacity
                and now >= self.shield_ready_at):
            self.shield_remaining = self.shield_capacity

        if self.is_reloading and now - self.reload_started >= self.weapon_data['reload_ms']:
            self.ammo = self.magazine_capacity
            self.is_reloading = False

        boost_key = keybinds.get('BOOST', keybinds.get('ENGINE_ABILITY', pygame.K_LSHIFT))
        boost_down = bool(keys.get(boost_key, False)) if isinstance(keys, dict) else keys[boost_key]
        if not boost_down and boost_key not in (pygame.K_LSHIFT, pygame.K_RSHIFT):
            shift_fallback = bool(keys.get(pygame.K_LSHIFT, False) or keys.get(pygame.K_RSHIFT, False)) if isinstance(keys, dict) else (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
            boost_down = shift_fallback
        if boost_down and not self.shift_was_down:
            self.activate_engine_ability(now)
        self.shift_was_down = boost_down

        shield_key = keybinds.get('SHIELD', pygame.K_e)
        shield_down = bool(keys.get(shield_key, False)) if isinstance(keys, dict) else keys[shield_key]
        # Fire on key-press (leading edge), consistent with engine_ability above.
        if shield_down and not self.shield_was_down:
            self.activate_shield(now)
        self.shield_was_down = shield_down

        flare_key = keybinds.get('FLARE', keybinds.get('CHAFF', pygame.K_f))
        flare_down = bool(keys.get(flare_key, False)) if isinstance(keys, dict) else keys[flare_key]
        if flare_down and not getattr(self, 'flare_was_down', False):
            self.deploy_chaff(now)
        self.flare_was_down = flare_down
        engine_boost = self.engine_ability['speed_multiplier'] if self.engine_ability and now < self.engine_active_until else 1.0
        movement_speed = self.speed * engine_boost
        if self.is_engine_overclocked:
            movement_speed += 2.2
            if random.random() < 0.7:
                self.afterburner_particles.append([
                    self.rect.centerx + random.uniform(-6, 6),
                    self.rect.bottom - 2,
                    random.uniform(-0.6, 0.6),
                    random.uniform(2.8, 5.0),
                    255
                ])
        active_ab = []
        for p in self.afterburner_particles:
            p[0] += p[2]
            p[1] += p[3]
            p[4] -= 18
            if p[4] > 0:
                active_ab.append(p)
        self.afterburner_particles = active_ab
        k_left = bool(keys.get(keybinds.get('LEFT', pygame.K_a), False) or keys.get(pygame.K_LEFT, False)) if isinstance(keys, dict) else (keys[keybinds.get('LEFT', pygame.K_a)] or keys[pygame.K_LEFT])
        k_right = bool(keys.get(keybinds.get('RIGHT', pygame.K_d), False) or keys.get(pygame.K_RIGHT, False)) if isinstance(keys, dict) else (keys[keybinds.get('RIGHT', pygame.K_d)] or keys[pygame.K_RIGHT])
        k_up = bool(keys.get(keybinds.get('UP', pygame.K_w), False) or keys.get(pygame.K_UP, False)) if isinstance(keys, dict) else (keys[keybinds.get('UP', pygame.K_w)] or keys[pygame.K_UP])
        k_down = bool(keys.get(keybinds.get('DOWN', pygame.K_s), False) or keys.get(pygame.K_DOWN, False)) if isinstance(keys, dict) else (keys[keybinds.get('DOWN', pygame.K_s)] or keys[pygame.K_DOWN])
        if k_left: self.x -= movement_speed
        if k_right: self.x += movement_speed
        if k_up: self.y -= movement_speed
        if k_down: self.y += movement_speed
        self.x = max(0, min(self.x, SCREEN_WIDTH - self.rect.width))
        self.y = max(0, min(self.y, SCREEN_HEIGHT - self.rect.height))
        self.rect.topleft = (round(self.x), round(self.y))
        self.velocity_x = self.x - previous_x
        self.velocity_y = self.y - previous_y
        self.locked_targets = self._rocket_targets(enemies) if self.weapon_data.get('salvo') else []

        if self.hp > 75: self.base_image = self.ship_states['full']
        elif self.hp > 50: self.base_image = self.ship_states['slight']
        elif self.hp > 25: self.base_image = self.ship_states['damaged']
        else: self.base_image = self.ship_states['very_damaged']

        if self.is_animating:
            now = pygame.time.get_ticks()
            if now - self.last_frame_time >= self.frame_duration:
                self.last_frame_time = now
                self.current_frame += 1
                if self.current_frame >= len(self.weapon_frames):
                    self.current_frame = 0
                    self.is_animating = False

    @property
    def emergency_invincible(self):
        return pygame.time.get_ticks() < self.invincibility_until

    @property
    def is_protected(self):
        return self.invulnerable or self.emergency_invincible

    def activate_invincibility(self, duration_ms=5000):
        self.invincibility_until = pygame.time.get_ticks() + duration_ms

    def activate_shield(self, now=None):
        if not self.shield_data or self.shield_active or self.shield_remaining <= 0:
            return False
        now = pygame.time.get_ticks() if now is None else now
        if now < self.shield_ready_at:
            return False
        self.shield_active = True
        self.shield_uses += 1
        return True

    def activate_engine_ability(self, now=None):
        now = pygame.time.get_ticks() if now is None else now
        if now < self.engine_ready_at:
            return False
        duration = self.engine_ability['duration'] if self.engine_ability else 800
        cooldown = self.engine_ability['cooldown'] if self.engine_ability else 3200
        self.engine_active_until = now + duration
        self.engine_ready_at = now + cooldown
        self.engine_uses += 1
        self.chaff_deployed = True
        return True

    def deploy_chaff(self, now=None):
        """Release defensive chaff / flare decoys to deflect homing missiles and break radar lock."""
        now = pygame.time.get_ticks() if now is None else now
        if now < getattr(self, 'flare_ready_at', 0):
            return False
        self.chaff_deployed = True
        self.flare_ready_at = now + 1200
        return True

    def start_reload(self):
        if self.is_reloading or self.ammo >= self.magazine_capacity:
            return False
        self.is_reloading = True
        self.reload_started = pygame.time.get_ticks()
        return True

    def reload_status(self):
        if self.is_reloading:
            remaining = max(0, self.weapon_data['reload_ms'] - (pygame.time.get_ticks() - self.reload_started))
            return f"RELOADING {remaining / 1000:.1f}s"
        return f"{self.ammo}/{self.magazine_capacity}"

    def _rocket_targets(self, enemies):
        lock_range = self.weapon_data['lock_range']
        candidates = []
        for enemy in enemies:
            dx = enemy.rect.centerx - self.rect.centerx
            dy = self.rect.centery - enemy.rect.centery
            distance = math.hypot(dx, dy)
            if dy > 0 and distance <= lock_range and abs(dx) <= dy * 0.8:
                candidates.append((distance, enemy))
        candidates.sort(key=lambda item: item[0])
        return [enemy for _, enemy in candidates[:3]]

    def shoot(self, keys, keybinds, enemies):
        now = pygame.time.get_ticks()
        is_overclocked = self.is_weapon_overclocked
        w_id = self.equipped_weapon

        # Auto Cannon Overclock: Zero reload downtime / continuous fire
        if is_overclocked and w_id == 'auto_cannon':
            self.is_reloading = False
            self.ammo = self.magazine_capacity

        shoot_key = keybinds.get('SHOOT', pygame.K_SPACE)
        shoot_down = bool(keys.get(shoot_key, False)) if isinstance(keys, dict) else keys[shoot_key]
        if not shoot_down or (self.is_reloading and not (is_overclocked and w_id == 'auto_cannon')):
            return []

        salvo_size = self.weapon_data.get('salvo', 1)
        # Rockets Overclock: 5-rocket salvo!
        if is_overclocked and w_id == 'rockets':
            salvo_size = 5

        if self.ammo < salvo_size:
            if is_overclocked and w_id == 'auto_cannon':
                self.ammo = self.magazine_capacity
            else:
                self.start_reload()
                return []

        # Fire rate computation
        base_cd = self.weapon_data['cooldown']
        if is_overclocked:
            if w_id == 'auto_cannon':
                base_cd = base_cd * 0.50  # 2x fire rate
            elif w_id == 'big_space_gun':
                base_cd = 320  # 320ms fire rate
            elif w_id == 'rockets':
                base_cd = base_cd * 0.70

        fire_rate = self.engine_ability['fire_rate_multiplier'] if self.engine_ability and now < self.engine_active_until else 1.0
        if now - self.last_shot_time < base_cd * fire_rate:
            return []

        self.last_shot_time = now
        self.ammo -= salvo_size
        self.shots_fired += salvo_size
        self.is_animating = True
        self.current_frame = 0
        self.last_frame_time = now

        b_speed = self.weapon_data['speed']
        b_damage = self.weapon_data['damage']
        b_pierce = self.weapon_data.get('pierce', 0)
        b_chain_range = self.weapon_data.get('chain_range', 0)
        b_chain_count = self.weapon_data.get('chain_count', 0)
        b_image = self.bullet_image

        if is_overclocked:
            if w_id == 'auto_cannon':
                # Twin parallel bullets
                shots = []
                for x_off in (-7, 7):
                    shots.append(Bullet(
                        self.rect.centerx + x_off, self.rect.top, b_image,
                        speed=b_speed, damage=b_damage,
                        pierce=b_pierce
                    ))
                return shots
            elif w_id == 'big_space_gun':
                b_pierce = 99  # Pierces all targets
                bw, bh = b_image.get_size()
                b_image = pygame.transform.scale(b_image, (int(bw * 1.3), int(bh * 1.3)))
            elif w_id == 'rockets':
                b_speed = b_speed * 1.40  # +40% velocity
            elif w_id == 'zapper':
                b_chain_count = 4  # Chains up to 4 targets
                b_chain_range = int(b_chain_range * 1.5)  # +50% range

        targets = self.locked_targets if self.weapon_data.get('salvo') else []
        shots = []
        for i in range(salvo_size):
            step = 10 if salvo_size <= 3 else 8
            x_offset = (i - (salvo_size - 1) / 2) * step if salvo_size > 1 else 0
            target = targets[i % len(targets)] if targets else None
            shots.append(Bullet(
                self.rect.centerx + x_offset, self.rect.top, b_image,
                speed=b_speed, damage=b_damage,
                pierce=b_pierce, target=target,
                max_range=self.weapon_data.get('lock_range', 0) + 240 if target else None,
                chain_range=b_chain_range,
                chain_count=b_chain_count,
            ))
        return shots

    def draw(self, screen):
        now = pygame.time.get_ticks()

        # Cyan Afterburner Wake during Engine Overdrive
        if getattr(self, 'afterburner_particles', None):
            for p in self.afterburner_particles:
                s_alpha = max(0, min(255, p[4]))
                s_surf = pygame.Surface((8, 8), pygame.SRCALPHA)
                pygame.draw.circle(s_surf, (0, 240, 255, s_alpha), (4, 4), 3)
                pygame.draw.circle(s_surf, (180, 255, 255, s_alpha), (4, 4), 1)
                screen.blit(s_surf, (round(p[0] - 4), round(p[1] - 4)))

        if self.invulnerable and not self.emergency_invincible and (now // 100) % 2 == 0: return 
        screen.blit(self.engine_image, self.engine_image.get_rect(center=self.rect.center))
        weapon_img = self.weapon_frames[self.current_frame]
        screen.blit(weapon_img, weapon_img.get_rect(center=self.rect.center))
        screen.blit(self.base_image, self.base_image.get_rect(center=self.rect.center))
        visible_shield = self.shield_frames if self.shield_active else []
        if self.emergency_invincible:
            visible_shield = self.emergency_shield_frames
        if visible_shield:
            shield_img = visible_shield[(now // 80) % len(visible_shield)]
            screen.blit(shield_img, shield_img.get_rect(center=self.rect.center))

        # Golden/Cyan Shield Barrier during Shield Surge Overcharge
        if self.is_shield_overcharged:
            s_radius = max(self.rect.width, self.rect.height) // 2 + 8
            pulse = int(140 + 60 * math.sin(now / 110.0))
            overlay = get_shared_overlay()
            overlay.fill((0, 0, 0, 0))
            pygame.draw.circle(overlay, (255, 215, 60, pulse), self.rect.center, s_radius, 2)
            pygame.draw.circle(overlay, (80, 255, 140, pulse // 2), self.rect.center, s_radius - 2, 1)
            screen.blit(overlay, (0, 0))

class Bullet:
    def __init__(self, x, y, image, speed=10, damage=1, pierce=0, target=None, max_range=None, chain_range=0, chain_count=0):
        self.image = image
        self.rect = self.image.get_rect(midbottom=(x, y))
        self.x, self.y = float(self.rect.centerx), float(self.rect.centery)
        self.speed = float(speed)
        self.vx, self.vy = 0.0, -float(speed)
        self.damage = damage
        self.pierce = pierce
        self.target = target
        self.max_range = max_range
        self.distance_travelled = 0
        self.expired = False
        self.hit_enemies = set()
        self.chain_range = chain_range
        self.chain_count = chain_count
        # Individual Missile Deflection & Trajectory Telemetry
        self.is_rocket = (max_range is not None)
        self.deflected = False
        self.flare_evaluated = False
        self.deflect_spin = 0.0
        self.deflection_smoke = []

    def update(self, enemies=None):
        if self.deflected:
            self.target = None
            self.vx *= 0.985
            self.vy += 0.08
            self.deflect_spin += 16.0
            self.x += self.vx
            self.y += self.vy
            self.rect.center = (round(self.x), round(self.y))
            self.distance_travelled += self.speed
            # Generate smoke particles
            if random.random() < 0.65:
                self.deflection_smoke.append([self.x, self.y, random.uniform(-0.8, 0.8), random.uniform(-0.5, 0.5), 180, random.uniform(2, 5)])
            active_smoke = []
            for p in self.deflection_smoke:
                p[0] += p[2]
                p[1] += p[3]
                p[4] -= 12
                if p[4] > 0:
                    active_smoke.append(p)
            self.deflection_smoke = active_smoke
            if (self.distance_travelled >= (self.max_range + 220 if self.max_range else 800)
                    or self.x < -50 or self.x > SCREEN_WIDTH + 50 or self.y > SCREEN_HEIGHT + 50):
                self.expired = True
            return

        if self.target is not None and enemies is not None:
            if self.target in enemies:
                dx = self.target.rect.centerx - self.x
                dy = self.target.rect.centery - self.y
                distance = math.hypot(dx, dy) or 1
                desired_vx = dx / distance * self.speed
                desired_vy = dy / distance * self.speed
                self.vx = self.vx * 0.86 + desired_vx * 0.14
                self.vy = self.vy * 0.86 + desired_vy * 0.14
                velocity = math.hypot(self.vx, self.vy) or 1
                self.vx *= self.speed / velocity
                self.vy *= self.speed / velocity
            else:
                self.target = None
        self.x += self.vx
        self.y += self.vy
        self.rect.center = (round(self.x), round(self.y))
        self.distance_travelled += self.speed
        if self.max_range is not None and self.distance_travelled >= self.max_range:
            self.expired = True

    def draw(self, screen):
        # Render deflection smoke trails
        if self.deflection_smoke:
            for p in self.deflection_smoke:
                smk = pygame.Surface((10, 10), pygame.SRCALPHA)
                pygame.draw.circle(smk, (220, 130, 40, int(p[4])), (5, 5), int(p[5]))
                screen.blit(smk, (round(p[0]) - 5, round(p[1]) - 5))

        if self.deflected:
            image = pygame.transform.rotate(self.image, self.deflect_spin)
            screen.blit(image, image.get_rect(center=self.rect.center))
        elif self.max_range is not None:
            angle = math.degrees(math.atan2(self.vx, -self.vy))
            image = pygame.transform.rotate(self.image, -angle)
            screen.blit(image, image.get_rect(center=self.rect.center))
        else:
            screen.blit(self.image, self.rect)

class EnemyBullet:
    def __init__(self, x, y, frames, speed=6, damage=3, vx=0, vy=None,
                 target=None, homing_turn=0.0, bullet_type="normal", shooter=None, shield_damage=None):
        self.frames = frames
        self.damage = damage
        self.shield_damage = shield_damage if shield_damage is not None else (45 if bullet_type == "shield_buster_torpedo" else damage)
        self.vx = float(vx)
        self.vy = float(speed if vy is None else vy)
        self.current_frame = 0
        self.frame_duration = 60
        self.born_at = pygame.time.get_ticks()
        self.burnout_at = self.born_at + 2800  # 2.8s rocket burn limit
        self.last_frame_time = self.born_at
        self.image = self.frames[self.current_frame]
        self.rect = self.image.get_rect(midtop=(x, y))
        self.x, self.y = float(self.rect.centerx), float(self.rect.top)
        # Guidance parameters (SARH & EMP Shield-Buster Homing)
        self.target = target
        self.homing_turn = float(homing_turn)
        self.bullet_type = bullet_type
        self.shooter = shooter
        self.trail_positions = []

    def update(self):
        now = pygame.time.get_ticks()

        # 1. Guidance Logic for SARH Missiles and Homing Shield-Buster Torpedoes
        if self.bullet_type in ("sarh_missile", "shield_buster_torpedo") and self.target is not None:
            shooter_alive = (self.shooter is not None and getattr(self.shooter, 'hp', 0) > 0)
            target_alive = (getattr(self.target, 'hp', 0) > 0)

            # A. Fuel Burnout check: rocket motor cuts out after 2.8s
            if now >= self.burnout_at:
                self.bullet_type = "ballistic_lost_lock"
            # B. Seeker Aspect Overshoot: if missile has flown past target vertically by > 12px, seeker loses line-of-sight!
            elif self.y > getattr(self.target.rect, 'centery', 9999) + 12:
                self.bullet_type = "ballistic_lost_lock"
            elif shooter_alive and target_alive and self.homing_turn > 0:
                tx, ty = self.target.rect.centerx, self.target.rect.centery
                dx = tx - self.x
                dy = ty - self.y
                dist = math.hypot(dx, dy)
                target_angle = math.atan2(dx, dy)
                current_angle = math.atan2(self.vx, self.vy)
                angle_diff = (target_angle - current_angle + math.pi) % (2 * math.pi) - math.pi

                # C. Seeker Gimbal / Notching Limit: sharp angular cut (>75°) at close range (<140px) breaks tracking!
                if dist < 140 and abs(angle_diff) > 1.30:
                    self.bullet_type = "ballistic_lost_lock"
                else:
                    turn = max(-self.homing_turn, min(self.homing_turn, angle_diff))
                    new_angle = current_angle + turn
                    current_speed = math.hypot(self.vx, self.vy)
                    self.vx = math.sin(new_angle) * current_speed
                    self.vy = math.cos(new_angle) * current_speed
            else:
                # Flagship or launching corvette destroyed -> Illumination lock broken!
                self.bullet_type = "ballistic_lost_lock"

        # Record exhaust trail points for heavy homing missiles & torpedoes
        if self.bullet_type in ("sarh_missile", "shield_buster_torpedo", "ballistic_lost_lock"):
            self.trail_positions.append((self.rect.centerx, self.rect.centery))
            if len(self.trail_positions) > 7:
                self.trail_positions.pop(0)

        self.x += self.vx
        self.y += self.vy
        self.rect.centerx, self.rect.top = round(self.x), round(self.y)
        if now - self.last_frame_time >= self.frame_duration:
            self.last_frame_time = now
            self.current_frame = (self.current_frame + 1) % len(self.frames)
            center = self.rect.center
            self.image = self.frames[self.current_frame]
            self.rect = self.image.get_rect(center=center)

    def draw(self, screen):
        if self.bullet_type in ("sarh_missile", "shield_buster_torpedo", "ballistic_lost_lock"):
            # Draw missile exhaust trails
            if self.trail_positions:
                for idx, (tx, ty) in enumerate(self.trail_positions):
                    r = max(1, int(1 + (idx / len(self.trail_positions)) * 2.5))
                    if self.bullet_type == "shield_buster_torpedo":
                        color = (0, 240, 255)  # Cyan electric trail for EMP Torpedoes
                    elif self.bullet_type == "sarh_missile":
                        color = (255, 140, 40)  # Orange flame trail for SARH Missiles
                    else:
                        color = (150, 150, 150)  # Faded smoke trail when lock is lost
                    pygame.draw.circle(screen, color, (round(tx), round(ty)), r)

            # Rotate missile image along velocity vector
            angle = -math.degrees(math.atan2(self.vx, self.vy))
            rot_img = pygame.transform.rotate(self.image, angle)
            screen.blit(rot_img, rot_img.get_rect(center=self.rect.center))
        else:
            screen.blit(self.image, self.rect)


class Enemy:
    def __init__(self, enemy_type, behavior="default", spawn_x=None, spawn_y=None, difficulty="medium"):
        self.name = enemy_type['name']
        self.behavior = behavior
        self.difficulty = difficulty
        self.hp = enemy_type['hp']
        self.max_hp = self.hp
        self.contact_damage = enemy_type.get('contact_damage', {'asteroid': 15, 'fighter': 8, 'scout': 5}.get(self.name, 8))
        self.score_value = enemy_type.get('score_value', 10)
        self.explosion_frames = enemy_type['explosion']
        self.flame_frames = enemy_type.get('flame')
        self.idle_frames = enemy_type.get('idle_frames', [enemy_type['ship']])
        self.attack_frames = enemy_type.get('attack_frames', self.idle_frames)
        self.attack_overlay = enemy_type.get('attack_overlay', False)
        self.image = self.idle_frames[0]
        self.frame_started_at = pygame.time.get_ticks()
        self.attack_until = 0
        self.last_shot_time = pygame.time.get_ticks() + random.randint(0, 1000)
        self.strafe_phase = random.uniform(0, math.tau)
        self.heal_ready_at = pygame.time.get_ticks() + 1800
        self.shot_count = 0
        base_speed = {'asteroid': 3.0, 'fighter': 1.9, 'scout': 2.0, 'bomber': 1.35,
                      'torpedo': 1.65, 'support': 1.15, 'frigate': 1.0,
                      'battlecruiser': 0.72, 'dreadnought': 0.32,
                      'klaed_scout': 2.3, 'klaed_fighter': 2.0, 'klaed_torpedo': 1.6,
                      'klaed_bomber': 1.3, 'klaed_support': 1.15, 'klaed_frigate': 1.0,
                      'klaed_battlecruiser': 0.78, 'klaed_dreadnought': 0.34,
                      'nairan_scout': 2.4, 'nairan_fighter': 2.1, 'nairan_torpedo': 1.7,
                      'nairan_bomber': 1.35, 'nairan_support': 1.15, 'nairan_frigate': 1.05,
                      'nairan_battlecruiser': 0.76, 'nairan_dreadnought': 0.33,
                      'shadow_interceptor': 3.2}.get(self.name, 1.0)
        if self.name == 'asteroid' and behavior == 'fast':
            base_speed = 4.5
        base_cd = {'fighter': 1900, 'bomber': 2600, 'torpedo': 3400,
                   'support': 4000, 'frigate': 2100, 'battlecruiser': 2800,
                   'dreadnought': 2900,
                   'klaed_scout': 2200, 'klaed_fighter': 1700, 'klaed_torpedo': 3000,
                   'klaed_bomber': 2500, 'klaed_support': 3800, 'klaed_frigate': 2100,
                   'klaed_battlecruiser': 2700, 'klaed_dreadnought': 2600,
                   'nairan_scout': 2100, 'nairan_fighter': 1600, 'nairan_torpedo': 2900,
                   'nairan_bomber': 2400, 'nairan_support': 3600, 'nairan_frigate': 2000,
                   'nairan_battlecruiser': 2600, 'nairan_dreadnought': 2500,
                   'shadow_interceptor': 1400}.get(self.name, 999999)

        # Apply difficulty adjustments to enemy speed, firing cadence, and contact damage
        if difficulty == 'easy':
            self.speed = base_speed * 0.88
            self.shoot_cooldown = int(base_cd * 1.25)
            self.contact_damage = max(1, round(self.contact_damage * 0.75))
        elif difficulty == 'hard':
            self.speed = base_speed * 1.10
            self.shoot_cooldown = int(base_cd * 0.85)
            self.contact_damage = max(1, round(self.contact_damage * 1.20))
        else:
            self.speed = base_speed
            self.shoot_cooldown = base_cd
        if spawn_x is not None:
            x = max(0, min(float(spawn_x), float(SCREEN_WIDTH - self.image.get_width())))
        else:
            x = float(random.randint(0, max(0, SCREEN_WIDTH - self.image.get_width())))
        y = float(-self.image.get_height() if spawn_y is None else spawn_y)
        self.rect = self.image.get_rect(topleft=(round(x), round(y)))
        self.x, self.y = x, y
        self.initial_x = x
        self.roaming = False
        self.roam_speed = 2.0
        self.target_x, self.target_y = self.x, self.y

        # Squad & Tactical Subsystems
        self.is_leader = False
        self.disarray_until = 0
        self.spotter_target = None
        self.spotter_until = 0
        self.smoke_particles = []

        # Shadow Interceptor Neural Clone State
        self.is_shadow = (self.name == 'shadow_interceptor')
        self.shield_hp = 45 if self.is_shadow else 0
        self.max_shield_hp = 45 if self.is_shadow else 0
        self.afterimages = []
        self.last_dash_time = 0
        self.dash_cooldown = 3200
        self.aim_lock_pos = None
        self.aim_lock_until = 0
        self.dash_vx = 0.0
        self.vx = 0.0

        # Capital Ship / Dreadnought Holographic Telegraph State
        self.charging_salvo = False
        self.charge_progress = 0.0
        self.radar_lock_until = 0
        self.radar_lock_target = None

        # Support Ship Tether State
        self.heal_beams = []
        self.shield_conduit_target = None
        self.is_invulnerable_tethered = False
        self.tether_support_ship = None
        self.tether_prompt_until = 0

        # Torpedo Ship Locking Telegraph
        self.torpedo_lock_active = False
        self.torpedo_lock_pos = None
        self.torpedo_lock_progress = 0.0

        # Asteroid Inbound Hazard Warning State
        self.inbound_warning_until = 0
        self.spawn_lane_x = self.rect.centerx
        self.hit_flash_until = 0

        # Modular Subsystems for capital ships and flagships
        self.subsystems = {}
        if any(k in self.name for k in ('dreadnought', 'battlecruiser', 'frigate')):
            w = self.rect.width
            h = self.rect.height
            self.subsystems = {
                'main_turret': {
                    'name': 'Main Battery',
                    'hp': max(6, int(self.max_hp * 0.35)),
                    'max_hp': max(6, int(self.max_hp * 0.35)),
                    'destroyed': False,
                    'rel_rect': pygame.Rect(int(w * 0.32), int(h * 0.28), int(w * 0.36), int(h * 0.40)),
                },
                'left_engine': {
                    'name': 'Port Thruster',
                    'hp': max(4, int(self.max_hp * 0.25)),
                    'max_hp': max(4, int(self.max_hp * 0.25)),
                    'destroyed': False,
                    'rel_rect': pygame.Rect(int(w * 0.04), int(h * 0.55), int(w * 0.28), int(h * 0.40)),
                },
                'right_engine': {
                    'name': 'Starboard Thruster',
                    'hp': max(4, int(self.max_hp * 0.25)),
                    'max_hp': max(4, int(self.max_hp * 0.25)),
                    'destroyed': False,
                    'rel_rect': pygame.Rect(int(w * 0.68), int(h * 0.55), int(w * 0.28), int(h * 0.40)),
                },
            }

    def check_subsystem_hit(self, hit_rect):
        """Checks if a bullet hit an active subsystem."""
        if not self.subsystems:
            return None
        for sub_id, sub in self.subsystems.items():
            if not sub['destroyed']:
                world_rect = pygame.Rect(
                    self.rect.x + sub['rel_rect'].x,
                    self.rect.y + sub['rel_rect'].y,
                    sub['rel_rect'].width,
                    sub['rel_rect'].height
                )
                if world_rect.colliderect(hit_rect):
                    return sub_id
        return None

    def damage_subsystem(self, sub_id, amount):
        """Applies damage to a specific subsystem. Returns True if destroyed by this shot."""
        if sub_id not in self.subsystems:
            return False
        sub = self.subsystems[sub_id]
        if sub['destroyed']:
            return False
        sub['hp'] -= amount
        if sub['hp'] <= 0:
            sub['hp'] = 0
            sub['destroyed'] = True
            return True
        return False

    @property
    def hitbox(self) -> pygame.Rect:
        if 'dreadnought' in self.name or 'battlecruiser' in self.name:
            dw = int(self.rect.width * 0.22)
            dh = int(self.rect.height * 0.18)
            hb = self.rect.inflate(-dw, -dh)
            hb.center = self.rect.center
            return hb
        elif 'frigate' in self.name:
            dw = int(self.rect.width * 0.15)
            dh = int(self.rect.height * 0.12)
            hb = self.rect.inflate(-dw, -dh)
            hb.center = self.rect.center
            return hb
        return self.rect

    def enter_disarray(self, duration_ms=2200):
        """Puts unit in disarray following the loss of squad leader."""
        if not self.is_leader:
            self.disarray_until = pygame.time.get_ticks() + duration_ms

    def absorb_shield_damage(self, amount: int) -> tuple[int, bool]:
        """Absorbs incoming damage with energy barrier if active. Returns (remaining_damage, shield_broke)."""
        if self.shield_hp <= 0:
            return amount, False
        absorbed = min(self.shield_hp, amount)
        self.shield_hp -= absorbed
        remaining = amount - absorbed
        broke = (self.shield_hp <= 0)
        return remaining, broke

    def _pick_new_scout_target(self):
        self.target_x = random.uniform(0, max(0, SCREEN_WIDTH - self.rect.width))
        self.target_y = random.uniform(0, max(0, SCREEN_HEIGHT // 2 - self.rect.height))

    def _animate(self, now):
        base_frame = self.idle_frames[(now - self.frame_started_at) // 110 % len(self.idle_frames)]
        if now < self.attack_until:
            attack_frame = self.attack_frames[(now - self.frame_started_at) // 55 % len(self.attack_frames)]
            if self.attack_overlay:
                frame = base_frame.copy()
                frame.blit(attack_frame, (0, 0))
            else:
                frame = attack_frame
        else:
            frame = base_frame
        center = (round(self.x + self.rect.width / 2), round(self.y + self.rect.height / 2))
        self.image = frame
        self.rect = self.image.get_rect(center=center)

    def update(self, player=None, allies=()):
        now = pygame.time.get_ticks()

        # Update damaged subsystem smoke trails
        active_smoke = []
        for p in self.smoke_particles:
            p[0] += p[2]
            p[1] += p[3]
            p[4] -= 7
            if p[4] > 0:
                active_smoke.append(p)
        self.smoke_particles = active_smoke

        # Check Disarray State (following loss of squad leader)
        in_disarray = (now < self.disarray_until)

        # 1. Asteroid Behavior
        if self.name == 'asteroid':
            if now < getattr(self, 'inbound_warning_until', 0):
                return
            self.y += self.speed

        # 2. Scout & Skirmishers (Nautolan, Kla'ed, Nairan)
        elif self.name in ('scout', 'klaed_scout', 'nairan_scout'):
            # Spotter Laser Painting Logic: paints player for allied heavy fire
            if player is not None and not in_disarray:
                if self.spotter_until == 0 and random.random() < 0.012:
                    self.spotter_until = now + 1600
                    self.spotter_target = player.rect.center
                elif now > self.spotter_until + 4500:
                    self.spotter_until = 0

            # Swarm Bodyguard check
            damaged_cap = next((a for a in allies if a is not self and any(k in a.name for k in ('dreadnought', 'battlecruiser', 'frigate')) and a.hp < a.max_hp * 0.5), None)

            # Squad Leader Anchoring (Escort wings)
            leader = None
            if not self.is_leader and not in_disarray:
                leader = next((a for a in allies if a is not self and getattr(a, 'is_leader', False) and a.name != 'asteroid'), None)

            if leader is not None:
                offset_x = -70.0 if getattr(self, 'initial_x', self.x) <= leader.rect.centerx else 70.0
                anchor_x = leader.x + offset_x
                anchor_y = leader.y + 25.0
                dx = anchor_x - self.x
                dy = anchor_y - self.y
                self.x += max(-3.4, min(3.4, dx * 0.10))
                self.y += max(-2.2, min(2.2, dy * 0.08))
            # Swarm Bodyguard Protocol: If an allied capital ship is heavily damaged, screen it!
            elif damaged_cap and not in_disarray:
                target_x = player.rect.centerx - self.rect.width / 2 if player else damaged_cap.rect.centerx
                self.x += max(-3.4, min(3.4, (target_x - self.x) * 0.15))
                target_y = min(damaged_cap.rect.bottom + 20, 220)
                self.y += max(-2.0, min(2.0, (target_y - self.y) * 0.10))
            elif in_disarray:
                self.x += math.sin(now / 70 + self.strafe_phase) * 3.8
                self.y += max(0.5, self.speed * 0.7)
            elif self.behavior == 'kamikaze' and player is not None:
                predicted_x = player.rect.centerx + player.velocity_x * 18
                self.x += max(-3.6, min(3.6, predicted_x - self.rect.width / 2 - self.x))
                self.y += 4.5
            elif self.behavior == 'pincer_flank':
                self.y += self.speed * 1.15
                target_lane = SCREEN_WIDTH * 0.40 if getattr(self, 'initial_x', self.x) < SCREEN_WIDTH / 2 else SCREEN_WIDTH * 0.60
                if player is not None and abs(player.rect.centerx - self.x) < 240:
                    target_lane = player.rect.centerx - self.rect.width / 2
                dx = target_lane - self.x
                self.x += max(-3.2, min(3.2, dx * 0.08))
            elif self.behavior == 'escort_screen':
                cap_ships = [a for a in allies if a is not self and any(k in a.name for k in ('dreadnought', 'battlecruiser', 'frigate'))]
                if cap_ships:
                    lead_cap = cap_ships[0]
                    target_x = lead_cap.rect.centerx - self.rect.width / 2 + math.sin(now / 320 + self.strafe_phase) * 55
                    target_y = min(lead_cap.rect.bottom + 25, 200)
                    self.x += max(-3.0, min(3.0, (target_x - self.x) * 0.12))
                    self.y += max(-2.5, min(2.5, (target_y - self.y) * 0.10))
                else:
                    self.y += self.speed
                    self.x += math.sin(now / 240 + self.strafe_phase) * 2.8
            elif not self.roaming:
                self.y += self.speed
                if self.y >= 20:
                    self.roaming = True
                    self._pick_new_scout_target()
            else:
                if (self.behavior in ('hunter', 'hunter_lead')) and player is not None:
                    lead_ticks = 16 if self.behavior == 'hunter_lead' else 10
                    self.target_x = player.rect.centerx + player.velocity_x * lead_ticks - self.rect.width / 2
                    self.target_y = max(85, player.rect.centery - 240)
                    self.roam_speed = 3.0
                dx, dy = self.target_x - self.x, self.target_y - self.y
                distance = math.hypot(dx, dy)
                if distance < 4:
                    self._pick_new_scout_target()
                else:
                    self.x += dx / distance * self.roam_speed
                    self.y += dy / distance * self.roam_speed

        # 2b. The Shadow Interceptor (Neural Clone Mirror AI)
        elif self.name == 'shadow_interceptor':
            # Decay afterimages
            self.afterimages = [(ax, ay, a - 14, s) for (ax, ay, a, s) in self.afterimages if a > 15]

            # Hover altitude
            target_hover_y = 120.0
            if self.y < target_hover_y:
                self.y += min(self.speed, target_hover_y - self.y)
            else:
                self.y = target_hover_y + math.sin(now / 350.0 + self.strafe_phase) * 18.0

            # Smooth dash velocity integration and aerodynamic deceleration
            self.x += self.dash_vx
            self.dash_vx *= 0.88
            if abs(self.dash_vx) > 2.5:
                self.afterimages.append((self.rect.x, self.rect.y, 140, self.image.copy()))

            if player is not None:
                # Mirroring & Reactive Jinking (Smooth damped lateral tracking):
                target_x = player.rect.centerx - self.rect.width / 2 + math.sin(now / 320.0) * 40.0
                dx = target_x - self.x
                self.vx = self.vx * 0.85 + (dx * 0.08) * 0.15
                self.x += max(-4.2, min(4.2, self.vx))

                # Evasive Thruster Dash when player is close or firing
                if now - self.last_dash_time > self.dash_cooldown:
                    if random.random() < 0.03 or abs(player.rect.centerx - self.rect.centerx) < 40:
                        dash_dir = -1.0 if self.x > SCREEN_WIDTH / 2 else 1.0
                        self.afterimages.append((self.rect.x, self.rect.y, 220, self.image.copy()))
                        self.dash_vx = dash_dir * 8.5
                        self.afterimages.append((self.rect.x, self.rect.y, 180, self.image.copy()))
                        self.last_dash_time = now

                # Aim lock telegraph 400ms before shooting
                time_until_shoot = (self.last_shot_time + self.shoot_cooldown) - now
                if 0 < time_until_shoot <= 400:
                    pred_px = player.rect.centerx + player.velocity_x * 12
                    self.aim_lock_pos = (pred_px, player.rect.centery)
                    self.aim_lock_until = now + time_until_shoot
                else:
                    if now > self.aim_lock_until:
                        self.aim_lock_pos = None

        # 3. Fighters (Nautolan, Kla'ed, Nairan)
        elif self.name in ('fighter', 'klaed_fighter', 'nairan_fighter'):
            leader = None
            if not self.is_leader and not in_disarray:
                leader = next((a for a in allies if a is not self and getattr(a, 'is_leader', False) and a.name != 'asteroid'), None)

            if leader is not None:
                offset_x = -70.0 if getattr(self, 'initial_x', self.x) <= leader.rect.centerx else 70.0
                anchor_x = leader.x + offset_x
                anchor_y = leader.y + 25.0
                dx = anchor_x - self.x
                dy = anchor_y - self.y
                self.x += max(-3.4, min(3.4, dx * 0.10))
                self.y += max(-2.0, min(2.0, dy * 0.08))
            elif in_disarray:
                self.x += math.sin(now / 70 + self.strafe_phase) * 3.5
                self.y += max(0.5, self.speed * 0.7)
            elif self.behavior == 'pincer_flank':
                self.y += self.speed * 1.1
                target_x = SCREEN_WIDTH * 0.40 if getattr(self, 'initial_x', self.x) < SCREEN_WIDTH / 2 else SCREEN_WIDTH * 0.60
                if player is not None:
                    target_x = player.rect.centerx - self.rect.width / 2
                dx = target_x - self.x
                self.x += max(-2.8, min(2.8, dx * 0.07))
            elif self.behavior == 'hunter_lead' and player is not None:
                if self.y < 125:
                    self.y += self.speed
                else:
                    self.y += math.sin(now / 450 + self.strafe_phase) * 0.6
                pred_x = player.rect.centerx + player.velocity_x * 16 - self.rect.width / 2
                self.x += max(-3.0, min(3.0, (pred_x - self.x) * 0.09))
            elif self.behavior == 'suppression_sweep':
                if self.y < 115:
                    self.y += self.speed
                p_center = player.rect.centerx if player else SCREEN_WIDTH / 2
                self.x = p_center - self.rect.width / 2 + math.sin(now / 280 + self.strafe_phase) * 130
            else:
                self.y += self.speed
                self.x += math.sin(now / 260 + self.strafe_phase) * 2.6

        # 4. Heavy / Capital / Support / Bomber / Dreadnought
        else:
            hover_y = {'bomber': 110, 'torpedo': 135, 'support': 80, 'frigate': 105,
                       'battlecruiser': 70, 'dreadnought': 38,
                       'klaed_bomber': 115, 'klaed_torpedo': 140, 'klaed_support': 80,
                       'klaed_frigate': 95, 'klaed_battlecruiser': 65,
                       'klaed_dreadnought': 38,
                       'nairan_bomber': 110, 'nairan_torpedo': 135, 'nairan_support': 80,
                       'nairan_frigate': 95, 'nairan_battlecruiser': 65,
                       'nairan_dreadnought': 38}.get(self.name, 90)

            # Generate smoke trails if engines or turrets are destroyed
            if self.subsystems:
                w, h = self.rect.width, self.rect.height
                if self.subsystems.get('left_engine', {}).get('destroyed', False) and (now // 60) % 2 == 0:
                    self.smoke_particles.append([self.rect.x + w * 0.16, self.rect.y + h * 0.80, random.uniform(-0.6, 0.6), random.uniform(-1.5, -0.4), 220, random.uniform(3, 6)])
                if self.subsystems.get('right_engine', {}).get('destroyed', False) and (now // 60) % 2 == 0:
                    self.smoke_particles.append([self.rect.x + w * 0.84, self.rect.y + h * 0.80, random.uniform(-0.6, 0.6), random.uniform(-1.5, -0.4), 220, random.uniform(3, 6)])
                if self.subsystems.get('main_turret', {}).get('destroyed', False) and (now // 80) % 2 == 0:
                    self.smoke_particles.append([self.rect.x + w * 0.50, self.rect.y + h * 0.45, random.uniform(-0.8, 0.8), random.uniform(-1.8, -0.6), 240, random.uniform(4, 7)])

            if 'dreadnought' in self.name:
                target_hover_y = 36.0 + math.sin(now / 1500.0) * 4.0
                if self.y < 36.0:
                    entry_spd = 1.6 if self.y < 0 else self.speed
                    self.y += min(entry_spd, max(0.15, (36.0 - self.y) * 0.06))
                else:
                    self.y += (target_hover_y - self.y) * 0.05
                if self.y >= 0:
                    self.y = min(48.0, max(10.0, self.y))

                if player is not None:
                    target_x = player.rect.centerx - self.rect.width / 2 + math.sin(now / 1100.0 + self.strafe_phase) * 75.0
                    # Tactical Hull Angling: protects damaged engine side
                    if self.subsystems.get('left_engine', {}).get('destroyed', False):
                        target_x += 35
                    elif self.subsystems.get('right_engine', {}).get('destroyed', False):
                        target_x -= 35
                    target_x = max(20, min(SCREEN_WIDTH - self.rect.width - 20, target_x))
                    dx = target_x - self.x

                    speed_mult = 1.0
                    if self.subsystems.get('left_engine', {}).get('destroyed', False):
                        speed_mult *= 0.60
                    if self.subsystems.get('right_engine', {}).get('destroyed', False):
                        speed_mult *= 0.60

                    step = max(-1.6 * speed_mult, min(1.6 * speed_mult, dx * 0.035))
                    self.x += step
            elif self.behavior == 'dive_bomb' and 'bomber' in self.name:
                cycle = (now + int(self.strafe_phase * 1000)) % 4000
                if cycle < 1600:
                    target_dive_y = 185
                    self.y += max(1.2, (target_dive_y - self.y) * 0.08)
                else:
                    self.y = max(hover_y, self.y - 1.4)
                if player is not None:
                    self.x += max(-2.4, min(2.4, (player.rect.centerx - self.rect.width / 2 - self.x) * 0.06))
            elif 'support' in self.name:
                cap_bosses = [a for a in allies if a is not self and any(k in a.name for k in ('dreadnought', 'battlecruiser')) and getattr(a, 'hp', 0) > 0]
                if cap_bosses:
                    boss = cap_bosses[0]
                    boss_cx = boss.rect.centerx
                    boss_cy = boss.rect.centery
                    shield_r = max(boss.rect.width, boss.rect.height) // 2 + 14
                    supp_r = max(self.rect.width, self.rect.height) // 2
                    min_dist = shield_r + supp_r + 16  # Absolute boundary outside the shield
                    standoff_dist = min_dist + 26      # Natural cruising offset (~150px)

                    # Dynamic Flank Allocation: coordinate with other alive support ships
                    if getattr(self, 'escort_flank', None) not in (-1, 1):
                        other_flanks = [getattr(a, 'escort_flank', None) for a in allies if a is not self and 'support' in a.name]
                        if -1 in other_flanks and 1 not in other_flanks:
                            self.escort_flank = 1
                        elif 1 in other_flanks and -1 not in other_flanks:
                            self.escort_flank = -1
                        else:
                            self.escort_flank = -1 if self.rect.centerx <= boss_cx else 1

                    # Flank screen boundary avoidance: switch flanks if pinned against border
                    desired_x = boss_cx + self.escort_flank * standoff_dist
                    if desired_x - supp_r < 20:
                        self.escort_flank = 1
                        desired_x = boss_cx + standoff_dist
                    elif desired_x + supp_r > SCREEN_WIDTH - 20:
                        self.escort_flank = -1
                        desired_x = boss_cx - standoff_dist

                    # Escort target with gentle tactical oscillation outside the shield
                    target_x = desired_x - self.rect.width / 2.0 + math.sin(now / 520.0 + self.strafe_phase) * 14.0
                    target_y = boss_cy - 10.0 + math.sin(now / 420.0 + self.strafe_phase) * 12.0 - self.rect.height / 2.0
                    target_x = max(15, min(SCREEN_WIDTH - self.rect.width - 15, target_x))
                    target_y = max(15, min(SCREEN_HEIGHT * 0.40, target_y))

                    dx = target_x - self.x
                    dy = target_y - self.y
                    self.x += max(-3.0, min(3.0, dx * 0.08))
                    self.y += max(-2.4, min(2.4, dy * 0.08))
                elif self.y < hover_y:
                    self.y += self.speed
                else:
                    self.x += math.sin(now / 400 + self.strafe_phase) * self.speed
            elif self.y < hover_y:
                self.y += self.speed
            else:
                is_heavy = any(k in self.name for k in ('battlecruiser', 'frigate'))
                if is_heavy and player is not None:
                    target_x = player.rect.centerx - self.rect.width / 2 + math.sin(now / 550 + self.strafe_phase) * 65
                    # Tactical Hull Angling: protects damaged engine side
                    if self.subsystems.get('left_engine', {}).get('destroyed', False):
                        target_x += 35
                    elif self.subsystems.get('right_engine', {}).get('destroyed', False):
                        target_x -= 35
                    target_x = max(10, min(SCREEN_WIDTH - self.rect.width - 10, target_x))
                    dx = target_x - self.x

                    speed_mult = 1.0
                    if self.subsystems.get('left_engine', {}).get('destroyed', False):
                        speed_mult *= 0.60
                    if self.subsystems.get('right_engine', {}).get('destroyed', False):
                        speed_mult *= 0.60

                    track_spd = min(4.2, max(0.9, abs(dx) * 0.042)) * speed_mult
                    step = max(-track_spd, min(track_spd, dx * 0.14))
                    self.x += step
                elif 'torpedo' in self.name and player is not None:
                    pred_x = player.rect.centerx + player.velocity_x * 14 - self.rect.width / 2
                    self.x += max(-2.2, min(2.2, (pred_x - self.x) * 0.06))
                else:
                    self.x += math.sin(now / 650 + self.strafe_phase) * self.speed

            if 'support' in self.name:
                # 1. Active Healing Beam
                if now >= self.heal_ready_at:
                    healed_any = False
                    for ally in allies:
                        if ally is not self and ally.name != 'asteroid' and ally.hp < ally.max_hp:
                            if math.hypot(ally.rect.centerx - self.rect.centerx, ally.rect.centery - self.rect.centery) < 190:
                                ally.hp = min(ally.max_hp, ally.hp + 3)
                                self.heal_beams.append({'target': ally, 'target_pos': ally.rect.center, 'expire': now + 400})
                                healed_any = True
                    if healed_any:
                        self.heal_ready_at = now + 2400

                # 2. Boss Defense Tether (Invulnerability Link)
                cap_bosses = [a for a in allies if a is not self and any(k in a.name for k in ('dreadnought', 'battlecruiser', 'frigate'))]
                if cap_bosses:
                    target_boss = cap_bosses[0]
                    self.shield_conduit_target = target_boss
                    target_boss.is_invulnerable_tethered = True
                    target_boss.tether_support_ship = self
                else:
                    self.shield_conduit_target = None

        # Drop invulnerability tether if support ship is no longer alive among allies
        if getattr(self, 'is_invulnerable_tethered', False):
            supp = getattr(self, 'tether_support_ship', None)
            if not supp or supp not in allies or getattr(supp, 'hp', 0) <= 0:
                self.is_invulnerable_tethered = False
                self.tether_support_ship = None

        # Torpedo Ship Target-Locking Laser Telegraph (1.2s prior to firing)
        if 'torpedo' in self.name:
            time_until_shot = (self.last_shot_time + self.shoot_cooldown) - now
            if 0 < time_until_shot <= 1200 and player is not None:
                self.torpedo_lock_active = True
                self.torpedo_lock_pos = (player.rect.centerx, player.rect.centery)
                self.torpedo_lock_progress = 1.0 - (time_until_shot / 1200.0)
            elif time_until_shot <= 0 or now > self.last_shot_time + 120:
                self.torpedo_lock_active = False

        # Check charge telegraph for Capital ships and Dreadnoughts
        is_capital = any(k in self.name for k in ('dreadnought', 'battlecruiser'))
        if is_capital:
            time_until_shot = (self.last_shot_time + self.shoot_cooldown) - now
            if 0 < time_until_shot <= 750:
                self.charging_salvo = True
                self.charge_progress = 1.0 - (time_until_shot / 750.0)
            else:
                self.charging_salvo = False
                self.charge_progress = 0.0

        # Soft Radial Separation Force (Anti-Clustering Flocking)
        if self.name != 'asteroid' and 'dreadnought' not in self.name and self.name != 'shadow_interceptor':
            for other in allies:
                if other is not self and other.name != 'asteroid' and getattr(other, 'hp', 0) > 0:
                    sep_dx = self.rect.centerx - other.rect.centerx
                    sep_dy = self.rect.centery - other.rect.centery
                    dist = math.hypot(sep_dx, sep_dy)
                    is_other_cap = any(k in other.name for k in ('dreadnought', 'battlecruiser'))
                    if 'support' in self.name and is_other_cap:
                        shield_r = max(other.rect.width, other.rect.height) // 2 + 14
                        supp_r = max(self.rect.width, self.rect.height) // 2
                        cap_min_dist = shield_r + supp_r + 16
                        if dist < cap_min_dist:
                            push_force = max(3.5, (cap_min_dist - dist) * 0.25)
                            nx = sep_dx / (dist if dist > 0.001 else 1)
                            ny = sep_dy / (dist if dist > 0.001 else 1)
                            self.x += nx * push_force
                            self.y += ny * (push_force * 0.6)
                    elif 0 < dist < 65:
                        self.x += (sep_dx / dist) * 1.8
                        y_mult = 0.5 if any(k in self.name for k in ('battlecruiser', 'frigate')) else 1.2
                        self.y += (sep_dy / dist) * y_mult

        # Strict Capital Shield Exclusion Boundary: Guarantees support ships NEVER penetrate capital shields
        if 'support' in self.name:
            for cap in allies:
                if cap is not self and cap.name != 'asteroid' and any(k in cap.name for k in ('dreadnought', 'battlecruiser')) and getattr(cap, 'hp', 0) > 0:
                    cap_cx, cap_cy = cap.rect.centerx, cap.rect.centery
                    shield_r = max(cap.rect.width, cap.rect.height) // 2 + 14
                    supp_r = max(self.rect.width, self.rect.height) // 2
                    min_dist = shield_r + supp_r + 18

                    cur_cx = self.x + self.rect.width / 2.0
                    cur_cy = self.y + self.rect.height / 2.0
                    cdx = cur_cx - cap_cx
                    cdy = cur_cy - cap_cy
                    cdist = math.hypot(cdx, cdy)

                    if cdist < min_dist:
                        flank_sign = getattr(self, 'escort_flank', -1)
                        if flank_sign not in (-1, 1):
                            flank_sign = -1.0 if cur_cx <= cap_cx else 1.0

                        if cdist < 0.1:
                            nx, ny = flank_sign, 0.0
                        else:
                            nx = cdx / cdist
                            ny = cdy / cdist
                            if abs(nx) < 0.35:
                                nx = flank_sign * 0.707
                                ny = math.copysign(0.707, ny if ny != 0 else 1.0)
                                norm = math.hypot(nx, ny)
                                nx /= norm
                                ny /= norm

                        target_cx = cap_cx + nx * min_dist
                        target_cy = cap_cy + ny * min_dist

                        if target_cx - supp_r < 15:
                            target_cx = cap_cx + min_dist
                        elif target_cx + supp_r > SCREEN_WIDTH - 15:
                            target_cx = cap_cx - min_dist

                        self.x = target_cx - self.rect.width / 2.0
                        self.y = target_cy - self.rect.height / 2.0

        elif any(k in self.name for k in ('dreadnought', 'battlecruiser')):
            for ally in allies:
                if ally is not self and 'support' in ally.name and getattr(ally, 'hp', 0) > 0:
                    shield_r = max(self.rect.width, self.rect.height) // 2 + 14
                    supp_r = max(ally.rect.width, ally.rect.height) // 2
                    min_dist = shield_r + supp_r + 18

                    acx = ally.x + ally.rect.width / 2.0
                    acy = ally.y + ally.rect.height / 2.0
                    cdx = acx - self.rect.centerx
                    cdy = acy - self.rect.centery
                    cdist = math.hypot(cdx, cdy)

                    if cdist < min_dist:
                        flank_sign = getattr(ally, 'escort_flank', -1)
                        if flank_sign not in (-1, 1):
                            flank_sign = -1.0 if acx <= self.rect.centerx else 1.0

                        if cdist < 0.1:
                            nx, ny = flank_sign, 0.0
                        else:
                            nx = cdx / cdist
                            ny = cdy / cdist
                            if abs(nx) < 0.35:
                                nx = flank_sign * 0.707
                                ny = math.copysign(0.707, ny if ny != 0 else 1.0)
                                norm = math.hypot(nx, ny)
                                nx /= norm
                                ny /= norm

                        target_cx = self.rect.centerx + nx * min_dist
                        target_cy = self.rect.centery + ny * min_dist

                        if target_cx - supp_r < 15:
                            target_cx = self.rect.centerx + min_dist
                        elif target_cx + supp_r > SCREEN_WIDTH - 15:
                            target_cx = self.rect.centerx - min_dist

                        ally.x = target_cx - ally.rect.width / 2.0
                        ally.y = target_cy - ally.rect.height / 2.0
                        ally.rect.x, ally.rect.y = round(ally.x), round(ally.y)

        self.x = max(0, min(self.x, SCREEN_WIDTH - self.rect.width))
        if 'dreadnought' in self.name and self.y >= 0:
            self.y = min(48.0, max(10.0, self.y))
        self.rect.x, self.rect.y = round(self.x), round(self.y)
        self._animate(now)

    def shoot(self, projectiles, player):
        now = pygame.time.get_ticks()
        if 'torpedo' in self.name:
            self.torpedo_lock_active = False
        if now - self.last_shot_time < self.shoot_cooldown:
            return []
        self.last_shot_time = now
        self.attack_until = now + 420
        self.shot_count += 1
        x, y = self.rect.centerx, self.rect.bottom

        # Difficulty bullet speed multiplier
        spd_mult = 0.85 if self.difficulty == 'easy' else (1.14 if self.difficulty == 'hard' else 1.0)

        # Compute aim angle toward the player
        if player is not None:
            dx = player.rect.centerx - x
            dy = max(50, player.rect.centery - y)
        else:
            dx, dy = 0, 100
        aim_angle = math.atan2(dx, dy)

        # ── Shadow Interceptor Mirror Weapon ──────────────────────────
        if self.name == 'shadow_interceptor':
            p_weap = getattr(player, 'equipped_weapon', 'auto_cannon') if player else 'auto_cannon'
            if p_weap == 'rockets':
                pred_x = (player.rect.centerx + player.velocity_x * 12) if player else x
                lead = max(-2.4, min(2.4, (pred_x - x) / 80))
                proj = projectiles.get('nairan_rocket', projectiles.get('rocket'))
                return [EnemyBullet(x - 14, y, proj, speed=5.5 * spd_mult, damage=8, vx=lead - 0.4),
                        EnemyBullet(x + 14, y, proj, speed=5.5 * spd_mult, damage=8, vx=lead + 0.4)]
            elif p_weap == 'zapper':
                proj = projectiles.get('nairan_ray', projectiles.get('ray'))
                return [EnemyBullet(x, y, proj, speed=6.2 * spd_mult, damage=3,
                                    vx=math.sin(aim_angle + off)*6.2*spd_mult, vy=math.cos(aim_angle + off)*6.2*spd_mult)
                        for off in (-0.18, 0.0, 0.18)]
            elif p_weap == 'big_space_gun':
                proj = projectiles.get('klaed_big_bullet', projectiles.get('bomb'))
                return [EnemyBullet(x - 10, y, proj, speed=4.6 * spd_mult, damage=12, vx=-0.4),
                        EnemyBullet(x + 10, y, proj, speed=4.6 * spd_mult, damage=12, vx=0.4)]
            else:
                proj = projectiles.get('nairan_bolt', projectiles.get('bullet'))
                spd = 6.6 * spd_mult
                return [EnemyBullet(x - 10, y, proj, speed=spd, damage=3, vx=math.sin(aim_angle)*spd, vy=math.cos(aim_angle)*spd),
                        EnemyBullet(x + 10, y, proj, speed=spd, damage=3, vx=math.sin(aim_angle)*spd, vy=math.cos(aim_angle)*spd)]

        # ── Nautolan Fleet Projectiles ──────────────────────────────────
        if self.name == 'fighter':
            spd = 5.5
            return [EnemyBullet(x, y, projectiles['bullet'], speed=spd, vx=math.sin(aim_angle)*spd, vy=math.cos(aim_angle)*spd)]
        if self.name == 'bomber':
            lead_drift = max(-1.6, min(1.6, dx / 140))
            return [EnemyBullet(x, y, projectiles['bomb'], speed=3.6, damage=10, vx=lead_drift)]
        if self.name == 'torpedo':
            # Twin Homing Torpedo Salvo with EMP Shield-Disrupter Warheads
            spd = 4.8 * spd_mult
            return [
                EnemyBullet(x - 12, y, projectiles['rocket'], speed=spd, damage=12,
                            vx=-1.0, vy=spd, target=player, homing_turn=0.038,
                            bullet_type="shield_buster_torpedo", shooter=self),
                EnemyBullet(x + 12, y, projectiles['rocket'], speed=spd, damage=12,
                            vx=1.0, vy=spd, target=player, homing_turn=0.038,
                            bullet_type="shield_buster_torpedo", shooter=self)
            ]
        if self.name == 'support':
            spd = 4.2
            return [EnemyBullet(x, y, projectiles['ray'], speed=spd, damage=2, vx=math.sin(aim_angle)*spd, vy=math.cos(aim_angle)*spd)]
        if self.name == 'frigate':
            spd = 5.0
            return [EnemyBullet(x, y, projectiles['spinning'], speed=spd, damage=3,
                                vx=math.sin(aim_angle + off)*spd, vy=math.cos(aim_angle + off)*spd)
                    for off in (-0.22, 0.0, 0.22)]
        if self.name == 'battlecruiser':
            spd = 4.2
            # 5 waves centered around the player's position
            return [EnemyBullet(x, y, projectiles['wave'], speed=spd, damage=4,
                                vx=math.sin(aim_angle + off)*spd, vy=math.cos(aim_angle + off)*spd)
                    for off in (-0.32, -0.16, 0.0, 0.16, 0.32)]
        if self.name == 'dreadnought':
            # Subsystem check: if main battery destroyed, beam salvo is crippled!
            main_turret_dead = self.subsystems.get('main_turret', {}).get('destroyed', False)

            mode = (self.shot_count - 1) % 4
            if mode == 0:
                # Mode 0: Heavy Tachyon Beam Barrage (Coherent Rays)
                if main_turret_dead:
                    spd = 4.0 * spd_mult
                    return [EnemyBullet(x, y, projectiles['ray'], speed=spd, damage=2,
                                        vx=math.sin(aim_angle) * spd, vy=math.cos(aim_angle) * spd)]
                spd = 4.8 * spd_mult
                spreads = (-0.42, -0.28, -0.14, 0.0, 0.14, 0.28, 0.42)
                return [EnemyBullet(x, y, projectiles['ray'], speed=spd, damage=5,
                                    vx=math.sin(aim_angle + off) * spd, vy=math.cos(aim_angle + off) * spd)
                        for off in spreads]

            elif mode == 1:
                # Mode 1: Semi-Active Radar Homing (SARH) Missiles + Radar Lock Painter
                if player is not None:
                    self.radar_lock_until = now + 3000
                    self.radar_lock_target = player
                spd = 4.6 * spd_mult
                return [
                    EnemyBullet(x - 26, y, projectiles['rocket'], speed=spd, damage=12,
                                vx=-1.2, vy=spd, target=player, homing_turn=0.042,
                                bullet_type="sarh_missile", shooter=self),
                    EnemyBullet(x + 26, y, projectiles['rocket'], speed=spd, damage=12,
                                vx=1.2, vy=spd, target=player, homing_turn=0.042,
                                bullet_type="sarh_missile", shooter=self)
                ]

            elif mode == 2:
                # Mode 2: Geometric Flak Waves & Spinning Bullets (Corridor Weave)
                spd = 4.4 * spd_mult
                bullets = []
                for off in (-0.32, 0.0, 0.32):
                    bullets.append(EnemyBullet(x, y, projectiles['wave'], speed=spd, damage=4,
                                               vx=math.sin(aim_angle + off) * spd, vy=math.cos(aim_angle + off) * spd))
                for off in (-0.22, -0.07, 0.07, 0.22):
                    bullets.append(EnemyBullet(x, y, projectiles['spinning'], speed=spd * 1.08, damage=3,
                                               vx=math.sin(aim_angle + off) * spd * 1.08, vy=math.cos(aim_angle + off) * spd * 1.08))
                return bullets

            else:
                # Mode 3: Predictive Annihilator Bombs & Flanking Kinetic Spread
                pred_x = (player.rect.centerx + player.velocity_x * 16) if player else x
                base_lead = max(-2.8, min(2.8, (pred_x - x) / 85))
                spd = 5.2 * spd_mult
                return [
                    EnemyBullet(x, y, projectiles['bomb'], speed=3.8 * spd_mult, damage=14, vx=base_lead),
                    EnemyBullet(x - 22, y, projectiles['bullet'], speed=spd, damage=3, vx=base_lead - 1.1, vy=spd),
                    EnemyBullet(x + 22, y, projectiles['bullet'], speed=spd, damage=3, vx=base_lead + 1.1, vy=spd),
                    EnemyBullet(x, y, projectiles['rocket'], speed=spd * 0.9, damage=8, vx=math.sin(aim_angle) * spd * 0.9, vy=math.cos(aim_angle) * spd * 0.9)
                ]

        # ── Kla'ed Void Fleet Projectiles ──────────────────────────────
        if self.name == 'klaed_scout':
            spd = 5.4
            return [EnemyBullet(x, y, projectiles['klaed_bullet'], speed=spd, damage=2,
                                vx=math.sin(aim_angle)*spd, vy=math.cos(aim_angle)*spd)]
        if self.name == 'klaed_fighter':
            spd = 5.8
            # Twin parallel plasma burst aimed at the player
            vx, vy = math.sin(aim_angle)*spd, math.cos(aim_angle)*spd
            return [EnemyBullet(x - 9, y, projectiles['klaed_bullet'], speed=spd, damage=3, vx=vx, vy=vy),
                    EnemyBullet(x + 9, y, projectiles['klaed_bullet'], speed=spd, damage=3, vx=vx, vy=vy)]
        if self.name == 'klaed_torpedo':
            # Twin Void Homing Torpedo Salvo with EMP Shield-Disrupter Warheads
            spd = 5.2 * spd_mult
            return [
                EnemyBullet(x - 14, y, projectiles['klaed_torpedo'], speed=spd, damage=14,
                            vx=-1.2, vy=spd, target=player, homing_turn=0.036,
                            bullet_type="shield_buster_torpedo", shooter=self),
                EnemyBullet(x + 14, y, projectiles['klaed_torpedo'], speed=spd, damage=14,
                            vx=1.2, vy=spd, target=player, homing_turn=0.036,
                            bullet_type="shield_buster_torpedo", shooter=self)
            ]
        if self.name == 'klaed_bomber':
            # Dual heavy void bombs
            return [EnemyBullet(x - 12, y, projectiles['klaed_big_bullet'], speed=4.0, damage=11, vx=-0.8),
                    EnemyBullet(x + 12, y, projectiles['klaed_big_bullet'], speed=4.0, damage=11, vx=0.8)]
        if self.name == 'klaed_support':
            spd = 4.4
            vx, vy = math.sin(aim_angle)*spd, math.cos(aim_angle)*spd
            return [EnemyBullet(x - 8, y, projectiles['klaed_ray'], speed=spd, damage=2, vx=vx, vy=vy),
                    EnemyBullet(x + 8, y, projectiles['klaed_ray'], speed=spd, damage=2, vx=vx, vy=vy)]
        if self.name == 'klaed_frigate':
            spd = 5.2
            # 4-shot aimed void ray spread
            return [EnemyBullet(x, y, projectiles['klaed_ray'], speed=spd, damage=4,
                                vx=math.sin(aim_angle + off)*spd, vy=math.cos(aim_angle + off)*spd)
                    for off in (-0.26, -0.09, 0.09, 0.26)]
        if self.name == 'klaed_battlecruiser':
            spd = 4.6
            # 4 heavy void waves sweeping toward the player
            return [EnemyBullet(x, y, projectiles['klaed_wave'], speed=spd, damage=5,
                                vx=math.sin(aim_angle + off)*spd, vy=math.cos(aim_angle + off)*spd)
                    for off in (-0.28, -0.09, 0.09, 0.28)]
        if self.name == 'klaed_dreadnought':
            # The Void Overlord Flagship: 4-mode cyclic arsenal
            main_turret_dead = self.subsystems.get('main_turret', {}).get('destroyed', False)

            mode = (self.shot_count - 1) % 4
            if mode == 0:
                # Mode 0: Void Lance Sweep (8-ray Coherent Arc)
                if main_turret_dead:
                    spd = 4.0 * spd_mult
                    return [EnemyBullet(x, y, projectiles['klaed_ray'], speed=spd, damage=2,
                                        vx=math.sin(aim_angle) * spd, vy=math.cos(aim_angle) * spd)]
                spd = 5.0 * spd_mult
                spreads = (-0.45, -0.32, -0.19, -0.06, 0.06, 0.19, 0.32, 0.45)
                return [EnemyBullet(x, y, projectiles['klaed_ray'], speed=spd, damage=5,
                                    vx=math.sin(aim_angle + off) * spd, vy=math.cos(aim_angle + off) * spd)
                        for off in spreads]

            elif mode == 1:
                # Mode 1: Void SARH Heavy Torpedoes & Center Void Bullet
                if player is not None:
                    self.radar_lock_until = now + 3200
                    self.radar_lock_target = player
                spd = 4.8 * spd_mult
                return [
                    EnemyBullet(x - 28, y, projectiles['klaed_torpedo'], speed=spd, damage=14,
                                vx=-1.4, vy=spd, target=player, homing_turn=0.038,
                                bullet_type="sarh_missile", shooter=self),
                    EnemyBullet(x, y, projectiles['klaed_big_bullet'], speed=4.2 * spd_mult, damage=11, vx=0.0),
                    EnemyBullet(x + 28, y, projectiles['klaed_torpedo'], speed=spd, damage=14,
                                vx=1.4, vy=spd, target=player, homing_turn=0.038,
                                bullet_type="sarh_missile", shooter=self)
                ]

            elif mode == 2:
                # Mode 2: Graviton Surge Waves (5 Heavy Void Waves)
                spd = 4.6 * spd_mult
                return [EnemyBullet(x, y, projectiles['klaed_wave'], speed=spd, damage=5,
                                    vx=math.sin(aim_angle + off) * spd, vy=math.cos(aim_angle + off) * spd)
                        for off in (-0.36, -0.18, 0.0, 0.18, 0.36)]

            else:
                # Mode 3: Void Annihilator Bombs & Kinetic Shrapnel
                pred_x = (player.rect.centerx + player.velocity_x * 16) if player else x
                lead = max(-3.0, min(3.0, (pred_x - x) / 78))
                spd = 5.2 * spd_mult
                return [
                    EnemyBullet(x - 20, y, projectiles['klaed_big_bullet'], speed=4.4 * spd_mult, damage=12, vx=lead - 0.7),
                    EnemyBullet(x + 20, y, projectiles['klaed_big_bullet'], speed=4.4 * spd_mult, damage=12, vx=lead + 0.7),
                    EnemyBullet(x - 34, y, projectiles['klaed_bullet'], speed=spd, damage=3, vx=lead - 1.4, vy=spd),
                    EnemyBullet(x + 34, y, projectiles['klaed_bullet'], speed=spd, damage=3, vx=lead + 1.4, vy=spd)
                ]

        # ── Nairan Cyber Fleet Projectiles ─────────────────────────────
        if self.name == 'nairan_scout':
            spd = 6.0 * spd_mult
            return [EnemyBullet(x, y, projectiles['nairan_bolt'], speed=spd, damage=2,
                                vx=math.sin(aim_angle)*spd, vy=math.cos(aim_angle)*spd)]
        if self.name == 'nairan_fighter':
            spd = 6.2 * spd_mult
            vx, vy = math.sin(aim_angle)*spd, math.cos(aim_angle)*spd
            return [EnemyBullet(x - 8, y, projectiles['nairan_bolt'], speed=spd, damage=3, vx=vx, vy=vy),
                    EnemyBullet(x + 8, y, projectiles['nairan_bolt'], speed=spd, damage=3, vx=vx, vy=vy)]
        if self.name == 'nairan_torpedo':
            # Twin Cyber Homing Torpedo Salvo with EMP Shield-Disrupter Warheads
            spd = 5.4 * spd_mult
            return [
                EnemyBullet(x - 14, y, projectiles['nairan_torpedo'], speed=spd, damage=13,
                            vx=-1.2, vy=spd, target=player, homing_turn=0.040,
                            bullet_type="shield_buster_torpedo", shooter=self),
                EnemyBullet(x + 14, y, projectiles['nairan_torpedo'], speed=spd, damage=13,
                            vx=1.2, vy=spd, target=player, homing_turn=0.040,
                            bullet_type="shield_buster_torpedo", shooter=self)
            ]
        if self.name == 'nairan_bomber':
            spd = 4.8 * spd_mult
            return [EnemyBullet(x - 14, y, projectiles['nairan_rocket'], speed=spd, damage=9, vx=-1.2),
                    EnemyBullet(x + 14, y, projectiles['nairan_rocket'], speed=spd, damage=9, vx=1.2)]
        if self.name == 'nairan_support':
            spd = 4.5 * spd_mult
            vx, vy = math.sin(aim_angle)*spd, math.cos(aim_angle)*spd
            return [EnemyBullet(x, y, projectiles['nairan_ray'], speed=spd, damage=2, vx=vx, vy=vy)]
        if self.name == 'nairan_frigate':
            spd = 5.2 * spd_mult
            return [EnemyBullet(x, y, projectiles['nairan_ray'], speed=spd, damage=4,
                                vx=math.sin(aim_angle + off)*spd, vy=math.cos(aim_angle + off)*spd)
                    for off in (-0.22, 0.0, 0.22)]
        if self.name == 'nairan_battlecruiser':
            spd = 5.0 * spd_mult
            return [EnemyBullet(x - 22, y, projectiles['nairan_ray'], speed=spd, damage=4,
                                vx=math.sin(aim_angle - 0.12)*spd, vy=math.cos(aim_angle - 0.12)*spd),
                    EnemyBullet(x + 22, y, projectiles['nairan_ray'], speed=spd, damage=4,
                                vx=math.sin(aim_angle + 0.12)*spd, vy=math.cos(aim_angle + 0.12)*spd),
                    EnemyBullet(x, y, projectiles['nairan_torpedo'], speed=spd * 1.1, damage=10,
                                vx=math.sin(aim_angle)*spd)]
        if self.name == 'nairan_dreadnought':
            # The Cyber Dreadnought Boss: 4-mode cyclic arsenal
            main_turret_dead = self.subsystems.get('main_turret', {}).get('destroyed', False)

            mode = (self.shot_count - 1) % 4
            if mode == 0:
                # Mode 0: Cybernetic Beam Fan (8 Precision Rays)
                if main_turret_dead:
                    spd = 4.2 * spd_mult
                    return [EnemyBullet(x, y, projectiles['nairan_ray'], speed=spd, damage=2,
                                        vx=math.sin(aim_angle) * spd, vy=math.cos(aim_angle) * spd)]
                spd = 5.2 * spd_mult
                spreads = (-0.42, -0.30, -0.18, -0.06, 0.06, 0.18, 0.30, 0.42)
                return [EnemyBullet(x, y, projectiles['nairan_ray'], speed=spd, damage=5,
                                    vx=math.sin(aim_angle + off) * spd, vy=math.cos(aim_angle + off) * spd)
                        for off in spreads]

            elif mode == 1:
                # Mode 1: Cybernetic SARH Missiles
                if player is not None:
                    self.radar_lock_until = now + 3000
                    self.radar_lock_target = player
                spd = 5.0 * spd_mult
                return [
                    EnemyBullet(x - 30, y, projectiles['nairan_rocket'], speed=spd, damage=11,
                                vx=-1.5, vy=spd, target=player, homing_turn=0.044,
                                bullet_type="sarh_missile", shooter=self),
                    EnemyBullet(x, y, projectiles['nairan_torpedo'], speed=5.4 * spd_mult, damage=12, vx=math.sin(aim_angle) * 5.4 * spd_mult, vy=math.cos(aim_angle) * 5.4 * spd_mult),
                    EnemyBullet(x + 30, y, projectiles['nairan_rocket'], speed=spd, damage=11,
                                vx=1.5, vy=spd, target=player, homing_turn=0.044,
                                bullet_type="sarh_missile", shooter=self)
                ]

            elif mode == 2:
                # Mode 2: Digital Pulse Flak Matrix (High Rate of Fire Grid)
                spd = 5.5 * spd_mult
                bullets = []
                for off in (-0.28, -0.10, 0.10, 0.28):
                    bullets.append(EnemyBullet(x, y, projectiles['nairan_bolt'], speed=spd, damage=3,
                                               vx=math.sin(aim_angle + off) * spd, vy=math.cos(aim_angle + off) * spd))
                for off in (-0.19, 0.0, 0.19):
                    bullets.append(EnemyBullet(x, y, projectiles['nairan_ray'], speed=spd * 0.92, damage=4,
                                               vx=math.sin(aim_angle + off) * spd * 0.92, vy=math.cos(aim_angle + off) * spd * 0.92))
                return bullets

            else:
                # Mode 3: Heavy Penetrator Torpedo Array (Quad Anticipation)
                pred_x = (player.rect.centerx + player.velocity_x * 16) if player else x
                lead = max(-3.0, min(3.0, (pred_x - x) / 78))
                spd = 5.6 * spd_mult
                return [
                    EnemyBullet(x - 28, y, projectiles['nairan_torpedo'], speed=spd, damage=12, vx=lead - 1.2),
                    EnemyBullet(x - 10, y, projectiles['nairan_rocket'], speed=spd * 0.9, damage=8, vx=-0.5),
                    EnemyBullet(x + 10, y, projectiles['nairan_rocket'], speed=spd * 0.9, damage=8, vx=0.5),
                    EnemyBullet(x + 28, y, projectiles['nairan_torpedo'], speed=spd, damage=12, vx=lead + 1.2)
                ]
        return []

    def draw(self, screen):
        now = pygame.time.get_ticks()

        # 0. Afterimages for Shadow Interceptor
        if getattr(self, 'afterimages', None):
            for ax, ay, a_alpha, a_surf in self.afterimages:
                ghost = a_surf.copy()
                ghost.set_alpha(max(0, min(255, a_alpha)))
                screen.blit(ghost, (round(ax), round(ay)))

        # Atmospheric entry flame for fast asteroids
        if self.name == 'asteroid' and (self.behavior == 'fast' or self.speed > 3.5) and getattr(self, 'flame_frames', None):
            flame_img = self.flame_frames[(now // 60) % len(self.flame_frames)]
            flame_scaled = pygame.transform.smoothscale(flame_img, (max(28, self.rect.width), int(self.rect.height * 0.95)))
            f_rect = flame_scaled.get_rect(midbottom=(self.rect.centerx, self.rect.top + 6))
            screen.blit(flame_scaled, f_rect)

        # 0a. Render Enemy Ship Sprite
        screen.blit(self.image, self.rect)

        # White Hit-Flash Silhouette (Strictly masked to ship pixels, no square leakage)
        flash_until = getattr(self, 'hit_flash_until', 0)
        if now < flash_until:
            try:
                flash_surf = getattr(self, '_flash_surf', None)
                flash_img_id = getattr(self, '_flash_img_id', None)
                if flash_surf is None or flash_img_id != id(self.image):
                    mask = pygame.mask.from_surface(self.image)
                    flash_surf = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
                    self._flash_surf = flash_surf
                    self._flash_img_id = id(self.image)
                rem = flash_until - now
                alpha = max(60, min(180, int(180 * (rem / 35.0))))
                flash_surf.set_alpha(alpha)
                screen.blit(flash_surf, self.rect)
            except Exception:
                pass

        # 0b. Damaged subsystem smoke trails
        if getattr(self, 'smoke_particles', None):
            for p in self.smoke_particles:
                s_alpha = max(0, min(255, p[4]))
                s_surf = pygame.Surface((6, 6), pygame.SRCALPHA)
                pygame.draw.circle(s_surf, (150, 150, 160, s_alpha), (3, 3), 3)
                screen.blit(s_surf, (round(p[0] - 3), round(p[1] - 3)))

        overlay = get_shared_overlay()
        overlay.fill((0, 0, 0, 0))
        overlay_used = False

        # 0b. Dreadnought / Capital Ship Holographic Telegraph Cones & Guide Lines
        if getattr(self, 'charging_salvo', False) and self.charge_progress > 0:
            alpha = int(140 * self.charge_progress)
            if 'nairan' in self.name:
                t_color = (255, 60, 90, alpha)
            elif 'klaed' in self.name:
                t_color = (210, 80, 255, alpha)
            elif 'dreadnought' in self.name:
                t_color = (60, 230, 255, alpha)
            else:
                t_color = (255, 190, 60, alpha)

            origin = (self.rect.centerx, self.rect.bottom)
            if 'dreadnought' in self.name:
                spreads = (-0.42, -0.28, -0.14, 0.0, 0.14, 0.28, 0.42)
            else:
                spreads = (-0.30, -0.15, 0.0, 0.15, 0.30)

            for off in spreads:
                end_x = origin[0] + math.sin(off) * 520
                end_y = origin[1] + math.cos(off) * 520
                pygame.draw.line(overlay, t_color, origin, (round(end_x), round(end_y)), 2)
                pygame.draw.circle(overlay, (t_color[0], t_color[1], t_color[2], min(255, alpha + 50)), (round(end_x), round(end_y)), 3)
            overlay_used = True

        # 0c. Dreadnought Semi-Active Radar Illumination Beam & Target Reticle
        if 'dreadnought' in self.name and now < getattr(self, 'radar_lock_until', 0) and getattr(self, 'radar_lock_target', None):
            target = self.radar_lock_target
            if getattr(target, 'hp', 0) > 0:
                t_pos = target.rect.center
                origin = (self.rect.centerx, self.rect.bottom)
                pulse = int(140 + 70 * math.sin(now / 90.0))

                if 'nairan' in self.name:
                    lock_col = (255, 60, 90, pulse)
                elif 'klaed' in self.name:
                    lock_col = (210, 80, 255, pulse)
                else:
                    lock_col = (0, 240, 255, pulse)

                pygame.draw.line(overlay, lock_col, origin, t_pos, 1)

                reticle_r = 18 + int(3 * math.sin(now / 100.0))
                tx, ty = t_pos
                b_len = 6
                pygame.draw.lines(overlay, lock_col, False, [(tx - reticle_r, ty - reticle_r + b_len), (tx - reticle_r, ty - reticle_r), (tx - reticle_r + b_len, ty - reticle_r)], 2)
                pygame.draw.lines(overlay, lock_col, False, [(tx + reticle_r - b_len, ty - reticle_r), (tx + reticle_r, ty - reticle_r), (tx + reticle_r, ty - reticle_r + b_len)], 2)
                pygame.draw.lines(overlay, lock_col, False, [(tx - reticle_r, ty + reticle_r - b_len), (tx - reticle_r, ty + reticle_r), (tx - reticle_r + b_len, ty + reticle_r)], 2)
                pygame.draw.lines(overlay, lock_col, False, [(tx + reticle_r - b_len, ty + reticle_r), (tx + reticle_r, ty + reticle_r), (tx + reticle_r, ty + reticle_r - b_len)], 2)
                pygame.draw.circle(overlay, lock_col, t_pos, 2)
                overlay_used = True

        # 1. Spotter Laser Targeting Line
        if self.spotter_until > now and self.spotter_target:
            progress = (self.spotter_until - now) / 1600
            alpha = int(210 * (1.0 - progress))
            pygame.draw.line(overlay, (255, 60, 60, alpha), self.rect.center, self.spotter_target, 2)
            pygame.draw.circle(overlay, (255, 80, 80, alpha), self.spotter_target, 8, 1)
            overlay_used = True

        # 1b. Shadow Interceptor Aim Lock Line & Crosshair
        if getattr(self, 'is_shadow', False) and self.aim_lock_pos and now < self.aim_lock_until:
            rem = self.aim_lock_until - now
            l_alpha = int(220 * (1.0 - rem / 400.0))
            pygame.draw.line(overlay, (255, 40, 180, l_alpha), self.rect.center, self.aim_lock_pos, 1)
            pygame.draw.circle(overlay, (255, 60, 220, l_alpha), (round(self.aim_lock_pos[0]), round(self.aim_lock_pos[1])), 9, 1)
            pygame.draw.circle(overlay, (255, 60, 220, l_alpha), (round(self.aim_lock_pos[0]), round(self.aim_lock_pos[1])), 3)
            overlay_used = True

        # 1c. Support Ship Healing Beams (pulsing neon-green laser tether, 400ms)
        if getattr(self, 'heal_beams', None):
            self.heal_beams = [b for b in self.heal_beams if now < b['expire']]
            for b in self.heal_beams:
                t_pos = b['target'].rect.center if (hasattr(b.get('target'), 'rect') and b['target'].hp > 0) else b.get('target_pos', self.rect.center)
                pygame.draw.line(overlay, (60, 255, 120, 100), self.rect.center, t_pos, 6)
                pygame.draw.line(overlay, (180, 255, 210, 240), self.rect.center, t_pos, 3)
                pygame.draw.circle(overlay, (80, 255, 120, 200), t_pos, 14, 2)
                overlay_used = True

        # 1d. Support Ship Boss Defense Conduit (Invulnerability Link)
        if getattr(self, 'shield_conduit_target', None) and getattr(self.shield_conduit_target, 'hp', 0) > 0:
            target_boss = self.shield_conduit_target
            b_center = target_boss.rect.center
            pulse_off = (now // 40) % 8
            pygame.draw.line(overlay, (0, 240, 255, 190), self.rect.center, b_center, 4)
            pygame.draw.line(overlay, (255, 235, 60, 210), self.rect.center, b_center, 2)
            pygame.draw.circle(overlay, (0, 240, 255, 220), b_center, 18 + pulse_off, 2)

            # Energy contact flare where conduit enters the shield perimeter
            s_radius = max(target_boss.rect.width, target_boss.rect.height) // 2 + 14
            cdx = self.rect.centerx - b_center[0]
            cdy = self.rect.centery - b_center[1]
            cdist = math.hypot(cdx, cdy)
            if cdist > s_radius:
                ix = int(b_center[0] + (cdx / cdist) * s_radius)
                iy = int(b_center[1] + (cdy / cdist) * s_radius)
                pygame.draw.circle(overlay, (0, 240, 255, 230), (ix, iy), 6 + pulse_off % 4, 2)
                pygame.draw.circle(overlay, (255, 255, 255, 240), (ix, iy), 3)
            overlay_used = True

        # 1e. Invulnerable Tether Barrier Bubble & Prompt (on protected Boss)
        if getattr(self, 'is_invulnerable_tethered', False):
            s_radius = max(self.rect.width, self.rect.height) // 2 + 14
            pulse = int(150 + 60 * math.sin(now / 140.0))
            pygame.draw.circle(overlay, (0, 240, 255, pulse), self.rect.center, s_radius, 3)
            pygame.draw.circle(overlay, (255, 235, 60, pulse // 2), self.rect.center, s_radius - 3, 2)
            overlay_used = True

        # 1f. Torpedo Ship Target-Locking Laser (1.2s prior to firing)
        if getattr(self, 'torpedo_lock_active', False) and getattr(self, 'torpedo_lock_pos', None):
            pygame.draw.line(overlay, (255, 50, 50, 160), self.rect.center, self.torpedo_lock_pos, 1)
            reticle_r = max(6, int(26 * (1.0 - self.torpedo_lock_progress * 0.70)))
            pygame.draw.circle(overlay, (255, 60, 60, 220), self.torpedo_lock_pos, reticle_r, 2)
            pygame.draw.circle(overlay, (255, 255, 255, 240), self.torpedo_lock_pos, 2)
            pygame.draw.line(overlay, (255, 60, 60, 200), (self.torpedo_lock_pos[0] - reticle_r - 4, self.torpedo_lock_pos[1]), (self.torpedo_lock_pos[0] + reticle_r + 4, self.torpedo_lock_pos[1]), 1)
            pygame.draw.line(overlay, (255, 60, 60, 200), (self.torpedo_lock_pos[0], self.torpedo_lock_pos[1] - reticle_r - 4), (self.torpedo_lock_pos[0], self.torpedo_lock_pos[1] + reticle_r + 4), 1)
            overlay_used = True

        # 1g. Asteroid Lane Inbound Warning Indicator (top of screen for 800ms)
        if self.name == 'asteroid' and now < getattr(self, 'inbound_warning_until', 0):
            if (now // 100) % 2 == 0:
                lane_x = getattr(self, 'spawn_lane_x', self.rect.centerx)
                pts = [(lane_x - 12, 28), (lane_x + 12, 28), (lane_x, 8)]
                pygame.draw.polygon(screen, (255, 215, 0), pts)
                pygame.draw.polygon(screen, (20, 20, 20), pts, 1)
                pygame.draw.line(screen, (20, 20, 20), (lane_x, 14), (lane_x, 21), 2)
                pygame.draw.circle(screen, (20, 20, 20), (lane_x, 24), 1)
                pygame.draw.line(overlay, (255, 215, 0, 110), (lane_x, 30), (lane_x, 150), 2)
                overlay_used = True

        # 2b. Pulsing Energy Shield Barrier (Shadow Interceptor)
        if getattr(self, 'shield_hp', 0) > 0:
            s_radius = max(self.rect.width, self.rect.height) // 2 + 8
            pulse = int(140 + 60 * math.sin(now / 150.0))
            pygame.draw.circle(overlay, (160, 40, 255, pulse), self.rect.center, s_radius, 2)
            pygame.draw.circle(overlay, (0, 240, 255, pulse // 2), self.rect.center, s_radius - 3, 1)
            overlay_used = True

        if overlay_used:
            screen.blit(overlay, (0, 0))

        # Floating prompt for invulnerable tether
        if getattr(self, 'is_invulnerable_tethered', False) and now < getattr(self, 'tether_prompt_until', 0):
            font = pygame.font.SysFont("Arial", 12, bold=True)
            txt = font.render("SHIELD CONDUIT ACTIVE // DESTROY SUPPORT SHIP", True, (255, 230, 60))
            txt_rect = txt.get_rect(center=(self.rect.centerx, self.rect.top - 16))
            bg_rect = txt_rect.inflate(8, 4)
            pygame.draw.rect(screen, (30, 20, 10), bg_rect)
            pygame.draw.rect(screen, (255, 215, 60), bg_rect, 1)
            screen.blit(txt, txt_rect)

        # 3. Squad Leader Tactical Chevron
        if self.is_leader:
            tip_x = self.rect.centerx
            tip_y = self.rect.top - 8
            pts = [(tip_x - 6, tip_y + 6), (tip_x, tip_y), (tip_x + 6, tip_y + 6), (tip_x, tip_y + 3)]
            pygame.draw.polygon(screen, (255, 215, 60), pts)
            pygame.draw.polygon(screen, (0, 240, 255), pts, 1)

        # 4. Disarray Warning Indicator
        if now < self.disarray_until:
            w_surf = pygame.Surface((16, 16), pygame.SRCALPHA)
            pygame.draw.circle(w_surf, (255, 180, 40, 230), (8, 8), 7)
            pygame.draw.circle(w_surf, (20, 20, 30), (8, 5), 2)
            pygame.draw.line(w_surf, (20, 20, 30), (8, 8), (8, 12), 2)
            screen.blit(w_surf, (self.rect.centerx - 8, self.rect.top - 18))

        # 5. Subsystem Destruction Indicators for Capital Ships
        if self.subsystems and self.max_hp >= 40:
            for sub_id, sub in self.subsystems.items():
                if sub['destroyed']:
                    wx = self.rect.x + sub['rel_rect'].centerx
                    wy = self.rect.y + sub['rel_rect'].centery
                    pygame.draw.line(screen, (255, 60, 60), (wx - 4, wy - 4), (wx + 4, wy + 4), 2)
                    pygame.draw.line(screen, (255, 60, 60), (wx + 4, wy - 4), (wx - 4, wy + 4), 2)

        # 6. Health bar
        if getattr(self, 'is_shadow', False):
            # Dual Shield + Hull health bar for Shadow Interceptor
            bar_width = min(80, self.rect.width + 20)
            bar_y = self.rect.bottom + 4
            if self.max_shield_hp > 0 and self.shield_hp > 0:
                s_bar = pygame.Rect(self.rect.centerx - bar_width // 2, bar_y, bar_width, 3)
                pygame.draw.rect(screen, (20, 40, 60), s_bar)
                s_fill = pygame.Rect(s_bar.x, s_bar.y, round(s_bar.width * max(0, self.shield_hp) / self.max_shield_hp), 3)
                pygame.draw.rect(screen, (0, 220, 255), s_fill)
                bar_y += 4
            h_bar = pygame.Rect(self.rect.centerx - bar_width // 2, bar_y, bar_width, 4)
            pygame.draw.rect(screen, (50, 15, 25), h_bar)
            h_fill = pygame.Rect(h_bar.x, h_bar.y, round(h_bar.width * max(0, self.hp) / self.max_hp), 4)
            pygame.draw.rect(screen, (255, 60, 160), h_fill)
            pygame.draw.rect(screen, (255, 180, 240), h_bar, 1)
        elif self.max_hp >= 200:
            # Prominent boss health bar for Dreadnoughts
            bar_width = min(120, self.rect.width + 20)
            bar = pygame.Rect(self.rect.centerx - bar_width // 2, self.rect.bottom + 5, bar_width, 6)
            pygame.draw.rect(screen, (50, 15, 25), bar)
            filled = pygame.Rect(bar.x, bar.y, round(bar.width * max(0, self.hp) / self.max_hp), bar.height)
            pygame.draw.rect(screen, (255, 60, 80), filled)
            pygame.draw.rect(screen, (255, 200, 200), bar, 1)
        elif self.max_hp >= 7:
            bar_width = min(54, max(28, self.rect.width))
            bar = pygame.Rect(self.rect.centerx - bar_width // 2, self.rect.bottom + 3, bar_width, 4)
            pygame.draw.rect(screen, (45, 25, 35), bar)
            filled = pygame.Rect(bar.x, bar.y, round(bar.width * max(0, self.hp) / self.max_hp), bar.height)
            pygame.draw.rect(screen, (235, 105, 120), filled)

class Explosion:
    def __init__(self, center_x, center_y, frames):
        self.frames = frames
        self.center = (center_x, center_y)
        self.current_frame = 0
        self.frame_duration = 40
        self.last_frame_time = pygame.time.get_ticks()
        self.is_finished = False
        self.image = self.frames[self.current_frame]
        self.rect = self.image.get_rect(center=self.center)

    def update(self):
        if self.is_finished: return
        now = pygame.time.get_ticks()
        if now - self.last_frame_time >= self.frame_duration:
            self.last_frame_time = now
            self.current_frame += 1
            if self.current_frame >= len(self.frames): self.is_finished = True
            else:
                self.image = self.frames[self.current_frame]
                self.rect = self.image.get_rect(center=self.center)
    def draw(self, screen):
        if not self.is_finished: screen.blit(self.image, self.rect)

class CreditOrb:
    """A glowing credit pickup dropped by heavy enemies on death."""
    RADIUS = 8

    def __init__(self, x, y, value):
        self.value    = value
        self.x        = float(x)
        self.y        = float(y)
        self.vy       = 1.4
        self.rect     = pygame.Rect(
            round(self.x) - self.RADIUS, round(self.y) - self.RADIUS,
            self.RADIUS * 2, self.RADIUS * 2,
        )
        self.created_at = pygame.time.get_ticks()
        self.lifetime   = 7000   # ms before fade-out finishes

    @property
    def age(self):
        return pygame.time.get_ticks() - self.created_at

    @property
    def is_expired(self):
        return self.age > self.lifetime or self.y > SCREEN_HEIGHT + 24

    def update(self):
        self.y      += self.vy
        cx           = round(self.x)
        cy           = round(self.y)
        self.rect.topleft = (cx - self.RADIUS, cy - self.RADIUS)

    def draw(self, screen):
        age = self.age
        # Alpha fade during the last 1.5 s of life
        alpha = 255
        fade_start = self.lifetime - 1500
        if age > fade_start:
            alpha = max(0, int(255 * (1.0 - (age - fade_start) / 1500)))

        pulse  = 0.8 + 0.2 * math.sin(age / 130)
        r      = max(4, round(self.RADIUS * pulse))
        cx, cy = round(self.x), round(self.y)

        # Draw on a temporary SRCALPHA surface so we can fade cleanly
        surf = pygame.Surface((r * 2 + 6, r * 2 + 6), pygame.SRCALPHA)
        cx_s, cy_s = r + 3, r + 3
        pygame.draw.circle(surf, (200, 150,  30, alpha), (cx_s, cy_s), r + 2)
        pygame.draw.circle(surf, (255, 220,  80, alpha), (cx_s, cy_s), r)
        pygame.draw.circle(surf, (255, 255, 160, alpha), (cx_s, cy_s), max(2, r - 3))
        screen.blit(surf, (cx - cx_s, cy - cy_s))

class OverclockPickup(pygame.sprite.Sprite):
    """In-run module overclock drop (Weapon Overdrive, Engine Overdrive, Shield Surge)."""
    def __init__(self, x, y, category, module_id, frames):
        super().__init__()
        self.category = category  # 'weapon', 'engine', 'shield'
        self.module_id = module_id
        self.frames = frames if frames else [pygame.Surface((32, 32))]
        self.current_frame = 0
        self.image = self.frames[0]
        self.rect = self.image.get_rect(center=(round(x), round(y)))
        self.x = float(self.rect.centerx)
        self.y = float(self.rect.centery)
        self.base_x = self.x
        self.speed = 1.2
        self.born_time = pygame.time.get_ticks()
        self.is_expired = False
        self.color_aura = (
            (255, 140, 40) if category == 'weapon' else
            ((0, 230, 255) if category == 'engine' else (100, 255, 140))
        )
        self.label = f"OVERCLOCK // {module_id.replace('_', ' ').upper()}"

    def update(self):
        now = pygame.time.get_ticks()
        elapsed = now - self.born_time
        # Drifts down at 1.2 speed with soft floating sine-wave bobbing
        self.y += self.speed
        self.x = self.base_x + math.sin(elapsed / 260.0) * 14.0
        self.rect.center = (round(self.x), round(self.y))

        if self.frames:
            self.current_frame = (elapsed // 70) % len(self.frames)
            self.image = self.frames[self.current_frame]

        if self.rect.top > SCREEN_HEIGHT + 24:
            self.is_expired = True

    def draw(self, screen):
        now = pygame.time.get_ticks()
        pulse = int(140 + 60 * math.sin(now / 150.0))
        glow_surf = pygame.Surface((50, 50), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*self.color_aura, pulse // 3), (25, 25), 22)
        pygame.draw.circle(glow_surf, (*self.color_aura, pulse), (25, 25), 18, 1)
        screen.blit(glow_surf, glow_surf.get_rect(center=self.rect.center))
        screen.blit(self.image, self.rect)


class FloatingText:
    """Floating tactical feedback text that drifts upwards and fades cleanly."""
    def __init__(self, x, y, text, color=(255, 230, 80), duration_ms=750, vy=-1.3):
        self.x = float(x)
        self.y = float(y)
        self.text = text
        self.color = color
        self.duration_ms = duration_ms
        self.born = pygame.time.get_ticks()
        self.vy = vy
        self.is_expired = False

    def update(self):
        now = pygame.time.get_ticks()
        elapsed = now - self.born
        if elapsed >= self.duration_ms:
            self.is_expired = True
            return
        self.y += self.vy

    def draw(self, screen, font, offset=(0, 0), scale=1.0):
        now = pygame.time.get_ticks()
        elapsed = now - self.born
        if elapsed >= self.duration_ms:
            return
        alpha = max(0, min(255, int(255 * (1.0 - elapsed / self.duration_ms))))
        surf = font.render(self.text, True, self.color)
        surf.set_alpha(alpha)
        screen.blit(surf, surf.get_rect(center=(round(self.x * scale + offset[0]), round(self.y * scale + offset[1]))))


class SparkParticle:
    """High-velocity kinetic impact spark with drag and tapering trail."""
    def __init__(self, x, y, color=(255, 220, 100), duration=None, life=None):
        self.x = float(x)
        self.y = float(y)
        angle = random.uniform(0, math.tau)
        speed = random.uniform(2.5, 6.0)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.color = color
        if life is not None:
            self.life = int(life)
        elif duration is not None:
            self.life = max(6, int(duration // 20))
        else:
            self.life = random.randint(8, 16)
        self.max_life = self.life

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.92
        self.vy *= 0.92
        self.life -= 1

    def draw(self, screen):
        if self.life > 0:
            length = max(2, int(4 * (self.life / self.max_life)))
            end_x = self.x - self.vx * 0.5
            end_y = self.y - self.vy * 0.5
            pygame.draw.line(screen, self.color, (round(self.x), round(self.y)), (round(end_x), round(end_y)), length)



