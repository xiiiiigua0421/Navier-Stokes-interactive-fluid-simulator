## 2024-05-18 - Crosshair Cursor for Interactive Simulation
**Learning:** Pygame provides system cursors. Using a crosshair over an interactive simulation area makes it much clearer to users that they can drag and drop/interact with the area compared to a standard arrow.
**Action:** Changed the cursor to `pygame.SYSTEM_CURSOR_CROSSHAIR` over the `VIEW_PIXELS` simulation area and `pygame.SYSTEM_CURSOR_ARROW` over the rest of the window in `main.py`.
