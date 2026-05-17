from text import TextBox
import pygame
from utils import get_assets_path

class Tooltip(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.position = pygame.math.Vector2(0,0)
        self.bg_container = pygame.image.load(get_assets_path("UI/Tooltip.png")).convert_alpha()
        self.bg_container = pygame.transform.smoothscale_by(self.bg_container,0.25)

        self.image = pygame.Surface((self.bg_container.get_width(), self.bg_container.get_height()), pygame.SRCALPHA)
        self.rect = self.image.get_rect()

        self.title_rect = pygame.Rect(11.38, 0, 113, 30)
        self.title_box = TextBox(
            self.title_rect,
            "",
            font_size=16,
            text_color=(255, 255, 255),
            font_url=get_assets_path("Jersey_10/Jersey10-Regular.ttf"),
            align="center",

        )

        self.desc_rect = pygame.Rect(11, 38, 113, 84)
        self.description_box = TextBox(
            self.desc_rect,
            "",
            font_size=16,
            text_color=(255, 255, 255),
            font_url=get_assets_path("Jersey_10/Jersey10-Regular.ttf"),
            align="center",
        )

        self._font = pygame.font.Font(get_assets_path("Jersey_10/Jersey10-Regular.ttf"), 16)
        self._current_desc = ""
        self._full_desc_surface = None
        self._scroll_offset = 0.0
        self._hover_time = 0.0
        self._scroll_delay = 0.8   # seconds before scrolling starts
        self._scroll_speed = 30.0  # pixels per second
        self._max_scroll = 0
        self._scroll_pause = 0.0
        self._scroll_pause_duration = 1.0
        self._scrolling_down = True

    def _build_full_desc_surface(self, description):
        """Render all description lines onto a surface tall enough for all text."""
        words = description.split(' ')
        lines = []
        current_line = ''
        for word in words:
            test_line = f"{current_line} {word}".strip()
            if self._font.size(test_line)[0] <= self.desc_rect.width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)

        line_height = self._font.get_linesize()
        total_height = max(len(lines) * line_height, self.desc_rect.height)

        surf = pygame.Surface((self.desc_rect.width, total_height), pygame.SRCALPHA)
        y = 0
        for line in lines:
            line_surf = self._font.render(line, True, (255, 255, 255))
            line_rect = line_surf.get_rect()
            line_rect.centerx = self.desc_rect.width // 2
            line_rect.top = y
            surf.blit(line_surf, line_rect)
            y += line_height

        max_scroll = max(0, total_height - self.desc_rect.height)
        return surf, max_scroll

    def set_position(self, position):
        self.rect.topleft = position

    def update(self, delta):
        if self._max_scroll <= 0:
            return

        self._hover_time += delta

        if self._hover_time < self._scroll_delay:
            return

        if self._scroll_pause > 0:
            self._scroll_pause -= delta
            return

        if self._scrolling_down:
            self._scroll_offset += self._scroll_speed * delta
            if self._scroll_offset >= self._max_scroll:
                self._scroll_offset = self._max_scroll
                self._scroll_pause = self._scroll_pause_duration
                self._scrolling_down = False
        else:
            self._scroll_offset -= self._scroll_speed * delta
            if self._scroll_offset <= 0:
                self._scroll_offset = 0
                self._scroll_pause = self._scroll_pause_duration
                self._scrolling_down = True

    def displayTooltip(self, position: pygame.math.Vector2, title, description, group):
        self.set_position(position)
        self.title_box.set_text(title)

        if description != self._current_desc:
            self._current_desc = description
            self._full_desc_surface, self._max_scroll = self._build_full_desc_surface(description)
            self._scroll_offset = 0.0
            self._hover_time = 0.0
            self._scroll_pause = 0.0
            self._scrolling_down = True
            self.description_box.set_text(description)

        self.image.fill((0, 0, 0, 0))
        self.image.blit(self.bg_container, (0, 0))
        self.image.blit(self.title_box.image, self.title_box.rect)

        if self._max_scroll > 0 and self._full_desc_surface is not None:
            clip_y = int(min(self._scroll_offset, self._max_scroll))
            clip_rect = pygame.Rect(0, clip_y, self.desc_rect.width, self.desc_rect.height)
            clipped = self._full_desc_surface.subsurface(clip_rect)
            self.image.blit(clipped, self.desc_rect.topleft)
        else:
            self.image.blit(self.description_box.image, self.description_box.rect)

        self.add(group)

    def hideTooltip(self):
        self._current_desc = ""
        self._scroll_offset = 0.0
        self._hover_time = 0.0
        self._scroll_pause = 0.0
        self._scrolling_down = True
        self.kill()
