.DEFAULT_GOAL := help
.PHONY: help check build build-check ci

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

check: ## Roster <-> disk drift guard
	@python3 scripts/check_roster.py

build: ## Generate targets/ from primitives-core (translation service)
	@python3 scripts/translate.py

build-check: ## Verify committed targets/ matches source (CI drift guard)
	@python3 scripts/translate.py --check

ci: check build-check ## All gates: roster + targets drift
