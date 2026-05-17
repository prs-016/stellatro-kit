import pygame
import math
from utils import get_assets_path
from stellatro_game.jokers import *

JOKER_IMAGE_TABLE = {}


def _make_outline(surf: pygame.Surface, color: tuple, thickness: int = 3) -> pygame.Surface:
    """Draw an outline that traces only the visible (non-transparent) pixels."""
    result = surf.copy()
    mask = pygame.mask.from_surface(surf)
    pts = mask.outline()
    if len(pts) > 2:
        pygame.draw.polygon(result, (*color, 255), pts, thickness)
    return result

JOKER_URL_MAPPING = {
    RegularJoker:        "stellatro_jokers/Regular Joker.png",
    PairMultBoost:       "stellatro_jokers/Jolly Joker.png",
    PairChipBoost:       "stellatro_jokers/Sly Joker.png",
    TripletMultBoost:    "stellatro_jokers/Zany Joker.png",
    TwoPairMultBoost:    "stellatro_jokers/Cheeky Joker.png",
    StraightMultBoost:   "stellatro_jokers/Witty Joker.png",
    FlushMultBoost:      "stellatro_jokers/Daring Joker.png",
    TripletChipBoost:    "stellatro_jokers/Merry Joker.png",
    TwoPairChipBoost:    "stellatro_jokers/Jovial Joker.png",
    StraightChipBoost:   "stellatro_jokers/Lively Joker.png",
    FlushChipBoost:      "stellatro_jokers/Vibrant Joker.png",
    DiamondMultBoost:    "stellatro_jokers/Diamond Joker.png",
    HeartMultBoost:      "stellatro_jokers/Heart Joker.png",
    ClubMultBoost:       "stellatro_jokers/Club Joker.png",
    SpadeMultBoost:      "stellatro_jokers/Spade Joker.png",
    WalkieTalkie:        "stellatro_jokers/Walkie Talkie Joker.png",
    Seltzer:             "stellatro_jokers/Seltzer Joker.png",
    SockAndBuskin:       "stellatro_jokers/Sock and Buskin Joker.png",
    SunGod:              "stellatro_jokers/Sun God Joker.png",
    EigthCollege:        "stellatro_jokers/Eight College Joker.png",
    PhotoGraphMultBoost: "stellatro_jokers/Photograph Joker.png",
    FlowerPot:           "stellatro_jokers/Flower Pot Joker.png",
    TheDuo:              "stellatro_jokers/The Duo Joker.png",
    TheTrio:             "stellatro_jokers/The Trio Joker.png",
    TheTribe:            "stellatro_jokers/The Tribe Joker.png",
    TheOrder:            "stellatro_jokers/The Order Joker.png",
    TheSingle:           "stellatro_jokers/UC Socially Dead Joker.png",
    BitByte:             "stellatro_jokers/Bit Byte Joker.png",
    StudentID:           "stellatro_jokers/Student ID Joker.png",
    LastLecture:         "stellatro_jokers/Last Lecture Joker.png",
    DiningHallPrices:    "stellatro_jokers/Dining Hall Prices Joker.png",
    HalfJoker:           "stellatro_jokers/Half Joker.png",
    Fibonacci:           "stellatro_jokers/Fibonacci Joker.png",
    ScaryFace:           "stellatro_jokers/Scary Face Joker.png",
    Mirror:              "stellatro_jokers/mirror_joker.png",
    Plasma:              "stellatro_jokers/plasma_joker.png",
    StarPlasma:          "stellatro_jokers/Star_Plasma.png",
    JamSession:          "stellatro_jokers/jam_session_joker.png",
    Spotlight:           "stellatro_jokers/spotlight_joker.png",
    ColorTheory:         "stellatro_jokers/color_theory_joker.png",
    StudyGroup:          "stellatro_jokers/study_group_joker.png",
    GroupProject:        "stellatro_jokers/group_project_joker.png",
    Encore:              "stellatro_jokers/encore_joker.png",
    WishUponAStar:       "stellatro_jokers/WishUponAStar.png",
    BinaryStar:          "stellatro_jokers/binary_star_joker.png",
    Pips:                "stellatro_jokers/pips_joker.png",
    ReportCard:          "stellatro_jokers/report_card_joker.png",
    CacheCoherence:      "stellatro_jokers/Cache Coherence Joker.png",
    Stargazing:          "stellatro_jokers/Stargazing Joker.png",
    BoilingPoint:        "stellatro_jokers/Boiling Point Joker.png",
    Galaxy:              "stellatro_jokers/Galaxy Joker.png",
    Popcorn:             "stellatro_jokers/Popcorn Joker.png",
    Starcorn:            "stellatro_jokers/Starcorn.png",
    Supernova:           "stellatro_jokers/Supernova.png",
    Snowball:            "stellatro_jokers/Snowball.png",
    Constellation:       "stellatro_jokers/Constellation Joker.png",
    Arrowhead:           "stellatro_jokers/Arrowhead.png",
    LossCut:             "stellatro_jokers/Loss_Cut.png",
    LockIn:              "stellatro_jokers/Lock In.png",
    Starjack:            "stellatro_jokers/Starjack.png",
    Blackjack:           "stellatro_jokers/Blackjack.png",
    SixSeven:            "stellatro_jokers/SixSeven.png",
    ThriceTwice:         "stellatro_jokers/ThriceTwice.png",
    FallenStar:          "stellatro_jokers/Fallen Star.png",
    StarFish:            "stellatro_jokers/Star Fish.png",
    BranchOut:           "stellatro_jokers/Branch_Out.png",
    Anya:                "stellatro_jokers/Anya.png",
    CacheCoherence:      "stellatro_jokers/Cache Coherence Joker.png",
    Stargazing:          "stellatro_jokers/Stargazing Joker.png",
    BoilingPoint:        "stellatro_jokers/Boiling Point Joker.png",
    Galaxy:              "stellatro_jokers/Galaxy Joker.png",
    Popcorn:             "stellatro_jokers/Popcorn Joker.png",
    Constellation:       "stellatro_jokers/Constellation Joker.png",
}

