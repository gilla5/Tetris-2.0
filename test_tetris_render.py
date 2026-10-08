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


if __name__ == "__main__":
    unittest.main()
