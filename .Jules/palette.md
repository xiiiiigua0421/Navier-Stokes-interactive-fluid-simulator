## 2024-10-25 - [Pygame Cursor in Headless Environment]
**Learning:** Setting the Pygame cursor (`pygame.mouse.set_cursor`) crashes with a `pygame.error` when running in a headless environment (like when `SDL_VIDEODRIVER=dummy` is used).
**Action:** Always wrap `pygame.mouse.set_cursor` calls in a `try/except pygame.error` block to ensure tests don't fail when checking UI/UX changes that involve the mouse cursor.
