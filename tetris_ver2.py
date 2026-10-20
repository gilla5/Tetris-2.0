import array
import hashlib
import hmac
import json
import math
import os
import random
import re
import secrets
from collections import deque
from pathlib import Path

import pygame

# ---------------------------------------------------------------------------
# Board / window configuration
# ---------------------------------------------------------------------------
BOARD_WIDTH = 10
BOARD_HEIGHT = 20

CELL_SIZE = 28
BOARD_ORIGIN_X = 200
BOARD_ORIGIN_Y = 60

WINDOW_SIZE = (700, 660)
FPS = 60

BLACK = (15, 15, 15)
WHITE = (245, 245, 245)
GRAY = (90, 90, 90)
PANEL_BG = (225, 225, 225)

# High score leaderboard, saved next to this file.
SCORES_FILE = Path(__file__).with_name("highscores.json")
LEADERBOARD_SIZE = 5
HIGHLIGHT = (220, 60, 40)

# User accounts. Accounts are saved in users.json, and each player gets their
# own high score file in the scores folder. Both live next to this file.
USERS_FILE = Path(__file__).with_name("users.json")
SCORES_DIR = Path(__file__).with_name("scores")
USERNAME_PATTERN = re.compile(r"[A-Za-z0-9_]{3,12}")
USERNAME_MAX_LEN = 12
MIN_PASSWORD_LEN = 6
MAX_PASSWORD_LEN = 64
# PBKDF2 work factor: higher is slower for an attacker, and for a login too.
PBKDF2_ITERATIONS = 600_000
SALT_BYTES = 16

# Side panels: hold box on the left, next-piece queue on the right.
NEXT_QUEUE_SIZE = 3
PREVIEW_CELL = 18
PANEL_WIDTH = 130
PANEL_SLOT_HEIGHT = 100

HOLD_BOX = (20, BOARD_ORIGIN_Y, PANEL_WIDTH, PANEL_SLOT_HEIGHT)
NEXT_BOX_X = BOARD_ORIGIN_X + BOARD_WIDTH * CELL_SIZE + 30
NEXT_BOXES = [
    (NEXT_BOX_X, BOARD_ORIGIN_Y + i * (PANEL_SLOT_HEIGHT + 10), PANEL_WIDTH, PANEL_SLOT_HEIGHT)
    for i in range(NEXT_QUEUE_SIZE)
]

# Buttons are (x, y, width, height) rects; clicks are checked with point_in_rect.
# SIGN_OUT_BUTTON sits in the bottom-right corner while playing. The game over
# buttons sit in a row inside the game over panel.
SIGN_OUT_BUTTON = (NEXT_BOX_X, WINDOW_SIZE[1] - 70, PANEL_WIDTH, 40)
_GAME_OVER_BUTTONS_LEFT = BOARD_ORIGIN_X + (BOARD_WIDTH * CELL_SIZE) // 2 - 150
_GAME_OVER_BUTTONS_Y = BOARD_ORIGIN_Y + (BOARD_HEIGHT * CELL_SIZE) // 2 + 12
GAME_OVER_BUTTONS = {
    "restart": (_GAME_OVER_BUTTONS_LEFT, _GAME_OVER_BUTTONS_Y, 96, 36),
    "sign_out": (_GAME_OVER_BUTTONS_LEFT + 102, _GAME_OVER_BUTTONS_Y, 96, 36),
    "quit": (_GAME_OVER_BUTTONS_LEFT + 204, _GAME_OVER_BUTTONS_Y, 96, 36),
}
BUTTON_HOVER = (205, 205, 205)
BUTTON_PRIMARY_HOVER = (195, 45, 30)

# Pause menu: three buttons stacked inside a panel centered on the board.
_BOARD_CENTER_X = BOARD_ORIGIN_X + (BOARD_WIDTH * CELL_SIZE) // 2
_BOARD_CENTER_Y = BOARD_ORIGIN_Y + (BOARD_HEIGHT * CELL_SIZE) // 2
PAUSE_PANEL = (_BOARD_CENTER_X - 130, _BOARD_CENTER_Y - 120, 260, 240)
PAUSE_BUTTONS = {
    "resume": (_BOARD_CENTER_X - 80, _BOARD_CENTER_Y - 30, 160, 38),
    "restart": (_BOARD_CENTER_X - 80, _BOARD_CENTER_Y + 16, 160, 38),
    "quit": (_BOARD_CENTER_X - 80, _BOARD_CENTER_Y + 62, 160, 38),
}

# Each player's theme and mute choice, saved next to this file.
SETTINGS_DIR = Path(__file__).with_name("settings")

PIECE_COLORS = {
    "I": (0, 240, 240),
    "O": (240, 240, 0),
    "T": (160, 0, 240),
    "S": (0, 240, 0),
    "Z": (240, 0, 0),
    "J": (0, 0, 240),
    "L": (240, 160, 0),
}

# ---------------------------------------------------------------------------
# Themes. apply_theme() swaps the color names above (and the piece colors) in
# place, so every draw function picks the new look up on its next call.
# ---------------------------------------------------------------------------
THEMES = {
    "light": {
        "WHITE": (245, 245, 245), "BLACK": (15, 15, 15), "GRAY": (90, 90, 90),
        "PANEL_BG": (225, 225, 225), "HIGHLIGHT": (220, 60, 40),
        "BUTTON_HOVER": (205, 205, 205), "BUTTON_PRIMARY_HOVER": (195, 45, 30),
        "pieces": dict(PIECE_COLORS),
    },
    "dark": {
        "WHITE": (25, 27, 34), "BLACK": (235, 235, 240), "GRAY": (110, 115, 130),
        "PANEL_BG": (45, 48, 60), "HIGHLIGHT": (255, 90, 70),
        "BUTTON_HOVER": (70, 74, 90), "BUTTON_PRIMARY_HOVER": (225, 70, 55),
        "pieces": dict(PIECE_COLORS),
    },
    "retro": {  # Game Boy greens
        "WHITE": (155, 188, 15), "BLACK": (15, 56, 15), "GRAY": (48, 98, 48),
        "PANEL_BG": (139, 172, 15), "HIGHLIGHT": (15, 56, 15),
        "BUTTON_HOVER": (125, 158, 15), "BUTTON_PRIMARY_HOVER": (30, 80, 30),
        "pieces": {
            "I": (15, 56, 15), "O": (48, 98, 48), "T": (30, 77, 30),
            "S": (80, 120, 20), "Z": (40, 90, 70), "J": (20, 70, 50),
            "L": (95, 130, 25),
        },
    },
}
THEME_ORDER = ["light", "dark", "retro"]
current_theme = "light"


