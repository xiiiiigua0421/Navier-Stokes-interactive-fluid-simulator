## 2025-02-28 - Dynamic State Labels and Colors
**Learning:** Pygame UIs can benefit greatly from context-aware instructions. Using fixed text like "Space: Pause" when the application is already paused causes friction. Also, changing text color based on state (e.g., orange for 'Paused', green for 'Running') provides an immediate visual queue without reading.
**Action:** Always verify if a toggle action's instructional text should dynamically reflect its *next* state, and use distinct colors to convey current system state.
