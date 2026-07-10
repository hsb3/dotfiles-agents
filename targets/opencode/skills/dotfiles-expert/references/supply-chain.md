# Package-manager supply-chain hardening

Authoritative statement: `~/dotfiles/CLAUDE.md` → "Package-manager supply-chain hardening" and `claude-code/.claude/instructions/terminal.md`. Config files: `.npmrc.example`, `uv/.config/uv/uv.toml`, `pip/.config/pip/pip.conf`, `pnpm/Library/Preferences/pnpm/config.yaml`, `bun/.bunfig.toml`.

**The mental model:** npm/pnpm/bun/uv/pip are configured **secure-by-default** following [npm-security-best-practices](https://github.com/lirantal/npm-security-best-practices) — a **7-day install cooldown** plus blocks on **install scripts** and **non-registry sources**, to mitigate supply-chain attacks (Shai-Hulud, etc.).

> **When an install fails for one of these reasons it is INTENTIONAL.** Do NOT disable the protection globally to "fix" it. Use the documented per-command override below, or fix the manifest.

## Per-manager settings

| Manager | File | Stowed? | Key settings |
|---|---|---|---|
| npm | `~/.npmrc` (template `.npmrc.example`) | No (machine-local, secret-free) | `ignore-scripts=true`, `allow-git=none`, `min-release-age=7` |
| pnpm | `~/Library/Preferences/pnpm/config.yaml` | Yes | `minimumReleaseAge: 10080` (7d, minutes), `trustPolicy: no-downgrade`, `blockExoticSubdeps: true`, `strictDepBuilds: true`. **pnpm 11 ignores a global `onlyBuiltDependencies`** (warns + drops the key), so the effective global policy is "block every build script" — allowlist trusted builders per-project in `pnpm-workspace.yaml` |
| bun | `~/.bunfig.toml` | Yes | `[install] minimumReleaseAge = 604800` (7d, seconds); `minimumReleaseAgeExcludes = ["typescript","@types/bun"]` (bun already blocks postinstall by default) |
| uv / uvx | `~/.config/uv/uv.toml` | Yes | `exclude-newer = "7 days"` (rolling cooldown), `index-strategy = "first-index"` (anti dependency-confusion) |
| pip / pipx | `~/.config/pip/pip.conf` | Yes | `index-url` pinned to PyPI only (no extra-index-url). No cooldown — use uv/uvx for cooldown-protected installs |

Note: pnpm 11 reads non-auth settings from `config.yaml`, NOT the legacy `.npmrc`-style `rc` (which holds auth only, machine-local).

## Failure signature → per-command override

| Symptom | Cause | Override (single command — do NOT flip the global) |
|---|---|---|
| version published <7 days ago is skipped / "not found" (incl. same-day security patches) | install cooldown | uv: `uv pip install pkg --exclude-newer-package "pkg=false"`; npm: `--before=<date>`; or wait out the window |
| postinstall/build script didn't run | npm `ignore-scripts=true` | run it explicitly, e.g. `npm rebuild <pkg>` — don't flip the global default |
| `EALLOWGIT` / git or non-registry dep rejected | npm `allow-git=none` | resolve from registry; one-off git dep: `npm i --allow-git=all <spec>` |
| pnpm: an unallowlisted dependency build is a HARD failure | `strictDepBuilds: true` (and pnpm 11 ignores a **global** `onlyBuiltDependencies`) | allowlist the package in the **project's** `pnpm-workspace.yaml` `onlyBuiltDependencies` — NOT the global config, and never by disabling `strictDepBuilds` |

## Commented opt-ins (present but OFF — they break common workflows)

These are in the config files commented out because they break editable installs, source-only packages, uv workspaces, etc. If you enable one, the per-package escape hatches are:

- uv `no-sources` / `no-build` (wheel-only) → escape: `uv pip install pkg --no-binary-package pkg`
- pip `only-binary = :all:` / `require-hashes` → escape: `pip install pkg --no-binary pkg`

`no-build`/`only-binary` are the real "ignore-scripts" for Python (no sdist build = no setup.py code runs). `index-strategy = first-index` (uv) and the single pinned `index-url` (pip) are the dependency-confusion defenses — NEVER add `extra-index-url` or `unsafe-best-match`.

## Private `@org` packages

Configure auth in a **per-project, gitignored `.npmrc`** with an env-var token (`${VAR}`), never a global plaintext token. The global `~/.npmrc` stays secret-free. Pattern:

```
@myorg:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=${GITHUB_PACKAGES_TOKEN}
```

Export the token only in that project (keychain / direnv / 1Password). npm expands `${VAR}` at runtime so the file on disk stays secret-free. Prefer a fine-grained `read:packages`-scoped token with expiry.

## Adjacent

`pip-audit` is installed as a uv tool for ad-hoc CVE scans. Deferred decisions (npq + Socket Firewall install-time scanners, the rest of the credential-on-disk migration) are tracked as GitHub issues with the `security` label.
