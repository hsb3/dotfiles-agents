// Rewrites every <a href> and <img src> in a page body: local paths become site
// URLs or GitHub URLs, and broken links and missing headings are reported.
import { realpath, stat } from "node:fs/promises";
import { join, posix, sep } from "node:path";
import { githubUrl, type Page, type Site } from "./pages.ts";
import { decodeEntities } from "./render.ts";

export interface LinkContext {
  site: Site;
  /** The Git ref GitHub links point at. */
  ref: string;
  /** Every `id` in each page's final HTML, by listed path. */
  ids: Map<string, Set<string>>;
}

export interface Rewritten {
  body: string;
  /** `<page>: broken local link: …` and `<page>: missing heading: …`, in document order. */
  problems: string[];
}

interface Destination {
  tag: "a" | "img";
  value: string;
}

/** Rewrites and checks the links and images in `body`, the rendered body of `page`. */
export async function rewriteLinks(context: LinkContext, page: Page, body: string): Promise<Rewritten> {
  const found: Destination[] = [];
  const collect = (tag: "a" | "img", attribute: string) => ({
    element(element: HTMLRewriterTypes.Element) {
      found.push({ tag, value: decodeEntities(element.getAttribute(attribute)!) });
    },
  });
  await new HTMLRewriter().on("a[href]", collect("a", "href")).on("img[src]", collect("img", "src")).transform(new Response(body)).text();

  const problems: string[] = [];
  const results: (string | undefined)[] = [];
  for (const destination of found) {
    const result = await resolve(context, page, destination);
    if ("problem" in result) problems.push(`${page.path}: ${result.problem}: ${destination.value}`);
    results.push("url" in result ? result.url : undefined);
  }

  let index = 0;
  const write = (attribute: string) => ({
    element(element: HTMLRewriterTypes.Element) {
      const url = results[index++];
      if (url !== undefined) element.setAttribute(attribute, url.replace(/&/g, "&amp;"));
    },
  });
  const rewritten = await new HTMLRewriter().on("a[href]", write("href")).on("img[src]", write("src")).transform(new Response(body)).text();
  return { body: rewritten, problems };
}

/** A new URL, nothing to change (`{}`), or a problem. */
type Resolution = { url: string } | { problem: string } | Record<string, never>;

async function resolve(context: LinkContext, page: Page, { tag, value }: Destination): Promise<Resolution> {
  if (/^[A-Za-z][A-Za-z0-9+.-]*:/.test(value) || value.startsWith("//")) return {};
  const hash = value.indexOf("#");
  const fragment = hash === -1 ? "" : value.slice(hash);
  const beforeHash = hash === -1 ? value : value.slice(0, hash);
  const question = beforeHash.indexOf("?");
  const query = question === -1 ? "" : beforeHash.slice(question);
  const rawPath = question === -1 ? beforeHash : beforeHash.slice(0, question);

  if (rawPath === "") {
    if (!headingExists(context, page, fragment)) return { problem: "missing heading" };
    return value.startsWith("#") ? {} : { url: page.url + query + fragment };
  }

  const target = await locate(context.site, page, rawPath);
  if (target === undefined) return { problem: "broken local link" };
  const linked = target.page;
  if (linked !== undefined) {
    if (!headingExists(context, linked, fragment)) return { problem: "missing heading" };
    return { url: linked.url + query + fragment };
  }
  const kind = tag === "img" ? "raw" : target.folder ? "tree" : "blob";
  return { url: githubUrl(context.site.config.repo, context.ref, kind, target.path) + query + fragment };
}

interface Target {
  /** Repo path, `""` for the checkout root. */
  path: string;
  folder: boolean;
  /** The page this path stands for: the page itself, or a folder's README.md page. */
  page: Page | undefined;
}

/** Finds a local link's target inside the checkout, or undefined when it is missing or leaves the checkout. */
async function locate(site: Site, page: Page, rawPath: string): Promise<Target | undefined> {
  let decoded: string;
  try {
    decoded = decodeURIComponent(rawPath);
  } catch {
    return undefined;
  }
  const wantsFolder = decoded.endsWith("/");
  const joined = decoded.startsWith("/") ? decoded.slice(1) : posix.join(posix.dirname(page.path), decoded);
  const path = posix.normalize(joined === "" ? "." : joined).replace(/\/+$/, "");
  if (path === ".." || path.startsWith("../")) return undefined;
  const repoPath = path === "." ? "" : path;

  const root = await realpath(site.root);
  let folder: boolean;
  try {
    const real = await realpath(join(site.root, repoPath));
    if (real !== root && !real.startsWith(root + sep)) return undefined;
    folder = (await stat(real)).isDirectory();
  } catch {
    return undefined;
  }
  if (wantsFolder && !folder) return undefined;
  const pagePath = folder ? posix.join(repoPath, "README.md") : repoPath;
  return { path: repoPath, folder, page: site.byPath.get(pagePath) };
}

/** Whether a fragment (with its `#`) names an id in the page; an empty fragment always does. */
function headingExists(context: LinkContext, page: Page, fragment: string): boolean {
  if (fragment.length <= 1) return true;
  let id = fragment.slice(1);
  try {
    id = decodeURIComponent(id);
  } catch {
    // A malformed escape is compared as written.
  }
  // A page that failed to render has no ids; its own problem is reported instead.
  return context.ids.get(page.path)?.has(id) ?? true;
}
