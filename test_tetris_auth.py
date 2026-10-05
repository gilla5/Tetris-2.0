import json
import os
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import tetris_ver2 as t


class AccountTestCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "users.json")
        # The real work factor makes every hash take a noticeable moment;
        # use a tiny one so the tests stay fast.
        self._iterations = t.PBKDF2_ITERATIONS
        t.PBKDF2_ITERATIONS = 1000

    def tearDown(self):
        t.PBKDF2_ITERATIONS = self._iterations
        self.dir.cleanup()


class ValidationTests(AccountTestCase):
    def test_good_credentials_pass(self):
        self.assertIsNone(t.validate_new_account("Aiden_1", "secret1"))

    def test_username_too_short(self):
        self.assertIsNotNone(t.validate_new_account("ab", "secret1"))

    def test_username_too_long(self):
        self.assertIsNotNone(t.validate_new_account("a" * 13, "secret1"))

    def test_username_rejects_odd_characters(self):
        for name in ("bad name", "../evil", "a/b/c", "name!", ""):
            self.assertIsNotNone(t.validate_new_account(name, "secret1"), name)

    def test_password_length_limits(self):
        self.assertIsNotNone(t.validate_new_account("aiden", "12345"))
        self.assertIsNotNone(t.validate_new_account("aiden", "x" * 65))
        self.assertIsNone(t.validate_new_account("aiden", "x" * 64))

    def test_password_cannot_match_username(self):
        self.assertIsNotNone(t.validate_new_account("aiden99", "AIDEN99"))


class RegisterAndLoginTests(AccountTestCase):
    def test_register_then_authenticate(self):
        name, error = t.register_user("Aiden", "hunter22", self.path)
        self.assertEqual((name, error), ("Aiden", None))
        self.assertEqual(t.authenticate("Aiden", "hunter22", self.path), "Aiden")

    def test_wrong_password_fails(self):
        t.register_user("Aiden", "hunter22", self.path)
        self.assertIsNone(t.authenticate("Aiden", "hunter23", self.path))
        self.assertIsNone(t.authenticate("Aiden", "", self.path))

    def test_unknown_user_fails(self):
        self.assertIsNone(t.authenticate("nobody", "whatever1", self.path))

    def test_username_is_case_insensitive_and_keeps_display_name(self):
        t.register_user("Aiden", "hunter22", self.path)
        self.assertEqual(t.authenticate("aIDEN", "hunter22", self.path), "Aiden")

    def test_duplicate_username_rejected_ignoring_case(self):
        t.register_user("Aiden", "hunter22", self.path)
        name, error = t.register_user("AIDEN", "another1", self.path)
        self.assertIsNone(name)
        self.assertIn("taken", error)
        # and the original password still works
        self.assertEqual(t.authenticate("aiden", "hunter22", self.path), "Aiden")

    def test_invalid_registration_is_not_saved(self):
        name, error = t.register_user("ab", "hunter22", self.path)
        self.assertIsNone(name)
        self.assertIsNotNone(error)
        self.assertFalse(os.path.exists(self.path))

    def test_password_is_not_stored_in_plain_text(self):
        t.register_user("Aiden", "hunter22", self.path)
        with open(self.path) as f:
            self.assertNotIn("hunter22", f.read())

    def test_same_password_gets_different_salt_and_hash(self):
        t.register_user("aiden", "samepass1", self.path)
        t.register_user("nathan", "samepass1", self.path)
        users = t.load_users(self.path)
        self.assertNotEqual(users["aiden"]["salt"], users["nathan"]["salt"])
        self.assertNotEqual(users["aiden"]["hash"], users["nathan"]["hash"])

    def test_old_accounts_still_work_after_work_factor_changes(self):
        t.register_user("aiden", "hunter22", self.path)
        t.PBKDF2_ITERATIONS = 2000
        self.assertEqual(t.authenticate("aiden", "hunter22", self.path), "aiden")

    def test_registration_fails_cleanly_if_file_cannot_be_written(self):
        bad_path = os.path.join(self.dir.name, "missing_folder", "users.json")
        name, error = t.register_user("aiden", "hunter22", bad_path)
        self.assertIsNone(name)
        self.assertIsNotNone(error)


