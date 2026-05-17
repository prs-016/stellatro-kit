import pygame
from text import TextBox
from utils import get_assets_path, format_number
from stellatro_game.game import Game
from button import ImageButton
class GameOverContainer(pygame.sprite.Sprite):
    def __init__(self, pos : pygame.math.Vector2, on_close, on_restart):
        super().__init__()
        self.bg_image = pygame.image.load(get_assets_path("UI/GameOverContainer.png")).convert_alpha()
        self.bg_image = pygame.transform.smoothscale_by(self.bg_image, 0.25)
        self.image = self.bg_image.copy()
        self.rect = self.image.get_rect(center=pos)

        font_path = get_assets_path("Jersey_10/Jersey10-Regular.ttf")
        
        
       
        header_rect = pygame.Rect(self.rect.topleft[0]+20,self.rect.topleft[1]+8,321,60)
        self.header_text = TextBox(
            header_rect, 
            text="",
            font_size=48, 
            text_color=(255, 255, 255), 
            font_url=font_path,
            align="center",
        )
        p1_score_rect = pygame.Rect(self.rect.topleft[0]+126.41,self.rect.topleft[1]+85.25,193,53)
        self.p1_score_text = TextBox(
            p1_score_rect, 
            text="",
            font_size=18, 
            text_color=(255, 255,255), 
            font_url=font_path,
            align="center",
        )
        p2_score_rect = pygame.Rect(self.rect.topleft[0]+128.91,self.rect.topleft[1] + 162.25,193,53)
        self.p2_score_text = TextBox(
            p2_score_rect, 
            text="",
            font_size=18, 
            text_color=(255, 255,255), 
            font_url=font_path,
            align="center",
        )
        seed_rect = pygame.Rect(self.rect.topleft[0]+91.5,self.rect.topleft[1]+239,124,53)
        self.seed_text = TextBox(
            seed_rect, 
            text="n/a",
            font_size=18, 
            text_color=(255, 255,255), 
            font_url=font_path,
            align="center",
        )
        self.close_btn = ImageButton(
            pos=(self.rect.topleft[0]+44,self.rect.topleft[1]+338),
            normal_path=get_assets_path("UI/CloseButton.png"),
            hover_path=get_assets_path("UI/CloseButton_hover.png"),
            active_path=get_assets_path("UI/CloseButton_active.png"),
            disabled_surf=get_assets_path("UI/CloseButton_disabled.png"),
            scale=0.25,
            action=on_close
        )
        self.restart_btn = ImageButton(
            pos=(self.rect.topleft[0]+187,self.rect.topleft[1]+338),
            normal_path=get_assets_path("UI/RestartButton.png"),
            hover_path=get_assets_path("UI/RestartButton_hover.png"),
            active_path=get_assets_path("UI/RestartButton_active.png"),
            disabled_surf=get_assets_path("UI/RestartButton_disabled.png"),
            scale=0.25,
            action=on_restart
        )
        self.buttons = pygame.sprite.Group()
        self.buttons.add(self.close_btn, self.restart_btn)
        self.seed = None


    def handle_events(self,event):
        for btn in self.buttons:
            btn.handle_event(event)
            
    def update(self,delta, game : Game, mouse_pos, mouse_btns):
        if game.player1_score > game.player2_score:
            self.header_text.set_text("P1 WINS!")
        elif game.player2_score > game.player1_score:
            self.header_text.set_text("P2 WINS!")
        else:
            self.header_text.set_text("DRAW!")
        
        
        self.p1_score_text.set_text(format_number(game.player1_score))
        self.p2_score_text.set_text(format_number(game.player2_score))
        self.seed_text.set_text(str(self.seed) if self.seed is not None else "n/a")
        self.buttons.update(delta,mouse_pos,mouse_btns)
    def draw(self, group):
        group.add(self)
        group.add(self.p1_score_text,self.p2_score_text,self.header_text,self.seed_text)
        group.add(self.buttons)
