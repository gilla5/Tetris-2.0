---
marp: true
theme: default
paginate: true
header: "Tetris-2.0 | Binary Ninjas | Team Sprint 1 Presentation (S1P)"
style: |
  section { font-size: 28px; }
  h1 { color: #1f4e79; }
  table { font-size: 22px; }
---

# Tetris-2.0
## Team Sprint 1 Presentation (S1P)

Team: **Binary Ninjas**
Team Leader: Aiden Gill
Members: Aiden · Nathan · Caleb · Jacob

<!-- 15 min presentation + 5 min Q&A. Title: 0:30 -->

---

# Agenda

1. Sprint 1 demo (video)
2. Progress: lines of code and burndown
3. What went well, what went wrong, improvements
4. Sprint 2: goals, responsibilities, tests, timeline
5. Q&A

<!-- 0:30 -->

---

<style scoped>
section { font-size: 24px; }
</style>

# 1. Sprint 1 Demo

<a href="https://www.youtube.com/watch?v=JWczvv1stH4"><img src="https://img.youtube.com/vi/JWczvv1stH4/hqdefault.jpg" alt="Watch the demo on YouTube" style="float:right; width:480px; margin-left:24px;"></a>

Shows:
- Signing in with an account
- Playing a game: pieces, next queue, ghost piece
- Pause menu (Resume, Restart, Quit)
- Light and dark themes
- Game over screen with stats and per-player high scores
- Sign Out and signing back in

[Watch the demo on YouTube](https://www.youtube.com/watch?v=JWczvv1stH4)

<!-- Demo: 3:00 (the recording is 2:26). Play the YouTube recording; talk over it. Needs internet. -->

---

# 2. Progress: Lines of Code

| Measure | Lines |
|---|---|
| Game code (`tetris_ver2.py`) | 1,424 |
| Test code (3 test files) | 953 |
| **Team total** | **2,377** |

| Member | Area | LoC |
|---|---|---|
| Aiden | Core engine and accounts | 1,777 |
| Nathan | Rendering and visual feedback | 456 |
| Caleb | Input and controls | 144 |
| Jacob | Audio and systems | 0 |

<!-- 1:30. Use the same LoC numbers as the Sprint 1 metrics page. Totals are raw line counts (wc -l), same method as before: 970 + 534 = 1,504 earlier. -->

---

# 2. Progress: Features and Requirements

**Sprint 1 only** (approved Sprint 1 scope):

- Features: 18 / 24 = 75%
- Requirements: 12 / 20 = 60%
- Remaining Sprint 1 requirements: 8

**Whole project (counts only):**

| | Planned | Completed | Remaining |
|---|---|---|---|
| Features | 24 | 18 | 6 |
| Requirements | 20 | 12 | 8 |

Automated tests: **109** (56 accounts, 10 rendering, 43 gameplay features)

<!-- 1:30. Numbers match the team rubric (HW4_team_project_rubric.md). -->

---

# 2. Burndown: Remaining Requirements

*[Insert burndown chart: remaining requirements vs. course week, with ideal line]*

| Week | Remaining |
|---|---|
| Start | 14 |
| End of Week 5 | 7 |
| End of Week 6 | 0 |
| End of Week 7 | 0 |
| End of Week 8 | 0 |

<!-- 1:00. Say whether the team is ahead, on track or behind. -->

---

# 3. What Went Well

- Accounts feature works end to end: sign up, sign in, per-player high scores
- 109 automated tests pass (accounts, rendering and gameplay features)
- Gameplay now includes pause, T-spins, combos, lock delay, sound, themes and animations
- Game code is organized into separate classes (`Board`, `Piece`, `SevenBag`, `Game`)
- Merge conflicts in the README and `tetris_ver2.py` were found and resolved

<!-- 1:30. Confirm each point is still true before presenting. -->

---

# 3. What Went Wrong

- Work was uneven: most code came from two members, so the input and audio tracks are behind
- Merge conflicts in `README.md` and `tetris_ver2.py` because changes lived on separate copies for too long
- Burndown is below plan, so the schedule needs adjusting
- Setup problems on Mac (pygame vs. pygame-ce on Python 3.14)

<!-- 1:30. Be direct; this is the part the class remembers. Adjust to what really happened. -->

---

# 3. Cause and Improvements

| Problem | Cause | Improvement |
|---|---|---|
| Uneven work | Tasks not broken into small pieces | Weekly check-in; small tasks with named owners |
| Merge conflicts | Long-lived changes, no branch routine | Small branches, pull before push, merge often |
| Burndown behind | Blocked or late tracks | Reassign work; update the schedule |
| Setup trouble | No standard environment | Adopt `uv` with a lockfile and `pygame-ce` |

<!-- 1:00 -->

---

# 4. Sprint 2 Goals

- **Refactoring:** split `tetris_ver2.py` into a `tetris/` package (constants, pieces, game, render, accounts, scores, main), removing globals and magic numbers
- **MVP:** finish the must-have list: 7-bag, hold and next queue, SRS with wall kicks, soft and hard drop, line clears with speed, pause menu, game over, high scores
- **UV adoption:** `pyproject.toml`, `uv.lock`, `uv sync`, `uv run`
- **Quality:** README, setup guide and design document

<!-- 1:30. Pause menu is already implemented; this bullet may now be "verify the must-have list with acceptance tests". -->

---

# 4. Sprint 2 Responsibilities

| Member | Responsibility |
|---|---|
| Aiden (Leader) | Engine refactor, `uv` migration, remaining engine feature, integration |
| Nathan | Rendering module, visual feedback, animations or themes |
| Caleb | Input module (key map, `handle_event`), pause menu, input tests |
| Jacob | Sound effects, music, mute toggle, audio tests |

*Proposed. Confirm each member before presenting.*

<!-- 1:00. Pause menu, sound effects, mute, animations and themes now exist in tetris_ver2.py, so these rows may need to change to refactoring, tests, background music, or 2-player mode. -->

---

# 4. Sprint 2 Test Plan

| Type | Files |
|---|---|
| Unit | `test_pieces.py`, `test_board.py` (7-bag, rotation, wall kicks, collision, scoring) |
| Integration | `test_tetris_auth.py`, `test_game_loop.py` (accounts, spawn, drop, lock, clear, game over) |
| Regression | `test_regression.py` (same inputs before and after the refactor) |
| Acceptance | `test_acceptance.py` (one test per requirement) plus a manual play-through checklist |

<!-- 1:00 -->

---

# 4. Sprint 2 Timeline

| Weeks | Plan |
|---|---|
| 9–10 | Refactoring and core features; move to `uv` |
| 11–12 | Features, tests and design clean-up |
| 13 | Acceptance tests, documents, initial GitHub Pages site |
| 14–15 | Fixes and final submission |

If burndown is not 100% by the end: adjust the schedule and submit a report.

<!-- 1:00 -->

---

# Summary

- Sprint 1: accounts, engine, rendering and gameplay extras working; 109 tests; 2,377 lines
- Biggest risks: uneven workload and merge conflicts
- Sprint 2: refactor, `uv`, finish MVP, full test plan

# Questions?

<!-- Q&A: up to 5 minutes. -->
