---
name: opencode-sandbox
description: Spin up a disposable, isolated opencode instance and hand it to this session as an MCP server — a sandboxed coding agent with its own workspace volume that cannot see the host filesystem. Use when the user asks for a sandbox, a scratch agent, an isolated or throwaway opencode instance, a place to let an agent work on a copy of a project, or says "opencode-sandbox", "sandbox this project", or "give me an isolated agent". Covers installing the CLI, seeding project context, custom config and plugins, worktrees inside the instance, registering with the current client, and destroying it afterward.
---

# opencode sandbox

An isolated opencode instance is a container stack with its own named volumes, reachable
over MCP. Its `/workspace` is a Docker volume, not a bind mount, so the instance cannot
read or write anything on the host. Use one when an agent should work somewhere that cannot
touch the real machine: on a copy of a project, on generated code, or on a long task that
deserves its own scratch space.

Everything goes through the `opencode-sandbox` binary. Invoke it by name — it is on PATH.

## Before anything else

Run `opencode-sandbox list`. If the command is not found, install it by running these —
do not ask the user where the project is, and do not improvise a docker or compose
invocation by hand, because the compose wiring, port allocation, and volume seeding are the
whole point of the CLI:

```
repo=$(gh search repos opencode-sandbox --owner @me --json fullName --jq '.[0].fullName')
gh release download --repo "$repo" --pattern "opencode-sandbox-$(uname -s | tr 'A-Z' 'a-z')-*" --dir /tmp
install -m 755 /tmp/opencode-sandbox-* ~/.local/bin/opencode-sandbox
```

Then confirm with `which opencode-sandbox`. If `gh` is missing or the search returns
nothing, `references/install.md` has the fallbacks, including building from source.

## Choosing instance topology

Decide this before running `create`, not after:

- **One project → one instance.** The default. Seeding only happens at create time, so a
  second project's tree cannot be layered into an existing instance without clobbering the
  first — never share a workspace across projects.
- **One project, several branches, one agent hopping between them** → in-instance git
  worktrees (`references/workspaces.md`), not a second instance.
- **One project, several branches, several agents working in parallel** → one instance per
  branch, named `<project>-<branch>` (e.g. `myapp-feature-x`), so each agent gets its own
  workspace, ports, and MCP registration.
- **Several projects** → several instances, always. A shared instance can't stand in for
  multiple projects anyway: its read/list MCP tools ignore the `directory` param and always
  report the one project they booted with.

## The flow

1. **Create.** Name it after what it is for.

   ```
   opencode-sandbox create <name> [--seed .] [--config ./opencode.jsonc] [--api-port <n>]
                     [--publish <port>] [--web]
   ```

   `--seed` copies a directory into the fresh workspace before first start, and it copies
   **everything except `.DS_Store` files** — no `.gitignore`, no skip list otherwise — so
   for a large repo seed a pruned copy instead. `references/project-context.md` covers
   whole vs partial seeding and how to move files in and out afterward. `--web` also
   publishes the browser UI; leave it off unless the user wants to click around.

   `--api-port <n>` publishes the raw opencode backend on `127.0.0.1:<n>`, for attaching a
   local opencode client to the same instance an agent is driving over MCP. `--publish
   <container-port>` or `--publish <host-port>:<container-port>` maps an extra host port
   into the instance — repeatable — for anything else running in there you want to reach
   from the host, like a dev server the agent started. Both bind `127.0.0.1` only, same as
   the MCP bridge, and neither has inbound authentication.

   Provider API keys are forwarded from your environment (`ANTHROPIC_API_KEY`,
   `OPENAI_API_KEY`, `GOOGLE_GENERATIVE_AI_API_KEY`, `OPENROUTER_API_KEY`). With none set
   the instance still runs on opencode's free hosted models, so a missing key is a
   limitation to mention, not a blocker. `create` does not report which keys it forwarded —
   check with `docker exec ocsbx-<name>-opencode-1 opencode models` if it matters.

2. **Register.** `create` prints the exact registration line, and `opencode-sandbox url
   <name>` reprints it. Run that line rather than composing the URL yourself — note that
   `url` emits a Claude Code command, so it will not substitute into one. For Claude Code:

   ```
   claude mcp add --transport http <name> http://127.0.0.1:<port>/mcp
   ```

   For Codex, take the URL from that output and use
   `codex mcp add <name> --url http://127.0.0.1:<port>/mcp`. Check with
   `codex mcp list`; use a unique name and do not overwrite an unrelated registration.
   Registration changes the selected client's configuration, never the other client's.

   MCP servers load at session start, so the session that registers an instance cannot use
   it. Register, then start a new session in that directory.

3. **Destroy when done.** Instances keep running until removed, so close the loop:

   ```
   claude mcp remove <name> && opencode-sandbox destroy <name>
   ```

   In Codex, unregister with `codex mcp remove <name>` instead, then run the same
   `opencode-sandbox destroy <name>`. Remove only the registration created for this instance.

   `destroy` deletes the workspace volume with everything in it. Salvage first —
   `opencode-sandbox export <name> <dir>` copies the whole workspace out (works even while
   stopped), or `opencode-sandbox fetch-url <name>` if what's worth keeping is a git branch
   with its history (see `references/project-context.md`). Confirm with the user if the
   instance produced real work.

## Going further

- `references/config.md` — pinning a model or provider, giving the instance its own MCP
  servers, loading plugins, and what to edit after creation. Note there is no theme setting.
  Also covers `gh`: neither container ships it, the manual-install workaround, and why
  `gh auth login` with the operator's own account defeats the isolation.
- `references/project-context.md` — seeding whole repos, tracked files only, or one
  subdirectory; getting work back out with `fetch-url` and `export`, `docker cp` for
  pushing a loose file in.
- `references/workspaces.md` — git worktrees inside an instance, what they require, and
  when a second instance is the better answer.

## Security posture

The MCP bridge has no inbound authentication. Anyone who can reach its port gets the full
tool surface — reading and writing files and running shell commands inside that instance's
`/workspace`. `--api-port` and `--publish` are the same story — no auth of their own, and
`--publish` opens whatever the agent happened to start. The CLI publishes all of these on
`127.0.0.1` only. Never widen the bind to `0.0.0.0`, forward a port, or put one behind a
public reverse proxy without a real auth layer in front of it.

The isolation protects the host from the instance, not the instance from itself. Anything
seeded into the workspace is readable by whatever runs in there, so do not seed secrets.
