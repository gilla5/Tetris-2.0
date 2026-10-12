import json
import os
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import tetris_ver2 as t


class LeaderboardTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "scores.json")

    def tearDown(self):
        self.dir.cleanup()

    def test_missing_file_is_empty(self):
        self.assertEqual(t.load_scores(self.path), [])

    def test_broken_file_is_empty(self):
        with open(self.path, "w") as f:
            f.write("not json")
        self.assertEqual(t.load_scores(self.path), [])

    def test_wrong_shape_is_empty(self):
        with open(self.path, "w") as f:
            json.dump({"a": 1}, f)
        self.assertEqual(t.load_scores(self.path), [])

    def test_save_sorts_high_to_low(self):
        for score in (300, 900, 100):
            scores = t.save_score(score, self.path)
        self.assertEqual(scores, [900, 300, 100])
        self.assertEqual(t.load_scores(self.path), [900, 300, 100])

    def test_save_keeps_only_top_five(self):
        for score in (100, 200, 300, 400, 500, 600, 50):
            scores = t.save_score(score, self.path)
        self.assertEqual(scores, [600, 500, 400, 300, 200])

    def test_zero_score_is_not_saved(self):
        self.assertEqual(t.save_score(0, self.path), [])
        self.assertFalse(os.path.exists(self.path))


class DrawingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.font.init()
        cls.font = pygame.font.Font(None, 22)

    def test_draw_cell_fills_center_and_leaves_outside(self):
        screen = pygame.Surface((60, 60))
        screen.fill(t.WHITE)
        color = t.PIECE_COLORS["T"]
        t.draw_cell(screen, 10, 10, 28, color)
        self.assertEqual(tuple(screen.get_at((24, 24)))[:3], color)
        self.assertEqual(tuple(screen.get_at((9, 9)))[:3], t.WHITE)

    def test_draw_cell_top_left_is_lighter_than_bottom_right(self):
        screen = pygame.Surface((60, 60))
        t.draw_cell(screen, 10, 10, 28, t.PIECE_COLORS["I"])
        top_left = sum(screen.get_at((12, 12))[:3])
        bottom_right = sum(screen.get_at((36, 36))[:3])
        self.assertGreater(top_left, bottom_right)

    def test_draw_leaderboard_draws_with_and_without_scores(self):
        for scores in ([], [900, 300, 100]):
            screen = pygame.Surface(t.WINDOW_SIZE)
            screen.fill(t.WHITE)
            t.draw_leaderboard(screen, self.font, scores, highlight=0 if scores else None)
            changed = pygame.mask.from_threshold(
                screen, t.WHITE, (1, 1, 1, 255)).count()
            self.assertLess(changed, t.WINDOW_SIZE[0] * t.WINDOW_SIZE[1])

    def test_ghost_cells_does_not_move_the_piece(self):
        game = t.Game()
        before = (game.piece.row, game.piece.col)
        t.ghost_cells(game.board, game.piece)
        self.assertEqual((game.piece.row, game.piece.col), before)


class PauseTests(unittest.TestCase):
    def test_toggle_pauses_and_resumes(self):
        game = t.Game()
        game.toggle_pause()
        self.assertEqual(game.state, "paused")
        game.toggle_pause()
        self.assertEqual(game.state, "playing")

    def test_toggle_does_nothing_after_game_over(self):
        game = t.Game()
        game.state = "gameover"
        game.toggle_pause()
        self.assertEqual(game.state, "gameover")

    def test_gravity_stops_while_paused(self):
        game = t.Game()
        game.toggle_pause()
        row = game.piece.row
        game.update(10.0)
        self.assertEqual(game.piece.row, row)

    def test_no_actions_while_paused(self):
        game = t.Game()
        game.toggle_pause()
        piece = game.piece
        before = (piece.row, piece.col, piece.rotation, game.score, game.hold_kind)
        self.assertFalse(game.move(-1, 0))
        game.rotate()
        game.soft_drop()
        game.hard_drop()
        game.hold()
        after = (piece.row, piece.col, piece.rotation, game.score, game.hold_kind)
        self.assertEqual(before, after)
        self.assertIs(game.piece, piece)

    def test_piece_moves_again_after_resume(self):
        game = t.Game()
        game.toggle_pause()
        game.toggle_pause()
        self.assertTrue(game.move(-1, 0))

    def test_draw_pause_covers_the_board(self):
        pygame.font.init()
        font = pygame.font.Font(None, 22)
        screen = pygame.Surface(t.WINDOW_SIZE)
        screen.fill(t.WHITE)
        game = t.Game()
        game.board.grid[0][0] = "T"
        t.draw_board(screen, game.board)
        t.draw_pause(screen, font, font)
        corner = (t.BOARD_ORIGIN_X + 5, t.BOARD_ORIGIN_Y + 5)
        self.assertEqual(tuple(screen.get_at(corner))[:3], t.PANEL_BG)


def fill_row(game, row, skip=None):
    for col in range(t.BOARD_WIDTH):
        if col != skip:
            game.board.grid[row][col] = "J"


def game_one_move_from_a_clear():
    """A game where dropping the active I piece finishes the bottom row."""
    game = t.Game()
    game.piece = t.Piece("I")
    last = t.BOARD_HEIGHT - 1
    fill_row(game, last)
    for col in range(3, 7):
        game.board.grid[last][col] = None
    game.piece.col = 3
    game.piece.row = last - 1
    return game


