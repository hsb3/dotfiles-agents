import { describe, expect, test } from "bun:test";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { ClientProvider, DataRegion, Pager, SafeLink, ToolboxClient, type Load } from "../ui/src/api.tsx";
import { App, Home, ShellFrame, parseHash } from "../ui/src/app.tsx";
import { PackagedMatches, type Catalog } from "../ui/src/catalog-view.tsx";
import { ExtenderDetails, NO_READER_FILES, ReaderFileItem, SourceDetails } from "../ui/src/documentation-view.tsx";

const HOSTILE = "<img src=x onerror=alert(1)>";
const ESCAPED = "&lt;img src=x onerror=alert(1)&gt;";

function render(node: ReactNode, client = new ToolboxClient("http://127.0.0.1:1")): string {
  return renderToStaticMarkup(<ClientProvider value={client}>{node}</ClientProvider>);
}

/** Visible text: tags removed, entities decoded. */
function textOf(html: string): string {
  return html
    .replace(/<[^>]+>/g, " ")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#x27;/g, "'")
    .replace(/&amp;/g, "&")
    .replace(/\s+/g, " ");
}

describe("data region", () => {
  const states: [Load<{ items: string[] }>, string, string][] = [
    [{ status: "loading" }, "Loading runs", "Please wait while Toolbox reads the current records."],
    [{ status: "access" }, "Access to runs is unavailable", "Your session may have expired or this area may not be available to your account."],
    [{ status: "error" }, "Could not load runs", "The service did not return a usable response. Try again."],
    [{ status: "ready", data: { items: [] } }, "No runs records", "This accessible source currently has no records."],
  ];
  const all = ["Loading runs", "Access to runs", "Could not load runs", "No runs records", "RECORD"];

  for (const [state, title, body] of states) {
    test(`shows exactly the ${state.status === "ready" ? "empty" : state.status} state`, () => {
      const text = textOf(render(<DataRegion subject="runs" state={state}>{() => "RECORD"}</DataRegion>));
      expect(text).toContain(title);
      expect(text).toContain(body);
      expect(all.filter((marker) => text.includes(marker))).toEqual([all.find((m) => title.startsWith(m))!]);
    });
  }

  test("shows the records, and their text as text", () => {
    const html = render(
      <DataRegion subject="runs" state={{ status: "ready", data: { items: [HOSTILE] } }}>
        {(d) => <p>{d.items[0]}</p>}
      </DataRegion>,
    );
    expect(html).toContain(ESCAPED);
    expect(html).not.toContain("<img");
    expect(textOf(html)).not.toContain("Loading");
  });
});

describe("links and pager", () => {
  test("a safe URL is a link; anything else is text", () => {
    expect(render(<SafeLink url="https://example.com/a" />)).toContain('href="https://example.com/a"');
    const unsafe = render(<SafeLink url="javascript:alert(1)" />);
    expect(unsafe).not.toContain("href");
    expect(unsafe).toContain("javascript:alert(1)");
    expect(render(<SafeLink url="//evil.example" label="Visit" fallback="URL unavailable" />)).toBe("<span>URL unavailable</span>");
  });

  test("pager", () => {
    const text = textOf(render(<Pager label="Runs" page={2} totalPages={3} onPage={() => {}} pageSize={25} pageSizes={[25, 50]} onPageSize={() => {}} />));
    expect(text).toContain("Page 2 of 3");
    expect(text).toContain("Previous page");
    expect(text).toContain("Next page");
    expect(text).toContain("Per page");
  });
});

