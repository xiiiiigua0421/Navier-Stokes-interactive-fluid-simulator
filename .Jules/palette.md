## 2024-05-20 - Pygame Cursor in Headless Environments
**Learning:** Pygame's cursor update function (`pygame.mouse.set_cursor`) can cause crashes in headless environments when using a dummy video driver.
**Action:** Always wrap `pygame.mouse.set_cursor` calls in a `try/except pygame.error` block to ensure stability across both interactive and headless testing environments.
