# Tetris 2.0: Testing

## 1. Short Answer

**No, the project does not do every type of testing.** It has a solid set of automated tests for the game rules, accounts, scores, settings, sound, music, and the cloud sync server and client. It does not yet have performance testing, real user (usability) testing, cross-platform testing, a coverage report, automatic runs on every push, or code quality checks.

This document lists what is covered, what is not, how to run the tests, and a manual test plan to fill the gaps.

---

## 2. Test Types: What Is and Isn't Covered

| Test type | Status | Where / notes |
|---|---|---|
| **Unit testing** | Covered | Scoring, 7-bag, line clearing, gravity, T-spin detection, combos, bombs, music tempo, score merging, password hashing |
| **Component testing** | Covered | `LoginScreen` flows, score and settings files, `Music` state changes, `ScoreStore` saving |
| **Integration testing** | Covered | Real HTTP server on a free port with the real client; game over sends the score to the server |
| **System / end-to-end (automated)** | Partial | Scripted play sessions drive the whole play loop with fake key events. They run with dummy video and audio, so nothing real is drawn or heard |
| **Functional testing** | Covered | Every feature has tests: pause, hold, next queue, bombs, themes, mute, accounts, scores |
| **Boundary and edge cases** | Covered | Username and password length limits, empty and corrupt files, 5-score limit, bomb cap, lock reset cap, 50-score request limit |
| **Negative testing** | Covered | Wrong passwords, bad usernames, bad request bodies, wrong API key, damaged data files, unreachable server |
| **Security testing (basic)** | Partial | Tests check hashing, name validation, path tricks (`../`), key checks, body size limits. There is no penetration test or dependency scan |
| **Layout testing** | Covered | Buttons and panels fit in the window and don't overlap |
| **Regression testing** | Covered | `test_tetris_regression.py` pins the scoring and speed values, re-checks past trouble spots, and plays random games to catch broken rules. Nothing runs it automatically yet |
| **Smoke testing** | Covered | The scripted play session checks that pausing, themes, muting, game over, restart, and quit all run without errors |
| **Performance testing** | Not done | Nobody has measured frame rate, memory, or load time |
| **Load / stress testing (server)** | Not done | The server has not been tested with many players at once |
| **Usability testing** | Not done | No real players have tried it and given feedback |
| **Acceptance testing** | Covered (automated) | `test_tetris_acceptance.py` checks each requirement as a Given / When / Then story. A manual sign-off with real people is still not done (section 5) |
| **Compatibility testing** | Not done | Not tested on Windows, macOS, and Linux, or on different Python and pygame versions |
| **Accessibility testing** | Not done | No checks for color blindness, readable text size, or keyboard-only play |
| **Visual / pixel testing** | Partial | A few tests check pixels, but they need real pygame to run |
| **Code coverage measurement** | Not done | No report shows which lines the tests never run |
| **Static analysis / linting** | Not done | No `flake8`, `pylint`, or type checking |
| **Continuous integration** | Not done | No GitHub Actions or similar |

---

## 3. Automated Test Inventory

There are **202 automated tests** in 7 files.

| File | Tests | What it checks |
|---|---|---|
| `test_tetris_auth.py` | 56 | Username and password rules, registering, signing in, stored data format, bad files, per-player score paths, Sign In and Sign Up screen behavior, layout |
| `test_tetris_features.py` | 43 | Pause, stats, combos, back-to-back, level up, T-spins, lock delay, animations, themes, settings files, sound generation, layout, a scripted play session |
| `test_tetris_cloud.py` | 27 | Score list cleaning and merging, client setup rules, the HTTP server (keys, bad input, bad paths, restart, persistence), local and cloud merging, game over sync |
| `test_tetris_extras.py` | 23 | 3-piece next queue, row bombs (earning, cap, blast, scoring, blocked cases), music tempo and playback state |
| `test_tetris_render.py` | 10 | Score file load and save, drawing helpers, ghost piece |
| `test_tetris_regression.py` | 23 | Golden values for scoring, speed, and limits; past trouble spots; 25 seeded random games that must never break the rules |
| `test_tetris_acceptance.py` | 20 | Requirement stories: sign up and sign in, playing, scoring, bombs, pause, game over, saved scores and settings, shared scores, full scripted sessions |

### Important: what was and wasn't actually run

- The tests are written to run with real pygame.
- In the environment where the cloud, bomb, music, regression, and acceptance tests were built, pygame could not be installed, so **192 tests were run with a stand-in** for pygame, and all of them passed. These are every test except the 10 in `test_tetris_render.py`.
- **Three tests in `test_tetris_render.py` check actual drawn pixels and cannot pass with the stand-in.** They need real pygame.
- **So please run the full suite once on your own computer** with real pygame installed (section 4) and treat that as the real result.

---

## 4. How to Run the Tests

From the game folder:

```
pip install pygame
python3 -m unittest test_tetris_render test_tetris_auth test_tetris_features test_tetris_cloud test_tetris_extras test_tetris_regression test_tetris_acceptance
```

