# Tetris 2.0: Software Design

This document explains how the game is designed inside: its goals, its parts, the main data structures and algorithms, and the reasons behind the main choices. For the big-picture view (components, runtime flow, deployment), see `ARCHITECTURE.md`. For how to play, see `Tetris_User_Manual.md`.

---

## 1. Goals and Scope

**What the software is:** a single-player Tetris clone for the desktop, written in Python with pygame, with local player accounts, per-player high scores and settings, and optional high score sync through a small self-hosted server.

**Design goals**

| Goal | What it means in the code |
|---|---|
| **Playable and correct** | Follows the standard Tetris rules: 7-bag, SRS rotation with wall kicks, lock delay, T-spins, combos, back-to-back |
| **Testable** | Game rules, accounts, scoring, and sync live in plain classes and functions that run without a window |
| **Safe by default** | Passwords are hashed, files are validated on load, the network is optional and never blocks play for long |
| **Easy to tune** | Every rule number (scoring, speed, lock delay, bomb limits, music tempo) is a named constant |
| **Easy to run** | One game file, one optional server file, standard library plus pygame only |

**Out of scope (for now):** 2-player battle mode, online accounts, a public hosted score service, and a rebindable-key menu.

---

## 2. Requirements Summary

**Functional**

1. Players create accounts, sign in, and sign out with the mouse and keyboard.
2. The game deals pieces from a 7-bag and shows a hold box and the next 3 pieces.
3. Pieces move, rotate (SRS with wall kicks), soft drop, hard drop, and lock after a delay.
4. Completed rows clear, score points, and raise the level every 10 lines.
5. T-spins, combos, and back-to-back clears earn bonus points.
6. A Tetris or T-spin line clear earns a row bomb (max 3); pressing B blasts the bottom 2 rows.
7. The game plays sound effects and looping music that speeds up with the level, and can be muted.
8. Players can pause, restart, quit, and sign out. Three themes are available.
9. Each player's top 5 scores and settings are saved locally.
10. Scores can optionally be merged with a score server through a small JSON API.

**Non-functional**

| Quality | Target |
|---|---|
| Performance | 60 frames per second on an ordinary laptop |
| Reliability | A damaged or missing data file never crashes the game; it falls back to defaults |
| Security | No plain-text passwords; usernames and file contents are validated; the server checks every request |
| Availability | The game works fully offline. The network is only used when cloud sync is turned on |
| Maintainability | Automated tests for rules, accounts, sync, bombs, and music |

---

## 3. Design Overview

The code follows one rule: **keep game logic separate from drawing and input.**

```
 Input events ──► play loop ──► Game (rules, no drawing) ──► events ──► SoundBank / Music
                      │                     │
                      │                     └──► state read by draw_* functions
                      └──► save/load functions (JSON files) ──► optional CloudSync ──► score server
```

- The **Game** object holds all the rules and state. It has no idea how it is drawn.
- **draw_\*** functions only read the state and paint it.
- The **play loop** turns key and mouse events into Game actions, advances time, plays sounds, and draws.
- Game rules talk to sound through a simple **event list** (`game.events`), not by calling the audio code.

Because of this split, almost all rules can be tested by calling methods directly, with no window.

---

## 4. Module Breakdown

### 4.1 `tetris_ver2.py` (the game)

The file is organized in labeled sections, top to bottom:

| Section | Contents |
|---|---|
| **Constants** | Board size, window layout, colors, file paths, limits |
| **Themes** | `THEMES`, `apply_theme`, `next_theme` |
| **Piece data** | `PIECE_SHAPES`, rotation states, SRS wall kick tables |
| **Rules constants** | Scoring tables, lock delay, bomb limits, `gravity_interval` |
| **Core classes** | `Piece`, `Board`, `SevenBag`, `Game` |
| **Sound** | `SOUND_NOTES`, `synth`, `SoundBank` |
| **Music** | `music_speed`, `music_notes`, `Music` |
| **Settings** | `settings_path`, `load_settings`, `save_settings` |
| **Drawing** | `draw_*` functions for cells, board, panels, effects, menus |
| **Scores** | `load_scores`, `save_score`, `write_scores`, `sync_scores` |
| **Accounts** | `register_user`, `authenticate`, `LoginScreen`, login layout |
| **Screens and loop** | `run_login`, `play`, `_play`, `main` |

### 4.2 `cloud_sync.py` (client, no pygame)

Score list rules (`clean_scores`, `merge_scores`) and the `CloudSync` client class.

### 4.3 `cloud_server.py` (server, standard library only)

