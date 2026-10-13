// Sign-in until a session exists, then the Toolbox shell: header, side
// navigation, skip link, breadcrumb, hash routes and the Home area.
import {
  Breadcrumb,
  BreadcrumbItem,
  Button,
  Form,
  Header,
  HeaderGlobalBar,
  HeaderMenuButton,
  HeaderName,
  InlineNotification,
  Link,
  PasswordInput,
  SideNav,
  SideNavItems,
  SideNavLink,
  SkipToContent,
  Stack,
  TextInput,
  Tile,
} from "@carbon/react";
import { useEffect, useRef, useState, useSyncExternalStore, type FormEvent, type MouseEvent } from "react";
import { ClientProvider, hashHref, ToolboxClient, useClient, type Notice } from "./api.tsx";
import { CatalogView } from "./catalog-view.tsx";
import { DocumentationView } from "./documentation-view.tsx";

// ---------------------------------------------------------------- routes

export const AREAS = ["home", "catalog", "documentation", "performance", "evaluations"] as const;
export type Area = (typeof AREAS)[number];

export const AREA_TITLES: Record<Area, string> = {
  home: "Home",
  catalog: "Catalog",
  documentation: "Documentation",
  performance: "Performance",
  evaluations: "Evaluations",
};

export interface Route {
  area: Area;
  params: Record<string, string>;
}

export const HOME_ROUTE: Route = { area: "home", params: {} };

function isArea(name: string): name is Area {
  return (AREAS as readonly string[]).includes(name);
}

/** The route of a hash fragment: `#<area>?<params>`, `#home` when empty; an unknown area keeps `current`. */
export function parseHash(hash: string, current: Route = HOME_ROUTE): Route {
  const raw = hash.startsWith("#") ? hash.slice(1) : hash;
  const mark = raw.indexOf("?");
  const name = mark < 0 ? raw : raw.slice(0, mark);
  const params = Object.fromEntries(new URLSearchParams(mark < 0 ? "" : raw.slice(mark + 1)));
  if (name === "") return { area: "home", params };
  return isArea(name) ? { area: name, params } : current;
}

export function routeKey(route: Route): string {
  return hashHref(route.area, route.params);
}

function currentHash(): string {
  return typeof window === "undefined" ? "" : window.location.hash;
}

function useHashRoute(): Route {
  const [route, setRoute] = useState(() => parseHash(currentHash()));
  useEffect(() => {
    const follow = () => setRoute((current) => parseHash(currentHash(), current));
    window.addEventListener("hashchange", follow);
    return () => window.removeEventListener("hashchange", follow);
  }, []);
  return route;
}

// ---------------------------------------------------------------- sign-in

export function SignIn() {
  const client = useClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [notice, setNotice] = useState<Notice | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setNotice(null);
    const failure = await client.signIn(email, password);
    setPassword("");
    setNotice(failure);
    setBusy(false);
  };

  return (
    <main className="toolbox-signin">
      <Tile>
        <Form onSubmit={submit} aria-labelledby="signin-title">
          <Stack gap={6}>
            <div>
              <h1 id="signin-title">Toolbox</h1>
              <p>Source and evidence workspace</p>
            </div>
            <TextInput id="signin-email" type="email" labelText="Email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required />
            <PasswordInput
              id="signin-password"
              labelText="Password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            {notice ? <InlineNotification kind="error" title={notice.title} subtitle={notice.subtitle} hideCloseButton lowContrast /> : null}
            <Button type="submit" disabled={busy}>
              {busy ? "Signing in" : "Sign in"}
            </Button>
          </Stack>
        </Form>
      </Tile>
    </main>
  );
}

// ---------------------------------------------------------------- home

export const HOME_CARDS: { area: Exclude<Area, "home">; text: string }[] = [
  { area: "catalog", text: "Find packaged tools and primitives for a workflow." },
  { area: "documentation", text: "Read stored instructions and references." },
  { area: "performance", text: "Explore recorded runs, comparisons, and evidence." },
  { area: "evaluations", text: "Review current assessments and coverage." },
];

