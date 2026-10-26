## 2024-05-24 - Headless Pygame Cursor Crashes
**Learning:** Setting the Pygame system cursor using `pygame.mouse.set_cursor()` crashes with an ALSA lib error when running in a headless environment (like tests with `SDL_VIDEODRIVER=dummy`), even though the dummy driver is set for video, not audio.
**Action:** Always wrap `pygame.mouse.set_cursor()` calls in a `try...except pygame.error:` block to ensure headless tests pass without crashing.
