## 2024-05-24 - Context-Aware Mouse Cursor
**Learning:** In Pygame applications with split interactive/UI areas, users may not realize which areas are interactive if the cursor remains static. Headless test environments (like `SDL_VIDEODRIVER=dummy`) often fail to set cursors and throw `pygame.error`, requiring try/except blocks.
**Action:** When implementing context-aware cursors (e.g. crosshair for drawing areas, arrow for panels), always wrap `pygame.mouse.set_cursor` in a `try/except pygame.error` block to ensure stability across environments.