export function Home() {
  return (
    <div className="toolbox-area">
      <h1>Your Toolbox</h1>
      <p>Find tools for your workflow, read their documentation, and explore recorded performance and evaluations.</p>
      <div className="toolbox-cards">
        {HOME_CARDS.map((card) => (
          <Tile key={card.area} className="toolbox-card">
            <h2>{AREA_TITLES[card.area]}</h2>
            <p>{card.text}</p>
            <Link href={hashHref(card.area)}>{`Open ${AREA_TITLES[card.area]}`}</Link>
          </Tile>
        ))}
      </div>
    </div>
  );
}

/** An area this build does not show yet. */
export function AreaPlaceholder({ area }: { area: Area }) {
  return (
    <div className="toolbox-area">
      <h1>{AREA_TITLES[area]}</h1>
      <p role="status">{`${AREA_TITLES[area]} is not available in this build yet.`}</p>
    </div>
  );
}

export function AreaView({ route }: { route: Route }) {
  switch (route.area) {
    case "home":
      return <Home />;
    case "catalog":
      return <CatalogView />;
    case "documentation":
      return <DocumentationView params={route.params} />;
    default:
      return <AreaPlaceholder area={route.area} />;
  }
}

// ---------------------------------------------------------------- shell

/** The shell for a route: header, side navigation, skip link, breadcrumb and the area in a focusable main region. */
export function ShellFrame({ route, onLogOut }: { route: Route; onLogOut: () => void }) {
  const main = useRef<HTMLElement>(null);
  const [navOpen, setNavOpen] = useState(false);
  const key = routeKey(route);

  useEffect(() => {
    main.current?.focus();
  }, [key]);

  const skip = (event: MouseEvent) => {
    event.preventDefault();
    main.current?.focus();
  };

  return (
    <>
      <Header aria-label="Toolbox">
        <SkipToContent href="#main-content" onClick={skip} />
        <HeaderMenuButton aria-label={navOpen ? "Close navigation" : "Open navigation"} isActive={navOpen} aria-expanded={navOpen} onClick={() => setNavOpen(!navOpen)} />
        <HeaderName href={hashHref("home")} prefix="">
          Toolbox
        </HeaderName>
        <span className="toolbox-caption">Source and evidence workspace</span>
        <HeaderGlobalBar>
          <Button kind="ghost" onClick={onLogOut}>
            Log out
          </Button>
        </HeaderGlobalBar>
        <SideNav aria-label="Side navigation" expanded={navOpen} isPersistent onOverlayClick={() => setNavOpen(false)}>
          <SideNavItems>
            {AREAS.map((area) => (
              <SideNavLink key={area} href={hashHref(area)} isActive={route.area === area} onClick={() => setNavOpen(false)}>
                {AREA_TITLES[area]}
              </SideNavLink>
            ))}
          </SideNavItems>
        </SideNav>
      </Header>
      <main id="main-content" className="toolbox-main" tabIndex={-1} ref={main}>
        <Breadcrumb noTrailingSlash>
          {route.area === "home" ? (
            <BreadcrumbItem isCurrentPage>Home</BreadcrumbItem>
          ) : (
            [
              <BreadcrumbItem key="home" href={hashHref("home")}>
                Home
              </BreadcrumbItem>,
              <BreadcrumbItem key="area" isCurrentPage>
                {AREA_TITLES[route.area]}
              </BreadcrumbItem>,
            ]
          )}
        </Breadcrumb>
        <AreaView route={route} />
      </main>
    </>
  );
}

function Shell() {
  const client = useClient();
  const route = useHashRoute();
  return <ShellFrame route={route} onLogOut={() => client.signOut()} />;
}

export function App({ client: given }: { client?: ToolboxClient }) {
  const [client] = useState(() => given ?? new ToolboxClient(window.location.origin));
  const signedIn = useSyncExternalStore(client.subscribe, client.isSignedIn, client.isSignedIn);
  return <ClientProvider value={client}>{signedIn ? <Shell /> : <SignIn />}</ClientProvider>;
}
