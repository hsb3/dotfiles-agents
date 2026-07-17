.DEFAULT_GOAL := help
.PHONY: help check identity provenance hook-layout floor build build-check test smoke ci

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

test: ## Unit tests (stdlib-only, zero-install) — also entry-gate floor check "tests pass"
	@python3 -m unittest discover -s tests -t . -q

smoke: ## Loadability smoke: install the bundles into a live Claude Code session (opt-in, NOT in ci)
	@echo "smoke is opt-in and lands with the bundle-install proof (D2/D3); not part of ci"

# All gates. The Tier-1 entry-gate machine floor (identity · tests · provenance · hook-layout)
# is required CI on every PR into dev; check (roster drift) + build-check (marketplace drift)
# guard the generated artifacts. The catalog lane folds in at D4.
ci: check identity provenance hook-layout build-check test ## All gates: floor + drift guards
