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
