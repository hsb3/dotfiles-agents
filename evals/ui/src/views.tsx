import { Breadcrumb, BreadcrumbItem, Button, Column, Content, Grid, Header, HeaderMenuButton, HeaderName, SideNav, SideNavItems, SideNavLink, SkipToContent } from "@carbon/react";
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

const desktopNavQuery = "(min-width: 66rem)";

export function Shell({ route, children, logout }: { route: Route; children: ReactNode; logout: () => void }) {
  const isDesktop = () => typeof window !== "undefined" && window.matchMedia(desktopNavQuery).matches;
  const [desktopNav, setDesktopNav] = useState(isDesktop);
  const [sideNavExpanded, setSideNavExpanded] = useState(isDesktop);

  useEffect(() => {
    const media = window.matchMedia(desktopNavQuery);
    const update = () => {
      setDesktopNav(media.matches);
      setSideNavExpanded(media.matches);
    };
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  const closeMobileSideNav = () => {
    if (!desktopNav) setSideNavExpanded(false);
  };

  return <>
    <Header aria-label="Toolbox">
      <SkipToContent href="#main-content" />
      <HeaderMenuButton
        aria-label={sideNavExpanded ? "Close navigation" : "Open navigation"}
        aria-expanded={sideNavExpanded}
        isActive={sideNavExpanded}
        isCollapsible
        onClick={() => setSideNavExpanded((expanded) => !expanded)}
      />
      <HeaderName href="#home" prefix="">Toolbox</HeaderName>
      <span className="header-caption">Source and evidence workspace</span>
      <Button kind="ghost" size="sm" className="logout" onClick={logout}>Log out</Button>
    </Header>
    <SideNav
      expanded={sideNavExpanded}
      isFixedNav={desktopNav}
      aria-label="Toolbox navigation"
      className="sidebar"
      onOverlayClick={closeMobileSideNav}
    >
      <SideNavItems>{routes.map((item) => <SideNavLink
        key={item.id}
        href={`#${item.id}`}
        isActive={route === item.id}
        aria-current={route === item.id ? "page" : undefined}
        onClick={closeMobileSideNav}
      >
        {item.label}
      </SideNavLink>)}</SideNavItems>
    </SideNav>
    <Content id="main-content" tabIndex={-1} className="content">{children}</Content>
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
