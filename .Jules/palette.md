## 2024-11-03 - Contextual Cursors in Simulation Apps
**Learning:** In applications with split interaction zones (e.g., a simulation area vs. a control panel), users lack visual cues about where interactions like drawing or panning are possible. A static cursor throughout the app can lead to clicks in unresponsive areas.
**Action:** Use contextual cursors (like a crosshair for the interactive area and an arrow for the UI panel) to visually separate functional zones and indicate interactivity, always wrapped in a try-except block to support headless environments.
