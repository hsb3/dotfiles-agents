import { Breadcrumb, BreadcrumbItem, Button, Column, Grid, Header, HeaderName, InlineNotification, Pagination, Search, SideNavItems, SideNavLink, SkipToContent } from "@carbon/react";
import { useEffect, useState } from "react";
import { Session } from "./api";
import { catalog, type Catalog, documentation, distributions, evaluations, extenders, jobCoverage, safeHref, type Distribution, type DocumentationFile, type Extender } from "./data";
import { Block, Login, StateNotice } from "./ui";

type Route = "home" | "catalog" | "documentation" | "performance" | "evaluations";
type State = "loading" | "access" | "error" | "empty" | "populated";
const routes: { id: Route; label: string }[] = [
  { id: "home", label: "Home" }, { id: "catalog", label: "Catalog" }, { id: "documentation", label: "Documentation" }, { id: "performance", label: "Performance" }, { id: "evaluations", label: "Evaluations" },
];
const currentRoute = (): Route => routes.some(({ id }) => location.hash === `#${id}`) ? location.hash.slice(1) as Route : "home";
const go = (route: Route) => { location.hash = route; };

function Shell({ route, children, onLogout }: { route: Route; children: React.ReactNode; onLogout?: () => void }) {
  return <><Header aria-label="Toolbox"><SkipToContent href="#main-content" /><HeaderName href="#home" prefix="">Toolbox</HeaderName><span className="header-caption">Source and evidence workspace</span>{onLogout && <Button kind="ghost" size="sm" className="logout" onClick={onLogout}>Log out</Button>}</Header>
    <div className="shell"><nav className="sidebar" aria-label="Toolbox navigation"><SideNavItems>{routes.map((item) => <SideNavLink key={item.id} href={`#${item.id}`} isActive={route === item.id} aria-current={route === item.id ? "page" : undefined}>{item.label}</SideNavLink>)}</SideNavItems><p>Read current records and their stated relationships.</p></nav>
      <main id="main-content" tabIndex={-1}>{children}</main></div></>;
}

function Crumbs({ route }: { route: Route }) { return <Breadcrumb noTrailingSlash><BreadcrumbItem href="#home">Home</BreadcrumbItem>{route !== "home" && <BreadcrumbItem isCurrentPage>{routes.find((item) => item.id === route)?.label}</BreadcrumbItem>}</Breadcrumb>; }

const homeAreas = [
  ["catalog", "Catalog", "Catalog discovers packaged workflows/plugins and database primitives."],
  ["documentation", "Documentation", "Documentation reads stored instructions, references, and source context."],
  ["performance", "Performance", "Performance explains when measurement provenance and comparability become available."],
  ["evaluations", "Evaluations", "Evaluations inspects current assessments and per-job coverage."],
] as const;
function Home() { return <><Block><Crumbs route="home" /><h1>Orient to the Toolbox</h1><p className="lede">Choose a source-aware area. Records remain separate unless the database explicitly relates them.</p></Block><Grid fullWidth className="area-grid">{homeAreas.map(([id, label, text]) => <Column key={id} sm={4} md={4} lg={4}><article className="area-card"><h2>{label}</h2><p>{text}</p><Button kind="tertiary" href={`#${id}`}>Open {label}</Button></article></Column>)}</Grid></>; }

function Catalog({ session, state: forced, onExpired }: { session: Session; state?: State; onExpired: () => void }) {
  const [state, setState] = useState<State>(forced ?? "loading"); const [snapshot, setSnapshot] = useState<Catalog>(); const [query, setQuery] = useState(""); const [page, setPage] = useState(1);
  useEffect(() => { if (forced) return; catalog(session).then((result) => { if (result.kind === "ok") { setSnapshot(result.data); setState("populated"); } else { setState(result.kind); if (result.kind === "access" && result.status === 401) onExpired(); } }); }, [forced, onExpired, session]);
  const plugins = Array.isArray(snapshot?.plugins) ? snapshot.plugins : [];
  return <><Block><Crumbs route="catalog" /><h1>Catalog</h1><p>Packaged snapshot results are separate from database extenders and explicit distribution membership.</p></Block><Block><Search id="catalog-search" labelText="Search packaged snapshot" value={query} onChange={(event) => { setQuery(event.currentTarget.value); setPage(1); }} /><Button kind="ghost" onClick={() => { setQuery(""); setPage(1); }}>Reset search</Button></Block>
    {state !== "populated" ? <Block><StateNotice state={state} subject="catalog" /></Block> : <><Grid fullWidth className="area-grid"><Column sm={4} md={8} lg={8}><section className="surface"><h2>Packaged snapshot</h2><p>Source snapshot: it does not establish a relationship to database records.</p><pre>{JSON.stringify(plugins.slice((page - 1) * 10, page * 10), null, 2)}</pre></section></Column><Column sm={4} md={8} lg={8}><DatabaseExtenders session={session} query={query} onExpired={onExpired} /></Column></Grid><Block><Pagination page={page} pageSize={10} pageSizes={[10]} totalItems={plugins.length} onChange={({ page }) => setPage(page)} /></Block></>}
  </>;
}
function DatabaseExtenders({ session, query, onExpired }: { session: Session; query: string; onExpired: () => void }) {
  const [state, setState] = useState<State>("loading"); const [items, setItems] = useState<Extender[]>([]); const [bundles, setBundles] = useState<Distribution[]>([]);
  useEffect(() => { extenders(session, query).then((result) => { if (result.kind === "ok") { setItems(result.data.items); setState(result.data.items.length ? "populated" : "empty"); } else { setState(result.kind); if (result.kind === "access" && result.status === 401) onExpired(); } }); }, [onExpired, query, session]);
  useEffect(() => { distributions(session).then((result) => { if (result.kind === "ok") setBundles(result.data.items); else if (result.kind === "access" && result.status === 401) onExpired(); }); }, [onExpired, session]);
  return <section className="surface"><h2>Database extenders</h2><p>These records are not inferred to belong to the packaged snapshot. Distribution membership is explicit.</p>{state === "populated" ? <ul>{items.map((item) => <li key={item.id}>{item.name || item.slug} · {item.kind}</li>)}</ul> : <StateNotice state={state} subject="extender" />}<h3>Distribution membership</h3>{bundles.length ? <ul>{bundles.map((bundle) => <li key={bundle.id}>{bundle.slug} · {bundle.members.length} explicit member record(s)</li>)}</ul> : <p>No accessible distribution memberships are stored.</p>}</section>;
}

