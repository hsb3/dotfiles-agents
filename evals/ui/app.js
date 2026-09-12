const runFields = "id,harness,campaign,candidate,case,config,model,passed,num_turns,cost_usd,duration_ms,error,ts,created";
const artifactFields = "id,run,kind,mime,blob,sha256,byte_size,text_ref,created";
const base = typeof location === "undefined" ? "" : new URLSearchParams(location.search).get("pb") || localStorage.getItem("toolbox-api") || "";

export function text(node, value) { node.textContent = String(value ?? ""); }
export function fileUrl(record, token) {
  return `/api/files/artifacts/${encodeURIComponent(record.id)}/${encodeURIComponent(record.blob)}?token=${encodeURIComponent(token)}`;
}
export async function api(path, options = {}, fetcher = fetch, token = "") {
  const headers = new Headers(options.headers || {});
  if (token) headers.set("Authorization", token);
  const response = await fetcher(`${base}${path}`, {...options, headers});
  if (!response.ok) throw new Error(`Request failed (${response.status}): ${await response.text()}`);
  return response.status === 204 ? null : response.json();
}
export async function collectPages(path, fields, fetcher = fetch, token = "") {
  const items = []; let page = 1; let totalPages = 1;
  while (page <= totalPages) {
    const query = new URLSearchParams({fields, page: String(page), perPage: "25", sort: "-created"});
    const result = await api(`${path}${path.includes("?") ? "&" : "?"}${query}`, {}, fetcher, token);
    items.push(...(result.items || [])); totalPages = result.totalPages || 1; page += 1;
  }
  return items;
}

if (typeof document !== "undefined") {
  let token = "", runs = [], selectedRun = "", compared = new Set();
  const byId = (id) => document.getElementById(id);
  const state = (id, message) => text(byId(id), message);
  const make = (tag, value) => { const node = document.createElement(tag); if (value !== undefined) text(node, value); return node; };
  const clear = (node) => node.replaceChildren();
  function show(id) { document.querySelectorAll(".view").forEach((view) => { view.hidden = view.id !== id; }); document.querySelectorAll("[data-view]").forEach((button) => button.classList.toggle("active", button.dataset.view === id)); }
  function renderCatalog(entries) { const target = byId("catalog"); clear(target); if (!entries.length) return state("auth-state", "Catalog snapshot is empty."); entries.forEach((entry) => { const card = make("article"); card.className = "card plugin"; card.append(make("h3", entry.name), make("p", entry.description), make("span", `Source: ${entry.source || "marketplace"}`)); target.append(card); }); }
  function renderRuns() { const target = byId("runs"); clear(target); if (!runs.length) return state("runs-state", "No historical runs matched this account."); state("runs-state", `Selected for comparison: ${compared.size} of 2. Choose evidence from one selected run.`); runs.forEach((run) => { const card = make("article"); card.className = "card run"; card.append(make("h3", `${run.campaign || "Untitled campaign"} · ${run.candidate || "unknown candidate"}`), make("p", `${run.harness || "unknown harness"} · ${run.model || "unknown model"}`), make("p", run.passed ? "Recorded result: passed" : "Recorded result: not passed")); const compare = make("button", compared.has(run.id) ? "Remove from comparison" : "Select for comparison"); compare.type = "button"; compare.addEventListener("click", () => { if (compared.has(run.id)) compared.delete(run.id); else if (compared.size < 2) compared.add(run.id); else return state("runs-state", "Select at most two historical observations for comparison."); renderRuns(); }); const evidence = make("button", selectedRun === run.id ? "Evidence selected" : "Inspect evidence"); evidence.type = "button"; evidence.disabled = !compared.has(run.id); evidence.addEventListener("click", () => { selectedRun = run.id; renderRuns(); loadArtifacts(run.id); show("detail"); }); card.append(compare, evidence); target.append(card); }); }
  async function loadRuns() { if (!token) return state("runs-state", "Sign in to load runs."); state("runs-state", "Loading historical runs…"); try { runs = await collectPages("/api/collections/runs/records", runFields, fetch, token); renderRuns(); } catch (error) { state("runs-state", `Could not load historical runs: ${error.message}`); } }
  async function loadArtifacts(run) { if (!token || !run) return; state("artifacts-state", "Loading evidence metadata…"); const target = byId("artifacts"); clear(target); try { const filter = encodeURIComponent(`run = '${String(run).replaceAll("'", "\\'")}'`); const artifacts = await collectPages(`/api/collections/artifacts/records?filter=${filter}`, artifactFields, fetch, token); if (!artifacts.length) return state("artifacts-state", "No evidence metadata is recorded for this run."); state("artifacts-state", "Evidence metadata is historical observation, not current runtime proof."); artifacts.forEach((artifact) => { const row = make("article"); row.className = "artifact"; row.append(make("strong", artifact.kind || "artifact"), make("p", `${artifact.mime || "unknown type"} · ${artifact.byte_size || 0} bytes`), make("p", artifact.text_ref || "No text reference recorded.")); if (artifact.blob) { const open = make("a", "Open protected file"); open.className = "artifact-link"; open.target = "_blank"; open.rel = "noopener"; open.addEventListener("click", async (event) => { event.preventDefault(); try { const grant = await api("/api/files/token", {method: "POST"}, fetch, token); open.href = fileUrl(artifact, grant.token); window.open(open.href, "_blank", "noopener"); } catch (error) { state("artifacts-state", `Could not request file access: ${error.message}`); } }); row.append(open); } target.append(row); }); } catch (error) { state("artifacts-state", `Could not load evidence metadata: ${error.message}`); } }
  document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => { show(button.dataset.view); if (button.dataset.view === "compare") loadRuns(); }));
  byId("login").addEventListener("submit", async (event) => { event.preventDefault(); const form = new FormData(event.currentTarget); state("auth-state", "Signing in…"); try { const auth = await api("/api/collections/users/auth-with-password", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({identity: form.get("email"), password: form.get("password")})}); token = auth.token; byId("logout").hidden = false; state("auth-state", "Signed in. Historical records are read-only."); loadRuns(); } catch (error) { state("auth-state", `Could not sign in: ${error.message}`); } });
  byId("logout").addEventListener("click", () => { token = ""; runs = []; selectedRun = ""; compared = new Set(); byId("logout").hidden = true; clear(byId("runs")); clear(byId("artifacts")); state("auth-state", "Signed out."); state("runs-state", "Sign in to load runs."); state("artifacts-state", "Select a run to load evidence metadata."); });
  state("auth-state", "Loading catalog source snapshot…"); api("/toolbox-catalog.json").then((catalog) => { renderCatalog(catalog.plugins || catalog); state("auth-state", "Sign in to read historical runs."); }).catch((error) => state("auth-state", `Could not load catalog source snapshot: ${error.message}`));
}
