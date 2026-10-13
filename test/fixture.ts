// Test helpers: temporary folders and synthetic checkouts.
import { mkdtemp, realpath } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

/** A new empty folder under the system temp folder, with symlinks resolved. */
export async function tempDir(): Promise<string> {
  return realpath(await mkdtemp(join(tmpdir(), "site-test-")));
}
