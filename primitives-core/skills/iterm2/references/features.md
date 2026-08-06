# Power features

The catalog to draw on when asked "what am I not using?". Items marked **[SI]** require shell
integration.

## Automation and output handling

- **Triggers** — regexes matched against incoming text, each with an action: highlight, run a
  coprocess, post a notification, set a mark, capture the output, or inject text. The main
  extension point of the terminal. *Profiles > Advanced > Triggers.*
- **Captured Output** **[SI]** — a trigger with the "Capture Output" action collects matching
  lines into a toolbelt pane; click one to scroll to it, double-click to run a coprocess. Built
  for compiler errors. A Clang-style matcher:
  `^([_a-zA-Z0-9+/.-]+):([0-9]+):[0-9]+: (?:error|warning):` with a coprocess of
  `echo vim \1; sleep 0.5; echo \2G` to open the file at the line. Raise scrollback first — the
  default 1000 lines will not hold a build.
- **Coprocesses** — a process attached to a session that reads its output and can type into it.
- **Smart Selection** — quad-click selects by content type (URL, path, quoted string). Rules can
  carry actions, surfaced on cmd-click and in the context menu.
- **Semantic History** — cmd-click a filename to open it in the configured editor.

## Navigation and recall

- **Marks** **[SI]** — `Cmd+Shift+Up`/`Down` between prompts; `Cmd+Shift+M` saves a mark,
  `Cmd+Shift+J` returns to it. Useful for pinning a compile error before switching away.
- **Instant Replay** — `Cmd+Opt+B`, then arrow keys to scrub backwards through what was on screen,
  timestamped to the second. Recovers output that a full-screen program overwrote.
- **Paste history** — `Cmd+Shift+H`, filterable; optionally persisted to disk.
- **Autocomplete** — `Cmd+;` completes from anything in the scrollback.
- **Copy mode / mouseless copy** — `Cmd+F` then tab/shift-tab to extend a selection by word.
- **Timestamps** — per-line modification time, for measuring how long something took.

## Window and session

- **Hotkey window** — a terminal summoned from anywhere by one system-wide keystroke. The highest
  value-per-minute setup on this list.
- **Split panes** — `Cmd+D` / `Cmd+Shift+D`; `Cmd+Shift+Enter` maximizes one pane temporarily.
- **Window arrangements** — snapshot windows/tabs/panes and restore them, optionally at launch.
- **Buried sessions** — park a session out of the way without killing it.
- **tmux integration** — `tmux -CC` maps tmux windows onto native iTerm2 tabs and windows, so
  there is no prefix key and native scrollback works. Sessions survive disconnect as usual. The
  best reason to use tmux locally rather than only over ssh.
- **Automatic Profile Switching** **[SI]** — change profile by hostname/username, e.g. a red
  background on production hosts.

## Display

- **Status bar** — a configurable per-pane bar of components: git branch, working directory, CPU
  and memory, current job, clock, a search field, and custom components fed by the Python API.
  *Profiles > Session > Status bar enabled > Configure.*
- **Badges** — a large translucent label drawn in the corner of a session, from interpolated
  variables such as the session name or git branch. Good for not typing into the wrong host.
- **Minimum contrast** / **smart cursor color** / **cursor guide** — legibility controls that
  rescue unreadable color combinations from other people's tools.
- **Inline images** — `imgcat` renders images in the terminal; `imgls` gives thumbnail listings.

## Scripting

- **Python API** — a websocket API with an async Python library for driving sessions, defining
  custom status bar components, and registering RPCs bound to triggers or keystrokes. Requires
  `EnableAPIServer`, and iTerm2 provisions its own runtime under
  `~/Library/Application Support/iTerm2/iterm2env` on first use.
- **Proprietary escape codes** — the scriptable surface without Python: set profiles, colors,
  badges, marks, progress bars, and folds by `printf`. AppleScript exists but is deprecated.
