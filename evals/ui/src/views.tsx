import { Breadcrumb, BreadcrumbItem, Button, Column, Grid, Header, HeaderName, SideNav, SideNavItems, SideNavLink, SkipToContent } from "@carbon/react";
import Content from "@carbon/react/es/components/UIShell/Content";
import { useEffect, useState, type ReactNode } from "react";
import { Session } from "./api";
import { Catalog } from "./catalog";
import { Documentation } from "./documentation";
import { Evaluations } from "./evaluations";
import { Performance } from "./performance";
import { Block, Login } from "./ui";

export type Route = "home" | "catalog" | "documentation" | "performance" | "evaluations";

const routes: { id: Route; label: string }[] = [
  { id: "home", label: "Home" },
  { id: "catalog", label: "Catalog" },
  { id: "documentation", label: "Documentation" },
  { id: "performance", label: "Performance" },
  { id: "evaluations", label: "Evaluations" },
];

export function parseRoute(hash: string, fallback: Route = "home"): Route {
  if (hash === "#main-content") return fallback;
  const route = hash.slice(1).split("?")[0];
  return routes.some((item) => item.id === route) ? route as Route : fallback;
}

function Crumbs({ route }: { route: Route }) {
  return <Breadcrumb noTrailingSlash>
    <BreadcrumbItem href="#home">Home</BreadcrumbItem>
    {route !== "home" && <BreadcrumbItem isCurrentPage>
      {routes.find((item) => item.id === route)?.label}
    </BreadcrumbItem>}
  </Breadcrumb>;
}

function Shell({ route, children, logout }: { route: Route; children: ReactNode; logout: () => void }) {
  return <>
    <Header aria-label="Toolbox">
      <SkipToContent href="#main-content" />
      <HeaderName href="#home" prefix="">Toolbox</HeaderName>
      <span className="header-caption">Source and evidence workspace</span>
      <Button kind="ghost" size="sm" className="logout" onClick={logout}>Log out</Button>
    </Header>
    <div className="shell">
      <SideNav isFixedNav expanded aria-label="Toolbox navigation" className="sidebar">
        <SideNavItems>{routes.map((item) => <SideNavLink
          key={item.id}
          href={`#${item.id}`}
          isActive={route === item.id}
          aria-current={route === item.id ? "page" : undefined}
        >
          {item.label}
        </SideNavLink>)}</SideNavItems>
      </SideNav>
      <Content id="main-content" tabIndex={-1} className="content">{children}</Content>
    </div>
  </>;
}

const homeAreas = [
  ["catalog", "Catalog", "Find packaged tools and primitives for a workflow."],
  ["documentation", "Documentation", "Read stored instructions and references."],
  ["performance", "Performance", "Explore recorded runs, comparisons, and evidence."],
  ["evaluations", "Evaluations", "Review current assessments and coverage."],
] as const;

export function Home() {
  return <>
    <Block>
      <Crumbs route="home" />
      <h1>Your Toolbox</h1>
      <p className="lede">Find tools for your workflow, read their documentation, and explore recorded performance and evaluations.</p>
    </Block>
    <Grid fullWidth className="area-grid">{homeAreas.map(([id, label, text]) => <Column key={id} sm={4} md={4} lg={4}>
      <article className="area-card">
        <h2>{label}</h2>
        <p>{text}</p>
        <Button kind="tertiary" href={`#${id}`}>Open {label}</Button>
      </article>
    </Column>)}</Grid>
  </>;
}

export function BrowserApp() {
  const [session] = useState(() => new Session());
  const [signedIn, setSignedIn] = useState(false);
  const [hash, setHash] = useState(location.hash);
  const [route, setRoute] = useState<Route>(() => parseRoute(location.hash));
  const clearUi = () => {
    setSignedIn(false);
    setRoute("home");
  };
  const logout = () => {
    session.logout();
    clearUi();
  };

  useEffect(() => {
    const unsubscribe = session.subscribe(clearUi);
    return () => { unsubscribe(); };
  }, [session]);
  useEffect(() => {
    const change = () => setHash((current) => location.hash === "#main-content" ? current : location.hash);
    addEventListener("hashchange", change);
    return () => removeEventListener("hashchange", change);
  }, []);
  useEffect(() => {
    setRoute((current) => parseRoute(hash, current));
  }, [hash]);
  useEffect(() => {
    document.getElementById("main-content")?.focus();
  }, [route]);

  if (!signedIn) return <Login session={session} onAuthenticated={() => setSignedIn(true)} />;
  const content = route === "home"
    ? <Home />
    : route === "catalog"
      ? <Catalog session={session} onExpired={clearUi} />
      : route === "documentation"
        ? <Documentation session={session} onExpired={clearUi} />
        : route === "evaluations"
          ? <Evaluations session={session} onExpired={clearUi} />
          : <Performance session={session} onExpired={clearUi} hash={hash} />;
  return <Shell route={route} logout={logout}>{content}</Shell>;
}
