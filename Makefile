.DEFAULT_GOAL := help
.PHONY: help check identity provenance hook-layout floor catalog build build-check test smoke ci harness-coupling flow symlinks

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

check: ## Roster <-> disk drift guard (schema + provenance)
	@python3 scripts/check_roster.py

identity: ## Entry-gate floor: identity-neutrality lint (no name/org/repo/issue in shipped bodies)
	@python3 scripts/check_identity.py

provenance: ## Entry-gate floor: provenance/externals conformance (primitives-core authored-only)
	@python3 scripts/check_provenance.py

hook-layout: ## Entry-gate floor: hooks use the ratified hooks/<name>/hook.py layout
	@python3 scripts/check_hook_layout.py

floor: identity test provenance hook-layout ## The Tier-1 entry-gate machine floor (required on PRs into dev)

build: ## Regenerate the dist lanes (dist/claude-code/ + dist/opencode/) from source
	@python3 scripts/gen_marketplace.py
	@python3 scripts/gen_opencode.py

build-check: ## Verify the committed dist lanes match source (regen drift guards)
	@python3 scripts/gen_marketplace.py --check
	@python3 scripts/gen_opencode.py --check

catalog: ## Standalone skill-catalog eligibility/drift + one-skill wrapper invariants
	@python3 scripts/check_skill_catalog.py
	@python3 scripts/gen_standalone.py --check

harness-coupling: ## No-repo-coupling gate for harness/ (stdlib-only; extraction guard, DESIGN §5)
	@python3 scripts/check_harness_coupling.py

flow: ## Repo-flow DAG guard (flow.yaml <-> tree: homes, planned paths, acyclicity, doc DAG)
	@python3 scripts/check_flow.py

symlinks: ## Symlink-assembly lint (ADR 0017): plugins/ links resolve in-repo; marketplace.json <-> assemblies 1:1
	@python3 scripts/check_symlinks.py

test: ## Unit tests (stdlib-only, zero-install) — also entry-gate floor check "tests pass"
	@python3 -m unittest discover -s tests -t . -q

smoke: ## Loadability smoke: install the bundles into a live Claude Code session (opt-in, NOT in ci)
	@echo "smoke is opt-in and lands with the bundle-install proof (D2/D3); not part of ci"

# All gates. The Tier-1 entry-gate machine floor (identity · tests · provenance · hook-layout)
# is required CI on every PR into dev; check (roster drift) + build-check (marketplace drift) +
# catalog (standalone eligibility/drift) guard the generated artifacts; harness-coupling keeps
# harness/ extraction-clean (stdlib-only — it must not need uv, so it lives in ci not harness-test).
ci: check identity provenance hook-layout catalog build-check symlinks harness-coupling flow test ## All gates: floor + drift guards

# --- agent harness (harness/) — its own uv project; deliberately NOT part of ci
# (evals need live CLIs + API keys; the harness has its own test lane, wired to ci in Wave 4).
.PHONY: harness-test harness-eval harness-report
harness-test: ## Run the agent-harness unit tests (uv project; NOT in ci)
	@uv run --project harness python -m unittest discover -s harness/tests -t harness/tests -q

harness-eval: ## Eval grid: ITEM=<name> [HARNESS=claude] [MODEL=] [CAMPAIGN=] (NOT in ci). Resolves skill dirs AND flat agents/<name>.md (auto-staged)
	@test -n "$(ITEM)" || { echo "usage: make harness-eval ITEM=<candidate> [HARNESS=claude] [MODEL=<model>] [CAMPAIGN=<label>]"; exit 2; }
	@dir=$$(find primitives-core -mindepth 2 -maxdepth 2 -type d -name "$(ITEM)" | head -1); \
	  stage=""; \
	  if [ -z "$$dir" ] && [ -f "primitives-core/agents/$(ITEM).md" ]; then \
	    stage=$$(mktemp -d); cp "primitives-core/agents/$(ITEM).md" "$$stage/"; dir="$$stage"; \
	    echo "staged agent candidate '$(ITEM)' from primitives-core/agents/$(ITEM).md -> $$dir"; \
	  fi; \
	  test -n "$$dir" || { echo "no primitive named '$(ITEM)' under primitives-core/ (need a skill dir or agents/$(ITEM).md)"; exit 2; }; \
	  uv run --project harness agent-harness "$(ITEM)" --candidate-dir "$$dir" \
	    --harness "$(or $(HARNESS),claude)" $(if $(MODEL),--model "$(MODEL)") $(if $(CAMPAIGN),--campaign "$(CAMPAIGN)"); \
	  status=$$?; \
	  if [ -n "$$stage" ]; then rm -rf "$$stage"; fi; \
	  exit $$status

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