class LineClearAnimationTests(unittest.TestCase):
    def test_full_rows_lists_only_full_rows(self):
        game = t.Game()
        fill_row(game, 19)
        fill_row(game, 18, skip=4)
        self.assertEqual(game.board.full_rows(), [19])

    def test_clear_waits_for_the_animation(self):
        game = game_one_move_from_a_clear()
        game.hard_drop()
        self.assertEqual(game.state, "clearing")
        self.assertEqual(game.clearing_rows, [t.BOARD_HEIGHT - 1])
        self.assertEqual(game.lines_cleared, 0)
        self.assertIsNotNone(game.board.grid[t.BOARD_HEIGHT - 1][0])

    def test_rows_are_removed_and_scored_when_it_ends(self):
        game = game_one_move_from_a_clear()
        game.hard_drop()
        before = game.score
        game.update(t.CLEAR_ANIM_SECONDS + 0.01)
        self.assertEqual(game.state, "playing")
        self.assertEqual(game.clearing_rows, [])
        self.assertEqual(game.lines_cleared, 1)
        self.assertEqual(game.score, before + t.LINE_CLEAR_SCORE[1])
        self.assertTrue(all(cell is None for cell in game.board.grid[t.BOARD_HEIGHT - 1]))

    def test_no_input_or_gravity_during_the_animation(self):
        game = game_one_move_from_a_clear()
        game.hard_drop()
        piece = game.piece
        row = piece.row
        game.update(t.CLEAR_ANIM_SECONDS / 2)
        game.soft_drop()
        game.hold()
        self.assertFalse(game.move(0, 1))
        self.assertEqual(game.state, "clearing")
        self.assertEqual((game.piece.row, game.hold_kind), (row, None))

    def test_pause_is_ignored_during_the_animation(self):
        game = game_one_move_from_a_clear()
        game.hard_drop()
        game.toggle_pause()
        self.assertEqual(game.state, "clearing")

    def test_no_clear_means_no_animation(self):
        game = t.Game()
        game.hard_drop()
        self.assertEqual(game.state, "playing")
        self.assertEqual(game.clearing_rows, [])

    def test_progress_goes_from_zero_to_one(self):
        game = game_one_move_from_a_clear()
        self.assertEqual(game.clear_progress, 0.0)
        game.hard_drop()
        game.update(t.CLEAR_ANIM_SECONDS / 2)
        self.assertAlmostEqual(game.clear_progress, 0.5, places=2)

    def test_level_up_starts_the_banner_timer(self):
        game = game_one_move_from_a_clear()
        game.lines_cleared = t.LINES_PER_LEVEL - 1
        game.hard_drop()
        game.update(t.CLEAR_ANIM_SECONDS + 0.01)
        self.assertEqual(game.level, 2)
        self.assertGreater(game.level_up_timer, 0)
        game.update(t.LEVEL_UP_SECONDS)
        self.assertEqual(game.level_up_timer, 0)

    def test_no_banner_without_a_level_up(self):
        game = game_one_move_from_a_clear()
        game.hard_drop()
        game.update(t.CLEAR_ANIM_SECONDS + 0.01)
        self.assertEqual(game.level_up_timer, 0)


class ClearColorTests(unittest.TestCase):
    color = t.PIECE_COLORS["T"]

    def test_row_blinks_white_then_color(self):
        first = t.clear_cell_color(self.color, 0, 10, 0.01)
        second = t.clear_cell_color(self.color, 0, 10, 0.2)
        self.assertEqual(first, t.WHITE)
        self.assertEqual(second, self.color)

    def test_middle_vanishes_before_the_edges(self):
        self.assertIsNone(t.clear_cell_color(self.color, 4, 10, 0.8))
        self.assertIsNotNone(t.clear_cell_color(self.color, 0, 10, 0.8))

    def test_everything_is_gone_at_the_end(self):
        for col in range(10):
            self.assertIsNone(t.clear_cell_color(self.color, col, 10, 1.0))

    def test_draw_board_skips_wiped_blocks(self):
        screen = pygame.Surface(t.WINDOW_SIZE)
        game = t.Game()
        fill_row(game, 19)
        screen.fill(t.WHITE)
        t.draw_board(screen, game.board, [19], 1.0)
        x = t.BOARD_ORIGIN_X + 3 * t.CELL_SIZE + t.CELL_SIZE // 2
        y = t.BOARD_ORIGIN_Y + 19 * t.CELL_SIZE + t.CELL_SIZE // 2
        self.assertEqual(tuple(screen.get_at((x, y)))[:3], t.WHITE)

    def test_draw_level_up_draws_something(self):
        pygame.font.init()
        font = pygame.font.Font(None, 40)
        screen = pygame.Surface(t.WINDOW_SIZE)
        screen.fill(t.WHITE)
        t.draw_level_up(screen, font, 2, t.LEVEL_UP_SECONDS)
        white = pygame.mask.from_threshold(screen, t.WHITE, (1, 1, 1, 255)).count()
        self.assertLess(white, t.WINDOW_SIZE[0] * t.WINDOW_SIZE[1])


if __name__ == "__main__":
    unittest.main()
