from stellatro_common.models import CardModel
import pygame
from stellatro_game.card import Card, Suit
from utils import get_assets_path
from pydantic import ConfigDict

CARD_IMAGE_TABLE = {}
STELLA_ICON_SIZE = 14
STELLA_ICON_GAP = 1
STELLA_MARGIN = 3
STELLA_MAX_VISIBLE = 5
_STELLA_IMAGE = None
_STELLA_FONT = None


def _get_stella_image():
    global _STELLA_IMAGE
    if _STELLA_IMAGE is None:
        full_path = get_assets_path("UI/stella.png")
        img = pygame.image.load(full_path).convert_alpha()
        _STELLA_IMAGE = pygame.transform.smoothscale(img, (STELLA_ICON_SIZE, STELLA_ICON_SIZE))
    return _STELLA_IMAGE


def _get_stella_font():
    global _STELLA_FONT
    if _STELLA_FONT is None:
        _STELLA_FONT = pygame.font.Font(get_assets_path("Jersey_10/Jersey10-Regular.ttf"), 12)
    return _STELLA_FONT



def _make_outline(surf: pygame.Surface, color: tuple, thickness: int = 3) -> pygame.Surface:
    """Draw an outline that traces only the visible (non-transparent) pixels."""
    result = surf.copy()
    mask = pygame.mask.from_surface(surf)
    pts = mask.outline()
    if len(pts) > 2:
        pygame.draw.polygon(result, (*color, 255), pts, thickness)
    return result


class CardSprite(pygame.sprite.Sprite, Card):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra='allow')
    selected : bool = False
    initialSuit : Suit
    is_playing : bool = False
    tooltip_offset : tuple[int,int] = (-45, -150)




    def __init__(self, card_instance : CardModel, x=0, y=0):
        suit_str = list(card_instance.suits)[0]
        Card.__init__(self, rank=card_instance.rank, suit=Suit(suit_str))
        pygame.sprite.Sprite.__init__(self)

        self._original_card = card_instance
        self.initialSuit = suit_str

        self.selected = False
        self.stella = getattr(card_instance, "stella", 0) or 0

        suits_dir = {
            'club': "clovers",
            'diamond': "diamonds",
            'heart': "hearts",
            'spade': "spades",
        }
        rank_dir = {
            2: "2",
            3: "3",
            4: "4",
            5: "5",
            6: "6",
            7: "7",
            8: "8",
            9: "9",
            10: "10",
            11: "jack",
            12: "queen",
            13: "king",
            14: "ace",
        }

        image_path = f"stellatro_cards/{suits_dir[self.initialSuit]}/{rank_dir[self.rank]}_of_{suits_dir[self.initialSuit]}.png"
        if image_path not in CARD_IMAGE_TABLE:
            full_path = get_assets_path(image_path)
            image = pygame.image.load(full_path).convert_alpha()
            image = pygame.transform.scale(image, (59,95))
            CARD_IMAGE_TABLE[image_path] = image
        
        base_key = (image_path, "base_outline")
        if base_key not in CARD_IMAGE_TABLE:
            CARD_IMAGE_TABLE[base_key] = _make_outline(CARD_IMAGE_TABLE[image_path], (212, 212, 212), 2)
        self.original_image = CARD_IMAGE_TABLE[base_key]

        selected_key = (image_path, "selected_outline")
        if selected_key not in CARD_IMAGE_TABLE:
            CARD_IMAGE_TABLE[selected_key] = _make_outline(CARD_IMAGE_TABLE[image_path], (212, 212, 212), 2)
        self.selected_image = CARD_IMAGE_TABLE[selected_key]
        self._rendered_stella = -1
        self._original_with_stella = self.original_image
        self._selected_with_stella = self.selected_image
        self._refresh_stella_overlay()
        self.image = self._selected_with_stella if self.selected else self._original_with_stella
        self.rect = self.image.get_rect(topleft=(x, y))
        self._current_pos = pygame.math.Vector2(self.rect.center) # Store float position
        self.target_pos = pygame.math.Vector2(self._current_pos) # Initial target is current position
        self.lerp_speed = 10

    def _compose_stella(self, base: pygame.Surface) -> pygame.Surface:
        if self.stella <= 0:
            return base

        composed = base.copy()
        stella_img = _get_stella_image()
        visible = min(self.stella, STELLA_MAX_VISIBLE)
        card_w, card_h = composed.get_size()
        x = card_w - STELLA_ICON_SIZE - STELLA_MARGIN
        for i in range(visible):
            y = card_h - STELLA_MARGIN - STELLA_ICON_SIZE - i * (STELLA_ICON_SIZE + STELLA_ICON_GAP)
            composed.blit(stella_img, (x, y))

        if self.stella > STELLA_MAX_VISIBLE:
            font = _get_stella_font()
            label = font.render(f"x{self.stella}", True, (255, 255, 255))
            label_bg = pygame.Surface(label.get_size(), pygame.SRCALPHA)
            label_bg.fill((0, 0, 0, 160))
            top_icon_y = card_h - STELLA_MARGIN - STELLA_ICON_SIZE - (visible - 1) * (STELLA_ICON_SIZE + STELLA_ICON_GAP)
            label_x = x + STELLA_ICON_SIZE - label.get_width()
            label_y = top_icon_y - label.get_height() - 1
            composed.blit(label_bg, (label_x, label_y))
            composed.blit(label, (label_x, label_y))
        return composed

    def _refresh_stella_overlay(self):
        if self.stella == self._rendered_stella:
            return
        self._rendered_stella = self.stella
        self._original_with_stella = self._compose_stella(self.original_image)
        self._selected_with_stella = self._compose_stella(self.selected_image)

    def get_tooltip_pos(self):
        return (self.rect.topleft[0]+self.tooltip_offset[0], self.rect.topleft[1]+self.tooltip_offset[1])
    def toggle_selection(self):
        self.selected = not self.selected
        # No need to directly modify position here, CardHandContainer.update will handle target_pos

    def update(self, dt):
        if self.stella != self._rendered_stella:
            self._refresh_stella_overlay()

        target_img = self._selected_with_stella if self.selected else self._original_with_stella
        if self.image is not target_img:
            center = self.rect.center
            self.image = target_img
            self.rect = self.image.get_rect(center=center)

        # Use a small epsilon for snapping to target to avoid floating point inaccuracies
        SNAP_DISTANCE = 0.5 # If closer than this, snap to target

        if self._current_pos.distance_to(self.target_pos) > SNAP_DISTANCE:
            lerp_factor = min(max(self.lerp_speed * dt, 0), 1)
            self._current_pos = self._current_pos.lerp(self.target_pos, lerp_factor)
        else:
            self._current_pos.update(self.target_pos) # Snap to target

        self.rect.center = (int(self._current_pos.x), int(self._current_pos.y))
    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return self is other

        
