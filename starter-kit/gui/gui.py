import sys
import os


    
script_dir = os.path.dirname(os.path.abspath(__file__))

# Get the parent directory (the project root)
project_root = os.path.dirname(script_dir)

# Add project root to path to allow sibling imports (e.g., from bots)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Construct paths to the sibling directories
common_dir = os.path.join(project_root, 'stellatro-common')
game_dir = os.path.join(project_root, 'stellatro-game')

# Add the sibling directories to the Python path
if common_dir not in sys.path:
    sys.path.insert(0, common_dir)
if game_dir not in sys.path:
    sys.path.insert(0, game_dir)

import pygame
from stellatro_game.card import RANKS, Card
from card_sprite import CardSprite
from utils import get_assets_path, load_bot, get_hand_type, get_chips_by_rank
from stellatro_game.game import Game, Phase, PlayerTurn, HAND_SCORES
from stellatro_game.jokers import Joker
from button import ImageButton
from text import Text, FloatingText
from joker_sprites import JokerSprite, create_joker_sprite
from joker_container import JokerContainer
from player_gui import PlayerGUI
from flow_background import FlowBackground
from wind_effect import WindEffect
from tooltip import Tooltip
from phase_container import PhaseContainer
from game_over_container import GameOverContainer
import argparse
import multiprocessing
import queue
import csv
import os
import random
from datetime import datetime, UTC

def bot_worker(bot_path, request_queue, response_queue):
    """
    Dedicated process for a single bot to avoid GIL issues.
    """
    try:
        bot = load_bot(bot_path)
        while True:
            try:
                task, state = request_queue.get()
                if task == "QUIT":
                    break
                
                if task == "PICK_JOKER":
                    res = bot.pick_joker(state)
                    response_queue.put(res)
                elif task == "PICK_HAND":
                    if hasattr(bot, 'pick_hand'):
                        res = bot.pick_hand(state)
                    else:
                        res = bot.pick_play_hand(state)
                    response_queue.put(res)
            except EOFError:
                break
    except Exception as e:
        print(f"Bot worker error: {e}")

class BotManager:
    def __init__(self, bot_path):
        self.bot_path = bot_path
        self.request_queue = multiprocessing.Queue()
        self.response_queue = multiprocessing.Queue()
        self.process = multiprocessing.Process(
            target=bot_worker, 
            args=(self.bot_path, self.request_queue, self.response_queue),
            daemon=True
        )
        self.process.start()
        self.busy = False

    def request(self, task, state):
        self.request_queue.put((task, state))
        self.busy = True

    def get_result(self):
        try:
            res = self.response_queue.get_nowait()
            self.busy = False
            return res
        except queue.Empty:
            return None