class StorageTests(AccountTestCase):
    def test_missing_file_is_empty(self):
        self.assertEqual(t.load_users(self.path), {})

    def test_broken_file_is_empty(self):
        with open(self.path, "w") as f:
            f.write("not json")
        self.assertEqual(t.load_users(self.path), {})

    def test_wrong_shape_is_empty(self):
        with open(self.path, "w") as f:
            json.dump(["a", "b"], f)
        self.assertEqual(t.load_users(self.path), {})

    def test_malformed_and_tampered_records_are_ignored(self):
        good = {"name": "aiden", "salt": "00", "hash": "00", "iterations": 5}
        with open(self.path, "w") as f:
            json.dump({
                "aiden": good,
                "../evil": {**good, "name": "../evil"},     # path trick
                "nathan": {**good, "name": "someoneelse"},  # key/name mismatch
                "caleb": {"name": "caleb"},                  # missing fields
                "jacob": "nope",
            }, f)
        self.assertEqual(list(t.load_users(self.path)), ["aiden"])

    def test_garbled_hex_fails_login_instead_of_crashing(self):
        with open(self.path, "w") as f:
            json.dump({"aiden": {"name": "aiden", "salt": "zz", "hash": "zz",
                                 "iterations": 5}}, f)
        self.assertIsNone(t.authenticate("aiden", "hunter22", self.path))

    def test_save_leaves_no_temp_file(self):
        t.register_user("aiden", "hunter22", self.path)
        self.assertEqual(os.listdir(self.dir.name), ["users.json"])

    @unittest.skipIf(os.name == "nt", "file modes work differently on Windows")
    def test_accounts_file_is_owner_only(self):
        t.register_user("aiden", "hunter22", self.path)
        self.assertEqual(os.stat(self.path).st_mode & 0o777, 0o600)


class ScoresPathTests(AccountTestCase):
    def test_path_is_inside_scores_dir_and_lowercase(self):
        path = t.scores_path("Aiden")
        self.assertEqual(path.parent, t.SCORES_DIR)
        self.assertEqual(path.name, "aiden.json")

    def test_each_player_has_their_own_scores(self):
        a = os.path.join(self.dir.name, "scores", "aiden.json")
        n = os.path.join(self.dir.name, "scores", "nathan.json")
        t.save_score(500, a)   # also creates the scores folder
        t.save_score(900, n)
        self.assertEqual(t.load_scores(a), [500])
        self.assertEqual(t.load_scores(n), [900])