`ScoreStore` (JSON file storage), `Handler` (HTTP request handling), `make_server`, and a command line `main`.

### 4.4 Tests

| File | Covers |
|---|---|
| `test_tetris_render.py` | Score file functions, drawing helpers, ghost piece |
| `test_tetris_auth.py` | Accounts, hashing, sign in and sign up screens |
| `test_tetris_features.py` | Pause, stats, combos, back-to-back, T-spins, lock delay, effects, themes, settings, sound, layout, a scripted play session |
| `test_tetris_cloud.py` | Score merging, the HTTP server, the client, game integration |
| `test_tetris_extras.py` | Next queue, row bombs, music |

---

## 5. Class Design

### 5.1 `Piece`

One falling tetromino: `kind` (I, O, T, S, Z, J, L), `rotation` (0 to 3), and its `row` and `col`. `cells()` returns the absolute board cells it covers. A piece has no knowledge of the board; the board and game decide if a position is allowed.

### 5.2 `Board`

Owns the 10 x 20 grid of locked cells (each cell is `None` or the kind letter that was locked there).

| Method | Responsibility |
|---|---|
| `is_valid(cells)` | True if every cell is inside the walls and floor and not already filled. Rows above the top are allowed so pieces can spawn partly off the top |
| `lock(piece)` | Writes the piece into the grid |
| `clear_lines()` | Removes full rows, drops the rest, returns how many were cleared |

### 5.3 `SevenBag`

The randomizer. When its bag is empty it refills with the 7 piece kinds and shuffles. `next_piece()` pops one. Every bag contains each kind exactly once.

### 5.4 `Game`

The rules engine. It ties together `Board`, `SevenBag`, the active piece, the hold slot, the next queue, scoring, and timers.

**Key state**

| Field | Meaning |
|---|---|
| `state` | `"playing"`, `"paused"`, or `"gameover"` |
| `score`, `level`, `lines_cleared` | Progress |
| `piece`, `hold_kind`, `can_hold`, `next_queue` | Pieces in play |
| `combo`, `back_to_back`, `bombs` | Bonus tracking |
| `elapsed`, `pieces_placed` | Stats shown at game over |
| `events` | Names of things that happened this frame, for the sound code |
| `message_lines`, `message_timer`, `level_up_timer`, `clear_anim` | Short-lived visual effects |

**Actions the input layer drives:** `move`, `rotate`, `soft_drop`, `hard_drop`, `hold`, `use_bomb`, `toggle_pause`.

**Time:** `update(dt)` advances gravity, the lock delay, and the effect timers.

**Internal helpers:** `_spawn_piece`, `_refill_queue`, `_grounded`, `_restart_lock_delay`, `_t_spin_kind`, `_lock_active_piece`, `_announce`, `_tick_effects`.

### 5.5 `SoundBank` and `Music`

`SoundBank` turns the `SOUND_NOTES` table into short sounds at start-up with `synth()` and plays them by name. It ignores unknown names and works silently if no audio device exists. `Music` builds a looping melody per tempo level and keeps it in step with the game (see 6.9).

### 5.6 `LoginScreen`

Holds the state of the Sign In and Sign Up pages (mode, field values, active field, message, signed-in user) and handles keys, clicks, and submit. Drawing is separate (`draw_login`), so the screen's behavior can be tested without a window.

### 5.7 `CloudSync` (client) and `ScoreStore` / `Handler` (server)

`CloudSync` wraps the HTTP calls and returns `None` on any failure. `ScoreStore` keeps all players' scores in one JSON file with a lock and atomic saves. `Handler` checks the key, the path, and the body, then calls the store.

---

## 6. Key Algorithms and Rules

### 6.1 Piece rotation (SRS with wall kicks)

Each piece's four rotation states are built once from the base shape by rotating the cell grid clockwise. When a rotation is blocked, the game tries the standard SRS offset list for that rotation (one table for J, L, S, T, Z and another for I). The first offset that fits is used, and its index is remembered as `_last_kick` (a "kick 4" rotation counts toward a full T-spin).

### 6.2 7-bag randomizer

See 5.3. It guarantees at most 12 pieces between two of the same kind and removes long droughts.

### 6.3 Gravity

```
seconds_per_row = max(0.05, (0.8 - (level - 1) * 0.007) ** (level - 1))
```

This follows the classic Guideline curve: about 1.0 s at level 1, 0.36 s at level 5, 0.06 s at level 10, never faster than 0.05 s.

### 6.4 Lock delay

