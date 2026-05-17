import pygame

class ImageButton(pygame.sprite.Sprite):
    any_button_hovered = False
    def __init__(self, pos, normal_path, hover_path, active_path,disabled_surf, scale=1.0, topleft_aligned=True, action=None, action_args=None,enabled= True):
        """
        Loads unique assets for normal, hover, and active states.
        """
        super().__init__()
        
        self.action = action
        self.action_args = action_args
        self.scale = scale
        self.enabled = enabled

        # 1. Load and Scale all three states
        self.normal_surf = self._load_and_scale(normal_path)
        self.hover_surf = self._load_and_scale(hover_path)
        self.active_surf = self._load_and_scale(active_path)
        self.disabled_surf = self._load_and_scale(disabled_surf)
        

        # 2. Sprite Setup
        self.image = self.normal_surf if self.enabled else self.disabled_surf
        
        if topleft_aligned:
            self.rect = self.image.get_rect(topleft=pos)
        else:
            self.rect = self.image.get_rect(center=pos)

    def _load_and_scale(self, path):
        """Helper to load and scale surfaces consistently."""
        img = pygame.image.load(path).convert_alpha()
        if self.scale != 1.0:
            new_size = (int(img.get_width() * self.scale), int(img.get_height() * self.scale))
            return pygame.transform.smoothscale(img, new_size)
        return img

    def update(self, delta, mouse_pos, mouse_btns):
        """Swaps the image based on mouse state."""
        if not self.enabled:
            self.image = self.disabled_surf
            return
        is_hovering = self.rect.collidepoint(mouse_pos)
        left_mouse_held = mouse_btns[0]

        if is_hovering:
            ImageButton.any_button_hovered = True
            # Order matters: Active (clicking) takes priority over Hover
            self.image = self.active_surf if left_mouse_held else self.hover_surf
        else:
            self.image = self.normal_surf

    def handle_event(self, event):
        """Processes the event and triggers the callback if clicked."""
        if not self.enabled:
            return
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.trigger_action()

    def trigger_action(self):
        """Executes the assigned callback function."""
        if self.action:
            if self.action_args:
                self.action(*self.action_args)
            else:
                self.action()