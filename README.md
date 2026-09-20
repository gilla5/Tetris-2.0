# Tetris-2.0 - Core Engine & Rules
============================

Covers the four engine responsibilities:
  1. Game loop, timing, and the 10x20 board grid
  2. Piece spawning, movement, and collision
  3. SRS-style rotation system with wall kicks
  4. Line-clear detection, scoring rules & level-speed curve

This is a refactor of tetris_ver2.py's approach: no module-level mutable
game state, no magic numbers, and named data structures instead of
index-encoded lists, per the code-smell notes left in that file.

Controls:
  Left / Right   move
  Up             rotate clockwise
  Z              rotate counter-clockwise
  Down           soft drop (hold)
  Space          hard drop
  C              hold piece
  R              restart after game over
  Q              quit after game over