When the active piece cannot move down (`_grounded`), `update` adds `dt` to a lock timer. At `LOCK_DELAY` (0.5 s) the piece locks. A successful move or rotation while grounded restarts the timer, up to `MAX_LOCK_RESETS` (15) times per piece. Hard drop locks at once.

### 6.5 Scoring

| Item | Points |
|---|---|
| Single / Double / Triple / Tetris | 100 / 300 / 500 / 800 x level |
| Soft drop / hard drop | 1 / 2 per row |
| T-spin (0 to 3 lines) | 400 / 800 / 1,200 / 1,600 x level |
| Mini T-spin (0 to 2 lines) | 100 / 200 / 400 x level |
| Combo | 50 x combo step x level |
| Back-to-back | 1.5x on a difficult clear that follows a difficult clear |
| Row bomb | 50 x blasted rows with blocks x level |

Level goes up every `LINES_PER_LEVEL` (10) lines.

### 6.6 T-spin detection

On lock, if the piece is a T and the last action was a rotation, the game counts blocked corners around its center (walls and floor count as blocked). Three or more blocked corners is a T-spin. It is **full** if both corners on the pointed side are blocked or the last kick was the long one; otherwise it is **mini**. Moving after rotating clears the "rotated last" flag.

### 6.7 Combos and back-to-back

`combo` starts at -1. Each lock that clears lines adds 1 and awards bonus points when it is 1 or more; a lock with no clear resets it to -1. A Tetris or T-spin clear is "difficult": if `back_to_back` is already set, the points are multiplied by 1.5; an ordinary clear turns the flag off; a lock with no clear leaves it alone.

### 6.8 Row bombs

`_lock_active_piece` adds one bomb (up to `MAX_BOMBS`) after a Tetris or T-spin line clear. `use_bomb` requires the playing state, at least one bomb, and at least one filled cell in the bottom `BOMB_ROWS` rows. It replaces the grid with `BOMB_ROWS` empty rows on top of the rows that were above the blasted ones, so the stack falls down.

### 6.9 Music

`music_speed(level)` is `1 + 0.08 x (min(level, 10) - 1)`. `music_notes(level)` scales each note's length by that speed. `Music.update(level, state, muted)` runs each frame:

| Condition | Action |
|---|---|
| muted or game over | stop |
| paused | pause the channel |
| new level tempo or nothing playing | build the loop for that tempo if needed (cached), start it looping |
| otherwise | resume |

### 6.10 Score merging

`merge_scores(a, b)` takes the **maximum count** of each score value across the two lists, sorts high to low, and keeps the top 5. Using the maximum, not the sum, makes syncing repeatable: syncing the same scores twice changes nothing.

---

## 7. Data Design

All data is JSON, stored next to the game.

| File | Shape | Written by |
|---|---|---|
| `users.json` | `{ "username_lowercase": { "name": "...", "salt": "hex", "hash": "hex", "iterations": 600000 } }` | `register_user` |
| `scores/<user>.json` | `[900, 500, 300, 200, 100]` (top 5, high to low) | `save_score`, `write_scores` |
| `settings/<user>.json` | `{ "theme": "light", "muted": false }` | `save_settings` |
| `cloud_scores.json` (server) | `{ "username_lowercase": [scores...] }` | `ScoreStore` |

**Load rules:** every load function validates what it reads. A missing file, broken JSON, or wrong shape gives the safe default (empty scores, default settings, no users). Bad fields fall back one at a time.

**Save rules:** the server writes to a temporary file and then renames it, so a crash cannot leave a half-written file.

---

## 8. Screens and Control Flow

```
main()
 └─ loop: apply light theme → run_login() → user or None
        └─ play(user) → "logout" (back to login) or "quit" (exit)
```

- `run_login` runs the `LoginScreen` until someone signs in or quits.
- `play` wraps `_play` and always stops the music when it ends.
- `_play` is the frame loop: read events, apply them to `Game`, call `game.update(dt)`, play queued sound events, update music, draw. At game over it saves the score and syncs once.

Frame time `dt` comes from `clock.tick(FPS) / 1000`. Holding the Down key sets a flag on key down and clears it on key up, so soft drop repeats each frame.

---

## 9. Error Handling

| Situation | Behavior |
|---|---|
| No audio device | `SoundBank` and `Music` become silent; the game runs normally |
| Missing, empty, or corrupt data file | Defaults are used; the game keeps running |
| Hand-edited `users.json` | Records are re-validated; bad entries are ignored |
| Cloud server unreachable, wrong key, bad reply | `CloudSync` returns `None`; local scores are kept |
| Server receives bad input | Replies 400, 401, or 404 with a short JSON error; nothing is stored |
| Window closed with the X button | Exits without saving the unfinished run (Pause > Quit and Sign Out do save) |

