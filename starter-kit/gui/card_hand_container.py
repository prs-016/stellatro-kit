import pygame
from card_sprite import CardSprite
from stellatro_game.card import Suit

class CardHandContainer(pygame.sprite.Group):
    SELECTED_OFFSET = -30 
    LERP_SPEED = 5.0  # Adjust this to make the container move faster/slower

    def __init__(self, x: float, y: float, width: float, height: float, 
                 bg_path: str = None, padding_x: float = 15, padding_y: float = 20, gap: float = 8):
        super().__init__()
        
        self.rect = pygame.Rect(x, y, width, height)
        # 1. Initialize position vectors
        self.pos = pygame.math.Vector2(x, y)
        self.target_pos = pygame.math.Vector2(x, y)
        
        self.padding_x = padding_x
        self.padding_y = padding_y
        self.gap = gap
        
        self.bg_surface = None
        self.background_sprite = None
        if bg_path:
            raw_bg = pygame.image.load(bg_path).convert_alpha()
            self.bg_surface = pygame.transform.smoothscale(raw_bg, (int(width), int(height)))
            self.background_sprite = pygame.sprite.Sprite()
            self.background_sprite.image = self.bg_surface
            self.background_sprite.rect = self.background_sprite.image.get_rect(topleft=(x,y))
        
    def update(self, delta: float):
        # 2. Lerp the container's position toward the target
        # Use delta to ensure movement is framerate-independent
        if self.pos != self.target_pos:
            # Formula: Current + (Target - Current) * Speed * Delta
            self.pos += (self.target_pos - self.pos) * self.LERP_SPEED * delta
            
            # Snap to target if very close to prevent micro-stuttering
            if self.pos.distance_to(self.target_pos) < 0.5:
                self.pos = pygame.math.Vector2(self.target_pos)
            
            # Sync the rect with the vector (Rects only hold integers)
            self.rect.topleft = (int(self.pos.x), int(self.pos.y))
        if self.background_sprite:
            self.background_sprite.rect.topleft = self.rect.topleft
        
        sprites = self.sprites()
        if not sprites:
            return

        num_cards = len(sprites)
        card_w = sprites[0].rect.width
        card_h = sprites[0].rect.height
        
        inner_width = self.rect.width - (self.padding_x * 2)
        preferred_total_width = (num_cards * card_w) + ((num_cards - 1) * self.gap)
        
        if preferred_total_width > inner_width:
            effective_gap = (inner_width - (num_cards * card_w)) / max(1, num_cards - 1)
            actual_content_width = inner_width
        else:
            effective_gap = self.gap
            actual_content_width = preferred_total_width

        start_x = self.rect.left + self.padding_x + (inner_width - actual_content_width) / 2
        inner_height = self.rect.height - (self.padding_y * 2)
        base_y_center = self.rect.top + self.padding_y + (inner_height / 2)

        for i, sprite in enumerate(sprites):
            card: CardSprite = sprite
            current_x = start_x + (i * (card_w + effective_gap)) + (card_w / 2)
            
            target_y = base_y_center
            if card.selected:
                target_y += self.SELECTED_OFFSET
                
            card.target_pos = pygame.math.Vector2(current_x, target_y)
            card.update(delta)
    def draw(self, group: pygame.sprite.Group):
        # Draw background container
        if self.background_sprite:
            group.add(self.background_sprite)
        
        # Draw cards
        for sprite in self.sprites():
            group.add(sprite)
    def sort(self, group : pygame.sprite.Group, by="rank"):
        suit_sort_order = {
            Suit.SPADE.value: 1,
            Suit.HEART.value: 2,
            Suit.DIAMOND.value: 3,
            Suit.CLUB.value: 4
        }
        if by == "rank":
            sorted_sprites=sorted(self.sprites(),key=lambda card: card.rank)
            self.empty()
            self.add(sorted_sprites)
            group.remove(sorted_sprites)
            for sprite in sorted_sprites:
                group.add(sprite)
        elif by == "suit":
            sorted_sprites=sorted(self.sprites(),key=lambda card: suit_sort_order.get(card.initialSuit,99))
            self.empty()
            self.add(sorted_sprites)
            group.remove(sorted_sprites)
            for sprite in sorted_sprites:
                group.add(sprite)
        