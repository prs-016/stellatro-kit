import pygame
from card_sprite import CardSprite


class JokerContainer(pygame.sprite.Group):
    """A simple grid-like container for displaying jokers.

    The layout algorithm tries to behave like a CSS flexbox with wrapping.  Cards
    are arranged in rows; when the number of cards in a row would exceed the
    available width the layout wraps to the next line.  The caller can control
    the maximum gap and the padding around the grid via the constructor.  The
    container will attempt to centre each row of cards horizontally and will
    always respect the top/left padding values.

    The implementation is intended to handle at least 15 jokers (5 columns by
    three rows) given a reasonable container size, but additional cards will
    simply continue wrapping onto further rows.
    """

    def __init__(self, x: float, y: float, width: float, height: float,
                 bg_path: str = None, padding_x: float = 15,
                 padding_y: float = 20, gap: float = 8, max_columns: int = 5):
        super().__init__()

        self.rect = pygame.Rect(x, y, width, height)
        self.padding_x = padding_x
        self.padding_y = padding_y
        self.gap = gap
        # user can override the maximum cards per row; default is 5
        self.max_columns = max_columns

        self.bg_surface = None
        self.background_sprite = None
        if bg_path:
            raw_bg = pygame.image.load(bg_path).convert_alpha()
            self.bg_surface = pygame.transform.smoothscale(raw_bg,
                                                          (int(width),
                                                           int(height)))
            self.background_sprite = pygame.sprite.Sprite()
            self.background_sprite.image = self.bg_surface
            self.background_sprite.rect = self.background_sprite.image.get_rect(topleft=(x,y))

    def update(self, delta: float):
        sprites = self.sprites()
        if not sprites:
            return

        num_cards = len(sprites)
        BASE_CARD_W = 65 
        BASE_CARD_H = 87

        inner_width = self.rect.width - (self.padding_x * 2)

        # determine how many columns we can fit based on the available width
        # and the card width/gap; never exceed the configured max_columns
        possible_cols = int((inner_width + self.gap) // (BASE_CARD_W + self.gap))
        columns = max(1, min(possible_cols, self.max_columns))

        # layout the cards row by row, centring each row individually
        for idx, sprite in enumerate(sprites):
            row = idx // columns
            col = idx % columns

            # compute how many cards are in this row (last row may be short)
            remaining = num_cards - row * columns
            row_count = columns if remaining >= columns else remaining

            row_width = (row_count * BASE_CARD_W) + ((row_count - 1) * self.gap)
            start_x = (self.rect.left + self.padding_x +
                       (inner_width - row_width) / 2 +
                       BASE_CARD_W / 2)

            current_x = start_x + col * (BASE_CARD_W + self.gap)
            current_y = (self.rect.top + self.padding_y +
                         row * (BASE_CARD_H + self.gap) +
                         BASE_CARD_H / 2)

            card: CardSprite = sprite
            card.target_pos = pygame.math.Vector2(current_x, current_y)
            card.update(delta)

    def draw(self, group: pygame.sprite.Group):
        if self.background_sprite:
            group.add(self.background_sprite)
        group.add(self.sprites())

    # we may want the same sort helpers as CardHandContainer
    def sort(self, by="rank"):
        if by == "rank":
            sorted_sprites = sorted(self.sprites(), key=lambda card: card.rank)
            self.empty()
            self.add(sorted_sprites)
        elif by == "suit":
            sorted_sprites = sorted(self.sprites(),
                                    key=lambda card: card.initialSuit)
            self.empty()
            self.add(sorted_sprites)
