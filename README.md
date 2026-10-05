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
<<<<<<< HEAD
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

## High Scores

Each player's top 5 scores are saved to `scores/<username>.json` next to the game. They show on the game over screen. `users.json` and the `scores` folder are not tracked by git, so add them to `.gitignore`.

## Tests

`python3 -m unittest test_tetris_render test_tetris_auth`
=======
| Q | Quit after game over |


## High Scores

The top 5 scores are saved to `highscores.json` next to the game. They show on the game over screen. The file is not tracked by git.

## Tests

`python3 -m unittest test_tetris_render`
>>>>>>> origin/main

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
<<<<<<< HEAD
- User accounts (login, create account, per-player high scores)
=======


>>>>>>> origin/main
