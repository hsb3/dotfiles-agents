.PHONY: help check

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

check: ## Roster <-> disk drift guard (stdlib-only)
	@python3 scripts/check_roster.py
