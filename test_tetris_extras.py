import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

import tetris_ver2 as t


def setup_tetris(game):
    """Rows 16-19 full except the last column, with a vertical I above it."""
    for r in range(16, 20):
        game.board.grid[r] = ["X"] * 9 + [None]
    game.piece = t.Piece("I")
    game.piece.rotation = 1
    game.piece.col = 7


def setup_single(game):
    """Bottom row full except cols 6-9, with a flat I piece above that gap."""
    game.board.grid[19] = ["X"] * 6 + [None] * 4
    game.piece = t.Piece("I")
    game.piece.col = 6


class NextQueueTests(unittest.TestCase):
    def test_three_pieces_are_shown(self):
        self.assertEqual(t.NEXT_QUEUE_SIZE, 3)
        self.assertEqual(len(t.NEXT_BOXES), 3)
        self.assertEqual(len(t.Game().next_queue), 3)

    def test_boxes_fit_in_the_window_and_do_not_overlap(self):
        width, height = t.WINDOW_SIZE
        for i, (x, y, w, h) in enumerate(t.NEXT_BOXES):
            self.assertTrue(x >= 0 and y >= 0 and x + w <= width and y + h <= height, i)
            if i:
                px, py, pw, ph = t.NEXT_BOXES[i - 1]
                self.assertGreaterEqual(y, py + ph)

    def test_queue_stays_full_and_comes_out_in_order(self):
        game = t.Game()
        for _ in range(30):
            shown = list(game.next_queue)
            self.assertEqual(len(shown), 3)
            game.hard_drop()
            if game.state != "playing":
                break
            self.assertEqual(game.piece.kind, shown[0])
            self.assertEqual(list(game.next_queue)[:2], shown[1:])

    def test_preview_draws_in_every_theme(self):
        pygame.font.init()
        font = pygame.font.Font(None, 22)
        for name in t.THEMES:
            t.apply_theme(name)
            t.draw_next_queue(pygame.Surface(t.WINDOW_SIZE), font, t.Game())
        t.apply_theme("light")


class BombTests(unittest.TestCase):
    def test_a_tetris_earns_a_bomb(self):
        game = t.Game()
        setup_tetris(game)
        game.hard_drop()
        self.assertEqual(game.bombs, 1)
        self.assertIn("bombready", game.events)

    def test_a_t_spin_line_clear_earns_a_bomb(self):
        game = t.Game()
        game.board.grid[19] = ["X"] * 4 + [None] * 3 + ["X"] * 3
        game.board.grid[18][4] = game.board.grid[18][6] = "X"
        game.piece = t.Piece("T")
        game.piece.row, game.piece.col = 18, 4
        game._rotated_last = True
        game._lock_active_piece()
        self.assertEqual(game.bombs, 1)

    def test_a_plain_clear_or_no_clear_earns_nothing(self):
        game = t.Game()
        setup_single(game)
        game.hard_drop()
        game.hard_drop()
        self.assertEqual(game.bombs, 0)

    def test_bombs_are_capped(self):
        game = t.Game()
        for _ in range(t.MAX_BOMBS + 2):
            setup_tetris(game)
            game.hard_drop()
        self.assertEqual(game.bombs, t.MAX_BOMBS)

    def test_bomb_blasts_the_bottom_rows_and_drops_the_rest(self):
        game = t.Game()
        game.bombs = 1
        game.board.grid[17] = ["A"] + [None] * 9
        game.board.grid[18] = ["B"] * 5 + [None] * 5
        game.board.grid[19] = ["C"] * 9 + [None]
        self.assertTrue(game.use_bomb())
        self.assertEqual(game.bombs, 0)
        # The two bottom rows are gone and the block that was in row 17 has
        # sunk two rows, to the floor.
        self.assertEqual(game.board.grid[19], ["A"] + [None] * 9)
        self.assertEqual(game.board.grid[18], [None] * 10)
        self.assertEqual(game.board.grid[17], [None] * 10)
        self.assertEqual(len(game.board.grid), t.BOARD_HEIGHT)
        self.assertEqual(game.score, t.BOMB_POINTS * 2 * game.level)

    def test_bomb_scores_and_announces(self):
        game = t.Game()
        game.bombs = 1
        game.board.grid[19] = ["C"] * 9 + [None]
        game.use_bomb()
        self.assertEqual(game.score, t.BOMB_POINTS * 1 * game.level)
        self.assertEqual(game.message_lines, ["BOOM!"])
        self.assertIn("bomb", game.events)

    def test_no_bomb_in_hand_does_nothing(self):
        game = t.Game()
        game.board.grid[19] = ["C"] * 9 + [None]
        before = [row[:] for row in game.board.grid]
        self.assertFalse(game.use_bomb())
        self.assertEqual(game.board.grid, before)

    def test_a_bomb_is_not_wasted_on_an_empty_floor(self):
        game = t.Game()
        game.bombs = 2
        self.assertFalse(game.use_bomb())
        self.assertEqual(game.bombs, 2)

    def test_no_bombs_while_paused_or_over(self):
        for state in ("paused", "gameover"):
            game = t.Game()
            game.bombs = 1
            game.board.grid[19] = ["C"] * 9 + [None]
            game.state = state
            self.assertFalse(game.use_bomb(), state)
            self.assertEqual(game.bombs, 1)

    def test_hud_and_hints_draw(self):
        pygame.font.init()
        font = pygame.font.Font(None, 22)
        screen = pygame.Surface(t.WINDOW_SIZE)
        game = t.Game()
        game.bombs = 2
        t.draw_hud(screen, font, game)
        t.draw_hints(screen, font, False)

    def test_b_key_uses_a_bomb_in_the_play_loop(self):
        pygame.init()
        screen = pygame.display.set_mode(t.WINDOW_SIZE)
        font = pygame.font.Font(None, 22)
        big = pygame.font.Font(None, 46)
        key = lambda k: pygame.event.Event(pygame.KEYDOWN, key=k)
        frames = [[key(pygame.K_b)], [pygame.event.Event(pygame.QUIT)]]
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(t, "SCORES_DIR", Path(tmp) / "scores"), \
                mock.patch.object(t, "SETTINGS_DIR", Path(tmp) / "settings"), \
                mock.patch.object(t.Game, "use_bomb", autospec=True) as bomb, \
                mock.patch.object(pygame.event, "get", side_effect=frames):
            t.play(screen, pygame.time.Clock(), font, big, "tester", t.SoundBank())
        t.apply_theme("light")
        bomb.assert_called_once()


