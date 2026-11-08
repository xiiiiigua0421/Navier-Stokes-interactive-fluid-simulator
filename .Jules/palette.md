## 2025-02-28 - Pygame System Cursor Accessibility
**Learning:** Headless environments (like testing with SDL_VIDEODRIVER=dummy) crash if system cursors are set directly without error handling.
**Action:** Always wrap `pygame.mouse.set_cursor()` in a `try/except pygame.error` block to prevent crashes in headless/unsupported environments.