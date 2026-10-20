import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

import tetris_ver2 as t


def _inside(rect, outer):
    x, y, w, h = rect
    ox, oy, ow, oh = outer
    return x >= ox and y >= oy and x + w <= ox + ow and y + h <= oy + oh


def _overlap(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def setup_single(game):
    """Bottom row full except cols 6-9, with a flat I piece above that gap."""
    game.board.grid[19] = ["X"] * 6 + [None] * 4
    game.piece = t.Piece("I")
    game.piece.col = 6


def setup_tetris(game):
    """Rows 16-19 full except the last column, with a vertical I above it."""
    for r in range(16, 20):
        game.board.grid[r] = ["X"] * 9 + [None]
    game.piece = t.Piece("I")
    game.piece.rotation = 1
    game.piece.col = 7


class PauseAndStatsTests(unittest.TestCase):
    def test_pause_freezes_the_game(self):
        game = t.Game()
        row = game.piece.row
        game.toggle_pause()
        self.assertEqual(game.state, "paused")
        game.update(5.0)
        game.hard_drop()
        game.rotate()
        self.assertEqual((game.piece.row, game.elapsed, game.pieces_placed), (row, 0.0, 0))

    def test_resume_continues(self):
        game = t.Game()
        game.toggle_pause()
        game.toggle_pause()
        self.assertEqual(game.state, "playing")

    def test_cannot_pause_after_game_over(self):
        game = t.Game()
        game.state = "gameover"
        game.toggle_pause()
        self.assertEqual(game.state, "gameover")

    def test_stats_count_pieces_and_time(self):
        game = t.Game()
        game.update(0.5)
        game.update(0.5)
        game.hard_drop()
        self.assertAlmostEqual(game.elapsed, 1.0)
        self.assertEqual(game.pieces_placed, 1)

    def test_format_time(self):
        self.assertEqual(t.format_time(0), "0:00")
        self.assertEqual(t.format_time(59.9), "0:59")
        self.assertEqual(t.format_time(125), "2:05")


class ScoringBonusTests(unittest.TestCase):
    def test_combo_adds_bonus_and_resets(self):
        game = t.Game()
        setup_single(game)
        game.hard_drop()
        self.assertEqual(game.combo, 0)
        setup_single(game)
        before = game.score
        game.hard_drop()
        # 18 rows hard dropped (2 each) + single + one combo step
        self.assertEqual(game.score - before, 36 + 100 + t.COMBO_POINTS)
        self.assertEqual(game.combo, 1)
        self.assertEqual(game.message_lines, ["SINGLE", "COMBO x1"])
        game.hard_drop()  # lands without clearing anything
        self.assertEqual(game.combo, -1)

    def test_back_to_back_tetris_scores_extra(self):
        game = t.Game()
        setup_tetris(game)
        game.hard_drop()
        self.assertTrue(game.back_to_back)
        self.assertEqual(game.score, 32 + 800)
        setup_tetris(game)
        before = game.score
        game.hard_drop()
        self.assertEqual(game.score - before, 32 + int(800 * t.B2B_MULTIPLIER) + t.COMBO_POINTS)
        self.assertEqual(game.message_lines, ["BACK-TO-BACK", "TETRIS", "COMBO x1"])
        self.assertIn("tetris", game.events)

    def test_ordinary_clear_ends_back_to_back(self):
        game = t.Game()
        setup_tetris(game)
        game.hard_drop()
        setup_single(game)
        game.hard_drop()
        self.assertFalse(game.back_to_back)
        setup_tetris(game)
        before = game.score
        game.hard_drop()
        self.assertEqual(game.score - before, 32 + 800 + 2 * t.COMBO_POINTS)

    def test_level_up_sets_message_and_event(self):
        game = t.Game()
        game.lines_cleared = 9
        setup_single(game)
        game.hard_drop()
        self.assertEqual(game.level, 2)
        self.assertEqual(game.level_up_timer, t.LEVEL_UP_TIME)
        self.assertIn("levelup", game.events)


class TSpinTests(unittest.TestCase):
    def make(self, filled, rotation=0, rotated=True):
        game = t.Game()
        game.piece = t.Piece("T")
        game.piece.rotation = rotation
        game.piece.row, game.piece.col = 10, 4
        for r, c in filled:
            game.board.grid[r][c] = "X"
        game._rotated_last = rotated
        return game

    def test_three_corners_with_both_front_corners_is_full(self):
        game = self.make([(10, 4), (10, 6), (12, 4)])
        self.assertEqual(game._t_spin_kind(), "full")

    def test_three_corners_missing_a_front_corner_is_mini(self):
        game = self.make([(10, 4), (12, 4), (12, 6)])
        self.assertEqual(game._t_spin_kind(), "mini")

    def test_two_corners_is_not_a_t_spin(self):
        game = self.make([(10, 4), (10, 6)])
        self.assertIsNone(game._t_spin_kind())

    def test_must_end_with_a_rotation(self):
        game = self.make([(10, 4), (10, 6), (12, 4)], rotated=False)
        self.assertIsNone(game._t_spin_kind())

    def test_last_kick_makes_it_full(self):
        game = self.make([(10, 4), (12, 4), (12, 6)])
        game._last_kick = 4
        self.assertEqual(game._t_spin_kind(), "full")

    def test_only_t_pieces_count(self):
        game = self.make([(10, 4), (10, 6), (12, 4)])
        game.piece = t.Piece("S")
        self.assertIsNone(game._t_spin_kind())

    def test_moving_after_rotating_cancels_it(self):
        game = t.Game()
        game.piece = t.Piece("T")
        game.rotate()
        self.assertTrue(game._rotated_last)
        game.move(1, 0)
        self.assertFalse(game._rotated_last)

    def test_t_spin_with_no_lines_scores_bonus(self):
        game = self.make([(10, 4), (10, 6), (12, 4)])
        game._lock_active_piece()
        self.assertEqual(game.score, t.TSPIN_SCORE[0])
        self.assertEqual(game.message_lines, ["T-SPIN"])
        self.assertIn("tspin", game.events)

    def test_t_spin_single_scores_and_counts_as_difficult(self):
        game = t.Game()
        game.board.grid[19] = ["X"] * 4 + [None] * 3 + ["X"] * 3
        game.board.grid[18][4] = game.board.grid[18][6] = "X"
        game.piece = t.Piece("T")
        game.piece.row, game.piece.col = 18, 4
        game._rotated_last = True
        game._lock_active_piece()
        self.assertEqual(game.score, t.TSPIN_SCORE[1])
        self.assertTrue(game.back_to_back)
        self.assertEqual(game.message_lines[0], "T-SPIN SINGLE")


class LockDelayTests(unittest.TestCase):
    def landed_game(self):
        game = t.Game()
        while game.move(0, 1):
            pass
        return game

    def test_piece_does_not_lock_right_away(self):
        game = self.landed_game()
        game.update(0.2)
        game.update(0.2)
        self.assertEqual(game.pieces_placed, 0)

    def test_piece_locks_after_the_delay(self):
        game = self.landed_game()
        for _ in range(3):
            game.update(0.2)
        self.assertEqual(game.pieces_placed, 1)

    def test_moving_restarts_the_delay(self):
        game = self.landed_game()
        game.update(0.2)
        game.update(0.2)
        game.move(1, 0)
        game.update(0.2)
        game.update(0.2)
        self.assertEqual(game.pieces_placed, 0)
        game.update(0.2)
        self.assertEqual(game.pieces_placed, 1)

    def test_resets_are_capped(self):
        game = self.landed_game()
        for i in range(1, 21):
            game.update(0.3)
            if i <= t.MAX_LOCK_RESETS + 1:
                self.assertEqual(game.pieces_placed, 0, i)
            game.move(1 if i % 2 else -1, 0)
        self.assertGreaterEqual(game.pieces_placed, 1)

    def test_hard_drop_still_locks_instantly(self):
        game = t.Game()
        game.hard_drop()
        self.assertEqual(game.pieces_placed, 1)


class EffectTests(unittest.TestCase):
    def test_clear_animation_runs_then_ends(self):
        game = t.Game()
        setup_single(game)
        game.hard_drop()
        self.assertEqual(game.clear_anim["rows"], [19])
        self.assertEqual(game.clear_anim["grid"][19][0], "X")
        game.update(0.1)
        self.assertIsNotNone(game.clear_anim)
        game.update(0.3)
        self.assertIsNone(game.clear_anim)

    def test_message_fades_out(self):
        game = t.Game()
        setup_single(game)
        game.hard_drop()
        self.assertTrue(game.message_lines)
        game.update(t.MESSAGE_TIME + 0.1)
        self.assertEqual(game.message_lines, [])

    def test_rotate_and_hold_make_events(self):
        game = t.Game()
        game.piece = t.Piece("T")
        game.rotate()
        game.hold()
        self.assertEqual(game.events[:2], ["rotate", "hold"])

    def test_game_over_makes_event(self):
        game = t.Game()
        for r in range(4):
            game.board.grid[r] = ["X"] * 10
        game._spawn_piece()
        self.assertEqual(game.state, "gameover")
        self.assertIn("gameover", game.events)


class ThemeAndSettingsTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "me.json")

    def tearDown(self):
        t.apply_theme("light")
        self.dir.cleanup()

    def test_apply_theme_changes_colors(self):
        t.apply_theme("dark")
        self.assertEqual(t.WHITE, t.THEMES["dark"]["WHITE"])
        self.assertEqual(t.current_theme, "dark")
        t.apply_theme("retro")
        self.assertEqual(t.PIECE_COLORS["I"], t.THEMES["retro"]["pieces"]["I"])
        t.apply_theme("light")
        self.assertEqual(t.WHITE, (245, 245, 245))

    def test_every_theme_colors_every_piece(self):
        for name, theme in t.THEMES.items():
            self.assertEqual(set(theme["pieces"]), set(t.PIECE_SHAPES), name)
        self.assertEqual(set(t.THEME_ORDER), set(t.THEMES))

    def test_unknown_theme_is_rejected(self):
        with self.assertRaises(ValueError):
            t.apply_theme("neon")

    def test_next_theme_cycles(self):
        self.assertEqual(t.next_theme("light"), "dark")
        self.assertEqual(t.next_theme("retro"), "light")

    def test_every_theme_can_draw_the_game_over_screen(self):
        pygame.font.init()
        font = pygame.font.Font(None, 22)
        for name in t.THEMES:
            t.apply_theme(name)
            screen = pygame.Surface(t.WINDOW_SIZE)
            t.draw_game_over(screen, font, font, t.Game())

    def test_settings_round_trip(self):
        t.save_settings({"theme": "retro", "muted": True}, self.path)
        self.assertEqual(t.load_settings(self.path), {"theme": "retro", "muted": True})

    def test_missing_or_broken_settings_give_defaults(self):
        default = {"theme": "light", "muted": False}
        self.assertEqual(t.load_settings(self.path), default)
        with open(self.path, "w") as f:
            f.write("not json")
        self.assertEqual(t.load_settings(self.path), default)

    def test_bad_values_fall_back_per_field(self):
        with open(self.path, "w") as f:
            json.dump({"theme": "neon", "muted": "yes"}, f)
        self.assertEqual(t.load_settings(self.path), {"theme": "light", "muted": False})

    def test_settings_path_is_per_player_and_lowercase(self):
        path = t.settings_path("Aiden_1")
        self.assertEqual(path.parent, t.SETTINGS_DIR)
        self.assertEqual(path.name, "aiden_1.json")


