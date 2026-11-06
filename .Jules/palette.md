## 2024-11-06 - Pygame Headless Cursors
**Learning:** Pygame's `mouse.set_cursor` can crash in headless environments (e.g. dummy video driver) during testing.
**Action:** Always wrap `pygame.mouse.set_cursor` calls in a `try/except pygame.error` block to prevent crashes during CI/testing.