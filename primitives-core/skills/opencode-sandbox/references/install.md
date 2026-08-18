# Installing the CLI

`opencode-sandbox` is a single compiled binary. It is not on any package index — it is
distributed from its own repository's GitHub Releases, so installing it means fetching a
release asset or building from source.

## Locate the repository

The skill body cannot hardcode an owner or URL, so resolve it from the user's own GitHub
account instead of guessing:

```
repo=$(gh search repos opencode-sandbox --owner @me --json fullName --jq '.[0].fullName')
echo "$repo"
```

If that returns nothing, the user is not authenticated as the account that owns it, or the
repository is named something else. Ask them for the `owner/repo` rather than searching
GitHub at large — several unrelated projects share the name.

## Install a release binary

Assets are named per platform: `opencode-sandbox-darwin-arm64`, `opencode-sandbox-linux-x64`.

```
gh release download --repo "$repo" --pattern "opencode-sandbox-$(uname -s | tr 'A-Z' 'a-z')-*" --dir /tmp
install -m 755 /tmp/opencode-sandbox-* ~/.local/bin/opencode-sandbox
```

`~/.local/bin` must be on `PATH`. Confirm with `which opencode-sandbox` before continuing —
the binary is invoked by name, never by path.

## Or build from source

Needs `bun`. The repository ships a script that compiles and installs in one step:

```
gh repo clone "$repo" && cd opencode-sandbox && bun run install-local
```

That writes the binary to `~/.local/bin/opencode-sandbox`. `bun run build` instead leaves
it in `dist/` if the user wants to place it themselves.

## Verify

```
opencode-sandbox --version
docker version --format '{{.Server.Os}}'
```

Check Docker separately — `list` reads local state and reports instances as `stopped` when
the daemon is down rather than complaining, so it is not a daemon check. `create` and
`destroy` do check, and refuse with a clear message. Check before the first `create` anyway:
pulling the images on a cold cache takes minutes, and a user who thinks it has hung will
kill it halfway.
