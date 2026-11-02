## 2024-05-24 - Contextual cursors in Pygame
**Learning:** Pygame headless mode crashes when setting cursors without a try/except block.
**Action:** Always wrap `pygame.mouse.set_cursor` in a `try/except pygame.error` block.
