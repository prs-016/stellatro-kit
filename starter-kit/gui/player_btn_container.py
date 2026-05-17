from button import ImageButton
from utils import get_assets_path

class PlayerButtonContainer:
    def __init__(self,  play_hand_action, view_deck_action, sort_rank_action, sort_suit_action, startPos=(43,620), isP1 = True):
        self.startPos = startPos
        player_suffix = "P1" if isP1 else "P2"
        
        self.play_hand_btn = ImageButton(
            pos=(startPos[0],startPos[1]+1.5),
            normal_path=get_assets_path(f"UI/PlayHand_{player_suffix}.png"),
            hover_path=get_assets_path(f"UI/PlayHand_{player_suffix}_hover.png"),
            active_path=get_assets_path(f"UI/PlayHand_{player_suffix}_active.png"),
            disabled_surf=get_assets_path("UI/PlayHand_disabled.png"),
            scale=0.25,
            action=play_hand_action
        )
        # self.view_deck_btn = ImageButton(
        #     pos=(startPos[0]+323,startPos[1]+1.5),
        #     normal_path=get_assets_path("UI/ViewDeck.png"),
        #     hover_path=get_assets_path("UI/ViewDeck_hover.png"),
        #     active_path=get_assets_path("UI/ViewDeck_active.png"),
        #     disabled_surf=get_assets_path("UI/ViewDeck_disabled.png"),
        #     scale=0.25,
        #     action=view_deck_action
        # )
        # self.sort_by_img = pygame.image.load(get_assets_path("UI/SortByText.png")).convert_alpha()
        # self.sort_by_img = pygame.transform.smoothscale_by(self.sort_by_img, 0.25)
        # self.sort_by_img.get_rect(topleft=(startPos[0]+195,startPos[1]))
        
        self.sort_rank_btn = ImageButton(
            pos=(startPos[0]+153,startPos[1]+26),
            normal_path=get_assets_path("UI/SortRank.png"),
            hover_path=get_assets_path("UI/SortRank_hover.png"),
            active_path=get_assets_path("UI/SortRank_active.png"),
            disabled_surf=get_assets_path("UI/SortRank_disabled.png"),
            scale=0.25,
            action=sort_rank_action
        )
        self.sort_suit_btn = ImageButton(
            pos=(startPos[0]+238,startPos[1]+26),
            normal_path=get_assets_path("UI/SortSuit.png"),
            hover_path=get_assets_path("UI/SortSuit_hover.png"),
            active_path=get_assets_path("UI/SortSuit_active.png"),
            disabled_surf=get_assets_path("UI/SortSuit_disabled.png"),
            scale=0.25,
            action=sort_suit_action
        )
    def handle_events(self,event):
        self.play_hand_btn.handle_event(event)
        # self.view_deck_btn.handle_event(event)
        self.sort_rank_btn.handle_event(event)
        self.sort_suit_btn.handle_event(event)
        
    def update(self,delta,mouse_pos,mouse_btns):
        self.play_hand_btn.update(delta,mouse_pos,mouse_btns)
        # self.view_deck_btn.update(delta,mouse_pos,mouse_btns)
        self.sort_suit_btn.update(delta,mouse_pos,mouse_btns)
        self.sort_rank_btn.update(delta,mouse_pos,mouse_btns)
    def draw(self,group):
        group.add(self.play_hand_btn)
        # group.add(self.view_deck_btn)
        group.add(self.sort_rank_btn)
        group.add(self.sort_suit_btn)
