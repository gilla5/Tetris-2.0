# Tetris 2.0: Test Plan

The four required test types, with the plan and files for each. All four are in place.

Run everything from the game folder:

```
pip install pygame
python3 -m unittest test_tetris_render test_tetris_auth test_tetris_features test_tetris_cloud test_tetris_extras test_tetris_regression test_tetris_acceptance
```

---

## Unit tests

**Plan/files:** test each rule and helper on its own, with no window and no network, so a failure points to one place.

| File | Tests | Covers |
|---|---|---|
| `test_tetris_auth.py` | 56 | Username and password rules, hashing, registering, signing in, file loading, score paths |
| `test_tetris_features.py` | 43 | Pause, stats, combos, back-to-back, level up, T-spins, lock delay, themes, settings, sound generation |
| `test_tetris_render.py` | 10 | Score file load and save, drawing helpers, ghost piece |
| `test_tetris_extras.py` | 23 | 3-piece next queue, row bombs, music tempo and state |
| `test_tetris_cloud.py` (first classes) | part of 27 | Score cleaning and merging, client setup rules |

**Pass when:** every test passes (`OK`).

---

## Integration tests

**Plan/files:** test that the parts work together: the real score server with the real client over HTTP, the game with the score files, and the play loop with fake key events.

| File | Covers |
|---|---|
| `test_tetris_cloud.py` | Server on a free port with the real client: keys, bad input, saving across a restart, merging local and cloud scores, game over sending the score to the server |
| `test_tetris_features.py` (`PlayLoopSmokeTest`) | Pause, theme, mute, game over, and restart through the real play loop |
| `test_tetris_extras.py` | B key reaching the bomb, music following game state |

**Pass when:** every test passes, including the ones that start the server.

---

## Regression tests

**Plan/files:** make sure changes don't quietly break what already works. `test_tetris_regression.py` has three parts.

| Part | What it does |
|---|---|
| **Golden values** | Locks the scoring tables, gravity curve, lock delay, bomb limits, account limits, and music tempo. Changing one on purpose means updating the test |
| **Past trouble spots** | Damaged files, usernames with path tricks, zero scores, double counting in sync, pause freezing everything, bombs on an empty floor, hold rules, unknown sounds, passwords never stored |
| **Random play** | 25 seeded random games of 1,500 moves each. After every move: the piece is in a valid spot, the score never drops, the queue has 3 pieces, bombs stay between 0 and 3, the level matches the lines cleared |

**When to run:** after every change, and before every push.
**Pass when:** all 23 tests pass. If a seeded game fails, the message shows its seed so it can be repeated.

---

## Acceptance tests

**Plan/files:** check that the game does what the requirements say, written as Given / When / Then stories from the player's point of view. `test_tetris_acceptance.py` has 20, named after requirements R1 to R10.

| Group | Stories |
|---|---|
| **Accounts (R1)** | New player signs up; returning player signs in; wrong password and unknown name give the same message; sign up explains what to fix; passwords are never written down |
| **Gameplay (R2 to R6, R8)** | Piece falls and can be steered; hard drop lands and the next piece appears; 3-piece preview and one hold per piece; a Tetris scores 800; 10 lines raise the level; a Tetris earns a bomb and the bomb clears rows; pause and resume; game over with stats |
| **Saved data (R8, R9)** | Each player keeps their own top 5; theme and sound are remembered per player |
| **Shared scores (R10)** | Scores follow a player to another computer; scores still save when the server is down |
| **Whole sessions** | Full game from first move to sign out; quitting from the pause menu keeps the score; signing out mid-game keeps the score |

**Manual sign-off (still to do):** the checklist in `TESTING.md` section 5 (functional, cloud, performance, compatibility, usability) with real people and real screens.
**Pass when:** all 20 automated stories pass and the manual checklist is signed off.

---

## Results Log

| Date | Tester | Unit | Integration | Regression | Acceptance | Notes |
|---|---|---|---|---|---|---|
| | | | | | | |
