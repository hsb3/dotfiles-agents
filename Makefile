.DEFAULT_GOAL := help
.PHONY: help check validate names catalog build build-check test smoke ci

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

check: ## Roster <-> disk drift guard
	@python3 scripts/check_roster.py

validate: ## Primitive content validation (frontmatter, mcp specs, secret hygiene)
	@python3 scripts/validate_primitives.py

names: ## Naming taxonomy lint
	@python3 scripts/check_naming.py

catalog: ## Standalone skill-catalog eligibility + drift guard
	@python3 scripts/check_skill_catalog.py

build: ## Generate targets/ from primitives-core (translation service)
	@python3 scripts/translate.py

build-check: ## Verify committed targets/ matches source (CI drift guard)
	@python3 scripts/translate.py --check

test: ## Unit tests for the render/transform/parse logic + generated artifacts
	@python3 -m unittest discover -s tests -t . -q

smoke: ## Loadability smoke: drive installed opencode/claude against targets/ (opt-in, NOT in ci)
	@python3 scripts/smoke.py

ci: check validate names catalog build-check test ## All gates: roster + content + naming + catalog + targets + tests