class SoundTests(unittest.TestCase):
    def test_synth_length_matches_duration(self):
        self.assertEqual(len(t.synth([(440, 0.1)])), int(t.SOUND_RATE * 0.1) * 2)
        self.assertEqual(len(t.synth([(440, 0.1)], channels=2)), int(t.SOUND_RATE * 0.1) * 4)

    def test_synth_stays_in_range_and_is_not_silent(self):
        import array
        samples = array.array("h", t.synth([(440, 0.05)]))
        self.assertTrue(any(samples))
        self.assertLessEqual(max(abs(s) for s in samples), 32767)

    def test_every_game_event_has_a_sound(self):
        for name in ("move", "rotate", "hold", "lock", "clear", "tetris",
                     "tspin", "levelup", "gameover"):
            self.assertIn(name, t.SOUND_NOTES)

    def test_mute_toggle_and_safe_play(self):
        pygame.init()
        bank = t.SoundBank()
        self.assertFalse(bank.muted)
        self.assertTrue(bank.toggle_mute())
        bank.play("lock")
        bank.play("no_such_sound")
        self.assertFalse(bank.toggle_mute())


class LayoutTests(unittest.TestCase):
    def test_pause_buttons_fit_the_panel_and_do_not_overlap(self):
        buttons = list(t.PAUSE_BUTTONS.values())
        self.assertEqual(set(t.PAUSE_BUTTONS), {"resume", "restart", "quit"})
        board = (t.BOARD_ORIGIN_X, t.BOARD_ORIGIN_Y,
                 t.BOARD_WIDTH * t.CELL_SIZE, t.BOARD_HEIGHT * t.CELL_SIZE)
        self.assertTrue(_inside(t.PAUSE_PANEL, board))
        for i, a in enumerate(buttons):
            self.assertTrue(_inside(a, t.PAUSE_PANEL), a)
            for b in buttons[i + 1:]:
                self.assertFalse(_overlap(a, b), (a, b))

    def test_stats_fit_above_the_game_over_buttons(self):
        center_y = t.BOARD_ORIGIN_Y + (t.BOARD_HEIGHT * t.CELL_SIZE) // 2
        panel_top = center_y + 60 - 160
        button_top = min(r[1] for r in t.GAME_OVER_BUTTONS.values())
        self.assertGreaterEqual(center_y - 72 - 25, panel_top - 5)  # title near top
        self.assertLess(center_y - 40 + 22 + 12, button_top)         # last stat line clears buttons


