from stellatro_game.game import Game, Phase, PlayerTurn
import pygame
from utils import get_assets_path
from text import TextBox



class PhaseContainer:
    def __init__(self, pos : pygame.math.Vector2, game : Game):
        self.pos = pos
        self.game = game
        self.group = pygame.sprite.Group()

        self.container_img = pygame.image.load(get_assets_path("UI/PhaseContainer.png")).convert_alpha()
        self.container_img = pygame.transform.smoothscale_by(self.container_img,0.25)
        
        self.background_sprite = pygame.sprite.Sprite()
        self.background_sprite.image = self.container_img
        self.background_sprite.rect = self.container_img.get_rect(topleft=pos)

        self.phase_title_rect = pygame.Rect(self.pos.x+ 96.32,self.pos.y+4,112,57)
        self.phase_title_box = TextBox(
            self.phase_title_rect, 
            "", 
            font_size=24, 
            text_color=(255, 255, 255), 
            font_url=get_assets_path("Jersey_10/Jersey10-Regular.ttf"),
            align="center",
        )
        
        self.phase_desc_rect = pygame.Rect(self.pos.x+10.23,self.pos.y+68,190,66)
        self.phase_desc_box = TextBox(
            self.phase_desc_rect, 
            "", 
            font_size=24, 
            text_color=(255, 255, 255), 
            font_url=get_assets_path("Jersey_10/Jersey10-Regular.ttf"),
            align="center",
        )

        self.group.add(self.background_sprite, self.phase_title_box, self.phase_desc_box)

    def update(self,delta):
        self.phase_title_box.set_text(self.game.phase.name)
        self.phase_desc_box.set_text(self.get_phase_description())

    def draw(self,group):
        group.add(self.group)
        
    def get_phase_description(self):
        if self.game.phase == Phase.DRAFT:
            turnString = "P1" if self.game.current_turn == PlayerTurn.PLAYER1 else "P2"
            return f"{turnString}: Select a Joker"
        return ""
        