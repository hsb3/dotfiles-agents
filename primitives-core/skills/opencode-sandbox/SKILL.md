---
name: opencode-sandbox
description: Spin up a disposable, isolated opencode instance and hand it to this session as an MCP server — a sandboxed coding agent with its own workspace volume that cannot see the host filesystem. Use when the user asks for a sandbox, a scratch agent, an isolated or throwaway opencode instance, a place to run generated code safely, or says "opencode-sandbox", "sandbox this project", or "give me an isolated agent". Covers creating an instance with seeded content, registering it with claude mcp add, and destroying it afterward.
---

# opencode sandbox

An isolated opencode instance is a container stack with its own named volumes, reachable
over MCP. Its `/workspace` is a Docker volume, not a bind mount, so the instance cannot
read or write anything on the host. Use one when work should run somewhere that cannot
touch the real machine: executing generated code, letting an agent loose on a copy of a
project, or giving a long task its own scratch space.

Everything goes through the `opencode-sandbox` binary. Invoke it by name — it is on PATH.

## Before anything else

Run `opencode-sandbox list`. If the command is not found, stop and tell the user to install
the CLI — a compiled binary from the `opencode-sandbox` project, either built there with
`bun run install-local` or downloaded from its releases. Do not improvise a docker or
compose invocation by hand: the compose wiring, port allocation, and volume seeding are
the whole point of the CLI, and a hand-rolled stack will collide with instances it does
not know about.

An instance needs a provider API key in the environment at create time
(`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_GENERATIVE_AI_API_KEY`, or
`OPENROUTER_API_KEY`). Whichever are set get forwarded in. If none are set, say so before
creating — the instance will come up with no usable model.

## The flow

1. **Create.** Name it after what it is for. Seed it with the current project when the
   sandbox should work on a copy of real code, and pass a config when the instance needs
   its own model or theme settings:

   ```
   opencode-sandbox create <name> [--seed .] [--config ./opencode.jsonc] [--web]
   ```

   `--seed` copies a directory into the fresh workspace before first start. `--web` also
   publishes the browser UI; leave it off unless the user wants to click around.

2. **Register.** `create` prints the exact registration line, and `opencode-sandbox url
   <name>` reprints it. Run that line — do not compose the URL yourself:

   ```
   claude mcp add --transport http <name> http://127.0.0.1:<port>/mcp
   ```

   The instance's tools then appear in this session, all scoped to its `/workspace`.

3. **Destroy when done.** Instances keep running until removed, so close the loop rather
   than leaving one behind:

   ```
   claude mcp remove <name> && opencode-sandbox destroy <name>
   ```

   `destroy` deletes the workspace volume with everything in it. Confirm with the user
   first if the instance produced work worth keeping — copy it out beforehand.

## Security posture

The MCP bridge has no inbound authentication. Anyone who can reach its port gets the full
tool surface — reading and writing files and running shell commands inside that
instance's `/workspace`. The CLI publishes on `127.0.0.1` only. Never widen the bind to
`0.0.0.0`, forward the port, or put it behind a public reverse proxy without a real auth
layer in front of it.

The isolation protects the host from the instance, not the instance from itself. Anything
seeded into the workspace is readable by whatever runs in there, so do not seed secrets.