class PlayLoopSmokeTest(unittest.TestCase):
    """Drives play() with scripted events to check that pausing, themes,
    muting, game over and restarting all run without errors."""

    def test_scripted_session(self):
        pygame.init()
        screen = pygame.display.set_mode(t.WINDOW_SIZE)
        font = pygame.font.Font(None, 22)
        big = pygame.font.Font(None, 46)
        key = lambda k: pygame.event.Event(pygame.KEYDOWN, key=k)
        resume = t.PAUSE_BUTTONS["resume"]
        click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                   pos=(resume[0] + 5, resume[1] + 5))
        frames = [
            [key(pygame.K_t), key(pygame.K_m)],
            [key(pygame.K_p)], [],
            [click], [],
            [key(pygame.K_LEFT), key(pygame.K_UP), key(pygame.K_c), key(pygame.K_DOWN)],
            [key(pygame.K_SPACE)] * 40, [],
            [key(pygame.K_r)], [],
            [pygame.event.Event(pygame.QUIT)],
        ]
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(t, "SCORES_DIR", Path(tmp) / "scores"), \
                mock.patch.object(t, "SETTINGS_DIR", Path(tmp) / "settings"), \
                mock.patch.object(pygame.event, "get", side_effect=frames):
            result = t.play(screen, pygame.time.Clock(), font, big, "tester", t.SoundBank())
            saved = t.load_settings(t.settings_path("tester"))
        t.apply_theme("light")
        self.assertEqual(result, "quit")
        self.assertEqual(saved, {"theme": "dark", "muted": True})


if __name__ == "__main__":
    unittest.main()