def main():
    # 1. Setup
    pygame.init()
    screen = pygame.display.set_mode((1080, 720),pygame.SCALED)
    pygame.display.set_caption("Stellatro AI")
    clock = pygame.time.Clock()
    running = True

    #args
    parser = argparse.ArgumentParser(description="Stellatro AI")
    parser.add_argument('--p1', type=str, default=None,help="Path to Player 1 Bot (ignore if human)")
    parser.add_argument('--p2', type=str, default=None,help="Path to Player 2 Bot (ignore if human)")
    parser.add_argument('--game_speed', type=float, default=1.0, help="Game speed multiplier.")
    parser.add_argument('--report', action='store_true', help="Whether to report game results to a CSV file.")
    parser.add_argument('--no_bg', action='store_true', help="Disable the dynamic flowing background.")
    parser.add_argument('--autorestart', action='store_true', help="Immediately restart the game after it ends.")
    args = parser.parse_args()

    NAVY_BLUE = (255, 228, 196)  # Bisque fallback

    p1_manager = BotManager(args.p1) if args.p1 else None
    p1_bot_cards_to_play = []
    
    p2_manager = BotManager(args.p2) if args.p2 else None
    p2_bot_cards_to_play = []

    bot_delay = 0.5
    bot_timer = 0.0
    thinking_timer = 0.0
    reported = False

    # Session-based reporting setup
    session_time = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    report_root_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
    report_file = os.path.join(report_root_dir, f"session_{session_time}.csv")
    game_counter = 0


    # Dynamic Flowing Background
    flow_bg = FlowBackground(1080, 720)
    wind_effect = WindEffect(1080, 720)

    # Initialize status text - pushed up to 670
    font_path = get_assets_path("Jersey_10/Jersey10-Regular.ttf")
    bot_status_text = Text((1060, 670), "", 30, (50, 50, 50), font_path, align="right")

    # Large P1/P2 watermark labels centered in each half of the split screen
    watermark_font = pygame.font.Font(font_path, 220)
    p1_watermark = watermark_font.render("P1", True, (255, 255, 255))
    p1_watermark.set_alpha(120)
    p1_watermark_rect = p1_watermark.get_rect(center=(270, 330))
    p2_watermark = watermark_font.render("P2", True, (255, 255, 255))
    p2_watermark.set_alpha(120)
    p2_watermark_rect = p2_watermark.get_rect(center=(810, 330))

    def update_bot_status(text):
        bot_status_text.updateText(text)
        if args.no_bg:
            screen.fill(NAVY_BLUE)
        else:
            flow_bg.update(0)
            flow_bg.draw(screen)
            wind_effect.draw(screen)
        screen.blit(p1_watermark, p1_watermark_rect)
        screen.blit(p2_watermark, p2_watermark_rect)
        all_sprites.draw(screen)
        screen.blit(bot_status_text.image, bot_status_text.rect)
        pygame.display.update()

    def populate_bot_hand(game : Game, card_indices : list[int], is_p1 : bool) -> list[CardSprite]:
        """
        Determines which cards a bot wants to play and returns the corresponding
        CardSprite objects from the player's GUI hand.
        """
        if not card_indices:
            return []

        gui = p1_gui if is_p1 else p2_gui
        logical_hand = game.p1hand if is_p1 else game.p2hand
        
        sprites_to_play = []
        for idx in card_indices:
            found = False
            for sprite in gui.hand.sprites():
                if getattr(sprite, 'logical_index', -1) == idx:
                    sprites_to_play.append(sprite)
                    found = True
                    break
            if not found:
                 print(f"Warning: Could not find sprite for logical index {idx}")
        return sprites_to_play

    current_seed = random.randint(0, 2**31 - 1)
    game = Game(rng=random.Random(current_seed))
    game.start_round()

    background = pygame.Surface(screen.get_size())
    background = background.convert()
    background.fill("bisque")

    all_sprites = pygame.sprite.LayeredUpdates()
    tooltip = Tooltip()
    phase_container = PhaseContainer(pygame.math.Vector2(434,13),game)

    joker_pool = JokerContainer(
        x=291, y=203, width=500, height=265, padding_x=0, padding_y=0, max_columns=5, gap=8,
    )
    for joker in game.jokers:
        joker_pool.add(create_joker_sprite(joker))

    def on_select_joker(joker : JokerSprite, gui : PlayerGUI):
        joker_pool.remove(joker)
        joker.tooltip_offset = (-30,100)
        gui.jokers.add(joker)

    def clear_joker_pool():
        all_sprites.remove(phase_container.group.sprites())
        all_sprites.remove(joker_pool.sprites())
        if joker_pool.background_sprite:
            all_sprites.remove(joker_pool.background_sprite)
        joker_pool.empty()

    def get_rank_name(rank_value):
        if 2 <= rank_value <= 10: return str(rank_value)
        if rank_value == 11: return "Jack"
        if rank_value == 12: return "Queen"
        if rank_value == 13: return "King"
        if rank_value == 14: return "Ace"
        return ""

    def play_hand_p1(): p1_gui.play_hand()
    def sort_rank_p1(): p1_gui.hand.sort(all_sprites,by="rank")
    def sort_suit_p1(): p1_gui.hand.sort(all_sprites,by="suit")
    def play_hand_p2(): p2_gui.play_hand()
    def sort_rank_p2(): p2_gui.hand.sort(all_sprites,by="rank")
    def sort_suit_p2(): p2_gui.hand.sort(all_sprites,by="suit")

    p1_callbacks = {"play_hand": play_hand_p1, "view_deck": lambda: None, "sort_rank": sort_rank_p1, "sort_suit": sort_suit_p1}
    p1_gui = PlayerGUI(game,startPos=(0, 0), callbacks=p1_callbacks, is_p1=True)

    p2_callbacks = {"play_hand": play_hand_p2, "view_deck": lambda: None, "sort_rank": sort_rank_p2, "sort_suit": sort_suit_p2}
    p2_gui = PlayerGUI(game,startPos=(540, 0), callbacks=p2_callbacks, is_p1=False)

    def on_close():
        nonlocal running
        running = False

    def on_restart():
        nonlocal game, p1_gui, p2_gui, joker_pool, phase_container, p1_bot_cards_to_play, p2_bot_cards_to_play, reported, game_counter, current_seed
        reported = False
        game_counter += 1
        current_seed = random.randint(0, 2**31 - 1)
        game = Game(rng=random.Random(current_seed))
        game.start_round()
        game_over_container.seed = current_seed
        all_sprites.empty()
        phase_container = PhaseContainer(pygame.math.Vector2(434,13),game)
        joker_pool.empty()
        for joker in game.jokers:
            joker_pool.add(create_joker_sprite(joker))
        
        p1_gui = PlayerGUI(game,startPos=(0, 0), callbacks=p1_callbacks, is_p1=True)
        p2_gui = PlayerGUI(game,startPos=(540, 0), callbacks=p2_callbacks, is_p1=False)

        initial_state = game.get_game_state()
        for i, card in enumerate(initial_state.player1_hand):
            sprite = CardSprite(card)
            sprite.logical_index = i
            p1_gui.hand.add(sprite)
        for i, card in enumerate(initial_state.player2_hand):
            sprite = CardSprite(card)
            sprite.logical_index = i
            p2_gui.hand.add(sprite)
        
        p1_bot_cards_to_play = []
        p2_bot_cards_to_play = []

    game_over_container = GameOverContainer(pos=screen.get_rect().center, on_close=on_close, on_restart=on_restart)
    game_over_container.seed = current_seed

    initial_state = game.get_game_state()
    for i, card in enumerate(initial_state.player1_hand):
        sprite = CardSprite(card); sprite.logical_index = i; p1_gui.hand.add(sprite)
    for i, card in enumerate(initial_state.player2_hand):
        sprite = CardSprite(card); sprite.logical_index = i; p2_gui.hand.add(sprite)

    # 2. Main Game Loop
    while running:
        ImageButton.any_button_hovered = False
        delta = (clock.tick(60) / 1000.0) * args.game_speed
        mouse_pos = pygame.mouse.get_pos()
        mouse_btns = pygame.mouse.get_pressed()
        
        for card in reversed(p1_gui.hand.sprites()):
            if card.rect.collidepoint(mouse_pos): ImageButton.any_button_hovered = True
        for card in reversed(p2_gui.hand.sprites()):
            if card.rect.collidepoint(mouse_pos): ImageButton.any_button_hovered = True
        
        is_animating = p1_gui.is_playing_anim or p2_gui.is_playing_anim

        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if is_animating: continue

            if event.type == pygame.MOUSEBUTTONDOWN:
                if not p1_manager: p1_gui.handle_card_click(event.pos)
                if not p2_manager: p2_gui.handle_card_click(event.pos)
                
                if game.phase == Phase.DRAFT:
                    for joker in joker_pool.sprites():
                        if joker.rect.collidepoint(event.pos):
                            idx = game.jokers.index(joker)
                            if game.current_turn == PlayerTurn.PLAYER1 and not p1_manager:
                                on_select_joker(joker,p1_gui); game.step(1,idx)
                            elif game.current_turn == PlayerTurn.PLAYER2 and not p2_manager:
                                on_select_joker(joker,p2_gui); game.step(2,idx)
                            if game.phase == Phase.PLAY: clear_joker_pool()
            
            if not p1_manager: p1_gui.handle_events(event)
            if not p2_manager: p2_gui.handle_events(event)
            if game.phase == Phase.OVER: game_over_container.handle_events(event)
            
        if not args.no_bg:
            flow_bg.update(delta)
            wind_effect.update(delta)
        p1_gui.update(delta, game, mouse_pos, mouse_btns, all_sprites)
        p2_gui.update(delta, game, mouse_pos, mouse_btns, all_sprites)
        for sprite in all_sprites.sprites():
            if isinstance(sprite, FloatingText): sprite.update(delta)
        if game.phase == Phase.OVER:
            game_over_container.update(delta,game,mouse_pos,mouse_btns)
            
            if args.report and not reported:
                reported = True
                game_state = game.get_game_state()

                p1_score = game_state.player1_score
                p2_score = game_state.player2_score
                winner = "player1" if p1_score > p2_score else "player2" if p2_score > p1_score else "tie"
                p1_jokers = ";".join(j.name for j in game_state.player1_jokers)
                p2_jokers = ";".join(j.name for j in game_state.player2_jokers)

                row = {
                    "game": game_counter,
                    "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "player1_score": p1_score,
                    "player2_score": p2_score,
                    "winner": winner,
                    "player1_jokers": p1_jokers,
                    "player2_jokers": p2_jokers,
                }

                try:
                    os.makedirs(report_root_dir, exist_ok=True)
                    write_header = not os.path.exists(report_file)
                    with open(report_file, 'a', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=row.keys())
                        if write_header:
                            writer.writeheader()
                        writer.writerow(row)
                except Exception as e:
                    print(f"Error writing report file: {e}")
            
            if args.autorestart:
                # Add a small delay or check to ensure the user sees the final score?
                # For "immediately", we just call on_restart
                on_restart()

        hovered_sprite = None
        joker_sprites = list(joker_pool.sprites()) + list(p1_gui.jokers.sprites()) + list(p2_gui.jokers.sprites()) if game.phase == Phase.DRAFT else list(p1_gui.jokers.sprites()) + list(p2_gui.jokers.sprites())
        joker_pool.update(delta)
        phase_container.update(delta)

        for joker in joker_sprites:
            if joker.rect.collidepoint(mouse_pos):
                ImageButton.any_button_hovered = True; hovered_sprite = joker; break
        if not hovered_sprite:
            card_sprites = p1_gui.hand.sprites() + p2_gui.hand.sprites() + p1_gui.playing_hand.sprites() + p2_gui.playing_hand.sprites()
            for card in reversed(card_sprites):
                if card.rect.collidepoint(mouse_pos):
                    ImageButton.any_button_hovered = True; hovered_sprite = card; break

        if hovered_sprite:
            tooltip.update(delta)
            if isinstance(hovered_sprite, Joker):
                tooltip_pos = hovered_sprite.get_tooltip_pos()
                tooltip.displayTooltip(pygame.math.Vector2(tooltip_pos[0],tooltip_pos[1]),hovered_sprite.name,hovered_sprite.description, all_sprites)
                hovered_sprite.hover()
            elif isinstance(hovered_sprite, Card):
                tooltip_pos = hovered_sprite.get_tooltip_pos()
                header = f"{get_rank_name(hovered_sprite.rank)} of {hovered_sprite.initialSuit.capitalize()}s"
                description = f"+{get_chips_by_rank(hovered_sprite.rank)} chips"
                stella_count = getattr(hovered_sprite, "stella", 0) or 0
                if stella_count:
                    description += f" | {stella_count} stella"
                tooltip.displayTooltip(pygame.math.Vector2(tooltip_pos[0],tooltip_pos[1]), header, description, all_sprites)
        else:
            tooltip.hideTooltip()
            
        bot_timer += delta
        current_manager = p1_manager if game.current_turn == PlayerTurn.PLAYER1 else p2_manager
        
        if current_manager and current_manager.busy:
            thinking_timer += delta
            num_dots = int(thinking_timer * 3) % 4
            update_bot_status("Bot is thinking" + "." * num_dots)
            
            res = current_manager.get_result()
            if res is not None:
                if game.phase == Phase.DRAFT:
                    chosen_joker = game.jokers[res]
                    joker_sprite = next((s for s in joker_pool.sprites() if s == chosen_joker), None)
                    if joker_sprite:
                        gui = p1_gui if game.current_turn == PlayerTurn.PLAYER1 else p2_gui
                        on_select_joker(joker_sprite, gui); game.step(1 if game.current_turn == PlayerTurn.PLAYER1 else 2, res)
                    if game.phase == Phase.PLAY: clear_joker_pool()
                else:
                    if game.current_turn == PlayerTurn.PLAYER1:
                        p1_bot_cards_to_play = populate_bot_hand(game, res, True)
                    else:
                        p2_bot_cards_to_play = populate_bot_hand(game, res, False)
                update_bot_status("")
        elif not is_animating and bot_timer >= bot_delay:
            if game.phase == Phase.DRAFT and current_manager:
                current_manager.request("PICK_JOKER", game.get_game_state())
                thinking_timer = 0.0
            elif game.phase == Phase.PLAY:
                if game.current_turn == PlayerTurn.PLAYER1 and p1_manager:
                    if not p1_bot_cards_to_play and not p1_gui.selected_cards and not p1_gui.is_playing_anim:
                        p1_manager.request("PICK_HAND", game.get_game_state())
                        thinking_timer = 0.0
                    if p1_bot_cards_to_play: p1_gui.select_card(p1_bot_cards_to_play.pop(0))
                    elif not p1_gui.is_playing_anim and len(p1_gui.selected_cards) == 5: play_hand_p1()
                elif game.current_turn == PlayerTurn.PLAYER2 and p2_manager:
                    if not p2_bot_cards_to_play and not p2_gui.selected_cards and not p2_gui.is_playing_anim:
                        p2_manager.request("PICK_HAND", game.get_game_state())
                        thinking_timer = 0.0
                    if p2_bot_cards_to_play: p2_gui.select_card(p2_bot_cards_to_play.pop(0))
                    elif not p2_gui.is_playing_anim and len(p2_gui.selected_cards) == 5: play_hand_p2()
            bot_timer = 0.0

        if args.no_bg:
            screen.fill(NAVY_BLUE)
        else:
            flow_bg.draw(screen)
            wind_effect.draw(screen)
        screen.blit(p1_watermark, p1_watermark_rect)
        screen.blit(p2_watermark, p2_watermark_rect)
        p1_gui.draw(all_sprites); p2_gui.draw(all_sprites)
        if game.phase == Phase.DRAFT: phase_container.draw(all_sprites); joker_pool.draw(all_sprites)
        if game.phase == Phase.PLAY: pygame.draw.line(screen, (255,255,255), (540, 0), (540, 720),1)
        if game.phase == Phase.OVER: game_over_container.draw(all_sprites)
        screen.blit(bot_status_text.image, bot_status_text.rect)
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if ImageButton.any_button_hovered else pygame.SYSTEM_CURSOR_ARROW)
        all_sprites.draw(screen); pygame.display.update()

    pygame.quit()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
