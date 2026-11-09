## 2025-02-12 - Pygame System Cursors in Headless Mode
**Learning:** Pygame's system cursor implementation (like `pygame.mouse.set_cursor`) fails and throws `pygame.error: Error while creating system cursor` when running headlessly with `SDL_VIDEODRIVER=dummy`.
**Action:** When setting system cursors in Pygame applications that will be tested headlessly, always wrap the `set_cursor` call in a `try/except pygame.error` block to prevent testing crashes.