class MusicTests(unittest.TestCase):
    def test_level_one_is_the_base_tempo(self):
        self.assertEqual(t.music_speed(1), 1.0)
        self.assertEqual(t.music_speed(0), 1.0)

    def test_music_gets_faster_every_level_up_to_a_limit(self):
        speeds = [t.music_speed(level) for level in range(1, t.MUSIC_MAX_LEVEL + 1)]
        self.assertEqual(speeds, sorted(set(speeds)))
        self.assertEqual(t.music_speed(t.MUSIC_MAX_LEVEL + 15), speeds[-1])

    def test_faster_levels_make_a_shorter_loop_with_the_same_notes(self):
        slow, fast = t.music_notes(1), t.music_notes(8)
        self.assertEqual([f for f, _ in slow], [f for f, _ in fast])
        self.assertLess(sum(s for _, s in fast), sum(s for _, s in slow))

    def test_loop_audio_matches_its_notes(self):
        notes = t.music_notes(3)
        total = sum(int(t.SOUND_RATE * seconds) for _, seconds in notes)
        self.assertEqual(len(t.synth(notes, volume=t.MUSIC_VOLUME)), total * 2)

    def test_music_follows_the_game_without_errors(self):
        pygame.init()
        music = t.Music()
        for level, state, muted in [(1, "playing", False), (1, "playing", False),
                                    (4, "playing", False), (4, "paused", False),
                                    (4, "playing", False), (4, "playing", True),
                                    (4, "playing", False), (6, "gameover", False)]:
            music.update(level, state, muted)
        music.stop()

    def test_each_tempo_is_built_once(self):
        pygame.init()
        music = t.Music()
        if not music.available:
            self.skipTest("no audio device")
        music.update(2, "playing", False)
        music.update(3, "playing", False)
        music.update(2, "playing", False)
        music.stop()
        self.assertEqual(set(music.loops), {2, 3})

    def test_muted_music_never_starts(self):
        pygame.init()
        music = t.Music()
        music.update(1, "playing", True)
        self.assertIsNone(music.channel)

    def test_new_sounds_exist(self):
        self.assertIn("bomb", t.SOUND_NOTES)
        self.assertIn("bombready", t.SOUND_NOTES)


if __name__ == "__main__":
    unittest.main()