---

## 10. Security Design

| Area | Design |
|---|---|
| **Passwords** | Never stored. Each account has a random 16-byte salt and a PBKDF2-HMAC-SHA256 hash (600,000 iterations); the iteration count is stored per account so it can be raised later |
| **Sign in errors** | One generic message, so it never says whether the username or password was wrong |
| **Usernames** | 3 to 12 letters, numbers, underscores. Re-checked when files are loaded and before any use in a file path or URL, which blocks path tricks such as `../` |
| **File paths** | Built from validated, lowercased usernames only |
| **Network** | Off unless `TETRIS_CLOUD_URL` is set. Only `http://` and `https://` addresses are accepted (no `file:`). Short timeout. Replies are size-limited |
| **Server** | API key checked with a constant-time comparison; request body capped at 4 KB; at most 50 scores per request; scores must be positive whole numbers up to 10^9; binds to `127.0.0.1` by default |

**Honest limits:** accounts are local, so anyone with file access can edit them. The API key is a shared secret sent in a header, so it needs `https` if the server is not on a trusted network. This is not meant to protect sensitive data.

---

## 11. Design Decisions and Trade-offs

| Decision | Why | Cost |
|---|---|---|
| **Rules in `Game`, drawing in `draw_*`** | Rules can be tested without a window | Drawing code reads many `Game` fields |
| **Event list instead of calling audio from rules** | Rules stay free of audio code and testable | One more list to clear each frame |
| **Sound generated in code** | No audio files to ship or lose | Simple beeps, not recorded music |
| **JSON files, not a database** | Simple, readable, no install | Not safe for many users at once; no queries |
| **Optional cloud sync, offline first** | The game always works | Scores are only shared when sync is on |
| **Merge by maximum count** | Syncing is repeatable and never double counts | Two real runs with the same score on different computers count as one |
| **Server in the standard library** | Nothing extra to install | Fewer features than a web framework |
| **Synchronous sync with a 1.5 s timeout** | Simple code, no threads | Can pause the game briefly at game over, sign out, or quit when the server is slow |
| **Single large game file** | Easy to run and hand in | Hard to navigate; see Future Work |
| **Theme colors as module-level variables** | Drawing code can use plain names like `WHITE` | Global state that tests must reset after changing theme |

---

## 12. Design Principles in Use

- **Separation of concerns:** rules, drawing, input, storage, and network are separate groups of code.
- **Single responsibility:** `Piece` is a position, `Board` is a grid, `SevenBag` is a randomizer, `Game` coordinates them.
- **Fail soft:** every outside source (files, audio, network) has a safe fallback.
- **Validate at the edge:** names, files, and requests are checked when they enter, not later.
- **Data-driven rules:** scoring, kicks, sounds, and themes are tables, so changing them does not change logic.
- **Defaults off for risk:** cloud sync is off unless set up, and the server listens only on the local machine.

---

## 13. Testing Strategy

| Level | Examples |
|---|---|
| **Unit** | Scoring, bag contents, line clearing, kick use, gravity, merge rules, password hashing |
| **Component** | `LoginScreen` flows, score and settings files, `Music` state changes, `ScoreStore` persistence |
| **Integration** | Real HTTP server on a free port with the real client; scripted play session driving the whole loop with mocked events |
| **Layout** | Buttons and panels fit inside the window and do not overlap |
| **Safety** | Bad usernames, bad request bodies, wrong keys, oversize bodies, damaged files |

Run: `python3 -m unittest test_tetris_render test_tetris_auth test_tetris_features test_tetris_cloud test_tetris_extras`

Tests set `SDL_VIDEODRIVER` and `SDL_AUDIODRIVER` to `dummy` so they run without a screen or speakers. A few drawing tests check actual pixels and need real pygame.

---

## 14. Known Limitations and Future Work

| Item | Notes |
|---|---|
| **Single file** | `tetris_ver2.py` is about 1,600 lines. Splitting into `rules.py`, `audio.py`, `accounts.py`, `ui.py` would help readability |
| **Global theme state** | A `Theme` object passed to the drawing functions would remove the globals |
| **Blocking sync** | A background thread would remove the short pause when the server is slow |
| **Closing with X loses a run** | Could save on the quit event |
| **No account recovery** | By design, since there is no email or server login |
| **2-player battle mode** | Planned, not built |
| **Rebindable keys** | Planned, not built |
| **Music** | A single short loop; more tracks or a real instrument mix could be added |
