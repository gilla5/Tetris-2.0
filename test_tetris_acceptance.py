"""Acceptance tests: does the game do what a player (or the instructor)
asked for? Each test is a short story written as Given / When / Then, using
only things a player can see or do: sign up, play, score, pause, game over,
saved scores, settings, and shared scores.

They are named after the requirements in SOFTWARE_DESIGN.md (R1 to R10).
"""
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

import cloud_server
import cloud_sync
import tetris_ver2 as t


def key(k, char=""):
    return pygame.event.Event(pygame.KEYDOWN, key=k, unicode=char)


def four_lines_ready(game):
    """Rows 16-19 are full except the last column; a vertical I is above it."""
    for r in range(16, 20):
        game.board.grid[r] = ["X"] * 9 + [None]
    game.piece = t.Piece("I")
    game.piece.rotation = 1
    game.piece.col = 7


class TempFolders(unittest.TestCase):
    """Gives each test its own empty accounts, scores, and settings folders."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        root = Path(self.dir.name)
        self.users = str(root / "users.json")
        patches = [mock.patch.object(t, "SCORES_DIR", root / "scores"),
                   mock.patch.object(t, "SETTINGS_DIR", root / "settings"),
                   mock.patch.object(t, "PBKDF2_ITERATIONS", 1000)]  # fast hashing
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.dir.cleanup)
        self.addCleanup(t.apply_theme, "light")

    def type_text(self, screen, text):
        for ch in text:
            screen.handle_key(ord(ch), ch)

    def sign_up(self, name, password, confirm=None):
        screen = t.LoginScreen(self.users)
        layout = t.login_layout("login")["switch"]
        x, y, w, h = layout
        screen.handle_click((x + w // 2, y + h // 2))        # Create an account
        self.type_text(screen, name); screen.handle_key(pygame.K_RETURN)
        self.type_text(screen, password); screen.handle_key(pygame.K_RETURN)
        self.type_text(screen, confirm or password); screen.handle_key(pygame.K_RETURN)
        return screen

    def sign_in(self, name, password):
        screen = t.LoginScreen(self.users)
        self.type_text(screen, name); screen.handle_key(pygame.K_RETURN)
        self.type_text(screen, password); screen.handle_key(pygame.K_RETURN)
        return screen


class AccountStories(TempFolders):
    def test_R1_a_new_player_can_sign_up_and_is_signed_in(self):
        """Given a new player, when they fill in the Sign Up page, then they are in the game."""
        screen = self.sign_up("Aiden", "hunter22")
        self.assertEqual(screen.user, "Aiden")

    def test_R1_a_returning_player_can_sign_in(self):
        """Given an account exists, when its owner signs in, then they are in the game."""
        self.sign_up("Aiden", "hunter22")
        self.assertEqual(self.sign_in("aiden", "hunter22").user, "Aiden")  # name is not case sensitive

    def test_R1_a_wrong_password_is_refused_without_saying_which_part_was_wrong(self):
        """Given an account, when someone gives a wrong password or a name that doesn't exist, then they see the same message."""
        self.sign_up("Aiden", "hunter22")
        wrong_password = self.sign_in("aiden", "nope1234")
        unknown_name = self.sign_in("nobody", "hunter22")
        self.assertIsNone(wrong_password.user)
        self.assertIsNone(unknown_name.user)
        self.assertEqual(wrong_password.message, unknown_name.message)
        self.assertEqual(wrong_password.message, "Wrong username or password.")

    def test_R1_sign_up_explains_what_to_fix(self):
        self.assertIn("3-12", self.sign_up("ab", "hunter22").message)
        self.assertIn("6-64", self.sign_up("aiden", "short").message)
        self.assertIn("match", self.sign_up("aiden", "hunter22", "hunter23").message)
        self.sign_up("taken_name", "hunter22")
        self.assertIn("taken", self.sign_up("Taken_Name", "otherpass1").message)

    def test_R1_passwords_are_never_written_down(self):
        self.sign_up("aiden", "hunter22")
        self.assertNotIn("hunter22", Path(self.users).read_text())


