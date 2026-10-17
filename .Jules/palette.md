## 2024-05-18 - Spatial Cursor Feedback in Painting Apps
**Learning:** In interactive canvas/simulation applications, the default system cursor lacks spatial context regarding action radius. When drawing on a dynamically colored canvas, simple cursors are often lost against varying color backgrounds.
**Action:** Replace the system cursor with a dynamic spatial cursor (like a brush size indicator) over interactive canvas regions. Use a double-stroke (e.g., white inner, black outer) to guarantee visibility across any background color.
