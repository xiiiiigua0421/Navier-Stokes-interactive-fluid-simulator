## 2024-05-18 - Visual Area-of-Effect Feedback on Canvas Interactions
**Learning:** Interactive canvases using custom physics/brush tools lack native OS cursor feedback for size. Users can easily lose track of the action's area-of-effect scale when resizing grids.
**Action:** Always replace the standard OS cursor with a visual area-of-effect indicator (like a circle matching the brush radius) when hovering over canvas elements that rely on brush-based interactions.