def apply_theme(name):
    """Switch every color to the named theme. Raises ValueError for an
    unknown name."""
    global WHITE, BLACK, GRAY, PANEL_BG, HIGHLIGHT, BUTTON_HOVER
    global BUTTON_PRIMARY_HOVER, current_theme
    if name not in THEMES:
        raise ValueError(f"unknown theme: {name}")
    theme = THEMES[name]
    WHITE, BLACK, GRAY = theme["WHITE"], theme["BLACK"], theme["GRAY"]
    PANEL_BG, HIGHLIGHT = theme["PANEL_BG"], theme["HIGHLIGHT"]
    BUTTON_HOVER = theme["BUTTON_HOVER"]
    BUTTON_PRIMARY_HOVER = theme["BUTTON_PRIMARY_HOVER"]
    PIECE_COLORS.update(theme["pieces"])
    current_theme = name


def next_theme(name):
    """The theme after this one in THEME_ORDER (wraps around)."""
    return THEME_ORDER[(THEME_ORDER.index(name) + 1) % len(THEME_ORDER)]


# ---------------------------------------------------------------------------
# Piece shapes
#
# Only the spawn orientation (state 0) is hand-written, as (row, col)
# offsets inside an NxN bounding box. States R (1), 2, and L (3) are
# generated by rotating that box 90 degrees clockwise three times, which
# is exactly how the SRS defines its four rotation states.
# ---------------------------------------------------------------------------
PIECE_SHAPES = {
    "I": (4, [(1, 0), (1, 1), (1, 2), (1, 3)]),
    "O": (2, [(0, 0), (0, 1), (1, 0), (1, 1)]),
    "T": (3, [(0, 1), (1, 0), (1, 1), (1, 2)]),
    "S": (3, [(0, 1), (0, 2), (1, 0), (1, 1)]),
    "Z": (3, [(0, 0), (0, 1), (1, 1), (1, 2)]),
    "J": (3, [(0, 0), (1, 0), (1, 1), (1, 2)]),
    "L": (3, [(0, 2), (1, 0), (1, 1), (1, 2)]),
}


def _rotate_cw(cells, box_size):
    """Rotate (row, col) cells 90 degrees clockwise inside a box_size
    square, with row increasing downward (screen convention)."""
    return [(c, box_size - 1 - r) for (r, c) in cells]


def _build_rotation_states():
    states = {}
    for name, (box_size, base_cells) in PIECE_SHAPES.items():
        rotations = [base_cells]
        for _ in range(3):
            rotations.append(_rotate_cw(rotations[-1], box_size))
        states[name] = {"box": box_size, "cells": rotations}
    return states


ROTATION_STATES = _build_rotation_states()

# ---------------------------------------------------------------------------
# SRS wall-kick tables: (from_state, to_state) -> ordered list of (dx, dy)
# offsets to try. dx = columns (right positive), dy = rows (down positive).
# The first offset that produces a legal position is used; O needs none,
# since its shape is identical in every rotation state.
# ---------------------------------------------------------------------------
JLSTZ_KICKS = {
    (0, 1): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
    (1, 0): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],
    (1, 2): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],
    (2, 1): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
    (2, 3): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
    (3, 2): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
    (3, 0): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
    (0, 3): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
}

I_KICKS = {
    (0, 1): [(0, 0), (-2, 0), (1, 0), (-2, 1), (1, -2)],
    (1, 0): [(0, 0), (2, 0), (-1, 0), (2, -1), (-1, 2)],
    (1, 2): [(0, 0), (-1, 0), (2, 0), (-1, -2), (2, 1)],
    (2, 1): [(0, 0), (1, 0), (-2, 0), (1, 2), (-2, -1)],
    (2, 3): [(0, 0), (2, 0), (-1, 0), (2, -1), (-1, 2)],
    (3, 2): [(0, 0), (-2, 0), (1, 0), (-2, 1), (1, -2)],
    (3, 0): [(0, 0), (1, 0), (-2, 0), (1, 2), (-2, -1)],
    (0, 3): [(0, 0), (-1, 0), (2, 0), (-1, -2), (2, 1)],
}

# ---------------------------------------------------------------------------
# Scoring & level-speed curve
# ---------------------------------------------------------------------------
LINE_CLEAR_SCORE = {1: 100, 2: 300, 3: 500, 4: 800}  # single/double/triple/tetris
LINES_PER_LEVEL = 10
SOFT_DROP_POINTS = 1
HARD_DROP_POINTS = 2

# T-spin scores by lines cleared (multiplied by level, like normal clears).
TSPIN_SCORE = {0: 400, 1: 800, 2: 1200, 3: 1600}
TSPIN_MINI_SCORE = {0: 100, 1: 200, 2: 400}
COMBO_POINTS = 50          # per combo step, times level
B2B_MULTIPLIER = 1.5       # back-to-back Tetris / T-spin line clears
LINE_NAMES = {1: "SINGLE", 2: "DOUBLE", 3: "TRIPLE", 4: "TETRIS"}

# Lock delay: a landed piece stays movable for a moment before it locks.
LOCK_DELAY = 0.5           # seconds
MAX_LOCK_RESETS = 15       # moves/rotations that can restart the delay

# How long the on-screen effects last, in seconds.
CLEAR_ANIM_TIME = 0.3
MESSAGE_TIME = 1.4
LEVEL_UP_TIME = 1.5