class GameplayStories(unittest.TestCase):
    def test_R3_a_piece_falls_on_its_own_and_the_player_can_steer_it(self):
        """Given a new game, when time passes and the player moves, then the piece falls and shifts."""
        game = t.Game()
        row, col = game.piece.row, game.piece.col
        game.update(1.0)
        self.assertEqual(game.piece.row, row + 1)
        game.move(1, 0)
        self.assertEqual(game.piece.col, col + 1)
        before = game.piece.rotation
        game.rotate()
        if game.piece.kind != "O":  # the O piece looks the same in every rotation
            self.assertNotEqual(game.piece.rotation, before)

    def test_R3_a_hard_drop_lands_at_once_and_the_next_piece_appears(self):
        game = t.Game()
        first_next = game.next_queue[0]
        game.hard_drop()
        self.assertEqual(game.pieces_placed, 1)
        self.assertEqual(game.piece.kind, first_next)
        self.assertGreater(game.score, 0)

    def test_R2_the_player_sees_the_next_three_pieces_and_can_hold_one(self):
        game = t.Game()
        self.assertEqual(len(game.next_queue), 3)
        current = game.piece.kind
        game.hold()
        self.assertEqual(game.hold_kind, current)
        game.hold()  # a second hold on the same piece does nothing
        self.assertEqual(game.hold_kind, current)

    def test_R4_clearing_four_lines_scores_a_tetris(self):
        """Given four nearly full rows, when an I piece is dropped in the gap, then TETRIS scores 800 at level 1."""
        game = t.Game()
        four_lines_ready(game)
        game.hard_drop()
        self.assertEqual(game.lines_cleared, 4)
        self.assertEqual(game.score, 32 + 800)      # 16 rows hard dropped x 2, plus the Tetris
        self.assertEqual(game.message_lines, ["TETRIS"])
        self.assertEqual(game.board.grid[19], [None] * 10)

    def test_R4_ten_lines_raise_the_level_and_speed(self):
        game = t.Game()
        game.lines_cleared = 9
        game.board.grid[19] = ["X"] * 6 + [None] * 4
        game.piece = t.Piece("I")
        game.piece.col = 6
        game.hard_drop()
        self.assertEqual(game.level, 2)
        self.assertLess(t.gravity_interval(2), t.gravity_interval(1))
        self.assertGreater(game.level_up_timer, 0)

    def test_R6_a_tetris_earns_a_bomb_and_the_bomb_clears_the_bottom_rows(self):
        game = t.Game()
        four_lines_ready(game)
        game.hard_drop()
        self.assertEqual(game.bombs, 1)
        game.board.grid[19] = ["X"] * 9 + [None]
        game.board.grid[18] = ["X"] * 9 + [None]
        self.assertTrue(game.use_bomb())
        self.assertEqual(game.bombs, 0)
        self.assertEqual(game.board.grid[19], [None] * 10)
        self.assertEqual(game.board.grid[18], [None] * 10)

    def test_R8_pausing_stops_the_game_and_resuming_continues_it(self):
        game = t.Game()
        game.update(0.4)
        game.toggle_pause()
        frozen = (game.piece.row, game.elapsed)
        game.update(10.0)
        game.hard_drop()
        self.assertEqual((game.piece.row, game.elapsed), frozen)
        game.toggle_pause()
        game.update(0.5)
        self.assertGreater(game.elapsed, frozen[1])

    def test_R8_the_game_ends_when_the_stack_reaches_the_top_and_reports_stats(self):
        game = t.Game()
        for _ in range(60):
            game.update(0.2)
            game.hard_drop()
            if game.state == "gameover":
                break
        self.assertEqual(game.state, "gameover")
        self.assertGreater(game.pieces_placed, 0)
        self.assertGreaterEqual(game.level, 1)
        self.assertGreater(game.elapsed, 0)
        self.assertIn("gameover", game.events)
        game.hard_drop()  # nothing more can happen
        self.assertEqual(game.state, "gameover")


