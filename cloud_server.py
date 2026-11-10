"""A small self-hosted high score API for Tetris (standard library only).

Run it on any machine the players can reach:

    python3 cloud_server.py --port 8765 --key mysecret

and point the game at it:

    export TETRIS_CLOUD_URL=http://127.0.0.1:8765
    export TETRIS_CLOUD_KEY=mysecret

Endpoints (JSON in, JSON out; everything but /health needs the X-API-Key
header when the server was started with a key):

    GET  /health            -> {"status": "ok"}
    GET  /scores/<user>     -> {"user": "<user>", "scores": [...]}
    POST /scores/<user>     body {"score": 1200}          -> adds one score
    POST /sync/<user>       body {"scores": [900, 300]}   -> merges a list

Scores are kept in cloud_scores.json next to this file. By default the
server only listens on 127.0.0.1, so it is not reachable from other
computers unless you pass --host 0.0.0.0 (and then use a key).
"""
import argparse
import hmac
import json
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from cloud_sync import (KEY_ENV, MAX_SCORE, MAX_SCORES_SENT, TOP_SCORES,
                        USERNAME_PATTERN, clean_scores, merge_scores)

DATA_FILE = Path(__file__).with_name("cloud_scores.json")
MAX_BODY = 4096
ROUTE = re.compile(r"/(scores|sync)/([A-Za-z0-9_]+)")


class ScoreStore:
    """Every player's top scores, kept in one JSON file."""

    def __init__(self, path=DATA_FILE):
        self.path = Path(path)
        self._lock = threading.Lock()

    def _load(self):
        try:
            with open(self.path) as f:
                data = json.load(f)
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _save(self, data):
        tmp = self.path.with_name(self.path.name + ".tmp")
        with open(tmp, "w") as f:
            json.dump(data, f)
        os.replace(tmp, self.path)

    def get(self, user):
        with self._lock:
            return clean_scores(self._load().get(user.lower()))

    def merge(self, user, scores):
        """Merge scores into the player's list, save, and return it."""
        key = user.lower()
        with self._lock:
            data = self._load()
            merged = merge_scores(data.get(key), scores)
            data[key] = merged
            self._save(data)
            return merged


class Handler(BaseHTTPRequestHandler):
    server_version = "TetrisScores/1.0"

    def log_message(self, fmt, *args):
        if getattr(self.server, "verbose", False):
            super().log_message(fmt, *args)

    def _reply(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self):
        key = self.server.api_key
        if not key:
            return True
        sent = self.headers.get("X-API-Key", "")
        return hmac.compare_digest(sent.encode("utf-8"), key.encode("utf-8"))

    def _route(self):
        """(kind, user) for /scores/<user> or /sync/<user>, else None."""
        match = ROUTE.fullmatch(self.path.split("?")[0])
        if match and USERNAME_PATTERN.fullmatch(match.group(2)):
            return match.group(1), match.group(2)
        return None

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            return None
        if not 0 < length <= MAX_BODY:
            return None
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except ValueError:
            return None
        return data if isinstance(data, dict) else None

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/health":
            return self._reply(200, {"status": "ok"})
        if not self._authorized():
            return self._reply(401, {"error": "bad or missing API key"})
        route = self._route()
        if route is None or route[0] != "scores":
            return self._reply(404, {"error": "not found"})
        user = route[1]
        self._reply(200, {"user": user.lower(), "scores": self.server.store.get(user)})

    def do_POST(self):
        if not self._authorized():
            return self._reply(401, {"error": "bad or missing API key"})
        route = self._route()
        if route is None:
            return self._reply(404, {"error": "not found"})
        body = self._read_json()
        if body is None:
            return self._reply(400, {"error": "send a small JSON object"})
        kind, user = route
        if kind == "sync":
            scores = body.get("scores")
            if (not isinstance(scores, list) or len(scores) > MAX_SCORES_SENT
                    or len(clean_scores(scores, MAX_SCORES_SENT)) != len(scores)):
                return self._reply(400, {"error": "scores must be a short list of positive whole numbers"})
        else:
            score = body.get("score")
            if (not isinstance(score, int) or isinstance(score, bool)
                    or not 0 < score <= MAX_SCORE):
                return self._reply(400, {"error": "score must be a positive whole number"})
            scores = [score]
        merged = self.server.store.merge(user, scores)
        self._reply(200, {"user": user.lower(), "scores": merged})


def make_server(host="127.0.0.1", port=8765, data_file=DATA_FILE, api_key=None,
                verbose=False):
    """Build the server (port 0 picks any free port). Call serve_forever()
    on the result, or run it in a thread."""
    server = ThreadingHTTPServer((host, port), Handler)
    server.store = ScoreStore(data_file)
    server.api_key = api_key or ""
    server.verbose = verbose
    return server


def main():
    parser = argparse.ArgumentParser(description="Tetris high score API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--key", default=os.environ.get(KEY_ENV, ""),
                        help=f"API key (or set {KEY_ENV})")
    args = parser.parse_args()
    server = make_server(args.host, args.port, api_key=args.key, verbose=True)
    note = "with an API key" if args.key else "WITHOUT an API key"
    print(f"Tetris score server on http://{args.host}:{server.server_address[1]} ({note})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
