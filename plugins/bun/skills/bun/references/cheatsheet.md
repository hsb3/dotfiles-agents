# Bun Cheatsheet

The API surface and CLI flags worth knowing. Conventions and the "use bun instead of X"
mapping live in `claude-code/.claude/rules/bun.md` — this is the depth behind them.

Signatures verified against `bun-llms-full.txt` (bun 1.4).

## CLI flags that replace tooling

```bash
bun --watch server.ts        # restart process on change (nodemon)
bun --hot server.ts          # reload in place, keeps process + state alive
bun build --compile ./cli.ts --outfile mycli   # single-file executable (pkg/nexe)
bun run --bun <cli>          # force a node-shebang CLI onto the bun runtime
bun --env-file=.env x.ts     # explicit env (REQUIRED alongside --bun; see traps.md trap 7)
bun install --frozen-lockfile   # npm ci
bun --filter '<pkg>' <script>   # run a script across workspace packages
bun -e 'console.log(1)'      # inline eval
```

## Package management

```bash
bun install                  # also auto-migrates package-lock.json -> bun.lock
bun add / remove / update
bun outdated                 # what's behind
bun patch <pkg>              # persistent patch of a dependency
bun pm ls -g                 # global packages
bun pm bin -g                # global bin dir (~/.bun/bin)
bun pm untrusted             # postinstalls that were blocked
bun pm trust <pkg>           # allow one (see traps.md trap 4)
bun pm cache                 # cache location; `bun pm cache rm` to clear
```

`bun.lock` is text and reviewable — commit it. The old binary `bun.lockb` is legacy; some
platforms (e.g. Vercel's preset) do not detect it.

## Built-ins that replace dependencies

**Shell** — replaces `execa`, `zx`, `shelljs`. Cross-platform, no shell injection:

```ts
import { $ } from "bun";
const version = await $`git describe --tags --always`.text();
await $`mkdir -p dist`;
```

**SQLite** — replaces `better-sqlite3`, with no native rebuild step:

```ts
import { Database } from "bun:sqlite";
const db = new Database("app.db");
db.query("SELECT * FROM users WHERE id = ?").get(1);
```

**HTTP server** — replaces `express` for straightforward services. Routes, params, and
WebSockets are built in:

```ts
Bun.serve({
  port: 3000,
  routes: {
    "/": () => new Response("ok"),
    "/users/:id": req => Response.json({ id: req.params.id }),
  },
});
```

**Secrets** — native OS keychain, encrypted by the OS. The right home for tokens on this
machine, instead of a plaintext dotfile:

```ts
import { secrets } from "bun";
await secrets.set({ service: "my-app", name: "api-user", value: token });
const token = await secrets.get({ service: "my-app", name: "api-user" });
await secrets.delete({ service: "my-app", name: "api-user" });
```

**Cron** — in-process scheduling, plus OS-level job registration:

```ts
Bun.cron("0 * * * *", async () => { await cleanupTempFiles(); });
const next = Bun.cron.parse("30 9 * * MON-FRI");   // next weekday 09:30 local
```

**Files** — faster than `fs` for whole-file reads/writes; `Bun.file()` is lazy:

```ts
const text = await Bun.file("data.json").text();
await Bun.write("out.txt", "contents");           // accepts string, Blob, Response
```

**Also shipped, so do not add a package for them:** `.env` loading (no `dotenv`),
`Bun.password` (argon2/bcrypt), `Bun.Glob`, `Bun.hash` / `Bun.CryptoHasher`,
`Bun.which`, `Bun.spawn`, `Bun.deepEquals`, `Bun.stringWidth`, `Bun.markdown`,
`Bun.XML`, `Bun.JSONL`, `Bun.Archive`, `Bun.color`, `Bun.Image`, `Bun.CSRF`, `Bun.Cookie`.

## Testing

`bun test` is Jest-compatible in shape — `describe`/`test`/`expect`, plus mocks, spies, and
module mocking. Useful flags:

```bash
bun test --coverage
bun test --bail        # or --bail=10
bun test --concurrent
bun test --watch
```

For **new** projects prefer `bun test` over jest/vitest. For an existing vitest suite,
migrating the runner is a separate decision from migrating the package manager — the
`functionform-obsidian` migration deliberately kept vitest (see [migration.md](migration.md)).

## Bundling

`bun build` covers most esbuild use. Notable gaps versus esbuild: no `--target`
down-levelling, no `--inject`, no `--global-name`, no stdin input, and a different
`--loader` syntax (`bun build app.ts --loader .svg:text`).

`--compile` produces a standalone executable with the runtime embedded; combine with
`--bytecode` for faster startup.
