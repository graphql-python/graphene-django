.PHONY: help
help:
	@echo "Please use \`make <target>' where <target> is one of"
	@grep -E '^\.PHONY: [a-zA-Z_-]+ .*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = "(: |##)"}; {printf "\033[36m%-30s\033[0m %s\n", $$2, $$3}'

.PHONY: dev-setup ## Install development dependencies
dev-setup:
	pip install -e ".[dev]"
	python -m pre_commit install

.PHONY: tests ## Run unit tests
tests:
	PYTHONPATH=. pytest graphene_django --cov=graphene_django -vv

.PHONY: tests-repeat ## Run unit tests 100 times to possibly identify flaky unit tests (and run them in parallel)
tests-repeat:
	PYTHONPATH=. pytest graphene_django --cov=graphene_django -vv --count 100 -n logical

.PHONY: format ## Format code
format:
	black graphene_django examples setup.py

.PHONY: lint ## Lint code
lint:
	ruff graphene_django examples

.PHONY: docs ## Generate docs
docs: dev-setup
	cd docs && make install && make html

.PHONY: docs-live ## Generate docs with live reloading
docs-live: dev-setup
	cd docs && make install && make livehtml
