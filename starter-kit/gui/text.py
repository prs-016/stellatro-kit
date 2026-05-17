import pygame

FONT_SIZE = 24

class Text(pygame.sprite.Sprite):
    def __init__(self, position, initial_text, font_size, text_color, textFontUrl=None, align="left"):
        super().__init__()
        self.text = initial_text
        self.font_size = font_size
        self.text_color = text_color
        self.position = position
        
        # Standard font loading - no massive scale factor needed
        self.font = pygame.font.Font(textFontUrl, font_size)
        self.align = align
        self.updateText(self.text)

    def updateText(self, newText):
        self.text = newText
        # Simply render with Anti-Aliasing (True)
        self.image = self.font.render(self.text, True, self.text_color)
        self.rect = self.image.get_rect()
        
        if self.align == "left":
            self.rect.topleft = self.position
        elif self.align == "center":
            self.rect.center = self.position
        elif self.align == "right":
            self.rect.topright = self.position

class TextBox(pygame.sprite.Sprite):
    """
    A class to render a block of text with wrapping and alignment within a given rectangle.
    """
    def __init__(self, rect: pygame.Rect, text: str, font_size: int, text_color, 
                 align='left', font_url=None, bg_color=None):
        """
        :param rect: The bounding rectangle for the text box.
        :param text: The text to be rendered.
        :param font_size: The font size.
        :param text_color: The color of the text.
        :param align: Text alignment ('left', 'center', 'right').
        :param font_url: Path to a .ttf font file.
        :param bg_color: Optional background color for the text box.
        """
        super().__init__()
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font_size = font_size
        self.text_color = text_color
        self.align = align
        self.font = pygame.font.Font(font_url, font_size)
        self.bg_color = bg_color
        
        self.render()

    def render(self):
        """
        Renders the text onto an internal surface. This should be called
        if the text or other properties change.
        """
        self.image = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        if self.bg_color:
            self.image.fill(self.bg_color)

        lines = self._wrap_text(self.text)
        line_height = self.font.get_linesize()
        total_text_height = len(lines) * line_height
        start_y = max(0, (self.rect.height - total_text_height) // 2)
        
        y = start_y
        for line in lines:
            line_surface = self.font.render(line, True, self.text_color)
            line_rect = line_surface.get_rect()
            
            if self.align == 'left':
                line_rect.left = 0
            elif self.align == 'center':
                line_rect.centerx = self.rect.width / 2
            elif self.align == 'right':
                line_rect.right = self.rect.width
            
            line_rect.top = y
            self.image.blit(line_surface, line_rect)
            y += self.font.get_linesize()

    def _wrap_text(self, text):
        """A helper method to wrap text into lines."""
        words = text.split(' ')
        lines = []
        current_line = ''
        for word in words:
            test_line = f"{current_line} {word}".strip()
            # Check width against self.rect.width
            if self.font.size(test_line)[0] <= self.rect.width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)
        return lines

    def set_text(self, new_text):
        """Updates the text and re-renders."""
        if self.text == new_text:
            return
        self.text = new_text
        self.render()

class FloatingText(pygame.sprite.Sprite):
    def __init__(self, position, text, font_size, color, font_url=None, duration=1.0, alignment="bottom"):
        super().__init__()
        self.font = pygame.font.Font(font_url, font_size)
        self.text = text
        self.color = color
        self.position = pygame.math.Vector2(position)
        self.duration = duration
        self.timer = 0.0
        self.alpha = 255
        self.alignment = alignment
        
        self._render()

    def _render(self):
        text_surface = self.font.render(self.text, True, self.color)
        self.image = pygame.Surface(text_surface.get_size(), pygame.SRCALPHA)
        self.image.blit(text_surface, (0, 0))
        if self.alignment == "bottom":
            self.rect = self.image.get_rect(midbottom=self.position)
        else:
            self.rect = self.image.get_rect(midtop=self.position)

    def update(self, dt):
        self.timer += dt
        if self.timer >= self.duration:
            self.kill()
            return

        # Move up (drift direction remains the same)
        self.position.y -= 50 * dt
        
        # Fade out
        progress = self.timer / self.duration
        self.alpha = int(255 * (1.0 - progress))
        
        # Re-render with alpha if needed (or just set alpha if surface supports it)
        self.image.set_alpha(self.alpha)
        if self.alignment == "bottom":
            self.rect.midbottom = self.position
        else:
            self.rect.midtop = self.position