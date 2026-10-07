## 2024-10-07 - Add Paused State Overlay
**Learning:** Pygame state indicators (like "paused") can be easily missed if they only rely on a small text update in a side panel. Users may be confused why their interactions or the fluid simulation stop working. Adding a semi-transparent overlay clearly separates active and paused states.
**Action:** Always provide strong visual feedback (like overlays or large central text) for modal states (like paused) that disable normal interactions.
