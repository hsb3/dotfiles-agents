# Configuration and preferences

## The preferences model

Everything except dynamic profiles lives in one domain, `com.googlecode.iterm2`, backed by
`~/Library/Preferences/com.googlecode.iterm2.plist`. iTerm2 holds it in memory and writes it back
on quit, which is why scripted changes made while it runs disappear (see SKILL.md).

Useful keys:

| Key | Type | Meaning |
|---|---|---|
| `Default Bookmark Guid` | string | GUID of the default profile |
| `LoadPrefsFromCustomFolder` | bool | Read prefs from a folder instead of the standard domain |
| `PrefsCustomFolder` | string | Absolute path to that folder |
| `EnableAPIServer` | bool | Allow the Python API to connect |
| `PromptOnQuit` | bool | Confirm before quitting |

Read a key without launching anything:

```bash
defaults read com.googlecode.iterm2 "Default Bookmark Guid"
```

## Dynamic profiles

JSON files in `~/Library/Application Support/iTerm2/DynamicProfiles/`, loaded at launch with no
import step — the right unit to track in a dotfiles repo.

```json
{
  "Profiles": [
    {
      "Name": "Newspaper",
      "Guid": "unique-stable-id",
      "Background Color":  { "Red Component": 0.96, "Green Component": 0.94, "Blue Component": 0.91 },
      "Normal Font": "BlexMonoNerdFont-Regular 15"
    }
  ]
}
```

Rules that bite:

- Every entry needs a unique, stable `Guid`. Reusing one across files triggers a duplicate-GUID
  warning at startup.
- iTerm2 loads **every file in the directory regardless of extension**. A `profiles.json.example`
  seed placed there is loaded as a real profiles file. Keep seeds in a sibling directory.
- A dynamic profile cannot set itself as default; that is the `Default Bookmark Guid` pref.
- Switch profiles at runtime with an escape sequence, which is how a shell function can retheme a
  live session: `printf "\033]50;SetProfile=Newspaper\a"`.

## Tracking the whole config in a repo

Dynamic profiles cover profiles only. Every other setting — keybindings, pointer behavior,
window options, status bar layout — stays untracked unless you point iTerm2 at a custom folder.

1. Quit iTerm2.
2. Export the current prefs and make them diffable. `defaults export` writes a **binary** plist,
   which git stores as an opaque blob:

   ```bash
   defaults export com.googlecode.iterm2 "$REPO/_config/iterm2/com.googlecode.iterm2.plist"
   plutil -convert xml1 "$REPO/_config/iterm2/com.googlecode.iterm2.plist"
   ```

3. Point iTerm2 at the folder:

   ```bash
   defaults write com.googlecode.iterm2 LoadPrefsFromCustomFolder -bool true
   defaults write com.googlecode.iterm2 PrefsCustomFolder -string "$REPO/_config/iterm2"
   ```

4. Relaunch. On first quit iTerm2 asks whether to save changes to the folder; choosing to save
   automatically keeps the tracked file current, and config changes then surface as a git diff.

Put the folder somewhere the dotfiles manager will not try to symlink into `$HOME`. Under GNU
Stow, a directory inside a stow package becomes a link target, so use a repo-internal path that is
not a stow package (or a `.stow-local-ignore` entry). iTerm2 rewrites this file itself, so it must
be a real file, never a symlink into the repo.

## Fonts

Nerd Font variants supply the glyphs that shell prompts like Starship and Powerlevel10k expect.
Set `Normal Font` in the profile to the PostScript-ish name plus point size
(`"BlexMonoNerdFont-Regular 15"`). iTerm2 does not require a monospaced font but renders them far
better.
