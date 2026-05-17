import pygame
import random
import math
import os
from utils import get_assets_path


class WindParticle:
    def __init__(self, images, width, height, randomize_x=False):
        self.images = images
        self.width = width
        self.height = height

        self.image_index = random.randint(0, len(images) - 1)
        self.scale = random.uniform(1.00, 1.50)
        self.alpha = random.randint(55, 150)
        self.speed_x = random.uniform(75, 130)  # px/sec, left to right
        self.drift_amplitude = random.uniform(12, 45)  # vertical sine drift
        self.phase = random.uniform(0, math.pi * 2)
        self.freq = random.uniform(0.35, 1.1)
        self.rotation = random.uniform(0, 360)
        self.rotation_speed = random.uniform(-25, 25)  # deg/sec

        if randomize_x:
            self.x = random.uniform(0, width)
        else:
            self.x = random.uniform(-220, -10)

        self.base_y = random.uniform(0, height)
        self.y = self.base_y

        self._build_surface()

    def _build_surface(self):
        src = self.images[self.image_index]
        w = max(1, int(src.get_width() * self.scale))
        h = max(1, int(src.get_height() * self.scale))
        self.surface = pygame.transform.smoothscale(src, (w, h))

    def update(self, dt, time):
        self.x += self.speed_x * dt
        self.y = self.base_y + math.sin(time * self.freq + self.phase) * self.drift_amplitude
        self.rotation += self.rotation_speed * dt

        if self.x > self.width + 60:
            self._respawn()

    def _respawn(self):
        self.x = random.uniform(-220, -10)
        self.base_y = random.uniform(0, self.height)
        self.y = self.base_y
        self.image_index = random.randint(0, len(self.images) - 1)
        self.scale = random.uniform(0.25, 0.85)
        self.alpha = random.randint(35, 110)
        self.speed_x = random.uniform(45, 130)
        self.drift_amplitude = random.uniform(12, 45)
        self.phase = random.uniform(0, math.pi * 2)
        self.freq = random.uniform(0.35, 1.1)
        self._build_surface()

    def draw(self, screen):
        rotated = pygame.transform.rotate(self.surface, self.rotation)
        rotated.set_alpha(self.alpha)
        rx = int(self.x - rotated.get_width() / 2)
        ry = int(self.y - rotated.get_height() / 2)
        screen.blit(rotated, (rx, ry))


class WindEffect:
    def __init__(self, width, height, count=28):
        self.width = width
        self.height = height
        self.time = 0.0

        

        sprite_files = [
            "stellatro-bg/stellatro-bg-club.png",
            "stellatro-bg/stellatro-bg-diamond.png",
            "stellatro-bg/stellatro-bg-heart.png",
            "stellatro-bg/stellatro-bg-spade.png",
        ]

        self.images = []
        for fname in sprite_files:
            self.images.append(pygame.image.load(get_assets_path(fname)).convert_alpha())

        # Scatter initial particles across the full screen so it's populated immediately
        self.particles = [
            WindParticle(self.images, width, height, randomize_x=True)
            for _ in range(count)
        ]

    def update(self, dt):
        self.time += dt
        for p in self.particles:
            p.update(dt, self.time)

    def draw(self, screen):
        for p in self.particles:
            p.draw(screen)
