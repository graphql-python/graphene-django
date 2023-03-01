.PHONY: dev-setup ## Install development dependencies
dev-setup:
	pip install -e ".[dev]"

.PHONY: install-dev
install-dev: dev-setup  # Alias install-dev -> dev-setup

.PHONY: tests
tests:
	py.test graphene_django --cov=graphene_django -vv

.PHONY: test
test: tests  # Alias test -> tests

.PHONY: format
format:
	pre-commit run --all-files

.PHONY: docs ## Generate docs
docs: dev-setup
	cd docs && make install && make html

.PHONY: docs-live ## Generate docs with live reloading
docs-live: dev-setup
	cd docs && make install && make livehtml
