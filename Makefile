.DEFAULT_GOAL := help
.PHONY: help check build build-check test smoke ci

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

check: ## Roster <-> disk drift guard (schema + provenance)
	@python3 scripts/check_roster.py

build: ## Regenerate the Claude Code marketplace (plugins/ + marketplace.json) from source
	@python3 scripts/gen_marketplace.py

build-check: ## Verify the committed marketplace matches source (regen drift guard)
	@python3 scripts/gen_marketplace.py --check

test: ## Unit tests (stdlib-only, zero-install)
	@python3 -m unittest discover -s tests -t . -q

smoke: ## Loadability smoke: install the bundles into a live Claude Code session (opt-in, NOT in ci)
	@echo "smoke is opt-in and lands with the bundle-install proof (D2/D3); not part of ci"

# CI floor. D6 folds its lanes in here later (identity, provenance, hook-layout, catalog);
# those seams are intentionally absent for now, not stubbed.
ci: check build-check test ## All gates: roster drift + marketplace drift + tests
