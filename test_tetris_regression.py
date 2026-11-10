"""Regression tests: they pin down behavior that must not change by accident.

Part 1 holds "golden" values (scoring, speed, limits). If someone edits one,
a test fails and the change has to be made on purpose, in both places.
Part 2 re-checks problems that were easy to break while adding features
(bad files, double counting, wasted bombs, frozen pause, and so on).
Part 3 plays thousands of random moves and checks the rules never break.
"""
import json
import os
import random
import tempfile
import unittest
import unittest.mock
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

import cloud_sync
import tetris_ver2 as t


class GoldenRuleValues(unittest.TestCase):
    def test_scoring_tables(self):
        self.assertEqual(t.LINE_CLEAR_SCORE, {1: 100, 2: 300, 3: 500, 4: 800})
        self.assertEqual(t.TSPIN_SCORE, {0: 400, 1: 800, 2: 1200, 3: 1600})
        self.assertEqual(t.TSPIN_MINI_SCORE, {0: 100, 1: 200, 2: 400})
        self.assertEqual((t.SOFT_DROP_POINTS, t.HARD_DROP_POINTS), (1, 2))
        self.assertEqual(t.COMBO_POINTS, 50)
        self.assertEqual(t.B2B_MULTIPLIER, 1.5)

    def test_progression_and_timing(self):
        self.assertEqual(t.LINES_PER_LEVEL, 10)
        self.assertEqual(t.LOCK_DELAY, 0.5)
        self.assertEqual(t.MAX_LOCK_RESETS, 15)

    def test_gravity_curve(self):
        self.assertEqual(t.gravity_interval(1), 1.0)
        self.assertAlmostEqual(t.gravity_interval(5), 0.355, places=3)
        self.assertAlmostEqual(t.gravity_interval(10), 0.064, places=3)
        self.assertEqual(t.gravity_interval(40), 0.05)

    def test_board_and_panels(self):
        self.assertEqual((t.BOARD_WIDTH, t.BOARD_HEIGHT), (10, 20))
        self.assertEqual(t.NEXT_QUEUE_SIZE, 3)
        self.assertEqual(t.WINDOW_SIZE, (700, 660))
        self.assertEqual(sorted(t.PIECE_SHAPES), list("IJLOSTZ"))

    def test_bomb_rules(self):
        self.assertEqual((t.MAX_BOMBS, t.BOMB_ROWS, t.BOMB_POINTS), (3, 2, 50))

    def test_account_limits(self):
        self.assertEqual((t.USERNAME_MAX_LEN, t.MIN_PASSWORD_LEN, t.MAX_PASSWORD_LEN),
                         (12, 6, 64))
        self.assertGreaterEqual(t.PBKDF2_ITERATIONS, 600_000)
        self.assertEqual(t.LEADERBOARD_SIZE, 5)
        self.assertEqual(cloud_sync.TOP_SCORES, t.LEADERBOARD_SIZE)

    def test_music_tempo(self):
        self.assertEqual(t.music_speed(1), 1.0)
        self.assertAlmostEqual(t.music_speed(10), 1.72)
        self.assertEqual(t.music_speed(99), t.music_speed(10))

    def test_themes_and_controls_exist(self):
        self.assertEqual(t.THEME_ORDER, ["light", "dark", "retro"])
        self.assertEqual(set(t.PAUSE_BUTTONS), {"resume", "restart", "quit"})
        self.assertEqual(set(t.GAME_OVER_BUTTONS), {"restart", "sign_out", "quit"})


