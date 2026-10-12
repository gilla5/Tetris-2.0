# Tetris-2.0 - Core Engine & Rules
============================

## Controls

| Key | Action |
|---|---|
| ↑ Up Arrow | Rotate the piece |
| ← Left Arrow | Move left |
| → Right Arrow | Move right |
| ↓ Down Arrow | Move down faster |
| Spacebar | Drop the piece instantly |
| Z | Rotate the other way |
| C | Hold the piece |
| T | Change the board theme (Classic, Dark, Pastel, Retro) |
| P or Esc | Pause and resume |
| R | Restart (when paused or after game over) |
| Q | Quit (when paused or after game over) |


## High Scores

The top 5 scores are saved to `highscores.json` next to the game. They show on the game over screen. The file is not tracked by git.

## Animations

Full rows blink and wipe out from the middle for 0.4 seconds before they are removed (the game waits during that time). The score is added when the rows are gone. A 'LEVEL n' banner fades out after each level up.

## Tests

`python3 -m unittest test_tetris_render`

# Feature Set

Core mechanics we need, plus the extras that make it feel great to play.

**MUST-HAVE / CORE**

- 7-bag piece randomizer
- Hold piece + next-piece queue
- SRS rotation system with wall kicks
- Soft drop and hard drop
- Line clears with rising difficulty/speed
- Pause menu and game-over screen
- Local high-score leaderboard

**NICE-TO-HAVE / STRETCH**

- Ghost piece
- T-spin detection and bonus scoring
- Sound effects + background music
- Mute toggle
- Line-clear and level-up animations
- Selectable board themes / skins
- 2-player battle mode


