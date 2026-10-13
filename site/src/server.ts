// Serves a built site folder on 127.0.0.1 under its base path, as Pages would.
import { realpath, stat } from "node:fs/promises";
import { join, sep } from "node:path";

export interface ServeOptions {
  /** The built output folder. */
  output: string;
  /** The site base path, such as `/dotfiles-agents`. */
  base: string;
  /** `0` picks a free port. */
  port: number;
}

/** Thrown when another process holds the port. */
export class PortTakenError extends Error {}

/** Starts serving; the returned server runs until stopped or the process is interrupted. */
export function startServer({ output, base, port }: ServeOptions): Bun.Server<undefined> {
  try {
    return Bun.serve({
      hostname: "127.0.0.1",
      port,
      async fetch(request) {
        if (request.method !== "GET" && request.method !== "HEAD") {
          return new Response("Method Not Allowed\n", { status: 405, headers: { Allow: "GET, HEAD" } });
        }
        const file = await resolveRequest(output, base, new URL(request.url).pathname);
        return file === undefined ? new Response("Not Found\n", { status: 404 }) : new Response(Bun.file(file));
      },
    });
  } catch (error) {
    if ((error as { code?: string }).code === "EADDRINUSE") throw new PortTakenError(`port ${port} is taken`);
    throw error;
  }
}

/**
 * The file a request path names inside `output`, or undefined for a 404: a path
 * outside `<base>/`, a missing file or folder index, or one that escapes the folder.
 */
export async function resolveRequest(output: string, base: string, pathname: string): Promise<string | undefined> {
  if (!pathname.startsWith(`${base}/`)) return undefined;
  let rest = pathname.slice(base.length + 1);
  if (rest === "" || rest.endsWith("/")) rest += "index.html";
  let segments: string[];
  try {
    segments = rest.split("/").map(decodeURIComponent);
  } catch {
    return undefined;
  }
  if (segments.some((segment) => segment === "" || segment === "." || segment === ".." || /[/\\\0]/.test(segment))) {
    return undefined;
  }
  try {
    const folder = await realpath(output);
    const file = await realpath(join(folder, ...segments));
    if (!file.startsWith(folder + sep) || !(await stat(file)).isFile()) return undefined;
    return file;
  } catch {
    return undefined;
  }
}
