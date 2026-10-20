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
| C | Hold the piece |
| Z | Rotate the other way |
| P or Esc | Pause / resume (the pause menu has **Resume**, **Restart**, **Quit**; R and Q also work while paused) |
| M | Turn sound on / off |
| T | Switch theme (light, dark, retro) |
| R | Restart after game over (or click **Restart**) |
| L | Sign out after game over (or click **Sign Out**) |
| Q | Quit after game over (or click **Quit**) |


## Accounts

The game opens on the **Sign In** page. Everything is done with the mouse:

- Click a box to type in it.
- Click **Show** / **Hide** next to a password to reveal or hide what you typed.
- Click **Sign In** to submit.
- Click **Create an account** to open the **Sign Up** page (username, password, confirm password). Click **Sign Up** to create the account and sign in. **Back to Sign In** returns to the first page.
- Click **Quit** to close the game.

Tab, the up and down arrows, and Enter also move between boxes and submit.

While playing, the **Sign Out** button in the bottom-right corner returns to the Sign In page (your current score is saved first). After a game over, the **Restart**, **Sign Out**, and **Quit** buttons appear.

- Usernames are 3-12 letters, numbers, or underscores, and are not case-sensitive.
- Passwords are 6-64 characters.
- Passwords are never stored. Each account keeps a random salt and a PBKDF2-HMAC-SHA256 hash, in `users.json` next to the game.
- Accounts are local to this computer. This keeps casual players out of each other's scores, but anyone with access to the files can delete or edit them, so it is not meant to protect anything sensitive.

## Gameplay Extras

- **Lock delay:** a landed piece stays movable for half a second. Moving or rotating it restarts the timer, up to 15 times, so a piece can't stall forever. Hard drop still locks instantly.
- **T-spins:** rotating a T piece into a tight spot (3 of the 4 corners around it blocked) scores a T-spin bonus, or a smaller mini T-spin.
- **Combos and back-to-back:** clearing lines on consecutive pieces adds combo points, and a Tetris or T-spin line clear right after another earns 1.5x.
- **Animations:** cleared rows flash before they drop, and a LEVEL UP! message appears when the level goes up.
- **Sound:** short effects for moving, rotating, holding, locking, clears, T-spins, level up, and game over. They are generated in code, so there are no audio files. If no audio device is found, the game stays silent.
- **Themes:** light, dark, and retro. Your theme and sound setting are saved per player in `settings/<username>.json`.
- **Game over stats:** pieces placed, lines cleared, level reached, and time played.

## High Scores

Each player's top 5 scores are saved to `scores/<username>.json` next to the game. They show on the game over screen. `users.json`, the `scores` folder, and the `settings` folder are not tracked by git, so add them to `.gitignore`.

## Tests

`python3 -m unittest test_tetris_render test_tetris_auth test_tetris_features`

# Feature Set

Core mechanics we need, plus the extras that make it feel great to play.

**MUST-HAVE / CORE**

- 7-bag piece randomizer
- Hold piece + next-piece queue
- SRS rotation system with wall kicks
- Soft drop and hard drop
- Line clears with rising difficulty/speed
- Pause menu and game-over screen (with stats)
- Local high-score leaderboard

**NICE-TO-HAVE / STRETCH**

- Ghost piece (done)
- T-spin detection and bonus scoring (done)
- Sound effects (done), background music (not yet)
- Mute toggle (done)
- Line-clear and level-up animations (done)
- Selectable board themes / skins (done)
- Combo and back-to-back bonuses (done)
- Lock delay (done)
- 2-player battle mode
- User accounts (login, create account, per-player high scores)
