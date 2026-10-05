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

    def test_register_flow_logs_the_player_in(self):
        self.press(pygame.K_F2)
        self.assertEqual(self.screen.mode, "register")
        self.type_text("Aiden")
        self.press(pygame.K_TAB)
        self.type_text("hunter22")
        self.press(pygame.K_TAB)
        self.type_text("hunter22")
        self.press(pygame.K_RETURN)
        self.assertEqual(self.screen.user, "Aiden")
        self.assertEqual(t.authenticate("aiden", "hunter22", self.path), "Aiden")

    def test_register_with_mismatched_passwords_is_refused(self):
        self.press(pygame.K_F2)
        self.type_text("aiden")
        self.press(pygame.K_TAB)
        self.type_text("hunter22")
        self.press(pygame.K_TAB)
        self.type_text("hunter23")
        self.press(pygame.K_RETURN)
        self.assertIsNone(self.screen.user)
        self.assertIn("match", self.screen.message)
        self.assertEqual(self.screen.values["password"], "")
        self.assertEqual(t.load_users(self.path), {})

    def test_register_shows_validation_error(self):
        self.press(pygame.K_F2)
        self.type_text("ai")
        self.press(pygame.K_TAB)
        self.type_text("hunter22")
        self.press(pygame.K_TAB)
        self.type_text("hunter22")
        self.press(pygame.K_RETURN)
        self.assertIsNone(self.screen.user)
        self.assertIn("Username", self.screen.message)

    def test_login_success(self):
        t.register_user("Aiden", "hunter22", self.path)
        self.type_text("aiden")
        self.press(pygame.K_TAB)
        self.type_text("hunter22")
        self.press(pygame.K_RETURN)
        self.assertEqual(self.screen.user, "Aiden")

    def test_login_failure_is_generic_and_clears_password(self):
        t.register_user("Aiden", "hunter22", self.path)
        for username in ("aiden", "nobody"):
            self.screen = t.LoginScreen(self.path)
            self.type_text(username)
            self.press(pygame.K_TAB)
            self.type_text("wrongpass")
            self.press(pygame.K_RETURN)
            self.assertIsNone(self.screen.user)
            self.assertEqual(self.screen.message, "Wrong username or password.")
            self.assertEqual(self.screen.values["password"], "")

    def test_toggle_mode_clears_passwords_and_message(self):
        self.press(pygame.K_TAB)
        self.type_text("hunter22")
        self.screen.message = "something"
        self.press(pygame.K_F2)
        self.assertEqual(self.screen.values["password"], "")
        self.assertEqual(self.screen.message, "")
        self.assertEqual(self.screen.active, 0)
        self.assertEqual(len(self.screen.fields), 3)


if __name__ == "__main__":
    unittest.main()