class PastProblems(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        t.apply_theme("light")
        self.dir.cleanup()

    def path(self, name):
        return os.path.join(self.dir.name, name)

    # --- files must never crash the game ---------------------------------
    def test_damaged_files_give_defaults(self):
        for name, loader, default in [
                ("s.json", t.load_scores, []),
                ("u.json", t.load_users, {}),
                ("p.json", t.load_settings, {"theme": "light", "muted": False})]:
            with open(self.path(name), "w") as f:
                f.write("{{ not json")
            self.assertEqual(loader(self.path(name)), default, name)
            self.assertEqual(loader(self.path("missing_" + name)), default, name)

    def test_hand_edited_user_with_a_path_in_the_name_is_ignored(self):
        evil = {"../evil": {"name": "../evil", "salt": "00", "hash": "00", "iterations": 5}}
        with open(self.path("u.json"), "w") as f:
            json.dump(evil, f)
        self.assertEqual(t.load_users(self.path("u.json")), {})

    def test_usernames_that_could_escape_a_folder_are_refused(self):
        for name in ("../x", "a/b", "..", "x" * 13, "ab"):
            self.assertIsNotNone(t.validate_new_account(name, "goodpass1"), name)

    # --- scores -----------------------------------------------------------
    def test_zero_score_is_never_saved_and_only_top_five_stay(self):
        p = self.path("sc.json")
        self.assertEqual(t.save_score(0, p), [])
        for s in (10, 20, 30, 40, 50, 60):
            scores = t.save_score(s, p)
        self.assertEqual(scores, [60, 50, 40, 30, 20])

    def test_syncing_the_same_scores_twice_never_double_counts(self):
        once = cloud_sync.merge_scores([900, 300], [900, 300])
        self.assertEqual(cloud_sync.merge_scores(once, once), [900, 300])

    def test_cloud_is_off_unless_configured(self):
        with unittest.mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(cloud_sync.URL_ENV, None)
            self.assertFalse(cloud_sync.CloudSync.from_env().enabled)
        scores, synced = t.sync_scores("aiden", self.path("x.json"), None)
        self.assertEqual((scores, synced), ([], False))

    # --- game rules -------------------------------------------------------
    def test_pause_freezes_everything_including_hard_drop(self):
        game = t.Game()
        game.toggle_pause()
        before = (game.piece.row, game.piece.col, game.score, game.elapsed)
        game.hard_drop(); game.rotate(); game.move(1, 0); game.hold(); game.update(9)
        self.assertEqual((game.piece.row, game.piece.col, game.score, game.elapsed), before)

    def test_a_bomb_is_not_wasted_on_an_empty_floor(self):
        game = t.Game()
        game.bombs = 2
        self.assertFalse(game.use_bomb())
        self.assertEqual(game.bombs, 2)

    def test_next_queue_stays_at_three_after_holds_and_drops(self):
        game = t.Game()
        game.hold()
        self.assertEqual(len(game.next_queue), 3)
        game.hard_drop()
        game.hold()
        self.assertEqual(len(game.next_queue), 3)

    def test_cannot_hold_twice_in_a_row(self):
        game = t.Game()
        game.hold()
        first = game.piece.kind
        game.hold()
        self.assertEqual(game.piece.kind, first)

    def test_every_seven_pieces_from_the_bag_are_all_different(self):
        bag = t.SevenBag()
        for _ in range(5):
            self.assertEqual(sorted(bag.next_piece() for _ in range(7)), list("IJLOSTZ"))

    def test_ghost_never_moves_the_real_piece(self):
        game = t.Game()
        before = (game.piece.row, game.piece.col, game.piece.rotation)
        t.ghost_cells(game.board, game.piece)
        self.assertEqual((game.piece.row, game.piece.col, game.piece.rotation), before)

    def test_unknown_sound_names_are_ignored(self):
        pygame.init()
        t.SoundBank().play("no_such_sound")

    def test_passwords_are_not_stored_in_the_users_file(self):
        old = t.PBKDF2_ITERATIONS
        t.PBKDF2_ITERATIONS = 1000
        try:
            t.register_user("aiden", "hunter22", self.path("u.json"))
        finally:
            t.PBKDF2_ITERATIONS = old
        self.assertNotIn("hunter22", Path(self.path("u.json")).read_text())


class RandomPlayNeverBreaksTheRules(unittest.TestCase):
    """Plays random moves with a fixed seed so any failure can be repeated."""

    ACTIONS = ("left", "right", "cw", "ccw", "soft", "hard", "hold", "bomb", "tick")

    def run_game(self, seed, steps):
        rng = random.Random(seed)
        random.seed(seed)  # the bag uses the global random
        game = t.Game()
        last_score = 0
        for _ in range(steps):
            action = rng.choice(self.ACTIONS)
            if action == "left": game.move(-1, 0)
            elif action == "right": game.move(1, 0)
            elif action == "cw": game.rotate(True)
            elif action == "ccw": game.rotate(False)
            elif action == "soft": game.soft_drop()
            elif action == "hard": game.hard_drop()
            elif action == "hold": game.hold()
            elif action == "bomb": game.use_bomb()
            else: game.update(rng.choice((0.016, 0.1, 0.5)))
            game.events.clear()
            if game.state == "gameover":
                game = t.Game()
                last_score = 0
                continue
            self.assertTrue(game.board.is_valid(game.piece.cells()), (seed, action))
            self.assertGreaterEqual(game.score, last_score, (seed, action))
            self.assertEqual(len(game.next_queue), t.NEXT_QUEUE_SIZE)
            self.assertTrue(0 <= game.bombs <= t.MAX_BOMBS)
            self.assertEqual(game.level, 1 + game.lines_cleared // t.LINES_PER_LEVEL)
            self.assertTrue(all(len(row) == t.BOARD_WIDTH for row in game.board.grid))
            self.assertEqual(len(game.board.grid), t.BOARD_HEIGHT)
            last_score = game.score

    def test_random_sessions(self):
        for seed in range(25):
            self.run_game(seed, 1500)


if __name__ == "__main__":
    import unittest.mock  # noqa: F401
    unittest.main()
