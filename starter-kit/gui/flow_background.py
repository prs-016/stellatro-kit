import pygame
import random
import math
import numpy as np

class FlowBackground:
    def __init__(self, width, height, resolution=4):
        self.width = width
        self.height = height
        self.resolution = resolution 
        self.res_w = width // resolution
        self.res_h = height // resolution
        self.time = 0.0
        
        # Precompute coordinate grids
        x = np.linspace(0, width, self.res_w)
        y = np.linspace(0, height, self.res_h)
        self.X, self.Y = np.meshgrid(x, y)
        
        # Metaballs: slow, organic movement
        self.balls = []
        for _ in range(8):
            self.balls.append({
                'pos': [random.uniform(0, width), random.uniform(0, height)],
                'vel': [random.uniform(-4, 4), random.uniform(-10, -20)], 
                'radius': random.uniform(70, 120),
                'phase': random.uniform(0, math.pi * 2)
            })
        
        # Bisque base with complementary deep slate-blue blobs
        self.color_base = pygame.Color("#FFE4C4")      # Bisque
        self.color_blob = pygame.Color("#3A5068")      # Deep slate-blue (complements warm bisque)
        self.color_highlight = pygame.Color("#263545") # Darker slate for inner blob sheen
        
        self.field_surface = pygame.Surface((self.res_w, self.res_h))
        self.display_surface = pygame.Surface((width, height))
        
    def update(self, dt):
        self.time += dt
        for ball in self.balls:
            ball['pos'][0] += ball['vel'][0] * dt
            ball['pos'][1] += ball['vel'][1] * dt
            
            if ball['pos'][0] < -100 or ball['pos'][0] > self.width + 100:
                ball['vel'][0] *= -1
            
            if ball['pos'][1] < -150: # Reached top
                ball['vel'][1] = abs(ball['vel'][1]) * 0.8
            elif ball['pos'][1] > self.height + 150: # Reached bottom
                ball['vel'][1] = -abs(ball['vel'][1]) * 1.2
            
            ball['vel'][0] += math.sin(self.time * 0.4 + ball['phase']) * 0.08
                
    def draw(self, screen):
        # 1. High Coordinate Distortion
        t = self.time * 0.25
        
        dx = np.sin(self.Y * 0.015 + t) * 60.0
        dx += np.sin(self.Y * 0.04 + t * 1.3) * 30.0
        
        dy = np.cos(self.X * 0.018 + t * 0.8) * 60.0
        dy += np.cos(self.X * 0.045 + t * 1.1) * 25.0
        
        distorted_X = self.X + dx
        distorted_Y = self.Y + dy
        
        # 2. Compute the Metaball Field
        field = np.zeros((self.res_h, self.res_w), dtype=np.float32)
        
        for ball in self.balls:
            bx = ball['pos'][0]
            by = ball['pos'][1]
            d2 = (distorted_X - bx)**2 + (distorted_Y - by)**2
            
            r2 = ball['radius']**2
            influence = r2 / (d2 + 80.0)
            field += influence ** 2

        # 3. Threshold and Sharpening
        field = np.maximum(0, (field - 0.12) * 2.0)
        mask = np.clip(field, 0, 2)

        # High power = very sharp 0->1 transition, crisp blob edges
        sharpened_mask = np.where(mask < 1.0, np.power(mask, 10.0), mask)
        
        # Vectorized color interpolation
        rgb = np.zeros((self.res_h, self.res_w, 3), dtype=np.uint8)
        
        r = np.where(sharpened_mask < 1.0, 
                     self.color_base.r + (self.color_blob.r - self.color_base.r) * sharpened_mask,
                     self.color_blob.r + (self.color_highlight.r - self.color_blob.r) * (sharpened_mask - 1.0))
        g = np.where(sharpened_mask < 1.0, 
                     self.color_base.g + (self.color_blob.g - self.color_base.g) * sharpened_mask,
                     self.color_blob.g + (self.color_highlight.g - self.color_blob.g) * (sharpened_mask - 1.0))
        b = np.where(sharpened_mask < 1.0, 
                     self.color_base.b + (self.color_blob.b - self.color_base.b) * sharpened_mask,
                     self.color_blob.b + (self.color_highlight.b - self.color_blob.b) * (sharpened_mask - 1.0))

        rgb[..., 0] = r.astype(np.uint8)
        rgb[..., 1] = g.astype(np.uint8)
        rgb[..., 2] = b.astype(np.uint8)
        
        # 4. Final Render
        pygame.surfarray.blit_array(self.field_surface, rgb.swapaxes(0, 1))
        pygame.transform.smoothscale(self.field_surface, (self.width, self.height), self.display_surface)
        
        screen.blit(self.display_surface, (0, 0))
