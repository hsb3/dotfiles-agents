// Test helpers: temporary folders and synthetic checkouts.
import { mkdir, mkdtemp, realpath, symlink } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";

/** A new empty folder under the system temp folder, with symlinks resolved. */
export async function tempDir(): Promise<string> {
  return realpath(await mkdtemp(join(tmpdir(), "site-test-")));
}

/**
 * Writes a checkout into a new temp folder. Each key is a repo path; a string
 * value is the file's content and `{ link }` makes a symlink to that target.
 */
export async function checkout(files: Record<string, string | { link: string }>): Promise<string> {
  const root = await tempDir();
  await writeTree(root, files);
  return root;
}

export async function writeTree(root: string, files: Record<string, string | { link: string }>): Promise<void> {
  for (const [path, content] of Object.entries(files)) {
    const full = join(root, path);
    await mkdir(dirname(full), { recursive: true });
    if (typeof content === "string") await Bun.write(full, content);
    else await symlink(content.link, full);
  }
}

export const UNIT = join(import.meta.dir, "..");

/** The shipped config's values, used by the end-to-end fixtures. */
export async function specConfig(): Promise<Record<string, unknown>> {
  return Bun.file(join(UNIT, "site.config.json")).json();
}

/**
 * A small dotfiles-agents look-alike covering the spec's fixture list: a
 * symlinked plugins/<id>/README.md, both decision frontmatter shapes, the
 * renamed .github/CONTRIBUTING.md, an excluded page linked from another page,
 * a Mermaid block, a folder link and an image.
 */
export const DOTFILES: Record<string, string | { link: string }> = {
  "README.md": "# dotfiles-agents\n\n## Install\n\nRead the [docs](docs/) and [how to contribute](.github/CONTRIBUTING.md).\n\n![logo](assets/logo.png)\n",
  LICENSE: "MIT\n",
  "assets/logo.png": "png",
  ".github/CONTRIBUTING.md": "# Contributing\n\nBack to [install](../README.md#install); see [LICENSE](../LICENSE).\n",
  "docs/README.md": [
    "# Documentation",
    "",
    "- [Codex support](codex-compatibility.md)",
    "- [Atelier](../plugins/atelier/)",
    "- [Template](decisions/0000-template.md)",
    "- [Decisions](decisions/)",
    "- [Primitives](../primitives-core)",
    "- [This page](#documentation)",
    "",
    "![flow](img/flow.png)",
    "",
  ].join("\n"),
  "docs/img/flow.png": "png",
  "docs/codex-compatibility.md":
    "# Codex distribution and runtime contract\n\n## Distribution and setup\n\n```mermaid\ngraph TD; A-->B\n```\n\n## Worker isolation\n\nText.\n",
  "docs/licenses.md": "# Licenses\n",
  "docs/decisions/README.md":
    "# Decision history\n\n- [021](0021-kaneo.md)\n- [030](0030-split.md#decision-030--split-the-catalog)\n",
  "docs/decisions/0000-template.md": "---\nid: decision-NNN\n---\n# Decision NNN · <decision title>\n",
  "docs/decisions/0021-kaneo.md":
    "---\nid: \"decision-021\"\ntitle: retired primitives are sunset by decision record, tag, and deletion (applied to kaneo)\ndate: '2026-09-08'\nstatus: accepted\n---\n**Amended 2026-09-08:** After the Kaneo retirement, …\n",
  "docs/decisions/0030-split.md":
    "---\ntitle: split the catalog\nid: decision-030\ntype: decision\nstatus: accepted\ncreated: '2026-08-01'\nsummary: Split it.\n---\n\n# Decision 030 · Split the catalog\n\nSee the [template](0000-template.md).\n",
  "plugins/atelier/README.md": "# Atelier\n\nSee [worker isolation](../../docs/codex-compatibility.md#worker-isolation).\n",
  "plugins/bun/README.md": { link: "../../primitives-core/skills/bun/README.md" },
  "plugins/bun/notes.md": "Notes next to the listed page.\n",
  "primitives-core/skills/bun/README.md": "# Bun\n\n[Local notes](notes.md) and [Atelier](../atelier/README.md).\n",
};
