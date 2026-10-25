import pygame
import random
import math

class ParallaxBackground:
    def __init__(self, bg_void, bg_stars, bg_planet=None, bg_black_hole=None, screen_size=(800, 600)):
        self.bg_void = bg_void
        self.bg_stars = bg_stars
        self.bg_planet = bg_planet or []
        self.bg_black_hole = bg_black_hole or []
        self.width = screen_size[0]
        self.height = screen_size[1]
        self.void_y1 = 0.0
        self.void_y2 = -float(self.height)
        self.stars_y1 = 0.0
        self.stars_y2 = -float(self.height)
        self.void_speed = 0.25
        self.stars_speed = 0.65

        # Layer 3: Celestial Landmark drifting at 0.15 speed
        self.landmark = None
        self.landmark_speed = 0.15
        self.last_landmark_spawn = -150000
        self.landmark_interval = 180000  # 180s

        # Layer 4: Foreground high-speed stars (speed 1.2)
        self.fg_stars_speed = 1.2
        self.fg_stars = [
            [random.uniform(0, self.width), random.uniform(0, self.height), random.uniform(1.1, 1.4), random.randint(190, 255)]
            for _ in range(50)
        ]

    def trigger_landmark(self, fleet_phase=0, force=False):
        now = pygame.time.get_ticks()
        if not force and self.landmark is not None:
            return
        if not force and (now - self.last_landmark_spawn < self.landmark_interval):
            return

        self.last_landmark_spawn = now
        default_x = self.width * 0.65
        if fleet_phase == 0 and self.bg_planet:
            self.landmark = {
                'type': 'planet',
                'frames': self.bg_planet,
                'x': default_x,
                'y': -170.0,
                'anim_speed': 90
            }
        elif fleet_phase >= 1 and self.bg_black_hole:
            self.landmark = {
                'type': 'black_hole',
                'frames': self.bg_black_hole,
                'x': default_x,
                'y': -240.0,
                'anim_speed': 110,
                'angle': 0.0
            }
        elif self.bg_planet:
            self.landmark = {
                'type': 'planet',
                'frames': self.bg_planet,
                'x': default_x,
                'y': -170.0,
                'anim_speed': 90
            }

    def update(self, fleet_phase=0):
        # Layer 1: Dark void base scrolling at speed 0.25
        self.void_y1 += self.void_speed
        self.void_y2 += self.void_speed
        if self.void_y1 >= self.height: self.void_y1 = -self.height
        if self.void_y2 >= self.height: self.void_y2 = -self.height

        # Layer 2: Subtle background stars scrolling at speed 0.65
        self.stars_y1 += self.stars_speed
        self.stars_y2 += self.stars_speed
        if self.stars_y1 >= self.height: self.stars_y1 = -self.height
        if self.stars_y2 >= self.height: self.stars_y2 = -self.height

        # Layer 3: Celestial Landmark drifting downwards at speed 0.15
        now = pygame.time.get_ticks()
        if self.landmark is None:
            self.trigger_landmark(fleet_phase)
        else:
            self.landmark['y'] += self.landmark_speed
            if self.landmark.get('type') == 'black_hole':
                self.landmark['angle'] = (self.landmark.get('angle', 0.0) + 0.15) % 360.0
            if self.landmark['y'] > self.height + 260:
                self.landmark = None
                self.last_landmark_spawn = now

        # Layer 4: Foreground high-speed stars scrolling at speed 1.2
        for s in self.fg_stars:
            s[1] += s[2] * (self.fg_stars_speed / 1.2)
            if s[1] >= self.height:
                s[1] = 0
                s[0] = random.uniform(0, self.width)

    def draw(self, screen):
        # Layer 1: Dark void base
        screen.blit(self.bg_void, (0, round(self.void_y1)))
        screen.blit(self.bg_void, (0, round(self.void_y2)))

        # Layer 2: Subtle background stars
        screen.blit(self.bg_stars, (0, round(self.stars_y1)))
        screen.blit(self.bg_stars, (0, round(self.stars_y2)))

        # Layer 3: Celestial Landmark
        if self.landmark and self.landmark.get('frames'):
            now = pygame.time.get_ticks()
            frames = self.landmark['frames']
            frame_idx = (now // self.landmark.get('anim_speed', 100)) % len(frames)
            frame_img = frames[frame_idx]
            if self.landmark.get('type') == 'black_hole' and self.landmark.get('angle', 0.0) != 0.0:
                frame_img = pygame.transform.rotate(frame_img, self.landmark['angle'])
            r = frame_img.get_rect(center=(round(self.landmark['x']), round(self.landmark['y'])))
            screen.blit(frame_img, r)

        # Layer 4: Foreground high-speed stars
        for s in self.fg_stars:
            c = s[3]
            sx, sy = round(s[0]), round(s[1])
            pygame.draw.line(screen, (c, c, c), (sx, sy), (sx, sy + 2), 1)
