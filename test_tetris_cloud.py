import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

import cloud_server
import cloud_sync
import tetris_ver2 as t

KEY = "test-key"


def start_server(data_file, api_key=KEY):
    server = cloud_server.make_server("127.0.0.1", 0, data_file, api_key)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_address[1]}"
    return server, url


def stop_server(server):
    server.shutdown()
    server.server_close()


def raw(method, url, body=None, key=KEY, raw_body=None):
    """Send a request without the client, to check the server's replies.
    Returns (status, decoded JSON)."""
    data = raw_body if raw_body is not None else (
        None if body is None else json.dumps(body).encode())
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    if key:
        request.add_header("X-API-Key", key)
    try:
        with urllib.request.urlopen(request, timeout=3) as reply:
            return reply.status, json.loads(reply.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


class ScoreListTests(unittest.TestCase):
    def test_clean_keeps_good_scores_highest_first(self):
        self.assertEqual(cloud_sync.clean_scores([5, 900, "x", 3.5, True, -4, 0, 300]),
                         [900, 300, 5])

    def test_clean_limits_to_top_five_and_rejects_non_lists(self):
        self.assertEqual(cloud_sync.clean_scores(list(range(1, 11))), [10, 9, 8, 7, 6])
        self.assertEqual(cloud_sync.clean_scores({"a": 1}), [])
        self.assertEqual(cloud_sync.clean_scores(None), [])

    def test_merge_combines_and_keeps_the_top_five(self):
        self.assertEqual(cloud_sync.merge_scores([900, 100], [500, 300, 200, 50]),
                         [900, 500, 300, 200, 100])

    def test_merging_the_same_scores_again_changes_nothing(self):
        once = cloud_sync.merge_scores([900, 300], [900, 300])
        self.assertEqual(once, [900, 300])
        self.assertEqual(cloud_sync.merge_scores(once, [900, 300]), once)

    def test_two_equal_scores_in_one_list_are_both_kept(self):
        self.assertEqual(cloud_sync.merge_scores([400, 400], []), [400, 400])


class ClientSetupTests(unittest.TestCase):
    def test_no_url_means_disabled_and_nothing_is_sent(self):
        client = cloud_sync.CloudSync()
        self.assertFalse(client.enabled)
        self.assertIsNone(client.sync_scores("aiden", [100]))
        self.assertFalse(client.health())

    def test_only_web_addresses_are_allowed(self):
        self.assertFalse(cloud_sync.CloudSync("file:///etc/passwd").enabled)
        self.assertFalse(cloud_sync.CloudSync("ftp://example.com").enabled)
        self.assertTrue(cloud_sync.CloudSync("https://example.com/").enabled)

    def test_settings_come_from_the_environment(self):
        env = {cloud_sync.URL_ENV: "http://127.0.0.1:1/", cloud_sync.KEY_ENV: "k"}
        with mock.patch.dict(os.environ, env):
            client = cloud_sync.CloudSync.from_env()
        self.assertEqual((client.base_url, client.api_key), ("http://127.0.0.1:1", "k"))

    def test_bad_usernames_are_never_sent(self):
        client = cloud_sync.CloudSync("http://127.0.0.1:1")
        for name in ("", "ab", "has space", "../etc", "waytoolongusername"):
            self.assertIsNone(client.sync_scores(name, [100]), name)
            self.assertIsNone(client.fetch_scores(name), name)

    def test_unreachable_server_gives_none_not_an_error(self):
        client = cloud_sync.CloudSync("http://127.0.0.1:1", timeout=0.5)
        self.assertIsNone(client.sync_scores("aiden", [100]))
        self.assertFalse(client.health())


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.data = Path(self.dir.name) / "cloud_scores.json"
        self.server, self.url = start_server(self.data)
        self.client = cloud_sync.CloudSync(self.url, KEY)

    def tearDown(self):
        stop_server(self.server)
        self.dir.cleanup()

    def test_health_needs_no_key(self):
        self.assertEqual(raw("GET", self.url + "/health", key=None), (200, {"status": "ok"}))
        self.assertTrue(self.client.health())

    def test_sync_stores_and_returns_the_merged_list(self):
        self.assertEqual(self.client.sync_scores("Aiden", [300, 900]), [900, 300])
        self.assertEqual(self.client.sync_scores("aiden", [500]), [900, 500, 300])
        self.assertEqual(self.client.fetch_scores("AIDEN"), [900, 500, 300])

    def test_syncing_twice_does_not_duplicate(self):
        self.client.sync_scores("aiden", [900, 300])
        self.assertEqual(self.client.sync_scores("aiden", [900, 300]), [900, 300])

    def test_players_are_kept_apart(self):
        self.client.sync_scores("aiden", [900])
        self.client.sync_scores("nathan", [100])
        self.assertEqual(self.client.fetch_scores("aiden"), [900])
        self.assertEqual(self.client.fetch_scores("nathan"), [100])
        self.assertEqual(self.client.fetch_scores("caleb"), [])

    def test_scores_survive_a_server_restart(self):
        self.client.sync_scores("aiden", [900, 300])
        stop_server(self.server)
        self.server, self.url = start_server(self.data)
        client = cloud_sync.CloudSync(self.url, KEY)
        self.assertEqual(client.fetch_scores("aiden"), [900, 300])

    def test_only_the_top_five_are_kept(self):
        merged = self.client.sync_scores("aiden", [10, 20, 30, 40, 50, 60, 70])
        self.assertEqual(merged, [70, 60, 50, 40, 30])

    def test_wrong_or_missing_key_is_refused(self):
        wrong = cloud_sync.CloudSync(self.url, "nope")
        self.assertIsNone(wrong.sync_scores("aiden", [100]))
        self.assertIsNone(cloud_sync.CloudSync(self.url).fetch_scores("aiden"))
        self.assertEqual(raw("GET", self.url + "/scores/aiden", key=None)[0], 401)
        self.assertEqual(raw("POST", self.url + "/sync/aiden", {"scores": [5]}, key="bad")[0], 401)
        self.assertEqual(self.client.fetch_scores("aiden"), [])  # nothing was stored

    def test_server_without_a_key_is_open(self):
        server, url = start_server(Path(self.dir.name) / "open.json", api_key="")
        try:
            client = cloud_sync.CloudSync(url)
            self.assertEqual(client.sync_scores("aiden", [42]), [42])
        finally:
            stop_server(server)

    def test_post_score_adds_one_score(self):
        status, body = raw("POST", self.url + "/scores/aiden", {"score": 250})
        self.assertEqual((status, body["scores"]), (200, [250]))

    def test_bad_requests_get_400(self):
        sync = self.url + "/sync/aiden"
        self.assertEqual(raw("POST", sync, {"scores": "lots"})[0], 400)
        self.assertEqual(raw("POST", sync, {"scores": [100, "x"]})[0], 400)
        self.assertEqual(raw("POST", sync, {"scores": [-5]})[0], 400)
        self.assertEqual(raw("POST", sync, {"scores": [1] * 51})[0], 400)
        self.assertEqual(raw("POST", sync, raw_body=b"not json")[0], 400)
        self.assertEqual(raw("POST", sync, raw_body=b"")[0], 400)
        self.assertEqual(raw("POST", self.url + "/scores/aiden", {"score": 10**10})[0], 400)
        self.assertEqual(raw("POST", self.url + "/scores/aiden", {"score": True})[0], 400)
        self.assertEqual(raw("POST", sync, raw_body=b"{" + b" " * 5000 + b"}")[0], 400)

    def test_bad_paths_and_usernames_are_refused(self):
        self.assertEqual(raw("GET", self.url + "/nothing")[0], 404)
        self.assertEqual(raw("GET", self.url + "/scores/ab")[0], 404)       # too short
        self.assertEqual(raw("GET", self.url + "/scores/a%2F..%2Fb")[0], 404)
        self.assertEqual(raw("POST", self.url + "/scores/..", {"score": 5})[0], 404)
        self.assertEqual(raw("GET", self.url + "/sync/aiden")[0], 404)       # sync is POST only
        self.assertFalse(self.data.exists())

    def test_a_damaged_data_file_starts_fresh(self):
        self.data.write_text("not json")
        self.assertEqual(self.client.sync_scores("aiden", [100]), [100])


class GameSyncTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.local = Path(self.dir.name) / "aiden.json"
        self.server, self.url = start_server(Path(self.dir.name) / "cloud.json")
        self.cloud = cloud_sync.CloudSync(self.url, KEY)

    def tearDown(self):
        stop_server(self.server)
        self.dir.cleanup()

    def test_local_and_cloud_scores_are_merged_into_both(self):
        t.write_scores([900, 100], self.local)
        self.cloud.sync_scores("aiden", [500, 300])
        scores, synced = t.sync_scores("aiden", self.local, self.cloud)
        self.assertTrue(synced)
        self.assertEqual(scores, [900, 500, 300, 100])
        self.assertEqual(t.load_scores(self.local), [900, 500, 300, 100])
        self.assertEqual(self.cloud.fetch_scores("aiden"), [900, 500, 300, 100])

    def test_a_new_computer_gets_its_scores_from_the_cloud(self):
        self.cloud.sync_scores("aiden", [700, 200])
        scores, synced = t.sync_scores("aiden", self.local, self.cloud)
        self.assertEqual((scores, synced), ([700, 200], True))
        self.assertEqual(t.load_scores(self.local), [700, 200])

    def test_offline_keeps_the_local_scores(self):
        t.write_scores([900, 100], self.local)
        down = cloud_sync.CloudSync("http://127.0.0.1:1", timeout=0.5)
        self.assertEqual(t.sync_scores("aiden", self.local, down), ([900, 100], False))
        self.assertEqual(t.load_scores(self.local), [900, 100])

    def test_no_cloud_set_up_is_fine(self):
        t.write_scores([900], self.local)
        for cloud in (None, cloud_sync.CloudSync()):
            self.assertEqual(t.sync_scores("aiden", self.local, cloud), ([900], False))

    def test_game_over_sends_the_score_to_the_cloud(self):
        """Plays until the stack is full, with the cloud turned on."""
        pygame.init()
        screen = pygame.display.set_mode(t.WINDOW_SIZE)
        font = pygame.font.Font(None, 22)
        big = pygame.font.Font(None, 46)
        key = lambda k: pygame.event.Event(pygame.KEYDOWN, key=k)
        frames = [[key(pygame.K_SPACE)] * 40, [], [], [pygame.event.Event(pygame.QUIT)]]
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(t, "SCORES_DIR", Path(tmp) / "scores"), \
                mock.patch.object(t, "SETTINGS_DIR", Path(tmp) / "settings"), \
                mock.patch.object(pygame.event, "get", side_effect=frames):
            result = t.play(screen, pygame.time.Clock(), font, big, "tester",
                            t.SoundBank(), cloud=self.cloud)
            local = t.load_scores(t.scores_path("tester"))
        t.apply_theme("light")
        self.assertEqual(result, "quit")
        self.assertTrue(local)
        self.assertEqual(self.cloud.fetch_scores("tester"), local)


if __name__ == "__main__":
    unittest.main()