function Documentation({ session, text = "", onExpired }: { session: Session; text?: string; onExpired: () => void }) { const [files, setFiles] = useState<DocumentationFile[]>([]); const [state, setState] = useState<State>("loading"); const [query, setQuery] = useState(""); const source = safeHref("/"); useEffect(() => { documentation(session, query).then((result) => { if (result.kind === "ok") { setFiles(result.data.items); setState(result.data.items.length ? "populated" : "empty"); } else { setState(result.kind); if (result.kind === "access" && result.status === 401) onExpired(); } }); }, [onExpired, query, session]); return <><Block><Crumbs route="documentation" /><h1>Documentation</h1><p>Stored files are rendered as text with their extender, role, and relative path. Metadata-only extenders have no stored reader.</p></Block><Grid fullWidth className="area-grid"><Column sm={4} md={4} lg={5}><section className="surface"><h2>Stored files</h2><Search id="documentation-search" labelText="Search stored files" value={query} onChange={(event) => setQuery(event.currentTarget.value)} />{state === "populated" ? <ul>{files.map((file) => <li key={file.id}>{file.role} · {file.relpath}</li>)}</ul> : <StateNotice state={state} subject="documentation" />}</section></Column><Column sm={4} md={4} lg={11}><article className="surface"><h2>Reader</h2>{text ? <pre>{text}</pre> : <p>Select a stored file to read its text. An extender body, entry file, and source remain parent context.</p>}<p>{source ? <a href={source}>Return to Home</a> : "Source unavailable"}</p></article></Column></Grid></>; }
function Performance() { return <Block><Crumbs route="performance" /><h1>Performance</h1><section className="surface"><h2>Measurement availability</h2><p>Performance becomes comparable only when provenance, availability, and validity are explicit. This workspace will show measurement records when that contract is present.</p><Button kind="tertiary" href="#home">Return to Home</Button></section></Block>; }
function Evaluations({ session, onExpired }: { session: Session; onExpired: () => void }) { const [assessmentCount, setAssessmentCount] = useState<number>(); const [coverageCount, setCoverageCount] = useState<number>(); useEffect(() => { evaluations(session).then((result) => { if (result.kind === "ok") setAssessmentCount(result.data.items.length); else if (result.kind === "access" && result.status === 401) onExpired(); }); jobCoverage(session).then((result) => { if (result.kind === "ok") setCoverageCount(result.data.items.length); else if (result.kind === "access" && result.status === 401) onExpired(); }); }, [onExpired, session]); return <><Block><Crumbs route="evaluations" /><h1>Evaluations</h1><p>Current associations show assessments by framework, element, extender, and optional evaluation run, plus one coverage row per job.</p></Block><Grid fullWidth className="area-grid"><Column sm={4} md={8} lg={8}><section className="surface"><h2>Assessments</h2><p>{assessmentCount === undefined ? "Loading current assessments." : `${assessmentCount} current assessment associations.`}</p><p>Verdict, evidence, assessor, and current campaign context are shown when stored. A numeric score is not presented as measured output quality.</p></section></Column><Column sm={4} md={8} lg={8}><section className="surface"><h2>Job coverage</h2><p>{coverageCount === undefined ? "Loading current job coverage." : `${coverageCount} current job coverage associations.`}</p><p>Absent coverage is unassessed. Coverage does not claim a whole-framework denominator or a plugin-harness link.</p></section></Column></Grid><Block><Button kind="tertiary" href="#home">Return to Home</Button></Block></>; }

export function App({ route: supplied, catalogState, documentText }: { route?: Route; catalogState?: State; documentText?: string }) {
  const [session] = useState(() => new Session()); const [signedIn, setSignedIn] = useState(Boolean(supplied)); const [route, setRoute] = useState<Route>(supplied ?? currentRoute());
  useEffect(() => { const update = () => setRoute(currentRoute()); addEventListener("hashchange", update); return () => removeEventListener("hashchange", update); }, []);
  useEffect(() => { document.getElementById("main-content")?.focus(); }, [route]);
  if (!signedIn) return <Login session={session} onAuthenticated={() => setSignedIn(true)} />;
  const logout = () => { session.logout(); setRoute("home"); setSignedIn(false); };
  const content = route === "home" ? <Home /> : route === "catalog" ? <Catalog session={session} state={catalogState} onExpired={logout} /> : route === "documentation" ? <Documentation session={session} text={documentText} onExpired={logout} /> : route === "performance" ? <Performance /> : <Evaluations session={session} onExpired={logout} />;
  return <Shell route={route} onLogout={logout}>{content}</Shell>;
}
export function BrowserApp() { return <App />; }