class LoginScreenTests(AccountTestCase):
    def setUp(self):
        super().setUp()
        self.screen = t.LoginScreen(self.path)

    def type_text(self, text):
        for ch in text:
            self.screen.handle_key(ord(ch), ch)

    def press(self, key):
        self.screen.handle_key(key, "")

    def click(self, name, field=None):
        """Click the middle of a button on the current page."""
        layout = t.login_layout(self.screen.mode)
        rect = layout[name][field] if field else layout[name]
        x, y, w, h = rect
        return self.screen.handle_click((x + w // 2, y + h // 2))

    def go_to_sign_up(self):
        self.click("switch")
        self.assertEqual(self.screen.mode, "register")

    def fill_sign_up(self, username, password, confirm):
        self.click("fields", "username")
        self.type_text(username)
        self.click("fields", "password")
        self.type_text(password)
        self.click("fields", "confirm")
        self.type_text(confirm)

    # --- typing -----------------------------------------------------------
    def test_typing_goes_to_the_active_field(self):
        self.type_text("aiden")
        self.press(pygame.K_TAB)
        self.type_text("hunter22")
        self.assertEqual(self.screen.values["username"], "aiden")
        self.assertEqual(self.screen.values["password"], "hunter22")

    def test_username_ignores_disallowed_characters_and_limits_length(self):
        self.type_text("ai den!/..")
        self.assertEqual(self.screen.values["username"], "aiden")
        self.type_text("x" * 30)
        self.assertEqual(len(self.screen.values["username"]), t.USERNAME_MAX_LEN)

    def test_password_may_contain_symbols_and_spaces(self):
        self.press(pygame.K_TAB)
        self.type_text("p@ss word!")
        self.assertEqual(self.screen.values["password"], "p@ss word!")

    def test_backspace_deletes(self):
        self.type_text("aidenx")
        self.press(pygame.K_BACKSPACE)
        self.assertEqual(self.screen.values["username"], "aiden")

    def test_non_printable_keys_do_nothing(self):
        self.screen.handle_key(pygame.K_ESCAPE, "\x1b")
        self.screen.handle_key(pygame.K_LEFT, "")
        self.assertEqual(self.screen.values["username"], "")

    def test_tab_cycles_fields(self):
        self.press(pygame.K_TAB)
        self.assertEqual(self.screen.active, 1)
        self.press(pygame.K_TAB)
        self.assertEqual(self.screen.active, 0)
        self.press(pygame.K_UP)
        self.assertEqual(self.screen.active, 1)

    def test_enter_on_first_field_moves_on_without_submitting(self):
        self.type_text("aiden")
        self.press(pygame.K_RETURN)
        self.assertEqual(self.screen.active, 1)
        self.assertEqual(self.screen.message, "")
        self.assertIsNone(self.screen.user)

    # --- clicking ---------------------------------------------------------
    def test_clicking_a_field_focuses_it(self):
        self.click("fields", "password")
        self.assertEqual(self.screen.active, 1)
        self.type_text("hunter22")
        self.click("fields", "username")
        self.assertEqual(self.screen.active, 0)
        self.type_text("aiden")
        self.assertEqual(self.screen.values["password"], "hunter22")
        self.assertEqual(self.screen.values["username"], "aiden")

    def test_clicking_empty_space_changes_nothing(self):
        self.click("fields", "password")
        self.assertIsNone(self.screen.handle_click((5, 5)))
        self.assertEqual(self.screen.active, 1)
        self.assertEqual(self.screen.mode, "login")

    def test_switch_button_goes_between_sign_in_and_sign_up(self):
        self.assertEqual(self.screen.mode, "login")
        self.assertEqual(len(self.screen.fields), 2)
        self.click("switch")
        self.assertEqual(self.screen.mode, "register")
        self.assertEqual(len(self.screen.fields), 3)
        self.assertNotEqual(self.screen.heading,
                            t.LoginScreen(self.path).heading)
        self.click("switch")  # the same spot is now "Back to Sign In"
        self.assertEqual(self.screen.mode, "login")

    def test_quit_button_returns_quit(self):
        self.assertEqual(self.click("quit"), "quit")
        self.go_to_sign_up()
        self.assertEqual(self.click("quit"), "quit")

    def test_other_buttons_do_not_return_quit(self):
        self.assertIsNone(self.click("switch"))
        self.assertIsNone(self.click("submit"))

    # --- show / hide password ---------------------------------------------
    def test_show_button_toggles_password_visibility(self):
        self.assertFalse(self.screen.show_password)
        self.click("toggles", "password")
        self.assertTrue(self.screen.show_password)
        self.click("toggles", "password")
        self.assertFalse(self.screen.show_password)

    def test_show_button_does_not_change_what_was_typed_or_the_focus(self):
        self.click("fields", "password")
        self.type_text("hunter22")
        self.click("fields", "username")
        self.click("toggles", "password")
        self.assertEqual(self.screen.values["password"], "hunter22")
        self.assertEqual(self.screen.active, 0)

    def test_sign_up_page_has_a_show_button_for_both_password_fields(self):
        self.go_to_sign_up()
        layout = t.login_layout("register")
        self.assertEqual(set(layout["toggles"]), {"password", "confirm"})
        self.click("toggles", "confirm")
        self.assertTrue(self.screen.show_password)

    def test_passwords_are_hidden_again_after_switching_pages(self):
        self.click("toggles", "password")
        self.go_to_sign_up()
        self.assertFalse(self.screen.show_password)

    # --- sign up ----------------------------------------------------------
    def test_sign_up_flow_signs_the_player_in(self):
        self.go_to_sign_up()
        self.fill_sign_up("Aiden", "hunter22", "hunter22")
        self.click("submit")
        self.assertEqual(self.screen.user, "Aiden")
        self.assertEqual(t.authenticate("aiden", "hunter22", self.path), "Aiden")

    def test_sign_up_with_mismatched_passwords_is_refused(self):
        self.go_to_sign_up()
        self.fill_sign_up("aiden", "hunter22", "hunter23")
        self.click("submit")
        self.assertIsNone(self.screen.user)
        self.assertIn("match", self.screen.message)
        self.assertEqual(self.screen.values["password"], "")
        self.assertEqual(t.load_users(self.path), {})

    def test_sign_up_shows_validation_error(self):
        self.go_to_sign_up()
        self.fill_sign_up("ai", "hunter22", "hunter22")
        self.click("submit")
        self.assertIsNone(self.screen.user)
        self.assertIn("Username", self.screen.message)

    def test_sign_up_with_taken_username_is_refused(self):
        t.register_user("Aiden", "hunter22", self.path)
        self.go_to_sign_up()
        self.fill_sign_up("aiden", "another1", "another1")
        self.click("submit")
        self.assertIsNone(self.screen.user)
        self.assertIn("taken", self.screen.message)

    def test_enter_on_last_field_also_submits(self):
        self.go_to_sign_up()
        self.fill_sign_up("Aiden", "hunter22", "hunter22")
        self.press(pygame.K_RETURN)
        self.assertEqual(self.screen.user, "Aiden")

    # --- sign in ----------------------------------------------------------
    def test_sign_in_success(self):
        t.register_user("Aiden", "hunter22", self.path)
        self.click("fields", "username")
        self.type_text("aiden")
        self.click("fields", "password")
        self.type_text("hunter22")
        self.click("submit")
        self.assertEqual(self.screen.user, "Aiden")

    def test_sign_in_failure_is_generic_and_clears_password(self):
        t.register_user("Aiden", "hunter22", self.path)
        for username in ("aiden", "nobody"):
            self.screen = t.LoginScreen(self.path)
            self.click("fields", "username")
            self.type_text(username)
            self.click("fields", "password")
            self.type_text("wrongpass")
            self.click("submit")
            self.assertIsNone(self.screen.user)
            self.assertEqual(self.screen.message, "Wrong username or password.")
            self.assertEqual(self.screen.values["password"], "")

    def test_switching_pages_clears_passwords_and_message(self):
        self.click("fields", "password")
        self.type_text("hunter22")
        self.screen.message = "something"
        self.click("switch")
        self.assertEqual(self.screen.values["password"], "")
        self.assertEqual(self.screen.message, "")
        self.assertEqual(self.screen.active, 0)


def _overlap(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def _inside(inner, outer):
    ix, iy, iw, ih = inner
    ox, oy, ow, oh = outer
    return ox <= ix and oy <= iy and ix + iw <= ox + ow and iy + ih <= oy + oh


class LayoutTests(unittest.TestCase):
    """The buttons must fit on screen and never sit on top of each other,
    since a click on overlapping buttons would be ambiguous."""

    window = (0, 0) + tuple(t.WINDOW_SIZE)

    def login_rects(self, mode):
        layout = t.login_layout(mode)
        rects = list(layout["fields"].values()) + list(layout["toggles"].values())
        rects += [layout["submit"], layout["switch"], layout["quit"]]
        return rects

    def test_point_in_rect_edges(self):
        rect = (10, 20, 30, 40)
        self.assertTrue(t.point_in_rect((10, 20), rect))
        self.assertTrue(t.point_in_rect((39, 59), rect))
        self.assertFalse(t.point_in_rect((40, 59), rect))
        self.assertFalse(t.point_in_rect((39, 60), rect))
        self.assertFalse(t.point_in_rect((9, 20), rect))

    def test_login_pages_fit_in_the_window(self):
        for mode in ("login", "register"):
            for rect in self.login_rects(mode):
                self.assertTrue(_inside(rect, self.window), (mode, rect))

    def test_login_buttons_do_not_overlap(self):
        for mode in ("login", "register"):
            rects = self.login_rects(mode)
            for i, a in enumerate(rects):
                for b in rects[i + 1:]:
                    self.assertFalse(_overlap(a, b), (mode, a, b))

    def test_sign_up_page_has_one_more_field_than_sign_in(self):
        self.assertEqual(len(t.login_layout("login")["fields"]), 2)
        self.assertEqual(len(t.login_layout("register")["fields"]), 3)

    def test_sign_out_button_fits_and_clears_the_next_queue(self):
        self.assertTrue(_inside(t.SIGN_OUT_BUTTON, self.window))
        for box in t.NEXT_BOXES:
            self.assertFalse(_overlap(t.SIGN_OUT_BUTTON, box))

    def test_sign_out_button_clears_the_board(self):
        board = (t.BOARD_ORIGIN_X, t.BOARD_ORIGIN_Y,
                 t.BOARD_WIDTH * t.CELL_SIZE, t.BOARD_HEIGHT * t.CELL_SIZE)
        self.assertFalse(_overlap(t.SIGN_OUT_BUTTON, board))

    def test_game_over_buttons_fit_in_the_panel_and_do_not_overlap(self):
        center_x = t.BOARD_ORIGIN_X + (t.BOARD_WIDTH * t.CELL_SIZE) // 2
        center_y = t.BOARD_ORIGIN_Y + (t.BOARD_HEIGHT * t.CELL_SIZE) // 2 + 60
        width, height = t.BOARD_WIDTH * t.CELL_SIZE + 40, 320
        panel = (center_x - width // 2, center_y - height // 2, width, height)
        buttons = list(t.GAME_OVER_BUTTONS.values())
        self.assertEqual(set(t.GAME_OVER_BUTTONS), {"restart", "sign_out", "quit"})
        for i, a in enumerate(buttons):
            self.assertTrue(_inside(a, panel), a)
            for b in buttons[i + 1:]:
                self.assertFalse(_overlap(a, b), (a, b))


if __name__ == "__main__":
    unittest.main()
