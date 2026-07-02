.DEFAULT_GOAL := help
.PHONY: help check validate names build build-check test ci

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

check: ## Roster <-> disk drift guard
	@python3 scripts/check_roster.py

validate: ## Primitive content validation (frontmatter, mcp specs, secret hygiene)
	@python3 scripts/validate_primitives.py

names: ## Naming taxonomy lint
	@python3 scripts/check_naming.py

build: ## Generate targets/ from primitives-core (translation service)
	@python3 scripts/translate.py

build-check: ## Verify committed targets/ matches source (CI drift guard)
	@python3 scripts/translate.py --check

test: ## Unit tests for the render/transform/parse logic + generated artifacts
	@python3 -W ignore::ResourceWarning -m unittest discover -s tests -t . -q

ci: check validate names build-check test ## All gates: roster + content + naming + targets + tests