class SavedDataStories(TempFolders):
    def test_R9_each_player_keeps_their_own_top_five(self):
        for score in (100, 900, 300, 700, 500, 200):
            t.save_score(score, t.scores_path("aiden"))
        t.save_score(42, t.scores_path("nathan"))
        self.assertEqual(t.load_scores(t.scores_path("aiden")), [900, 700, 500, 300, 200])
        self.assertEqual(t.load_scores(t.scores_path("nathan")), [42])
        self.assertEqual(t.load_scores(t.scores_path("caleb")), [])

    def test_R8_theme_and_sound_are_remembered_per_player(self):
        t.save_settings({"theme": "retro", "muted": True}, t.settings_path("aiden"))
        t.save_settings({"theme": "dark", "muted": False}, t.settings_path("nathan"))
        self.assertEqual(t.load_settings(t.settings_path("aiden")), {"theme": "retro", "muted": True})
        self.assertEqual(t.load_settings(t.settings_path("nathan")), {"theme": "dark", "muted": False})
        self.assertEqual(t.load_settings(t.settings_path("caleb")), {"theme": "light", "muted": False})


class SharedScoreStories(TempFolders):
    def start_server(self):
        server = cloud_server.make_server("127.0.0.1", 0, Path(self.dir.name) / "cloud.json", "k")
        threading.Thread(target=server.serve_forever, daemon=True).start()

        def stop():
            server.shutdown()
            server.server_close()
        self.addCleanup(stop)
        return cloud_sync.CloudSync(f"http://127.0.0.1:{server.server_address[1]}", "k")

    def test_R10_scores_follow_a_player_to_another_computer(self):
        """Given scores earned on computer A, when the player signs in on computer B with sync on, then B shows them."""
        cloud = self.start_server()
        computer_a = Path(self.dir.name) / "a" / "aiden.json"
        computer_b = Path(self.dir.name) / "b" / "aiden.json"
        t.write_scores([900, 300], computer_a)
        t.sync_scores("aiden", computer_a, cloud)
        scores, synced = t.sync_scores("aiden", computer_b, cloud)
        self.assertTrue(synced)
        self.assertEqual(scores, [900, 300])

    def test_R10_the_game_still_saves_scores_when_the_server_is_down(self):
        down = cloud_sync.CloudSync("http://127.0.0.1:1", timeout=0.3)
        path = t.scores_path("aiden")
        t.save_score(500, path)
        scores, synced = t.sync_scores("aiden", path, down)
        self.assertEqual((scores, synced), ([500], False))


class WholeSessionStories(TempFolders):
    def run_play(self, frames, user="tester", cloud=None):
        pygame.init()
        screen = pygame.display.set_mode(t.WINDOW_SIZE)
        font = pygame.font.Font(None, 22)
        big = pygame.font.Font(None, 46)
        with mock.patch.object(pygame.event, "get", side_effect=frames):
            return t.play(screen, pygame.time.Clock(), font, big, user, t.SoundBank(),
                          cloud=cloud or cloud_sync.CloudSync())

    def test_a_full_game_from_first_move_to_sign_out(self):
        """Steer, hold, pause, resume, play to game over, restart, play again, sign out."""
        frames = [
            [key(pygame.K_LEFT), key(pygame.K_UP), key(pygame.K_c), key(pygame.K_t)],
            [key(pygame.K_p)], [], [key(pygame.K_p)], [],
            [key(pygame.K_SPACE)] * 40, [],                   # game over, score saved
            [key(pygame.K_r)], [],                            # restart
            [key(pygame.K_SPACE)] * 40, [],                   # game over again
            [key(pygame.K_l)],                                # sign out
        ]
        self.assertEqual(self.run_play(frames), "logout")
        self.assertTrue(t.load_scores(t.scores_path("tester")))
        self.assertEqual(t.load_settings(t.settings_path("tester"))["theme"], "dark")

    def test_quitting_from_the_pause_menu_keeps_the_score(self):
        frames = [[key(pygame.K_SPACE)] * 3, [key(pygame.K_p)], [], [key(pygame.K_q)]]
        self.assertEqual(self.run_play(frames), "quit")
        self.assertTrue(t.load_scores(t.scores_path("tester")))

    def test_signing_out_in_the_middle_of_a_game_keeps_the_score(self):
        frames = [[key(pygame.K_SPACE)] * 3, [],
                  [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                      pos=(t.SIGN_OUT_BUTTON[0] + 5, t.SIGN_OUT_BUTTON[1] + 5))]]
        self.assertEqual(self.run_play(frames), "logout")
        self.assertTrue(t.load_scores(t.scores_path("tester")))


if __name__ == "__main__":
    unittest.main()
