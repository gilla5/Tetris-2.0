# Tetris 2.0: Features

## Core Gameplay

- 10 x 20 playing board with all 7 pieces (I, O, T, S, Z, J, L)
- 7-bag piece randomizer
- SRS rotation system with wall kicks
- Move left and right
- Rotate clockwise and counterclockwise
- Soft drop (fall faster)
- Hard drop (land instantly)
- Ghost piece showing where the piece will land
- Hold piece (once per piece)
- Next-piece preview showing the next 3 pieces
- Lock delay (half a second, restarts on a move or rotation up to 15 times)
- Line clears with a flash animation
- Level up every 10 lines, with pieces falling faster each level
- Game over when a new piece has no room

## Scoring and Bonuses

- Line clear scoring: Single, Double, Triple, and Tetris, multiplied by level
- Points for soft drops and hard drops
- T-spin detection with bonus scoring
- Mini T-spin detection
- Combo bonuses for clearing lines on back-to-back pieces
- Back-to-back bonus (1.5x) for consecutive Tetrises and T-spin clears

## Row Bombs

- Earn a row bomb with each Tetris or T-spin line clear
- Hold up to 3 bombs
- Press B to blast the bottom 2 rows and drop the stack down
- Bonus points for each blasted row
- A bomb is never used on an empty floor

## Game Screen

- Score, level, lines cleared, pieces placed, time played, and bomb count
- On-screen messages for clears, T-spins, combos, back-to-back, bombs, and level up
- Control reminders on screen
- Name of the signed-in player

## Menus and Controls

- Pause and resume (P or Esc)
- Pause menu with Resume, Restart, and Quit buttons
- Restart, Sign Out, and Quit buttons on the game over screen
- Sign Out button during play
- Keyboard shortcuts for every menu action
- Mouse buttons with hover highlighting

## Game Over Screen

- Final stats: pieces placed, lines cleared, level reached, and time played
- The player's top 5 scores, with the new score highlighted

## User Accounts

- Separate Sign In and Sign Up pages
- Mouse-driven pages with Tab, arrow keys, and Enter support
- Show / Hide password button
- Username rules (3 to 12 letters, numbers, or underscores; not case sensitive)
- Password rules (6 to 64 characters) and a confirm password box
- Clear error messages
- Salted PBKDF2-HMAC-SHA256 password hashing; passwords are never stored
- Sign out that saves the current score first

## Scores and Settings

- Personal top 5 high scores for each player
- Per-player saved settings (theme and sound)
- Safe loading: damaged or missing files fall back to defaults

## Sound and Music

- Sound effects for moving, rotating, holding, locking, clearing lines, T-spins, Tetrises, level up, earning a bomb, using a bomb, and game over
- Background music that gets faster with each level
- Music pauses with the game and stops at game over
- Mute toggle (M) for all sound
- Sounds and music are generated in code, so there are no audio files
- Runs silently if no audio device is found

## Themes

- Light, dark, and retro themes
- Switch themes during play with T
- Theme remembered for each player

## High Score Cloud Sync (Optional)

- Self-hosted score server with a JSON REST API
- API-key authentication
- Merges local and cloud scores without double counting
- Scores follow a player to another computer
- Works offline: if the server can't be reached, local scores are kept
- Sync runs on game over, sign out, and quit
- Server input validation and request size limits
- Cloud title shown on the game over screen when sync succeeds

## Quality and Documentation

- 202 automated tests: unit, integration, regression, and acceptance
- User manual (Marp slides)
- Software design document
- Architecture document
- Testing document and test plan
- Team rules document
