.DEFAULT_GOAL := help
.PHONY: help check identity provenance hook-layout floor test ci harness-coupling flow symlinks manifests readmes readme-currency parity

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

check: ## Roster <-> disk drift guard (provenance-manifest schema, ADR 0017) + catalog <-> README/marketplace guard + plugin-README diagram guard + per-unit README gate + README-currency gate
	@python3 scripts/check_roster.py
	@python3 scripts/check_catalog.py
	@python3 scripts/check_plugin_diagrams.py
	@python3 scripts/check_readmes.py
	@python3 scripts/check_readme_currency.py

identity: ## Entry-gate floor: identity-neutrality lint (no name/org/repo/issue in shipped bodies)
	@python3 scripts/check_identity.py

provenance: ## Entry-gate floor: provenance/externals conformance (primitives-core authored-only)
	@python3 scripts/check_provenance.py

hook-layout: ## Entry-gate floor: hooks use the ratified hooks/<name>/hook.py layout
	@python3 scripts/check_hook_layout.py

floor: identity test provenance hook-layout ## The Tier-1 entry-gate machine floor (required on PRs into dev)

harness-coupling: ## No-repo-coupling gate for harness/ (stdlib-only; extraction guard, DESIGN §5)
	@python3 scripts/check_harness_coupling.py

flow: ## Repo-flow DAG guard (flow.yaml <-> tree: homes, planned paths, acyclicity, doc DAG)
	@python3 scripts/check_flow.py

symlinks: ## Symlink-assembly lint (ADR 0017): plugins/ links resolve in-repo; marketplace.json <-> assemblies 1:1; solo-skills membership
	@python3 scripts/check_symlinks.py
	@python3 scripts/check_solo_skills.py

readmes: ## Per-unit README gate: every skill dir and every plugin ships a titled, non-empty README.md
	@python3 scripts/check_readmes.py

readme-currency: ## README-currency gate (decision-015): the last change to a skill or plugin also touched that unit's README (needs full git history)
	@python3 scripts/check_readme_currency.py

manifests: ## Manifest gate: `claude plugin validate --strict` over marketplace + every assembly (needs the claude CLI; NOT in ci)
	@python3 scripts/check_manifests.py

parity: ## atelier doctrine parity vs the opencode port, per docs/atelier-parity.md — the gate lives in dotfiles-agents-oc; override its location with ATELIER_OC_REPO= (needs that checkout + bun; NOT in ci)
	@ATELIER_CC_REPO=$(CURDIR) bun --cwd $(or $(ATELIER_OC_REPO),$(HOME)/Developer/dotfiles-agents-oc) gate/parity.ts

members: ## Print each plugin's members, derived live from the symlink assemblies
	@for p in plugins/*/; do id=$$(basename "$$p"); echo "$$id:"; \
	  find "$$p" -maxdepth 3 -type l -exec readlink {} \; \
	  | sed -e 's|.*primitives-core/|  |' | grep -v 'README.md' | sort -u; done

test: ## Unit tests (stdlib-only, zero-install) — also entry-gate floor check "tests pass"
	@python3 -m unittest discover -s tests -t . -q

# All gates. The Tier-1 entry-gate machine floor (identity · tests · provenance · hook-layout)
# is required CI on every PR into dev; check (roster drift) + symlinks (assembly lint, ADR 0017)
# guard the distribution surface; harness-coupling keeps harness/ extraction-clean
# (stdlib-only — it must not need uv, so it lives in ci not harness-test).
ci: check identity provenance hook-layout symlinks harness-coupling flow test ## All gates: floor + assembly/flow guards

# --- agent harness (harness/) — its own uv project; deliberately NOT part of ci
# (evals need live CLIs + API keys; the harness has its own test lane, wired to ci in Wave 4).
.PHONY: harness-test harness-eval harness-report
vendored-drift: ## Vendored base/ vs pinned upstream ref (needs network; NOT in ci)
	@python3 scripts/check_vendored_drift.py

harness-test: ## Run the agent-harness unit tests (uv project; NOT in ci)
	@uv run --project harness python -m unittest discover -s harness/tests -t harness/tests -q

harness-eval: ## Eval grid: ITEM=<name> [HARNESS=claude] [MODEL=] [CAMPAIGN=] (NOT in ci). Resolves skill/plugin dirs AND flat agents/<name>.md
	@test -n "$(ITEM)" || { echo "usage: make harness-eval ITEM=<candidate> [HARNESS=claude] [MODEL=<model>] [CAMPAIGN=<label>]"; exit 2; }
	@dir=$$(find primitives-core -mindepth 2 -maxdepth 2 -type d -name "$(ITEM)" | head -1); \
	  if [ -z "$$dir" ] && [ -f "primitives-core/agents/$(ITEM).md" ]; then \
	    dir="primitives-core/agents/$(ITEM).md"; \
	  fi; \
	  test -n "$$dir" || { echo "no primitive named '$(ITEM)' under primitives-core/ (need a skill dir or agents/$(ITEM).md)"; exit 2; }; \
	  uv run --project harness agent-harness "$(ITEM)" --candidate-dir "$$dir" \
	    --harness "$(or $(HARNESS),claude)" $(if $(MODEL),--model "$(MODEL)") $(if $(CAMPAIGN),--campaign "$(CAMPAIGN)")

harness-report: ## Aggregate the harness ledger for a candidate: ITEM=<name> (NOT in ci)
	@test -n "$(ITEM)" || { echo "usage: make harness-report ITEM=<candidate>"; exit 2; }
	@uv run --project harness agent-harness "$(ITEM)" --report

# --- weekly harness campaign (launchd) — full grid over cased candidates; live CLIs + keychain
.PHONY: harness-campaign harness-campaign-install harness-campaign-uninstall harness-campaign-status
harness-campaign: ## Full-grid eval campaign: cased candidates x claude,opencode x with,baseline x 3 trials (needs live CLIs + keychain; not in ci)
	@scripts/harness_campaign.sh run
harness-campaign-install: ## Install the weekly launchd agent (Mon 09:00; kickstart once to approve keychain)
	@scripts/harness_campaign.sh install
harness-campaign-uninstall: ## Remove the weekly launchd agent
	@scripts/harness_campaign.sh uninstall
harness-campaign-status: ## launchctl state of the weekly agent
	@scripts/harness_campaign.sh status
