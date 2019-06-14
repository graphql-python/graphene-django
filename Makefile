.PHONY: dev-setup ## Install development dependencies
dev-setup:
	pip install -e ".[dev]"

tests:
	py.test graphene_django --cov=graphene_django -vv

format:
	black --exclude "/migrations/" graphene_django examples

lint:
	flake8 graphene_django examples

.PHONY: docs ## Generate docs
docs: dev-setup
	cd docs && make install && make html

.PHONY: docs-live ## Generate docs with live reloading
docs-live: dev-setup
	cd docs && make install && make livehtml