# Base class for jokers
class JokerSprite(pygame.sprite.Sprite, Joker):
    tooltip_offset = (-145,-15)
    
    def __init__(self, imageUrl):
        super().__init__()
        self.imageUrl = imageUrl
        if self.imageUrl not in JOKER_IMAGE_TABLE:
            img_path = get_assets_path(self.imageUrl)
            # Using .convert_alpha() is good practice for performance with transparent images
            img = pygame.image.load(img_path).convert_alpha()
            img = pygame.transform.smoothscale(img,(65,87))
            JOKER_IMAGE_TABLE[self.imageUrl] = img
        
        base_key = (self.imageUrl, "base_outline")
        if base_key not in JOKER_IMAGE_TABLE:
            JOKER_IMAGE_TABLE[base_key] = _make_outline(JOKER_IMAGE_TABLE[self.imageUrl], (212, 212, 212), 1)
        self.original_image = JOKER_IMAGE_TABLE[base_key]

        hover_key = (self.imageUrl, "hover_outline")
        if hover_key not in JOKER_IMAGE_TABLE:
            JOKER_IMAGE_TABLE[hover_key] = _make_outline(JOKER_IMAGE_TABLE[self.imageUrl], (212, 212, 212), 1)
        self.hover_image = JOKER_IMAGE_TABLE[hover_key]

        self.image = self.original_image.copy()
        self.rect = self.image.get_rect(topleft=(0, 0))
        self.target_pos = pygame.math.Vector2(self.rect.center)
        self.lerp_speed= 10
        self.selected = False

        # Shake animation attributes
        self.is_shaking = False
        self.shake_timer = 0.0
        self.shake_duration = 0.3  # seconds
        self.shake_angle = 10      # degrees
        
        self.is_hovered = False
        self.hover_timer = 0.0
        self.hover_duration = 0.05
        self.current_scale = 1.0
        self.target_scale = 1.0
        self.scale_speed = 12.0
        
   
    def get_tooltip_pos(self):
        return (self.rect.topleft[0] + self.tooltip_offset[0], self.rect.topleft[1] + self.tooltip_offset[1])

    def update(self, dt):
        # Choose base image: outlined when hovered, plain otherwise
        base_image = self.hover_image if self.is_hovered else self.original_image

        # Position interpolation
        curr_pos = pygame.math.Vector2(self.rect.center)
        if curr_pos.distance_to(self.target_pos) > 1:
            lerp = min(max(self.lerp_speed * dt,0),1)
            new_pos = curr_pos.lerp(self.target_pos, lerp)
            self.rect.center = (new_pos.x, new_pos.y)

        # Shake animation
        if self.is_shaking:
            center = self.rect.center
            self.shake_timer += dt
            if self.shake_timer >= self.shake_duration:
                self.is_shaking = False
                self.shake_timer = 0.0
                self.image = base_image.copy()
                self.rect = self.image.get_rect(center=center)
            else:
                progress = self.shake_timer / self.shake_duration
                angle = self.shake_angle * math.sin(progress * math.pi * 2)
                self.image = pygame.transform.rotate(base_image, angle)
                self.rect = self.image.get_rect(center=center)

        if self.is_hovered:
            self.hover_timer += dt
            if self.hover_timer >= self.hover_duration:
                self.is_hovered = False
                self.hover_timer = 0.0

        self.target_scale = 1.15 if self.is_hovered else 1.0

        if abs(self.current_scale - self.target_scale) > 0.001:
            scale_lerp = min(self.scale_speed * dt, 1.0)
            self.current_scale += (self.target_scale - self.current_scale) * scale_lerp

            center = self.rect.center
            self.image = pygame.transform.smoothscale_by(base_image, self.current_scale)
            self.rect = self.image.get_rect(center=center)

    def shake(self):
        if not self.is_shaking:
            self.is_shaking = True
            self.shake_timer = 0.0
        else:
            self.shake_timer = 0.0
    def hover(self):
        """Pass True if mouse is over, False otherwise."""
        self.is_hovered = True
        self.hover_timer = 0.0

