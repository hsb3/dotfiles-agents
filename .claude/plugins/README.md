# .claude/plugins — vendored development tools

These copies of Anthropic's official plugins support development of this repository.
They are excluded from the published marketplace on `main`, but **are distributed
with the source repository**. Public source visibility therefore requires preserving
their licenses and attribution too.

All files in each directory match the following complete upstream subtree, verified
2026-09-09 against [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official):

| Local directory | Upstream path | Exact matching revision | Files |
|---|---|---|---|
| `plugin-dev` | `plugins/plugin-dev` | `ce721c1f1d5da2c281588818e072ae01a05d2e73` | 60 |
| `skill-creator` | `plugins/skill-creator` | `2a40fd2e7c52207aa903bd33fc4c65716126966e` | 21 |
| `mcp-server-dev` | `plugins/mcp-server-dev` | `f4b5494fb45946c1256e883001300dad87ffa036` | 22 |

Each contains its upstream Apache-2.0 `LICENSE`; each manifest identifies Anthropic
as author. The skill-creator skill also retains its own `LICENSE.txt`. No local
modifications were found in these three copied subtrees. The MIT sentence in
`plugin-dev/README.md` is upstream text; its included license is Apache-2.0.

The file-based `workbench` marketplace (`.claude-plugin/marketplace.json`) enables
these tools through `.claude/settings.json`. They are not entries in the current
`externals.yaml`. See [the license inventory](../../docs/licenses.md) for the wider
repository and historical-copy limitations.
