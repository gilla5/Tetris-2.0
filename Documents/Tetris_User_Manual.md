---
marp: true
theme: default
paginate: true
header: "Tetris 2.0 User Manual"
style: |
  section { font-size: 24px; }
  section h1 { color: #1F4E79; }
  section h2 { color: #C55A11; }
  table { font-size: 20px; }
  code { font-size: 0.85em; }
---

<!-- _paginate: false -->
<!-- _header: "" -->

# Tetris 2.0
## User Manual

A Tetris game with player accounts, hold and next queue, T-spins, combos, row bombs, music, themes, personal high scores, and optional cloud score sync.

**Version:** tetris_ver2.py
**Players:** one at a time, on one computer

---
# Contents

1. Getting started: install and launch
2. Creating an account and signing in
3. The game screen
4. Controls
5. Playing: pieces, hold, next queue, ghost piece
6. Scoring, levels, and speed
7. Advanced moves: T-spins, combos, back-to-back
8. Row bombs
9. Sound, music, and themes
10. Pause, game over, and signing out
11. High scores and cloud sync
12. Files the game creates
13. Troubleshooting and FAQ
14. For developers: tests and files
---

# 1. What You Need

- **Python 3** (a recent version, such as 3.10 or newer)
- **pygame**, the library that draws the game and plays sound
- A mouse and keyboard
- Sound is optional. If no audio device is found, the game stays silent and everything else still works.

**Install pygame** (once), in a terminal:

```
pip install pygame
```

On some computers the command is `pip3` or `python3 -m pip`.

---

# 2. Starting the Game

1. Put all the game files in one folder (see section 12).
2. Open a terminal in that folder.
3. Run:

```
python3 tetris_ver2.py
```

A window (700 x 660) opens on the **Sign In** page.

**To close the game:** click **Quit** on the Sign In page, or use the **Quit** buttons on the pause menu or game over screen.

*Tip: if you want cloud score sync, set it up first (section 11).*

---

# 3. Signing In and Creating an Account

The game always opens on the **Sign In** page. You use the mouse for almost everything.

| Do this | To |
|---|---|
| Click a box | Type in it |
| Click **Show / Hide** | Reveal or hide your password |
| Click **Sign In** | Submit |
| Click **Create an account** | Open the Sign Up page |
| Click **Quit** | Close the game |

**Keyboard helpers:** **Tab** and the **Up / Down arrows** move between boxes. **Enter** moves to the next box, and submits from the last box.

---

# 4. Creating an Account (Sign Up)

Click **Create an account**, then fill in:

- **Username:** 3 to 12 letters, numbers, or underscores. Not case sensitive (`Aiden` and `aiden` are the same player), but it keeps the capital letters you chose.
- **Password:** 6 to 64 characters. It can't be the same as your username.
- **Confirm password:** type the same password again.

Click **Sign Up**. You are signed in right away. **Back to Sign In** returns to the first page.

**Error messages tell you what to fix**, for example: *That username is taken*, *Passwords don't match*, *Password must be 6-64 characters*.

---

# 5. How Accounts Are Kept Safe (and Their Limits)

- Your password is **never stored**. The game keeps a random salt and a PBKDF2-HMAC-SHA256 hash in `users.json`.
- A wrong sign in always shows the same message: *Wrong username or password*. It never says which part was wrong.
- Accounts are **local to this computer**. They keep casual players out of each other's scores and settings.
- Anyone with access to the files can edit or delete them, so **do not reuse an important password here**.
- **There is no password recovery.** If you forget it, create a new account.

---

# 6. The Game Screen

| Area | What it shows |
|---|---|
| **Center** | The 10 x 20 board, your falling piece, and a **ghost** outline showing where it will land |
| **Top left: HOLD** | The piece you saved with **C** |
| **Right: NEXT** | The next **3 pieces**, in order |
| **Left, under HOLD** | Score, Level, Lines, Pieces, Time, and Bombs (n / 3) |
| **Bottom left** | Reminders: pause, sound on/off, current theme, row bomb key |
| **Bottom right** | Who is signed in, and the **Sign Out** button |
| **Top of the board** | Pop-up text: SINGLE, TETRIS, T-SPIN, COMBO, BACK-TO-BACK, BOOM!, LEVEL UP! |

---

# 7. Controls

| Key | Action |
|---|---|
| **Left / Right arrow** | Move the piece |
| **Up arrow** | Rotate clockwise |
| **Z** | Rotate the other way |
| **Down arrow** (hold) | Soft drop: fall faster |
| **Space** | Hard drop: land instantly |
| **C** | Hold the piece |
| **B** | Use a row bomb |
| **P** or **Esc** | Pause / resume |
| **M** | Sound and music on / off |
| **T** | Switch theme (light, dark, retro) |

---

# 8. Controls: Menus and Game Over

| Key | When | Action |
|---|---|---|
| **R** | Paused, or game over | Restart |
| **Q** | Paused, or game over | Quit the game |
| **L** | Game over | Sign out |

**Mouse:**
- Pause menu: click **Resume**, **Restart**, or **Quit**.
- Game over: click **Restart**, **Sign Out**, or **Quit**.
- During play: click **Sign Out** (bottom right) to return to the Sign In page.

*Pausing hides the board, so you can't plan your next move while paused.*

---

# 9. Pieces and the 7-Bag

There are 7 pieces: **I, O, T, S, Z, J, L**.

The game deals them with a **7-bag**: every bag contains each piece exactly once, in random order. So you never wait too long for a piece, and you never get long runs of the same one.

Pieces rotate with the standard **SRS system with wall kicks**: if a rotation would hit a wall or the stack, the game tries a few nearby positions so the turn still works. This is what makes tight spins possible.

---

# 10. Hold, Next Queue, and Ghost Piece

**Hold (C):** swap your falling piece into the hold box. If the box already has a piece, they trade places. You can hold **once per piece**; the next hold unlocks after the current piece locks.

**Next queue:** the right side always shows the next **3 pieces** in order, so you can plan ahead.

**Ghost piece:** the outline at the bottom of the board is exactly where your piece will land if you hard drop. Use it to line up drops precisely.

---

# 11. Lock Delay

A piece that lands **does not lock right away**. It stays movable for **half a second**, so you can slide or rotate it into place.

- Moving sideways or rotating on the ground **restarts the timer**.
- This can happen up to **15 times** per piece, so a piece can't stall forever.
- **Hard drop** (Space) locks instantly.

When the piece locks, completed rows flash, then disappear, and the next piece appears.

---

# 12. Scoring: Line Clears

All line clear points are **multiplied by your level**.

| Lines cleared | Name | Base points |
|---|---|---|
| 1 | SINGLE | 100 |
| 2 | DOUBLE | 300 |
| 3 | TRIPLE | 500 |
| 4 | TETRIS | 800 |

**Dropping also scores:** 1 point per row of soft drop, and 2 points per row of hard drop.

*Example: a Tetris at level 3 scores 800 x 3 = 2,400.*

---

# 13. Levels and Speed

- You gain a level every **10 lines**.
- A **LEVEL UP!** message appears and a short jingle plays.
- Pieces fall faster at every level, and the music gets faster too.

| Level | Seconds per row (about) |
|---|---|
| 1 | 1.00 |
| 5 | 0.36 |
| 10 | 0.06 |
| Higher | never faster than 0.05 |

The game over screen reports the level you reached.

---

# 14. T-Spins

Rotate a **T piece** into a tight slot so that **3 of the 4 corners** around it are blocked (walls and the floor count). The last thing you did must be the rotation.

| Result | No lines | 1 line | 2 lines | 3 lines |
|---|---|---|---|---|
| **T-SPIN** | 400 | 800 | 1,200 | 1,600 |
| **T-SPIN MINI** | 100 | 200 | 400 | |

Points are multiplied by level. A **mini** T-spin is one where the two corners on the pointed side are not both blocked. Moving the piece after rotating cancels the T-spin.

---

# 15. Combos and Back-to-Back

**Combo:** clear lines with **consecutive pieces** and each clear after the first adds bonus points: **50 x combo step x level**. A piece that clears nothing ends the combo. The screen shows *COMBO x2*, *COMBO x3*, and so on.

**Back-to-back (B2B):** a **Tetris** or a **T-spin line clear** is a "difficult" clear. Do one right after another difficult clear and it scores **1.5x**. The screen shows *BACK-TO-BACK*.

- A normal single, double, or triple **ends** the chain.
- A piece that clears nothing does **not** end it.

---

# 16. Row Bombs

**Earn a bomb:** every **Tetris** or **T-spin line clear** gives you one row bomb. You can hold up to **3**. The HUD shows *Bombs: n/3*, and a chime plays when you earn one.

**Use a bomb (B):** the **bottom 2 rows** are blasted away and everything above drops down. The screen shows *BOOM!*

- You score **50 points per blasted row that had blocks, times your level.**
- A bomb is **never wasted**: it won't fire on an empty floor, and you keep it.
- Bombs don't work while paused or after game over.

*Best use: rescue a stack that is getting too high, or open up a messy bottom.*

---

# 17. Sound and Music

**Sound effects** (generated in code, no audio files): moving, rotating, holding, locking, clears, T-spins, Tetris, level up, bomb earned, bomb blast, and game over.

**Background music** is a short loop that plays while you play:
- It gets **faster with each level**, up to level 10.
- It **pauses** when you pause and **stops** at game over.

**Press M** to turn all sound and music on or off. The setting is saved for your account.

*No audio device? The game stays silent and runs normally.*

---

# 18. Themes

Press **T** to cycle through three looks:

| Theme | Look |
|---|---|
| **Light** | The default: light background, bright piece colors |
| **Dark** | Dark background with soft contrast |
| **Retro** | Game Boy style greens |

Your theme and sound setting are saved **per player** in `settings/<username>.json` and come back the next time you sign in. The Sign In pages always use the light theme.

---

# 19. Pause Menu

Press **P** or **Esc** to pause. The board is hidden and a menu appears:

| Button | Key | What it does |
|---|---|---|
| **Resume** | P or Esc | Continue playing |
| **Restart** | R | Save your score and start a new game |
| **Quit** | Q | Save your score and close the game |

While paused, the time and gravity stop, and the music pauses.

**Important:** closing the window with the X button does **not** save an unfinished run. Use **Pause > Quit** or **Sign Out** to keep your score.

---

# 20. Game Over

The game ends when a new piece has no room to appear.

The game over screen shows:
- **Pieces** placed, **Lines** cleared, **Level** reached, and **Time** played
- Your **top 5 scores** (your new score is highlighted in red if it made the list)
- Buttons: **Restart** (R), **Sign Out** (L), **Quit** (Q)

Your score is saved automatically. A score of 0 is not saved.

---

# 21. Signing Out

Click **Sign Out** (bottom right) at any time, or press **L** after game over.

- Your **current score is saved first**, so you don't lose the run.
- You return to the Sign In page, where another player can sign in.
- Each player has their own scores and settings.

---

# 22. High Scores

Each player's **top 5 scores** are saved in `scores/<username>.json` next to the game. They appear on the game over screen under **YOUR HIGH SCORES**.

- Scores are kept separately for every account.
- Only your best 5 are kept.
- With cloud sync turned on, the title changes to **HIGH SCORES (CLOUD)** after a successful sync.

---

# 23. High Score Cloud Sync: What It Does

Cloud sync lets you keep the same top scores on **more than one computer**. It uses a small score server that comes with the game.

- It is **optional**. If you don't set it up, nothing changes.
- Scores are merged when you **sign out, quit, or reach game over**.
- The same score is **never counted twice**, even if you sync many times.
- If the server is off or unreachable, the game simply keeps your local scores. Syncing can pause the game for up to about 1.5 seconds.

The server is one you run yourself. It is not a public online service.

---

# 24. Cloud Sync: Setup

**Step 1: start the server** on a computer the players can reach:

```
python3 cloud_server.py --port 8765 --key mysecret
```

**Step 2: tell the game where it is**, before launching it (macOS / Linux):

```
export TETRIS_CLOUD_URL=http://127.0.0.1:8765
export TETRIS_CLOUD_KEY=mysecret
python3 tetris_ver2.py
```

On Windows PowerShell use `$env:TETRIS_CLOUD_URL="http://127.0.0.1:8765"` and `$env:TETRIS_CLOUD_KEY="mysecret"`.

---

# 25. Cloud Sync: Safety Notes

- By default the server listens on **127.0.0.1**, so only this computer can reach it.
- To allow other computers, add `--host 0.0.0.0`, and **always use a key**.
- The key is a shared password. If the server is not on your own network, put it behind **https**.
- Server data is stored in `cloud_scores.json`. Add it to `.gitignore`.
- The server checks every request: usernames, score values, and request size are limited, and bad requests are refused.

---

# 26. Cloud Sync: The API (Reference)

JSON in, JSON out. Everything except `/health` needs the `X-API-Key` header when the server has a key.

| Request | What it does |
|---|---|
| `GET /health` | Returns `{"status": "ok"}` |
| `GET /scores/<user>` | The player's top scores |
| `POST /scores/<user>` with `{"score": 1200}` | Adds one score |
| `POST /sync/<user>` with `{"scores": [900, 300]}` | Merges a list, returns the top 5 |

**Replies:** `200` success, `400` bad request, `401` wrong or missing key, `404` unknown path or bad username.

---

# 27. Files the Game Creates

| File or folder | What it holds |
|---|---|
| `users.json` | Accounts: usernames, salts, password hashes |
| `scores/<username>.json` | That player's top 5 scores |
| `settings/<username>.json` | That player's theme and sound setting |
| `cloud_scores.json` | Server only: all players' cloud scores |

These are created automatically next to the game. Don't commit them to git (add to `.gitignore`). To reset a player, delete their file in `scores` or `settings`.

---

# 28. Troubleshooting: Starting the Game

| Problem | Fix |
|---|---|
| `No module named pygame` | Run `pip install pygame` |
| `tetris_ver2.py` not found | Open the terminal **in the game folder** |
| Window doesn't open | Make sure Python and pygame installed in the same environment |
| `No module named cloud_sync` | Keep `cloud_sync.py` in the same folder as `tetris_ver2.py` |
| Slow or choppy | Close other programs; the game targets 60 frames per second |

---

# 29. Troubleshooting: Accounts and Scores

| Problem | Fix |
|---|---|
| "Wrong username or password" | Check spelling; the username is not case sensitive, the password is |
| "That username is taken" | Pick another name; names are not case sensitive |
| Forgot a password | There is no recovery; create a new account |
| My score didn't save | Use Pause > Quit or Sign Out. Closing the window with X loses an unfinished run |
| Scores missing on another computer | Accounts and scores are local unless cloud sync is on |
| Score of 0 not shown | Zero scores are never saved |

---

# 30. Troubleshooting: Sound and Cloud Sync

| Problem | Fix |
|---|---|
| No sound or music | Press **M** (it may be off). Check your computer's audio device |
| Music cuts out when paused | Normal: it pauses with the game |
| Cloud title never appears | The sync failed. Check the server is running, the URL and key match, and the firewall allows the port |
| Short freeze at game over | The game waited for the server (up to about 1.5 seconds) |
| `401` errors | The key in `TETRIS_CLOUD_KEY` doesn't match the server's `--key` |

**Quick check:** open `http://127.0.0.1:8765/health` in a browser. It should show `{"status": "ok"}`.

---

# 31. FAQ

**Can two people play at once?** No. Players take turns by signing in and out.

**Does my score change if I pause?** No. Time, gravity, and music all stop.

**How do I get more bombs?** Tetrises and T-spin line clears. Holding is capped at 3.

**Why can't I hold twice in a row?** One hold per piece is the standard rule; it unlocks when the piece locks.

**Is cloud sync required?** No, it's optional and off by default.

**Is 2-player battle mode available?** Not yet. Background music and bombs are done; battle mode is still planned.

---

# 32. For Developers: Tests

Run all tests from the game folder:

```
python3 -m unittest test_tetris_render test_tetris_auth \
  test_tetris_features test_tetris_cloud test_tetris_extras
```

| Test file | Covers |
|---|---|
| `test_tetris_render` | Drawing and the score file |
| `test_tetris_auth` | Accounts, passwords, sign in pages |
| `test_tetris_features` | Pause, T-spins, combos, lock delay, themes, sound |
| `test_tetris_cloud` | Score merging, the server, the sync client |
| `test_tetris_extras` | Next queue, row bombs, music |

---

# 33. For Developers: Project Files

| File | Purpose |
|---|---|
| `tetris_ver2.py` | The game: board, pieces, scoring, drawing, accounts, play loop |
| `cloud_sync.py` | Score client and merge rules (no pygame) |
| `cloud_server.py` | The score server (standard library only) |
| `README.md` | Short reference |
| `test_*.py` | Automated tests |

**Key settings** are constants at the top of `tetris_ver2.py` (window size, lock delay, scoring tables, bomb limits, music tempo), so you can tune the game without changing the logic.

---

<!-- _paginate: false -->

# Quick Reference Card

| | |
|---|---|
| **Move** | Left / Right |
| **Rotate** | Up (clockwise), Z (other way) |
| **Drop** | Down (soft), Space (hard) |
| **Hold** | C |
| **Row bomb** | B |
| **Pause** | P or Esc |
| **Sound / music** | M |
| **Theme** | T |
| **Restart / Quit / Sign out** | R / Q / L (when paused or game over) |

**Goal:** clear lines, chain combos, earn bombs, and beat your high score.
