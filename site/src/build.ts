// Runs a whole build: config, pages, rendering, links and layout. Every
// problem is collected first; the output folder is written only when there are none.
import { mkdir, realpath, stat } from "node:fs/promises";
import { basename, dirname, join, resolve, sep } from "node:path";
import { ConfigError, loadConfig, type SiteConfig } from "./config.ts";
import { layoutPage } from "./layout.ts";
import { rewriteLinks } from "./links.ts";
import { readSource, selectPages, type Site } from "./pages.ts";
import { PageError, renderPage, type Rendered } from "./render.ts";

export interface BuildOptions {
  /** The checkout to render. */
  root: string;
  /** The config file, and how messages name it. */
  config: string;
  configLabel: string;
  /** The stylesheet copied to `assets/site.css`. */
  stylesheet: string;
  /** Defaults to `/tmp/<name>-site/<name>`. */
  output?: string;
  /** Defaults to the config's `ref`. */
  ref?: string;
}

export type BuildResult =
  | { ok: true; site: Site; output: string; pages: number }
  | { ok: false; problems: string[] };

/** The default output folder for a site name. */
export function defaultOutput(name: string): string {
  return `/tmp/${name}-site/${name}`;
}

export async function build(options: BuildOptions): Promise<BuildResult> {
  const problems: string[] = [];
  let config: SiteConfig;
  try {
    config = await loadConfig(options.config, options.configLabel);
  } catch (error) {
    if (error instanceof ConfigError) return { ok: false, problems: error.problems };
    throw error;
  }
  const ref = options.ref ?? config.ref;
  const output = resolve(options.output ?? defaultOutput(config.name));
  const root = resolve(options.root);

  if (!(await isFolder(root))) return { ok: false, problems: [`${options.root}: checkout folder not found`] };
  if (await isInside(output, root)) problems.push(`${output}: output folder is the checkout or lies inside it`);
  if (!(await Bun.file(options.stylesheet).exists())) problems.push(`${options.stylesheet}: stylesheet not found`);

  let site: Site;
  try {
    site = await selectPages(config, root);
  } catch (error) {
    if (error instanceof ConfigError) return { ok: false, problems: [...error.problems, ...problems] };
    throw error;
  }

  const rendered = new Map<string, Rendered>();
  const pageProblems = new Map<string, string[]>(site.pages.map((page) => [page.path, []]));
  for (const page of site.pages) {
    try {
      rendered.set(page.path, await renderPage(page.path, await readSource(site, page)));
    } catch (error) {
      if (!(error instanceof PageError)) throw error;
      pageProblems.get(page.path)!.push(error.message);
    }
  }

  const ids = new Map([...rendered].map(([path, page]) => [path, new Set([...page.ids, "content"])]));
  const documents: [string, string][] = [];
  for (const page of site.pages) {
    const result = rendered.get(page.path);
    if (result === undefined) continue;
    const links = await rewriteLinks({ site, ref, ids }, page, result.body);
    pageProblems.get(page.path)!.push(...links.problems);
    const html = await layoutPage({ site, ref, page, title: result.title, body: links.body, mermaid: result.mermaid });
    documents.push([page.output, html]);
  }
  for (const page of site.pages) problems.push(...pageProblems.get(page.path)!);
  if (problems.length > 0) return { ok: false, problems };

  await mkdir(output, { recursive: true });
  for (const [path, html] of documents) {
    await mkdir(dirname(join(output, path)), { recursive: true });
    await Bun.write(join(output, path), html);
  }
  await mkdir(join(output, "assets"), { recursive: true });
  await Bun.write(join(output, "assets", "site.css"), await Bun.file(options.stylesheet).arrayBuffer());
  return { ok: true, site, output, pages: documents.length };
}

async function isFolder(path: string): Promise<boolean> {
  try {
    return (await stat(path)).isDirectory();
  } catch {
    return false;
  }
}

/** Whether `path`, once symlinks are resolved, is `folder` or lies inside it; `path` need not exist yet. */
async function isInside(path: string, folder: string): Promise<boolean> {
  const realFolder = await realpath(folder);
  const real = await realpathOfNearest(path);
  return real === realFolder || real.startsWith(realFolder + sep);
}

/** The real path of `path`, resolving its nearest existing ancestor and keeping the rest. */
async function realpathOfNearest(path: string): Promise<string> {
  try {
    return await realpath(path);
  } catch {
    const parent = dirname(path);
    if (parent === path) return path;
    return join(await realpathOfNearest(parent), basename(path));
  }
}