Run one file:

```
python3 -m unittest test_tetris_cloud
```

Run one test:

```
python3 -m unittest test_tetris_extras.BombTests.test_bomb_scores_and_announces
```

The tests set `SDL_VIDEODRIVER` and `SDL_AUDIODRIVER` to `dummy`, so no window opens and no sound plays. They also use temporary folders, so they never touch your real `users.json`, `scores`, or `settings`.

**Pass means:** the last lines show `OK`. Any `FAIL` or `ERROR` means something needs fixing.

---

## 5. Manual Test Plan

These cover what automation can't: real screens, real sound, real people. Record Pass or Fail and the date.

### 5.1 Functional checks

| # | Steps | Expected result | Result |
|---|---|---|---|
| F1 | Start the game | Sign In page appears | |
| F2 | Click Create an account, enter a valid name and password twice, click Sign Up | Signed in, game starts | |
| F3 | Try a username that is too short or a password under 6 characters | A clear error message appears | |
| F4 | Sign out, sign in with a wrong password | "Wrong username or password" | |
| F5 | Click Show / Hide beside a password | Text is revealed, then hidden | |
| F6 | Move, rotate (Up and Z), soft drop, hard drop | Piece responds correctly | |
| F7 | Press C twice in a row | First swaps; second does nothing until the piece locks | |
| F8 | Look at the right side | The next 3 pieces are shown | |
| F9 | Clear 1, 2, 3, and 4 lines | SINGLE, DOUBLE, TRIPLE, TETRIS appear; score rises | |
| F10 | Clear 10 lines | LEVEL UP!; pieces fall faster | |
| F11 | Make a Tetris | Bomb count rises to 1 | |
| F12 | Press B with a bomb and blocks at the bottom | BOOM!; bottom 2 rows vanish; stack drops | |
| F13 | Press B with no bomb | Nothing happens | |
| F14 | Press P, then Resume | Game freezes, then continues | |
| F15 | Press M | Sound and music turn off and on | |
| F16 | Press T three times | Light, dark, retro, back to light | |
| F17 | Play until game over | Stats and top 5 scores appear | |
| F18 | Click Restart, Sign Out, Quit in turn | Each works | |
| F19 | Sign out, sign back in | Theme, sound setting, and scores are remembered | |

### 5.2 Cloud sync checks

| # | Steps | Expected result | Result |
|---|---|---|---|
| C1 | Start the server with a key; open `http://127.0.0.1:8765/health` | `{"status": "ok"}` | |
| C2 | Set the URL and key, play to game over | Title shows HIGH SCORES (CLOUD) | |
| C3 | Stop the server, play to game over | Game works; title shows YOUR HIGH SCORES | |
| C4 | Use a wrong key | Game works; no cloud title | |
| C5 | Sign in with the same name on a second computer | The same top scores appear | |

### 5.3 Performance checks

| # | Steps | Expected result | Result |
|---|---|---|---|
| P1 | Play for 5 minutes at a high level | Smooth motion, no stutter | |
| P2 | Watch memory use in Task Manager or Activity Monitor | Stays steady, no steady climb | |
| P3 | Note the time from launch to Sign In page | A few seconds at most | |
| P4 | Level up through several tempos | Music change causes no noticeable freeze | |

### 5.4 Compatibility checks

| # | Check | Result |
|---|---|---|
| K1 | Runs on macOS | |
| K2 | Runs on Windows | |
| K3 | Runs on Linux | |
| K4 | Runs on the oldest Python version you plan to support | |
| K5 | Runs on the newest Python and pygame | |
| K6 | Runs with no sound device | |

### 5.5 Usability and accessibility checks

Ask 3 to 5 people who haven't seen the game to play for 5 minutes without help, then ask:

- Could you sign up and start without instructions?
- Did you find the controls?
- What was confusing?
- Were the text and colors easy to read in all three themes?

Also check that all three themes are readable, the text is large enough, and the game can be played with the keyboard alone after signing in.

---

## 6. Recommended Next Steps

| Priority | Step | How |
|---|---|---|
| 1 | Run the full suite on your computer with real pygame | Section 4 |
| 2 | Measure code coverage | `pip install coverage`, then `coverage run -m unittest ...` and `coverage report -m` |
| 3 | Add automatic test runs | A GitHub Actions workflow that installs pygame and runs the unit tests on every push |
| 4 | Add linting | `pip install flake8` and run `flake8 .` |
| 5 | Do the manual plan in section 5 | Fill in the Result columns and keep this file with the results |
| 6 | Try a quick load test on the server | Send many `POST /sync/<user>` requests in a loop and check the replies and the data file |
| 7 | Test on a second operating system | Run the suite and the manual checks there |

---

## 7. Test Summary Template

Fill this in each time you test, and keep it with the project.

| Item | Value |
|---|---|
| Date | |
| Tester | |
| Operating system | |
| Python version | |
| pygame version | |
| Automated tests run / passed / failed | |
| Manual tests run / passed / failed | |
| Defects found | |
| Notes | |
