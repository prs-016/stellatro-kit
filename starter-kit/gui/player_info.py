import pygame
from utils import get_assets_path, format_number
from text import Text
from stellatro_game.checker import HandType

def getHandTypeStr(hand_type : HandType):
    if hand_type == "":
        return ""
    if hand_type == HandType.HIGH_CARD:
        return "High Card"
    elif hand_type == HandType.PAIR:
        return "Pair"
    elif hand_type == HandType.TWO_PAIR:
        return "Two Pair"
    elif hand_type == HandType.THREE_OF_A_KIND:
        return "Three of a Kind"
    elif hand_type == HandType.STRAIGHT:
        return "Straight"
    elif hand_type == HandType.FLUSH:
        return "Flush"
    elif hand_type == HandType.FULL_HOUSE:
        return "Full House"
    elif hand_type == HandType.FOUR_OF_A_KIND:
        return "Four of a Kind"
    elif hand_type == HandType.STRAIGHT_FLUSH:
        return "Straight Flush"
    else:
        return "Invalid Hand Type"


class PlayerInfo():
    def __init__(self, topleft=(0,0)):
        super().__init__()

        player_info_surf = pygame.image.load(get_assets_path("UI/PlayerInfo.png"))
        player_info_surf =  pygame.transform.smoothscale_by(player_info_surf, 0.25)
        bg = pygame.sprite.Sprite()
        bg.image = player_info_surf
        bg.rect = bg.image.get_rect(topleft=topleft)
        self.topleft = topleft
        
        self.bg = bg
        
        # prepare text surfaces
        FONT_SIZE = 36
        fontPath= get_assets_path("Jersey_10/Jersey10-Regular.ttf")
        self.chips_text = Text((topleft[0] + 80, self.topleft[1] + 136), "0", FONT_SIZE, (255,255,255), fontPath,"right")
        self.mult_text = Text((topleft[0]+103,topleft[1]+136),"0",FONT_SIZE,(255,255,255),fontPath)
        self.round_text = Text((topleft[0]+120,topleft[1]+45),"0",FONT_SIZE,(255,255,255),fontPath,"center")
        self.hand_type_text = Text((topleft[0]+94,topleft[1]+105), "", FONT_SIZE, (255,255,255), fontPath,"center")

    
    def update(self, chips=None, mult=None, round_score=None, hand_type=None):
        if chips != None:
            self.chips_text.updateText(format_number(chips))
        if mult != None:
            self.mult_text.updateText(format_number(mult))
        if round_score != None:
            self.round_text.updateText(format_number(round_score))
        if hand_type != None:
            self.hand_type_text.updateText(getHandTypeStr(hand_type))
        


    def draw(self, group):
        group.add(self.bg)
        group.add(self.chips_text,self.mult_text,self.round_text,self.hand_type_text)