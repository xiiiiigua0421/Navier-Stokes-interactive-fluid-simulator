## 2024-05-23 - [Cursor State Tracking]
**Learning:** `pygame.mouse.get_cursor()` can fail or behave unpredictably in headless environments.
**Action:** When optimizing Pygame cursor updates to avoid redundant API calls, track the cursor state using a local Python variable instead of querying Pygame, and wrap `pygame.mouse.set_cursor` in a `try/except pygame.error` block to prevent crashes.