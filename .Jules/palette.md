## 2024-11-07 - Cursor Feedback for Interactive Canvas
**Learning:** Pygame's `set_cursor` method throws an exception in headless environments (like tests or CI using dummy video drivers). We must always wrap UI/cursor updates in `try/except pygame.error` to avoid crashes.
**Action:** Always wrap `pygame.mouse.set_cursor` with `try/except pygame.error` for robustness.