def format_time(seconds):
    """Seconds as m:ss."""
    seconds = int(seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"


def gravity_interval(level):
    """Seconds between automatic downward steps, following the classic
    Tetris Guideline gravity curve (frames-per-row translated to seconds).
    Clamped so it never hits zero/negative at very high levels."""
    return max(0.05, (0.8 - (level - 1) * 0.007) ** (level - 1))


# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------
class Piece:
    """A falling tetromino: its type, rotation state, and board position."""

    def __init__(self, kind):
        self.kind = kind
        self.rotation = 0
        box = ROTATION_STATES[kind]["box"]
        self.col = (BOARD_WIDTH - box) // 2
        self.row = 0

    def cells(self):
        """Absolute (row, col) board cells occupied at the current
        rotation and position."""
        offsets = ROTATION_STATES[self.kind]["cells"][self.rotation]
        return [(self.row + r, self.col + c) for (r, c) in offsets]


class Board:
    """The 10x20 well. Owns the locked-cell grid and line clearing."""

    def __init__(self, width=BOARD_WIDTH, height=BOARD_HEIGHT):
        self.width = width
        self.height = height
        self.grid = [[None] * width for _ in range(height)]

    def is_valid(self, cells):
        """True if every cell is in-bounds (horizontally and at the
        bottom) and unoccupied. Cells above the board (row < 0) are
        always allowed, so pieces can spawn partly off the top."""
        for row, col in cells:
            if col < 0 or col >= self.width or row >= self.height:
                return False
            if row >= 0 and self.grid[row][col] is not None:
                return False
        return True

    def lock(self, piece):
        for row, col in piece.cells():
            if row >= 0:
                self.grid[row][col] = piece.kind

    def clear_lines(self):
        """Remove every full row, shifting the rest down. Returns the
        number of lines cleared."""
        remaining = [row for row in self.grid if any(cell is None for cell in row)]
        cleared = self.height - len(remaining)
        if cleared:
            self.grid = [[None] * self.width for _ in range(cleared)] + remaining
        return cleared


class SevenBag:
    """Standard 7-bag randomizer: each piece type appears exactly once
    per bag, in shuffled order, before the bag refills. This avoids the
    long droughts/floods possible with tetris_ver2.py's uniform
    random.randint spawner."""

    def __init__(self):
        self._bag = []

    def next_piece(self):
        if not self._bag:
            self._bag = list(PIECE_SHAPES.keys())
            random.shuffle(self._bag)
        return self._bag.pop()


class Game:
    """Ties board + piece + randomizer + scoring/level together and
    exposes the actions the input layer drives."""

    def __init__(self):
        self.board = Board()
        self.bag = SevenBag()
        self.piece = None
        self.score = 0
        self.lines_cleared = 0
        self.level = 1
        self.state = "playing"  # "playing", "paused" or "gameover"
        self._fall_timer = 0.0

        # Stats for the game over screen. elapsed only counts while playing.
        self.pieces_placed = 0
        self.elapsed = 0.0

        # Combo, back-to-back and T-spin tracking.
        self.combo = -1  # -1 means no streak; 0 is the first clear in a row
        self.back_to_back = False
        self._rotated_last = False  # the last thing the player did was rotate
        self._last_kick = 0

        # Lock delay.
        self._lock_timer = 0.0
        self._lock_resets = 0

        # Effects. events are names like "lock" or "clear" that play() drains
        # to make sounds. The rest are timers the renderer reads.
        self.events = []
        self.message_lines = []
        self.message_timer = 0.0
        self.level_up_timer = 0.0
        self.clear_anim = None  # {"grid", "rows", "time"} while rows flash

        # Next-piece queue: always kept topped up to NEXT_QUEUE_SIZE so the
        # UI can show what's coming without consuming it.
        self.next_queue = deque()
        self._refill_queue()

        # Hold piece: starts empty; can_hold prevents hold/un-hold being
        # chained more than once per piece (the standard guideline rule).
        self.hold_kind = None
        self.can_hold = True

        self._spawn_piece()

    def _refill_queue(self):
        while len(self.next_queue) < NEXT_QUEUE_SIZE:
            self.next_queue.append(self.bag.next_piece())

    def _spawn_piece(self, kind=None):
        if kind is None:
            kind = self.next_queue.popleft()
            self._refill_queue()
        self.piece = Piece(kind)
        self._rotated_last = False
        self._last_kick = 0
        self._lock_timer = 0.0
        self._lock_resets = 0
        if not self.board.is_valid(self.piece.cells()):
            self.state = "gameover"
            self.events.append("gameover")

    def toggle_pause(self):
        """Pause a running game, or resume a paused one. Does nothing once
        the game is over."""
        if self.state == "playing":
            self.state = "paused"
        elif self.state == "paused":
            self.state = "playing"

    def hold(self):
        """Swap the active piece into the hold slot. Only one hold is
        allowed per piece, reset when the active piece locks."""
        if self.state != "playing" or not self.can_hold:
            return
        current_kind = self.piece.kind
        if self.hold_kind is None:
            self._spawn_piece()
        else:
            self._spawn_piece(kind=self.hold_kind)
        self.hold_kind = current_kind
        self.can_hold = False
        self.events.append("hold")

    def _grounded(self):
        """True if the active piece is resting on the stack or the floor."""
        self.piece.row += 1
        blocked = not self.board.is_valid(self.piece.cells())
        self.piece.row -= 1
        return blocked

    def _restart_lock_delay(self):
        """A move or rotation on the ground restarts the lock delay, up to
        MAX_LOCK_RESETS times so a piece can't stall forever."""
        if self._grounded() and self._lock_resets < MAX_LOCK_RESETS:
            self._lock_timer = 0.0
            self._lock_resets += 1

    def move(self, dcol, drow):
        """Attempt to move the active piece; returns False and leaves it
        unchanged if that would collide."""
        self.piece.col += dcol
        self.piece.row += drow
        if not self.board.is_valid(self.piece.cells()):
            self.piece.col -= dcol
            self.piece.row -= drow
            return False
        self._rotated_last = False
        if dcol:
            self._restart_lock_delay()
        return True

    def rotate(self, clockwise=True):
        if self.state != "playing" or self.piece.kind == "O":
            return
        old_state = self.piece.rotation
        new_state = (old_state + (1 if clockwise else -1)) % 4
        kicks = I_KICKS if self.piece.kind == "I" else JLSTZ_KICKS
        for index, (dx, dy) in enumerate(kicks.get((old_state, new_state), [(0, 0)])):
            self.piece.rotation = new_state
            self.piece.col += dx
            self.piece.row += dy
            if self.board.is_valid(self.piece.cells()):
                self._rotated_last = True
                self._last_kick = index
                self.events.append("rotate")
                self._restart_lock_delay()
                return
            self.piece.col -= dx
            self.piece.row -= dy
        self.piece.rotation = old_state

    def soft_drop(self):
        if self.state != "playing":
            return
        if self.move(0, 1):
            self.score += SOFT_DROP_POINTS
        else:
            self._lock_active_piece()

    def hard_drop(self):
        if self.state != "playing":
            return
        dropped = 0
        while self.move(0, 1):
            dropped += 1
        self.score += dropped * HARD_DROP_POINTS
        self._lock_active_piece()

    def update(self, dt):
        """Advance gravity, the lock delay and the effect timers by dt seconds."""
        if self.state != "playing":
            return
        self.elapsed += dt
        self._tick_effects(dt)
        self._fall_timer += dt
        if self._fall_timer >= gravity_interval(self.level):
            self._fall_timer = 0.0
            self.move(0, 1)
        if self._grounded():
            self._lock_timer += dt
            if self._lock_timer >= LOCK_DELAY:
                self._lock_active_piece()
        else:
            self._lock_timer = 0.0

    def _tick_effects(self, dt):
        self.message_timer = max(0.0, self.message_timer - dt)
        self.level_up_timer = max(0.0, self.level_up_timer - dt)
        if self.message_timer == 0.0:
            self.message_lines = []
        if self.clear_anim is not None:
            self.clear_anim["time"] += dt
            if self.clear_anim["time"] >= CLEAR_ANIM_TIME:
                self.clear_anim = None

    def _t_spin_kind(self):
        """None, "mini" or "full". Uses the three-corner rule: the last move
        was a rotation of a T piece and at least 3 of the 4 corners around
        its center are blocked (walls and floor count)."""
        p = self.piece
        if p.kind != "T" or not self._rotated_last:
            return None
        corners = {"nw": (p.row, p.col), "ne": (p.row, p.col + 2),
                   "sw": (p.row + 2, p.col), "se": (p.row + 2, p.col + 2)}

        def blocked(row, col):
            if col < 0 or col >= self.board.width or row >= self.board.height:
                return True
            return row >= 0 and self.board.grid[row][col] is not None

        filled = {name for name, (r, c) in corners.items() if blocked(r, c)}
        if len(filled) < 3:
            return None
        # The two corners on the side the T points toward decide mini vs full.
        front = {0: ("nw", "ne"), 1: ("ne", "se"), 2: ("sw", "se"), 3: ("nw", "sw")}
        if all(name in filled for name in front[p.rotation]) or self._last_kick == 4:
            return "full"
        return "mini"

    def _lock_active_piece(self):
        tspin = self._t_spin_kind()
        self.board.lock(self.piece)
        full_rows = [i for i, row in enumerate(self.board.grid)
                     if all(cell is not None for cell in row)]
        snapshot = [row[:] for row in self.board.grid] if full_rows else None
        cleared = self.board.clear_lines()
        self.pieces_placed += 1
        self.events.append("lock")

        if tspin == "full":
            points = TSPIN_SCORE[cleared]
        elif tspin == "mini":
            points = TSPIN_MINI_SCORE.get(cleared, 400)
        else:
            points = LINE_CLEAR_SCORE.get(cleared, 0)

        # Back-to-back: Tetrises and T-spin line clears are "difficult". A
        # difficult clear right after another earns a bonus; an ordinary
        # clear ends the chain. Locks that clear nothing change nothing.
        b2b_bonus = False
        if cleared:
            if cleared == 4 or tspin:
                if self.back_to_back:
                    points = int(points * B2B_MULTIPLIER)
                    b2b_bonus = True
                self.back_to_back = True
            else:
                self.back_to_back = False
            self.combo += 1
        else:
            self.combo = -1

        self.score += points * self.level
        if self.combo > 0:
            self.score += COMBO_POINTS * self.combo * self.level

        old_level = self.level
        if cleared:
            self.lines_cleared += cleared
            self.level = 1 + self.lines_cleared // LINES_PER_LEVEL
            self.clear_anim = {"grid": snapshot, "rows": full_rows, "time": 0.0}
        if self.level > old_level:
            self.level_up_timer = LEVEL_UP_TIME
            self.events.append("levelup")

        self._announce(cleared, tspin, b2b_bonus)
        self.can_hold = True
        self._spawn_piece()

    def _announce(self, cleared, tspin, b2b_bonus):
        """Set the on-screen text and the sound for what just happened."""
        lines = []
        if b2b_bonus:
            lines.append("BACK-TO-BACK")
        name = []
        if tspin:
            name.append("T-SPIN MINI" if tspin == "mini" else "T-SPIN")
        if cleared:
            name.append(LINE_NAMES[cleared])
        if name:
            lines.append(" ".join(name))
        if self.combo >= 1:
            lines.append(f"COMBO x{self.combo}")
        if lines:
            self.message_lines = lines
            self.message_timer = MESSAGE_TIME
        if cleared and (cleared == 4 or tspin):
            self.events.append("tetris")
        elif cleared:
            self.events.append("clear")
        elif tspin:
            self.events.append("tspin")


# ---------------------------------------------------------------------------
# Sound. Tones are generated in code, so there are no audio files to ship.
# If there is no audio device the game just stays silent.
# ---------------------------------------------------------------------------
SOUND_RATE = 22050
SOUND_NOTES = {  # name -> [(frequency in Hz, seconds), ...]
    "move": [(220, 0.03)],
    "rotate": [(330, 0.04)],
    "hold": [(262, 0.05), (330, 0.05)],
    "lock": [(130, 0.07)],
    "clear": [(523, 0.07), (659, 0.09)],
    "tetris": [(523, 0.06), (659, 0.06), (784, 0.06), (1047, 0.12)],
    "tspin": [(440, 0.06), (554, 0.06), (659, 0.10)],
    "levelup": [(392, 0.08), (523, 0.08), (659, 0.08), (784, 0.14)],
    "gameover": [(392, 0.15), (330, 0.15), (262, 0.15), (196, 0.30)],
}


def synth(notes, rate=SOUND_RATE, channels=1, volume=0.25):
    """16-bit sine tones with a fade-out (no clicks), as raw bytes."""
    samples = array.array("h")
    for freq, seconds in notes:
        count = int(rate * seconds)
        for i in range(count):
            value = int(32767 * volume * (1 - i / count)
                        * math.sin(2 * math.pi * freq * i / rate))
            samples.extend([value] * channels)
    return samples.tobytes()


class SoundBank:
    """All the game sounds, with a mute switch."""

    def __init__(self, muted=False):
        self.muted = muted
        self.sounds = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(SOUND_RATE, -16, 1)
            rate, fmt, channels = pygame.mixer.get_init()
            if fmt != -16:
                return
            for name, notes in SOUND_NOTES.items():
                self.sounds[name] = pygame.mixer.Sound(
                    buffer=synth(notes, rate, channels))
        except pygame.error:
            self.sounds = {}

    @property
    def available(self):
        return bool(self.sounds)

    def play(self, name):
        if not self.muted and name in self.sounds:
            self.sounds[name].play()

    def toggle_mute(self):
        self.muted = not self.muted
        return self.muted


# ---------------------------------------------------------------------------
# Per-player settings (theme and mute), saved in the settings folder
# ---------------------------------------------------------------------------
def settings_path(username):
    """Where one player's settings are kept. Safe to build from a username,
    because usernames are limited to letters, digits and _."""
    return SETTINGS_DIR / f"{username.lower()}.json"


def load_settings(path):
    """A player's saved settings. A missing or broken file gives defaults."""
    settings = {"theme": "light", "muted": False}
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return settings
    if isinstance(data, dict):
        if data.get("theme") in THEMES:
            settings["theme"] = data["theme"]
        if isinstance(data.get("muted"), bool):
            settings["muted"] = data["muted"]
    return settings


def save_settings(settings, path):
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(settings, f)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Rendering (thin - the classes above have no pygame dependency in their
# logic, only this section touches the screen)
# ---------------------------------------------------------------------------
def _shade(color, amount):
    """Lighten (amount > 0) or darken (amount < 0) an RGB color."""
    return tuple(max(0, min(255, c + amount)) for c in color)


def draw_cell(screen, x, y, size, color):
    """Draw one block with a light top/left edge and a dark bottom/right
    edge. Every block (board, active piece, previews) goes through here."""
    pygame.draw.rect(screen, color, (x + 1, y + 1, size - 2, size - 2))
    edge = max(2, size // 8)
    light = _shade(color, 60)
    dark = _shade(color, -70)
    pygame.draw.rect(screen, light, (x + 1, y + 1, size - 2, edge))
    pygame.draw.rect(screen, light, (x + 1, y + 1, edge, size - 2))
    pygame.draw.rect(screen, dark, (x + 1, y + size - 1 - edge, size - 2, edge))
    pygame.draw.rect(screen, dark, (x + size - 1 - edge, y + 1, edge, size - 2))


def draw_grid(screen, grid, flash_rows=(), flash_on=False):
    """Draw a grid of locked cells. Rows in flash_rows blink to the highlight
    color while flash_on is True (the line-clear animation)."""
    for row, cells in enumerate(grid):
        for col, kind in enumerate(cells):
            x = BOARD_ORIGIN_X + col * CELL_SIZE
            y = BOARD_ORIGIN_Y + row * CELL_SIZE
            pygame.draw.rect(screen, GRAY, (x, y, CELL_SIZE, CELL_SIZE), 1)
            if kind:
                color = HIGHLIGHT if (flash_on and row in flash_rows) else PIECE_COLORS[kind]
                draw_cell(screen, x, y, CELL_SIZE, color)


def draw_board(screen, board):
    draw_grid(screen, board.grid)


def draw_piece(screen, piece):
    color = PIECE_COLORS[piece.kind]
    for row, col in piece.cells():
        if row < 0:
            continue
        x = BOARD_ORIGIN_X + col * CELL_SIZE
        y = BOARD_ORIGIN_Y + row * CELL_SIZE
        draw_cell(screen, x, y, CELL_SIZE, color)


def ghost_cells(board, piece):
    # Show where the piece is going to fall with ghost colors
    row = piece.row
    while board.is_valid(piece.cells()):
        piece.row += 1
    piece.row -= 1
    landed = piece.cells()
    piece.row = row
    return landed


def draw_ghost(screen, board, piece):
    color = PIECE_COLORS[piece.kind]
    for row, col in ghost_cells(board, piece):
        if row < 0:
            continue
        x = BOARD_ORIGIN_X + col * CELL_SIZE
        y = BOARD_ORIGIN_Y + row * CELL_SIZE
        pygame.draw.rect(screen, color, (x + 3, y + 3, CELL_SIZE - 6, CELL_SIZE - 6), 2)


def draw_mini_piece(screen, kind, box_x, box_y, box_w, box_h):
    """Draw a small, centered preview of a piece's spawn orientation,
    used for both the hold slot and the next-piece queue."""
    box_size = ROTATION_STATES[kind]["box"]
    cells = ROTATION_STATES[kind]["cells"][0]
    piece_px = box_size * PREVIEW_CELL
    offset_x = box_x + (box_w - piece_px) // 2
    offset_y = box_y + (box_h - piece_px) // 2
    color = PIECE_COLORS[kind]
    for r, c in cells:
        x = offset_x + c * PREVIEW_CELL
        y = offset_y + r * PREVIEW_CELL
        draw_cell(screen, x, y, PREVIEW_CELL, color)


def draw_panel_slot(screen, rect, label, font, kind=None):
    x, y, w, h = rect
    pygame.draw.rect(screen, PANEL_BG, rect)
    pygame.draw.rect(screen, GRAY, rect, 2)
    screen.blit(font.render(label, True, BLACK), (x + 6, y - 22))
    if kind is not None:
        draw_mini_piece(screen, kind, x, y, w, h)


def draw_hold(screen, font, game):
    draw_panel_slot(screen, HOLD_BOX, "HOLD", font, game.hold_kind)


def draw_next_queue(screen, font, game):
    for i, box in enumerate(NEXT_BOXES):
        label = "NEXT" if i == 0 else ""
        draw_panel_slot(screen, box, label, font, game.next_queue[i])


def draw_hud(screen, font, game):
    lines = [f"Score: {game.score}", f"Level: {game.level}", f"Lines: {game.lines_cleared}",
             f"Pieces: {game.pieces_placed}", f"Time: {format_time(game.elapsed)}"]
    for i, line in enumerate(lines):
        screen.blit(font.render(line, True, BLACK), (HOLD_BOX[0], HOLD_BOX[1] + HOLD_BOX[3] + 30 + i * 26))


def draw_hints(screen, small_font, muted):
    """Key reminders for the features that aren't in the README table's
    basics, in the bottom-left corner."""
    lines = ["P / Esc  Pause", f"M  Sound {'off' if muted else 'on'}", f"T  Theme: {current_theme}"]
    top = WINDOW_SIZE[1] - 20 - len(lines) * 20
    for i, line in enumerate(lines):
        screen.blit(small_font.render(line, True, GRAY), (HOLD_BOX[0], top + i * 20))


def draw_effects(screen, font, big_font, game):
    """Clear / T-spin / combo text at the top of the board, and LEVEL UP."""
    for i, line in enumerate(game.message_lines):
        text = font.render(line, True, HIGHLIGHT)
        screen.blit(text, text.get_rect(center=(_BOARD_CENTER_X, BOARD_ORIGIN_Y + 30 + i * 26)))
    if game.level_up_timer > 0:
        text = big_font.render("LEVEL UP!", True, HIGHLIGHT)
        screen.blit(text, text.get_rect(center=(_BOARD_CENTER_X, BOARD_ORIGIN_Y + 130)))


def draw_pause(screen, big_font, font):
    """Cover the board (so you can't plan while paused) and show the menu."""
    board_rect = (BOARD_ORIGIN_X, BOARD_ORIGIN_Y, BOARD_WIDTH * CELL_SIZE, BOARD_HEIGHT * CELL_SIZE)
    pygame.draw.rect(screen, PANEL_BG, board_rect)
    pygame.draw.rect(screen, GRAY, board_rect, 2)
    pygame.draw.rect(screen, WHITE, PAUSE_PANEL, border_radius=8)
    pygame.draw.rect(screen, GRAY, PAUSE_PANEL, 2, border_radius=8)
    title = big_font.render("PAUSED", True, BLACK)
    screen.blit(title, title.get_rect(center=(_BOARD_CENTER_X, PAUSE_PANEL[1] + 40)))
    labels = {"resume": "Resume", "restart": "Restart", "quit": "Quit"}
    mouse_pos = pygame.mouse.get_pos()
    for name, rect in PAUSE_BUTTONS.items():
        draw_button(screen, font, rect, labels[name], mouse_pos, primary=(name == "resume"))


def load_scores(path=SCORES_FILE):
    """Top scores from the file, highest first. A missing or broken file
    just means no scores yet."""
    try:
        with open(path) as f:
            scores = json.load(f)
    except (OSError, ValueError):
        return []
    if not isinstance(scores, list):
        return []
    scores = [s for s in scores if isinstance(s, int) and not isinstance(s, bool)]
    return sorted(scores, reverse=True)[:LEADERBOARD_SIZE]


def save_score(score, path=SCORES_FILE):
    """Add a score to the file and return the new top list. A score of 0
    is not saved."""
    scores = load_scores(path)
    if score > 0:
        scores = sorted(scores + [score], reverse=True)[:LEADERBOARD_SIZE]
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                json.dump(scores, f)
        except OSError:
            pass
    return scores


# ---------------------------------------------------------------------------
# User accounts (no pygame needed for any of this)
#
# Passwords are never stored. For each account we keep a random salt and a
# PBKDF2-HMAC-SHA256 hash of the password, plus the iteration count used, so
# the work factor can be raised later without locking anyone out.
# ---------------------------------------------------------------------------
def _hash_password(password, salt, iterations=None):
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations or PBKDF2_ITERATIONS
    )


def _valid_record(key, record):
    """True if a users.json entry has the expected shape. Usernames are
    re-checked here so a hand-edited file can never smuggle in a name that
    would later be used as a file name."""
    if not isinstance(record, dict):
        return False
    name = record.get("name")
    iterations = record.get("iterations")
    return (
        isinstance(name, str)
        and USERNAME_PATTERN.fullmatch(name) is not None
        and key == name.lower()
        and isinstance(record.get("salt"), str)
        and isinstance(record.get("hash"), str)
        and isinstance(iterations, int)
        and not isinstance(iterations, bool)
        and iterations > 0
    )


def load_users(path=USERS_FILE):
    """All accounts as {lowercase username: record}. A missing or broken
    file just means no accounts yet."""
    try:
        with open(path) as f:
            users = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(users, dict):
        return {}
    return {key: rec for key, rec in users.items() if _valid_record(key, rec)}


def save_users(users, path=USERS_FILE):
    """Write the accounts file (readable by the owner only). Writes to a
    temporary file first, so a crash can't leave a half-written users.json.
    Returns True on success."""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(users, f)
        os.replace(tmp, path)
    except OSError:
        return False
    return True


def validate_new_account(username, password):
    """An error message for a bad username or password, or None if both
    are acceptable."""
    if USERNAME_PATTERN.fullmatch(username) is None:
        return "Username must be 3-12 letters, numbers or underscores."
    if not MIN_PASSWORD_LEN <= len(password) <= MAX_PASSWORD_LEN:
        return f"Password must be {MIN_PASSWORD_LEN}-{MAX_PASSWORD_LEN} characters."
    if password.lower() == username.lower():
        return "Password can't be the same as your username."
    return None


def register_user(username, password, path=USERS_FILE):
    """Create an account. Returns (username, None) on success, or
    (None, error message). Usernames are case-insensitive but keep the
    capitalisation they were registered with."""
    error = validate_new_account(username, password)
    if error:
        return None, error
    users = load_users(path)
    key = username.lower()
    if key in users:
        return None, "That username is taken."
    salt = secrets.token_bytes(SALT_BYTES)
    users[key] = {
        "name": username,
        "salt": salt.hex(),
        "hash": _hash_password(password, salt).hex(),
        "iterations": PBKDF2_ITERATIONS,
    }
    if not save_users(users, path):
        return None, "Couldn't save the account file."
    return username, None


def authenticate(username, password, path=USERS_FILE):
    """The account's username if the password is right, otherwise None.
    Callers should show one generic message for every failure, so nobody
    can use the login screen to find out which usernames exist."""
    record = load_users(path).get(username.lower())
    if record is None:
        _hash_password(password, bytes(SALT_BYTES))  # same cost as a real check
        return None
    try:
        salt = bytes.fromhex(record["salt"])
        expected = bytes.fromhex(record["hash"])
    except ValueError:
        return None
    actual = _hash_password(password, salt, record["iterations"])
    return record["name"] if hmac.compare_digest(actual, expected) else None


def scores_path(username):
    """Where one player's high scores are kept. Safe to build from a
    username, because usernames are limited to letters, digits and _."""
    return SCORES_DIR / f"{username.lower()}.json"


def point_in_rect(pos, rect):
    """True if the (x, y) point is inside an (x, y, width, height) rect."""
    x, y, w, h = rect
    return x <= pos[0] < x + w and y <= pos[1] < y + h


# Sign In / Sign Up page layout.
FIELD_W = 300
FIELD_H = 36
FIELD_SPACING = 80
FIELD_TOP = 200  # y of the first field's label
TOGGLE_W = 70    # the Show / Hide button beside a password box


def login_layout(mode):
    """Where everything sits on the Sign In ("login") or Sign Up
    ("register") page. Drawing and clicking both use this, so they always
    agree about where the buttons are."""
    left = WINDOW_SIZE[0] // 2 - FIELD_W // 2
    if mode == "login":
        fields = ("username", "password")
    else:
        fields = ("username", "password", "confirm")
    layout = {"fields": {}, "toggles": {}}
    for i, field in enumerate(fields):
        y = FIELD_TOP + i * FIELD_SPACING + 26
        layout["fields"][field] = (left, y, FIELD_W, FIELD_H)
        if field != "username":
            layout["toggles"][field] = (left + FIELD_W + 10, y, TOGGLE_W, FIELD_H)
    bottom = FIELD_TOP + (len(fields) - 1) * FIELD_SPACING + 26 + FIELD_H
    layout["message_y"] = bottom + 22
    layout["submit"] = (left, bottom + 50, FIELD_W, 44)
    layout["switch"] = (left, bottom + 110, FIELD_W, 40)
    layout["quit"] = (left, WINDOW_SIZE[1] - 70, FIELD_W, 36)
    return layout


class LoginScreen:
    """State, key handling and click handling for the Sign In and Sign Up
    pages. Drawing lives in draw_login; once login.user is set, the player
    is in."""

    MAX_LEN = {"username": USERNAME_MAX_LEN, "password": MAX_PASSWORD_LEN,
               "confirm": MAX_PASSWORD_LEN}

    def __init__(self, users_path=USERS_FILE):
        self.users_path = users_path
        self.mode = "login"  # the Sign In page; "register" is the Sign Up page
        self.values = {"username": "", "password": "", "confirm": ""}
        self.active = 0  # index into self.fields
        self.show_password = False
        self.message = ""
        self.user = None

    @property
    def fields(self):
        if self.mode == "login":
            return ("username", "password")
        return ("username", "password", "confirm")

    @property
    def heading(self):
        return "Sign in to play" if self.mode == "login" else "Create your account"

    def toggle_mode(self):
        """Go from the Sign In page to the Sign Up page, or back."""
        self.mode = "register" if self.mode == "login" else "login"
        self.values["password"] = ""
        self.values["confirm"] = ""
        self.show_password = False
        self.active = 0
        self.message = ""

    def handle_key(self, key, char=""):
        field = self.fields[self.active]
        if key in (pygame.K_TAB, pygame.K_DOWN):
            self.active = (self.active + 1) % len(self.fields)
        elif key == pygame.K_UP:
            self.active = (self.active - 1) % len(self.fields)
        elif key == pygame.K_BACKSPACE:
            self.values[field] = self.values[field][:-1]
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.active < len(self.fields) - 1:
                self.active += 1
            else:
                self.submit()
        elif char and char.isprintable():
            if field == "username" and re.fullmatch(r"[A-Za-z0-9_]", char) is None:
                return
            if len(self.values[field]) < self.MAX_LEN[field]:
                self.values[field] += char
                self.message = ""

    def handle_click(self, pos):
        """React to a left click at pos. Returns "quit" if the Quit button
        was clicked, otherwise None."""
        layout = login_layout(self.mode)
        for i, field in enumerate(self.fields):
            if point_in_rect(pos, layout["fields"][field]):
                self.active = i
                return None
            toggle = layout["toggles"].get(field)
            if toggle is not None and point_in_rect(pos, toggle):
                self.show_password = not self.show_password
                return None
        if point_in_rect(pos, layout["submit"]):
            self.submit()
        elif point_in_rect(pos, layout["switch"]):
            self.toggle_mode()
        elif point_in_rect(pos, layout["quit"]):
            return "quit"
        return None

    def submit(self):
        username = self.values["username"]
        password = self.values["password"]
        if self.mode == "login":
            name = authenticate(username, password, self.users_path)
            if name is None:
                self.message = "Wrong username or password."
                self.values["password"] = ""
                self.active = 1
                return
        else:
            if password != self.values["confirm"]:
                self.message = "Passwords don't match."
                self.values["password"] = ""
                self.values["confirm"] = ""
                self.active = 1
                return
            name, error = register_user(username, password, self.users_path)
            if error:
                self.message = error
                return
        self.user = name


def draw_leaderboard(screen, font, scores, highlight=None, title="HIGH SCORES"):
    """Top scores under the game over text. highlight is the index of the
    score that was just earned, shown in red."""
    center_x = BOARD_ORIGIN_X + (BOARD_WIDTH * CELL_SIZE) // 2
    top = BOARD_ORIGIN_Y + (BOARD_HEIGHT * CELL_SIZE) // 2 + 70
    heading = font.render(title, True, BLACK)
    screen.blit(heading, heading.get_rect(center=(center_x, top)))
    if not scores:
        line = font.render("No scores yet", True, GRAY)
        screen.blit(line, line.get_rect(center=(center_x, top + 30)))
        return
    for i, score in enumerate(scores):
        color = HIGHLIGHT if i == highlight else BLACK
        line = font.render(f"{i + 1}.  {score}", True, color)
        screen.blit(line, line.get_rect(center=(center_x, top + 30 + i * 24)))


def draw_button(screen, font, rect, label, mouse_pos, primary=False):
    """A clickable button. It darkens a little while the mouse is over it."""
    x, y, w, h = rect
    hover = point_in_rect(mouse_pos, rect)
    if primary:
        fill = BUTTON_PRIMARY_HOVER if hover else HIGHLIGHT
        text_color = WHITE
    else:
        fill = BUTTON_HOVER if hover else PANEL_BG
        text_color = BLACK
    pygame.draw.rect(screen, fill, rect, border_radius=6)
    pygame.draw.rect(screen, GRAY, rect, 2, border_radius=6)
    text = font.render(label, True, text_color)
    screen.blit(text, text.get_rect(center=(x + w // 2, y + h // 2)))


def draw_session_panel(screen, font, user):
    """Who is signed in, with the Sign Out button underneath."""
    x, y, _, _ = SIGN_OUT_BUTTON
    screen.blit(font.render("Signed in as:", True, GRAY), (x, y - 58))
    screen.blit(font.render(user, True, BLACK), (x, y - 32))
    draw_button(screen, font, SIGN_OUT_BUTTON, "Sign Out", pygame.mouse.get_pos())


def draw_game_over(screen, big_font, small_font, game=None):
    board_center_x = BOARD_ORIGIN_X + (BOARD_WIDTH * CELL_SIZE) // 2
    board_center_y = BOARD_ORIGIN_Y + (BOARD_HEIGHT * CELL_SIZE) // 2

    panel = pygame.Rect(0, 0, BOARD_WIDTH * CELL_SIZE + 40, 320)
    panel.center = (board_center_x, board_center_y + 60)
    pygame.draw.rect(screen, PANEL_BG, panel)
    pygame.draw.rect(screen, GRAY, panel, 2)

    title = big_font.render("GAME OVER", True, HIGHLIGHT)
    screen.blit(title, title.get_rect(center=(board_center_x, board_center_y - 72)))

    if game is not None:
        stats = [f"Pieces {game.pieces_placed}    Lines {game.lines_cleared}",
                 f"Level {game.level}    Time {format_time(game.elapsed)}"]
        for i, line in enumerate(stats):
            text = small_font.render(line, True, BLACK)
            screen.blit(text, text.get_rect(center=(board_center_x, board_center_y - 40 + i * 22)))

    labels = {"restart": "Restart", "sign_out": "Sign Out", "quit": "Quit"}
    mouse_pos = pygame.mouse.get_pos()
    for name, rect in GAME_OVER_BUTTONS.items():
        draw_button(screen, small_font, rect, labels[name], mouse_pos,
                    primary=(name == "restart"))


def draw_login(screen, font, big_font, login):
    mouse_pos = pygame.mouse.get_pos()
    layout = login_layout(login.mode)
    center_x = WINDOW_SIZE[0] // 2

    title = big_font.render("TETRIS", True, BLACK)
    screen.blit(title, title.get_rect(center=(center_x, 100)))
    heading = font.render(login.heading, True, GRAY)
    screen.blit(heading, heading.get_rect(center=(center_x, 150)))

    labels = {"username": "Username", "password": "Password",
              "confirm": "Confirm password"}
    blink_on = (pygame.time.get_ticks() // 500) % 2 == 0
    for i, field in enumerate(login.fields):
        box = layout["fields"][field]
        x, y, _, _ = box
        screen.blit(font.render(labels[field], True, BLACK), (x, y - 26))
        pygame.draw.rect(screen, PANEL_BG, box)
        active = i == login.active
        pygame.draw.rect(screen, HIGHLIGHT if active else GRAY, box, 2)

        text = login.values[field]
        hidden = field != "username" and not login.show_password
        shown = ("*" * len(text) if hidden else text)[-22:]
        if active and blink_on:
            shown += "|"
        screen.blit(font.render(shown, True, BLACK), (x + 8, y + 6))

        toggle = layout["toggles"].get(field)
        if toggle is not None:
            label = "Hide" if login.show_password else "Show"
            draw_button(screen, font, toggle, label, mouse_pos)

    if login.message:
        msg = font.render(login.message, True, HIGHLIGHT)
        screen.blit(msg, msg.get_rect(center=(center_x, layout["message_y"])))

    if login.mode == "login":
        submit_label, switch_label = "Sign In", "Create an account"
    else:
        submit_label, switch_label = "Sign Up", "Back to Sign In"
    draw_button(screen, font, layout["submit"], submit_label, mouse_pos, primary=True)
    draw_button(screen, font, layout["switch"], switch_label, mouse_pos)
    draw_button(screen, font, layout["quit"], "Quit", mouse_pos)


def run_login(screen, clock, font, big_font):
    """Show the Sign In / Sign Up pages until someone signs in. Returns
    their username, or None if they quit."""
    login = LoginScreen()
    pygame.key.set_repeat(400, 40)  # hold backspace to delete
    try:
        while login.user is None:
            clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                elif event.type == pygame.KEYDOWN:
                    login.handle_key(event.key, event.unicode)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if login.handle_click(event.pos) == "quit":
                        return None
            screen.fill(WHITE)
            draw_login(screen, font, big_font, login)
            pygame.display.flip()
        return login.user
    finally:
        pygame.key.set_repeat()  # key repeat would break the game controls


def play(screen, clock, font, big_font, user, sounds=None):
    """Run the game for one signed-in player. Returns "logout" or "quit"."""
    pygame.display.set_caption(f"Tetris - {user}")
    score_file = scores_path(user)
    settings_file = settings_path(user)
    settings = load_settings(settings_file)
    apply_theme(settings["theme"])
    sounds = sounds or SoundBank()
    sounds.muted = settings["muted"]
    small_font = pygame.font.SysFont("Calibri", 16, True)

    def save_prefs():
        save_settings({"theme": current_theme, "muted": sounds.muted}, settings_file)

    game = Game()
    soft_dropping = False
    scores = None
    highlight = None

    while True:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if point_in_rect(event.pos, SIGN_OUT_BUTTON):
                    if scores is None:
                        save_score(game.score, score_file)  # keep the current run
                    return "logout"
                if game.state == "paused":
                    if point_in_rect(event.pos, PAUSE_BUTTONS["resume"]):
                        game.toggle_pause()
                    elif point_in_rect(event.pos, PAUSE_BUTTONS["restart"]):
                        save_score(game.score, score_file)
                        game = Game()
                    elif point_in_rect(event.pos, PAUSE_BUTTONS["quit"]):
                        save_score(game.score, score_file)
                        return "quit"
                elif game.state == "gameover":
                    if point_in_rect(event.pos, GAME_OVER_BUTTONS["restart"]):
                        game = Game()
                        scores = None
                    elif point_in_rect(event.pos, GAME_OVER_BUTTONS["sign_out"]):
                        return "logout"
                    elif point_in_rect(event.pos, GAME_OVER_BUTTONS["quit"]):
                        return "quit"
            elif event.type == pygame.KEYDOWN:
                key = event.key
                if key == pygame.K_m:
                    sounds.toggle_mute()
                    save_prefs()
                elif key == pygame.K_t:
                    apply_theme(next_theme(current_theme))
                    save_prefs()
                elif key in (pygame.K_p, pygame.K_ESCAPE) and game.state != "gameover":
                    game.toggle_pause()
                elif game.state == "playing":
                    if key == pygame.K_LEFT:
                        if game.move(-1, 0):
                            sounds.play("move")
                    elif key == pygame.K_RIGHT:
                        if game.move(1, 0):
                            sounds.play("move")
                    elif key == pygame.K_UP:
                        game.rotate(clockwise=True)
                    elif key == pygame.K_z:
                        game.rotate(clockwise=False)
                    elif key == pygame.K_SPACE:
                        game.hard_drop()
                    elif key == pygame.K_c:
                        game.hold()
                    elif key == pygame.K_DOWN:
                        soft_dropping = True
                elif game.state == "paused":
                    if key == pygame.K_r:
                        save_score(game.score, score_file)
                        game = Game()
                    elif key == pygame.K_q:
                        save_score(game.score, score_file)
                        return "quit"
                elif game.state == "gameover":
                    if key == pygame.K_r:
                        game = Game()
                        scores = None
                    elif key == pygame.K_l:
                        return "logout"
                    elif key == pygame.K_q:
                        return "quit"
            elif event.type == pygame.KEYUP and event.key == pygame.K_DOWN:
                soft_dropping = False

        if game.state == "playing":
            if soft_dropping:
                game.soft_drop()
            game.update(dt)
        for name in game.events:
            sounds.play(name)
        game.events.clear()

        if game.state == "gameover" and scores is None:
            scores = save_score(game.score, score_file)
            highlight = scores.index(game.score) if game.score in scores else None

        screen.fill(WHITE)
        if game.state == "paused":
            draw_hold(screen, font, game)
            draw_next_queue(screen, font, game)
            draw_hud(screen, font, game)
            draw_session_panel(screen, font, user)
            draw_hints(screen, small_font, sounds.muted)
            draw_pause(screen, big_font, font)
        else:
            if game.clear_anim:
                anim = game.clear_anim
                draw_grid(screen, anim["grid"], anim["rows"], int(anim["time"] * 20) % 2 == 0)
            else:
                draw_board(screen, game.board)
            if game.state == "playing":
                draw_ghost(screen, game.board, game.piece)
                draw_piece(screen, game.piece)
            draw_hold(screen, font, game)
            draw_next_queue(screen, font, game)
            draw_hud(screen, font, game)
            draw_session_panel(screen, font, user)
            draw_hints(screen, small_font, sounds.muted)
            if game.state == "playing":
                draw_effects(screen, font, big_font, game)
            if game.state == "gameover":
                draw_game_over(screen, big_font, font, game)
                draw_leaderboard(screen, font, scores, highlight, title="YOUR HIGH SCORES")

        pygame.display.flip()


def main():
    pygame.mixer.pre_init(SOUND_RATE, -16, 1)
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Calibri", 22, True)
    big_font = pygame.font.SysFont("Calibri", 46, True)
    sounds = SoundBank()

    while True:
        apply_theme("light")  # the sign-in pages always use the default look
        pygame.display.set_caption("Tetris - Sign In")
        user = run_login(screen, clock, font, big_font)
        if user is None:
            break
        if play(screen, clock, font, big_font, user, sounds) == "quit":
            break

    pygame.quit()


if __name__ == "__main__":
    main()