describe("sign-in and shell", () => {
  test("a signed-out app shows sign-in with an empty password field", () => {
    const client = new ToolboxClient("http://127.0.0.1:1");
    const html = renderToStaticMarkup(<App client={client} />);
    expect(html).toContain('type="email"');
    expect(html).toContain('type="password"');
    expect(html).not.toMatch(/type="password"[^>]*value="[^"]/);
    expect(textOf(html)).toContain("Sign in");
  });

  test("the shell has header, caption, log out, side navigation, skip link and breadcrumb", () => {
    const html = render(<ShellFrame route={parseHash("#catalog")} onLogOut={() => {}} />);
    const text = textOf(html);
    expect(html).toContain('<a href="#home" class="cds--header__name"><span>Toolbox</span></a>');
    expect(text).toContain("Source and evidence workspace");
    expect(text).toContain("Log out");
    expect(html).toContain('class="cds--skip-to-content" href="#main-content"');
    expect(html).toContain('id="main-content"');
    expect(html).toMatch(/<main[^>]*tabindex="-1"/);
    for (const area of ["home", "catalog", "documentation", "performance", "evaluations"]) {
      expect(html).toContain(`href="#${area}"`);
    }
    const nav = html.slice(html.indexOf('aria-label="Side navigation"'));
    expect(textOf(nav.slice(0, nav.indexOf("</nav>")))).toContain("Home Catalog Documentation Performance Evaluations");
    const crumb = html.slice(html.indexOf("<nav aria-label=\"Breadcrumb\">"));
    expect(textOf(crumb.slice(0, crumb.indexOf("</nav>"))).trim()).toBe("Home Catalog");
    expect(text).toContain("Loading packaged catalog");
  });

  test("home texts and cards", () => {
    const text = textOf(render(<Home />));
    expect(text).toContain("Your Toolbox");
    expect(text).toContain("Find tools for your workflow, read their documentation, and explore recorded performance and evaluations.");
    for (const [area, line] of [
      ["Catalog", "Find packaged tools and primitives for a workflow."],
      ["Documentation", "Read stored instructions and references."],
      ["Performance", "Explore recorded runs, comparisons, and evidence."],
      ["Evaluations", "Review current assessments and coverage."],
    ]) {
      expect(text).toContain(`${area} ${line} Open ${area}`);
    }
  });

  test("performance and evaluations show a placeholder until they are built", () => {
    const text = textOf(render(<ShellFrame route={parseHash("#evaluations?extender=x")} onLogOut={() => {}} />));
    expect(text).toContain("Evaluations is not available in this build yet.");
  });
});

const CATALOG: Catalog = {
  plugins: Array.from({ length: 12 }, (_, i) => ({ id: `p${i}`, name: `plugin-${i}`, version: "", description: `${HOSTILE} ${i}`, workflows: [] })),
  source_snapshot: "abc",
  workflows: [{ id: "release", name: "Release", guidance: "Before release.", plugins: [] }],
};

describe("catalog and documentation", () => {
  test("packaged matches: workflows first, labelled, 10 per page, text as text", () => {
    const html = render(<PackagedMatches catalog={CATALOG} query="" />);
    const text = textOf(html);
    expect(text.indexOf("Workflow Release Before release.")).toBeGreaterThanOrEqual(0);
    expect(text.indexOf("Workflow")).toBeLessThan(text.indexOf("Plugin"));
    expect((html.match(/<li/g) ?? []).length).toBe(10);
    expect(text).toContain("Page 1 of 2");
    expect(html).not.toContain("<img");
    expect(render(<PackagedMatches catalog={CATALOG} query="zzz" />)).toContain("No packaged records match this search.");
  });

  test("extender details: entry file, assessments link, body as text, source and files regions", () => {
    const html = render(<ExtenderDetails extender={{ id: "e1", body: HOSTILE, entry_file: "SKILL.md", source: "s1" }} />);
    const text = textOf(html);
    expect(text).toContain("Entry file: SKILL.md");
    expect(html).toContain('href="#evaluations?extender=e1"');
    expect(text).toContain("View assessments");
    expect(html).toContain(ESCAPED);
    expect(html).not.toContain("<img");
    expect(text).toContain("Loading source");
    expect(text).toContain("Loading reader files");

    const bare = textOf(render(<ExtenderDetails extender={{ id: "e2", body: "", entry_file: "", source: "" }} />));
    expect(bare).toContain("No stored extender body.");
    expect(bare).toContain("Source unavailable");
  });

  test("source facts link only a safe URL", () => {
    const facts = { id: "s", name: "Src", publisher_kind: "first-party", maintenance: "active" };
    const safe = render(<SourceDetails source={{ ...facts, url: "https://example.com" }} />);
    expect(textOf(safe)).toContain("Source: Src first-party · active Visit source");
    expect(safe).toContain('href="https://example.com"');
    const unsafe = render(<SourceDetails source={{ ...facts, url: "javascript:alert(1)" }} />);
    expect(unsafe).not.toContain("href");
    expect(textOf(unsafe)).toContain("Source URL unavailable");
  });

  test("a reader file shows role and relpath and opens its content as text", () => {
    const html = render(<ReaderFileItem file={{ id: "f", extender: "e", role: "script", relpath: "hooks/check.py", content: HOSTILE }} />);
    expect(textOf(html)).toContain("script · hooks/check.py");
    expect(html).toContain("<details");
    expect(html).toContain(ESCAPED);
    expect(NO_READER_FILES).toBe("This metadata-only extender has no stored reader files.");
  });
});