def create_joker_sprite(joker_instance):
    """
    Takes an instantiated Joker object from the game logic, dynamically creates 
    a class inheriting from both JokerSprite and the specific Joker's class, 
    and returns a new sprite instance that preserves the joker's internal state.
    """
    joker_class = type(joker_instance)
    
    # Fallback to a default image if the joker isn't in the mapping yet
    image_url = JOKER_URL_MAPPING.get(joker_class, "balatro_jokers/balatro_jokers_0.png")

    class DynamicJokerSprite(JokerSprite, joker_class):
        def __init__(self, original_joker):
            # Initialize the sprite attributes (image, rect, etc.)
            JokerSprite.__init__(self, imageUrl=image_url)
            
            # Copy any internal state from the original joker (e.g., active suits, mult counters)
            self.__dict__.update(original_joker.__dict__)
            
            self._original_joker = original_joker
        def __eq__(self, other):
            # 1. Compare against another DynamicJokerSprite
            if hasattr(other, "_original_joker"):
                return self._original_joker == other._original_joker
            
            # 2. Compare directly against a logical Joker instance
            if isinstance(other, joker_class) or isinstance(other, type(self._original_joker)):
                return self._original_joker == other
                
            # Allow fallback to other comparison methods if type doesn't match
            return NotImplemented

        def __hash__(self):
            # Good practice: defining __eq__ means we should define __hash__ 
            # so the sprites can be safely used in sets or dictionary keys.
            return hash(self._original_joker)

    return DynamicJokerSprite(joker_instance)
