.DEFAULT_GOAL := help
.PHONY: help check identity provenance hook-layout floor catalog build build-check test smoke ci

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

build: ## Regenerate the Claude Code marketplace (plugins/ + marketplace.json) from source
	@python3 scripts/gen_marketplace.py

build-check: ## Verify the committed marketplace matches source (regen drift guard)
	@python3 scripts/gen_marketplace.py --check

catalog: ## Standalone skill-catalog eligibility/drift + one-skill wrapper invariants
	@python3 scripts/check_skill_catalog.py
	@python3 scripts/gen_standalone.py --check

test: ## Unit tests (stdlib-only, zero-install) — also entry-gate floor check "tests pass"
	@python3 -m unittest discover -s tests -t . -q

smoke: ## Loadability smoke: install the bundles into a live Claude Code session (opt-in, NOT in ci)
	@echo "smoke is opt-in and lands with the bundle-install proof (D2/D3); not part of ci"

# All gates. The Tier-1 entry-gate machine floor (identity · tests · provenance · hook-layout)
# is required CI on every PR into dev; check (roster drift) + build-check (marketplace drift) +
# catalog (standalone eligibility/drift) guard the generated artifacts.
ci: check identity provenance hook-layout catalog build-check test ## All gates: floor + drift guards

# --- agent harness (harness/) — its own uv project; deliberately NOT part of ci
# (evals need live CLIs + API keys; the harness has its own test lane, wired to ci in Wave 4).
.PHONY: harness-test harness-eval harness-report
harness-test: ## Run the agent-harness unit tests (uv project; NOT in ci)
	@uv run --project harness python -m unittest discover -s harness/tests -t harness/tests -q

harness-eval: ## Eval grid for a candidate: ITEM=<name> [HARNESS=claude] [MODEL=] (NOT in ci)
	@test -n "$(ITEM)" || { echo "usage: make harness-eval ITEM=<candidate> [HARNESS=claude] [MODEL=<model>]"; exit 2; }
	@dir=$$(find primitives-core -mindepth 2 -maxdepth 2 -type d -name "$(ITEM)" | head -1); \
	  test -n "$$dir" || { echo "no primitive named '$(ITEM)' under primitives-core/"; exit 2; }; \
	  uv run --project harness agent-harness "$(ITEM)" --candidate-dir "$$dir" \
	    --harness "$(or $(HARNESS),claude)" $(if $(MODEL),--model "$(MODEL)")

harness-report: ## Aggregate the harness ledger for a candidate: ITEM=<name> (NOT in ci)
	@test -n "$(ITEM)" || { echo "usage: make harness-report ITEM=<candidate>"; exit 2; }
	@uv run --project harness agent-harness "$(ITEM)" --report
