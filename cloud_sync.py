"""Client for the high score cloud sync API (see cloud_server.py).

No pygame in here. Sync is optional: it only runs when TETRIS_CLOUD_URL is
set, and every failure (no network, wrong key, server down) just returns
None so the game keeps using the local scores.

Settings (environment variables):
    TETRIS_CLOUD_URL  e.g. http://127.0.0.1:8765
    TETRIS_CLOUD_KEY  the API key the server was started with (if any)
"""
import json
import os
import re
import urllib.error
import urllib.request
from collections import Counter

TOP_SCORES = 5          # how many scores each player keeps
MAX_SCORE = 10**9       # anything bigger is treated as bad data
MAX_SCORES_SENT = 50    # the server refuses longer lists
DEFAULT_TIMEOUT = 1.5   # seconds; the game waits this long at most
URL_ENV = "TETRIS_CLOUD_URL"
KEY_ENV = "TETRIS_CLOUD_KEY"
USERNAME_PATTERN = re.compile(r"[A-Za-z0-9_]{3,12}")


def clean_scores(values, limit=TOP_SCORES):
    """The valid scores in a list (positive whole numbers), highest first,
    cut to the top `limit`. Anything else in the list is dropped."""
    if not isinstance(values, list):
        return []
    good = [v for v in values
            if isinstance(v, int) and not isinstance(v, bool) and 0 < v <= MAX_SCORE]
    return sorted(good, reverse=True)[:limit]


def merge_scores(first, second, limit=TOP_SCORES):
    """Combine two score lists into one top list.

    A score that appears in both lists is counted once, not twice, so
    syncing the same scores again and again changes nothing."""
    union = Counter(clean_scores(first, MAX_SCORES_SENT)) | Counter(
        clean_scores(second, MAX_SCORES_SENT))
    return sorted(union.elements(), reverse=True)[:limit]


class CloudSync:
    """Talks to the score server. Safe to create without any settings."""

    def __init__(self, base_url=None, api_key=None, timeout=DEFAULT_TIMEOUT):
        base_url = (base_url or "").strip().rstrip("/")
        if not base_url.startswith(("http://", "https://")):
            base_url = ""  # only web addresses are allowed (no file: URLs)
        self.base_url = base_url
        self.api_key = api_key or ""
        self.timeout = timeout

    @classmethod
    def from_env(cls):
        return cls(os.environ.get(URL_ENV), os.environ.get(KEY_ENV))

    @property
    def enabled(self):
        return bool(self.base_url)

    def _request(self, method, path, payload=None):
        """The decoded JSON reply, or None if anything went wrong."""
        if not self.enabled:
            return None
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(self.base_url + path, data=body, method=method)
        request.add_header("Content-Type", "application/json")
        if self.api_key:
            request.add_header("X-API-Key", self.api_key)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as reply:
                data = json.loads(reply.read(65536).decode("utf-8"))
        except (OSError, ValueError, urllib.error.URLError):
            return None
        return data if isinstance(data, dict) else None

    def health(self):
        """True if the server answers."""
        data = self._request("GET", "/health")
        return bool(data) and data.get("status") == "ok"

    def fetch_scores(self, username):
        """The player's cloud scores, or None."""
        if USERNAME_PATTERN.fullmatch(username or "") is None:
            return None
        data = self._request("GET", f"/scores/{username.lower()}")
        if data is None or not isinstance(data.get("scores"), list):
            return None
        return clean_scores(data["scores"])

    def sync_scores(self, username, local_scores):
        """Send the local scores, get back the merged top list (also stored
        in the cloud). Returns None if the sync didn't work."""
        if USERNAME_PATTERN.fullmatch(username or "") is None:
            return None
        payload = {"scores": clean_scores(local_scores, MAX_SCORES_SENT)}
        data = self._request("POST", f"/sync/{username.lower()}", payload)
        if data is None or not isinstance(data.get("scores"), list):
            return None
        return clean_scores(data["scores"])
