import pygame
from player_info import PlayerInfo
from card_hand_container import CardHandContainer
from player_btn_container import PlayerButtonContainer
from utils import get_assets_path, get_hand_type, format_number
from stellatro_game.checker import Checker, HandType
from stellatro_game.game import HAND_SCORES, Game, Phase, PlayerTurn
from stellatro_game.card import rank_to_score
from text import FloatingText

from collections import Counter

class PlayerGUI:
    def __init__(self, game : Game,startPos=(0, 0), callbacks=None, is_p1=True):
        """
        Initializes the GUI components for a player.
        :param startPos: The (x, y) offset for the player's UI section.
        :param callbacks: A dictionary containing function references for button actions.
        """
        self.startPos = pygame.Vector2(startPos)
        self.selected_cards = []
        self.chips = 0
        self.total_score = 0
        self.game = game
        self.isP1 = is_p1
        self.mult = 0
        
        # Default callbacks if none provided to avoid errors
        if callbacks is None:
            callbacks = {
                "play_hand": lambda: print("Play Hand pressed"),
                "view_deck": lambda: print("View Deck pressed"),
                "sort_rank": lambda: print("Sort Rank pressed"),
                "sort_suit": lambda: print("Sort Suit pressed")
            }

        # 1. Player Info (Chips, Mult, Hand Type display)
        self.player_info = PlayerInfo(
            (self.startPos.x + 12, 
            self.startPos.y + 12)
        )

        # 2. Joker Container (Top area for active jokers)
        joker_start_pos_x = self.startPos.x + 12 if is_p1 else self.startPos.x + 207
        self.jokers = CardHandContainer(
            x=joker_start_pos_x, 
            y=self.startPos.y + 12, 
            width=321, 
            height=97, 
            bg_path=get_assets_path("UI/JokerContainer.png"),
            padding_x=12,
            padding_y=15,
            gap=2,
        )
        
        self.joker_container_draft_pos = pygame.Vector2(self.startPos.x+ 12,self.startPos.y+12)#only for p1
        self.joker_container_play_pos = pygame.Vector2(self.startPos.x+ 207,self.startPos.y+12)

        # 3. Card Hand Container (The player's playable cards)
        self.hand = CardHandContainer(
            x=self.startPos.x + 30, 
            y=self.startPos.y + 500, 
            width=481, 
            height=111, 
            bg_path=get_assets_path("UI/CardHandContainer.png"),
            padding_x=8,
            padding_y=15,
            gap=2
        )
        self.playing_hand = CardHandContainer(
            x=self.startPos.x + 88, 
            y=self.startPos.y + 358, 
            width=346, 
            height=101,
            padding_x=20,
            padding_y=20,
            gap=2,
        )

        # 4. Player Button Container (Action buttons)
        self.buttons = PlayerButtonContainer(
            play_hand_action=callbacks["play_hand"],
            view_deck_action=callbacks["view_deck"],
            sort_rank_action=callbacks["sort_rank"],
            sort_suit_action=callbacks["sort_suit"],
            startPos=(self.startPos.x + 43, self.startPos.y + 620),
            isP1=is_p1
        )
        self.is_playing_anim = False
        self.anim_timer = 0
        self.anim_card_idx = 0
        self.anim_joker_idx = 0
        self.anim_step = 'initial-wait'
        self.cards_to_play = []
        self.anim_chips = 0
        self.anim_mult = 0
        self.hand_indices_to_play = None

    
    def play_hand(self):
        if len(self.selected_cards) != 5:
            print("Must have 5 cards to play!")
            return None
        
        cards_to_play_sprites = self.selected_cards[:]
        
        # Prepare logical hand for evaluation
        # We need to make sure we use the same trigger count logic as the game
        for card in cards_to_play_sprites:
            card.scored = False
            card.num_triggers = 1 # Reset to default
            self.hand.remove(card) 
            self.playing_hand.add(card)
            card.selected = False

        # Apply pre-phase jokers to the sprites (which are Cards)
        # Note: some jokers might change rank or add triggers
        temp_hand = cards_to_play_sprites[:]
        for joker in self.jokers.sprites():
            temp_hand = joker.pre_card_phase(temp_hand)
            
        checker = Checker(temp_hand) 
        hand_type = checker.check()
        if any(joker.scores_all_cards() for joker in self.jokers.sprites()):
            for card in temp_hand:
                card.scored = True

        # For High Card hands, we'll manually mark the highest card as scored for animation 
        # IF nothing else was marked scored.
        if hand_type == HandType.HIGH_CARD:
            if not any(c.scored for c in temp_hand):
                highest_card = max(temp_hand, key=lambda c: c.rank)
                highest_card.scored = True
        
        # Calculate expected base score
        self.anim_chips, self.anim_mult = HAND_SCORES.get(hand_type, (0, 0))
        
        # Start animation
        self.is_playing_anim = True
        self.anim_timer = 0.0
        self.anim_card_idx = 0
        self.anim_trigger_idx = 0
        self.anim_joker_idx = 0
        self.anim_step = 'initial-wait'
        self.cards_to_play = temp_hand
        
        self.selected_cards.clear()
        
        # Prepare hand indices for game logic step later
        self.hand_indices_to_play = [card.logical_index for card in cards_to_play_sprites]
        
        # Calculate expected final score using deepcopy to avoid mutating current state
        from copy import deepcopy
        temp_game = deepcopy(self.game)
        player_num = 1 if self.isP1 else 2
        success, game_state = temp_game.step(player_num, None, self.hand_indices_to_play)
        
        if success:
            self.expected_total_score = game_state.player1_score if self.isP1 else game_state.player2_score
        else:
            print("Warning: Game logic dry-run failed!")
            self.expected_total_score = self.total_score

        return None

    def select_card(self, card):
        changed = False
        if card in self.selected_cards:
            self.selected_cards.remove(card)
            card.toggle_selection()
            changed = True
        elif len(self.selected_cards) < 5:
            self.selected_cards.append(card)
            card.toggle_selection()
            changed = True
        
        if changed:
            if len(self.selected_cards) == 0:
                self.chips = 0
                self.mult = 0
                self.player_info.update(0, 0, None, "")
            else:
                hand_type = get_hand_type(self.selected_cards)
                chips, mult = HAND_SCORES[hand_type]
                self.chips = chips
                self.mult = mult
                self.player_info.update(chips, mult, None, hand_type)
        return changed
        
    def handle_card_click(self, mouse_pos):
        for card in reversed(self.hand.sprites()):
            if card.rect.collidepoint(mouse_pos):
                self.select_card(card)
                break

    def handle_events(self, event):
        self.buttons.handle_events(event)

    def draw(self, group):
        """Draws all player GUI elements to the screen."""
        if self.game.phase == Phase.PLAY:
            self.player_info.draw(group)
        self.jokers.draw(group)
        self.hand.draw(group)
        self.playing_hand.draw(group)
        self.buttons.draw(group)

    def update(self, delta, game: Game, mouse_pos, mouse_btns, group):
        """Updates animations or states for GUI components."""
        self.hand.update(delta)
        self.playing_hand.update(delta)
        
        if self.game.phase == Phase.DRAFT and self.isP1:
            self.jokers.target_pos = self.joker_container_draft_pos
        elif self.game.phase == Phase.PLAY:
            self.jokers.target_pos = self.joker_container_play_pos
        self.jokers.update(delta)
        
        canPlay = game.phase == Phase.PLAY and (self.isP1 and game.current_turn == PlayerTurn.PLAYER1 or not self.isP1 and game.current_turn == PlayerTurn.PLAYER2)
        self.buttons.play_hand_btn.enabled = (len(self.selected_cards) == 5) and canPlay
        self.buttons.update(delta, mouse_pos, mouse_btns)
        
        # animation update
        if self.is_playing_anim:
            self.anim_timer += delta
            
            if self.anim_timer >= 0.4 and self.anim_step == 'initial-wait':
                self.anim_timer = 0
                self.anim_joker_idx = 0
                self.anim_step = 'base-score'

            elif self.anim_step == 'base-score':
                self.player_info.update(self.anim_chips, self.anim_mult, None, None)
                font_url = get_assets_path("Jersey_10/Jersey10-Regular.ttf")
                group.add(FloatingText(self.player_info.bg.rect.midtop, f"+{format_number(self.anim_chips)} Chips", 30, (255, 150, 180), font_url))
                group.add(FloatingText(self.player_info.bg.rect.midtop, f"+{format_number(self.anim_mult)} Mult", 30, (180, 100, 220), font_url))

                self.anim_timer = 0.0
                self.anim_card_idx = 0
                self.anim_trigger_idx = 0
                self.anim_step = 'select'
                while self.anim_card_idx < len(self.cards_to_play) and not self.cards_to_play[self.anim_card_idx].scored:
                    self.anim_card_idx += 1

            elif self.anim_timer >= 0.15 and self.anim_step == 'select':
                if self.anim_card_idx < len(self.cards_to_play):
                    card = self.cards_to_play[self.anim_card_idx]
                    added_chips = rank_to_score(card.rank)
                    self.anim_chips += added_chips
                    self.player_info.update(self.anim_chips, self.anim_mult, None, None)
                    card.selected = True
                    
                    font_url = get_assets_path("Jersey_10/Jersey10-Regular.ttf")
                    group.add(FloatingText(card.rect.midtop, f"+{format_number(added_chips)}", 30, (255, 150, 180), font_url))

                    self.anim_timer = 0.0
                    self.anim_joker_idx = 0
                    self.anim_step = 'apply-card-joker'
                else:
                    self.anim_timer = 0.0
                    self.anim_joker_idx = 0
                    self.anim_step = 'post-phase'

            elif self.anim_step == 'apply-card-joker':
                if self.anim_timer >= 0.15:
                    if self.anim_joker_idx < len(self.jokers.sprites()):
                        joker = self.jokers.sprites()[self.anim_joker_idx]
                        old_chips, old_mult = self.anim_chips, self.anim_mult
                        
                        card = self.cards_to_play[self.anim_card_idx]
                        self.anim_chips, self.anim_mult = joker.apply_card_phase(
                            self.anim_chips, self.anim_mult, card.rank, next(iter(card.suits)), card.stella
                        )
                        
                        if old_chips != self.anim_chips or old_mult != self.anim_mult:
                            self.player_info.update(self.anim_chips, self.anim_mult, None, None)
                            joker.shake()
                            font_url = get_assets_path("Jersey_10/Jersey10-Regular.ttf")
                            if self.anim_chips > old_chips:
                                group.add(FloatingText(joker.rect.midbottom, f"+{format_number(self.anim_chips - old_chips)} Chips", 30, (255, 150, 180), font_url, alignment="top"))
                            if self.anim_mult > old_mult:
                                group.add(FloatingText(joker.rect.midbottom, f"+{format_number(self.anim_mult - old_mult)} Mult", 30, (180, 100, 220), font_url, alignment="top"))

                            self.anim_timer = 0.0
                        self.anim_joker_idx += 1
                    else:
                        self.anim_timer = 0.0
                        self.anim_step = 'check-retrigger'

            elif self.anim_step == 'check-retrigger':
                card = self.cards_to_play[self.anim_card_idx]
                self.anim_trigger_idx += 1
                if self.anim_trigger_idx < card.num_triggers:
                    # Trigger again!
                    self.anim_joker_idx = 0
                    self.anim_step = 'select' # Go back to select to show chips adding again
                else:
                    self.anim_timer = 0.0
                    self.anim_step = 'deselect'

            elif self.anim_timer >= 0.1 and self.anim_step == 'deselect':
                self.cards_to_play[self.anim_card_idx].selected = False
                self.anim_timer = 0.0
                self.anim_card_idx += 1
                self.anim_trigger_idx = 0
                while self.anim_card_idx < len(self.cards_to_play) and not self.cards_to_play[self.anim_card_idx].scored:
                    self.anim_card_idx += 1
                self.anim_step = 'select'

            elif self.anim_step == 'post-phase':
                if self.anim_timer >= 0.15:
                    if self.anim_joker_idx < len(self.jokers.sprites()):
                        joker = self.jokers.sprites()[self.anim_joker_idx]
                        old_chips, old_mult = self.anim_chips, self.anim_mult
                        
                        self.anim_chips, self.anim_mult = joker.post_card_phase(
                            self.anim_chips, self.anim_mult, self.cards_to_play
                        )
                        
                        if old_chips != self.anim_chips or old_mult != self.anim_mult:
                            self.player_info.update(self.anim_chips, self.anim_mult, None, None)
                            joker.shake()
                            font_url = get_assets_path("Jersey_10/Jersey10-Regular.ttf")
                            if self.anim_chips > old_chips:
                                group.add(FloatingText(joker.rect.midbottom, f"+{format_number(self.anim_chips - old_chips)} Chips", 30, (255, 150, 180), font_url, alignment="top"))
                            if self.anim_mult > old_mult:
                                group.add(FloatingText(joker.rect.midbottom, f"+{format_number(self.anim_mult - old_mult)} Mult", 30, (180, 100, 220), font_url, alignment="top"))
                            self.anim_timer = 0.0
                        self.anim_joker_idx += 1
                    else:
                        self.anim_timer = 0.0
                        self.anim_step = 'remove'

            elif self.anim_timer >= 0.3 and self.anim_step == 'remove':
                # Execute the actual game logic step now that animations are done
                player_num = 1 if self.isP1 else 2
                self.game.step(player_num, None, self.hand_indices_to_play)
                self.hand_indices_to_play = None

                # Final synchronization with the actual game score
                self.total_score = self.expected_total_score
                self.player_info.update(0, 0, self.total_score, "")

                group.remove(self.playing_hand.sprites())
                self.playing_hand.empty()
                self.is_playing_anim = False
