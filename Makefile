dev-setup:
	pip install -e ".[dev]"

tests:
	py.test graphene_django --cov=graphene_django -vv

format:
	black --exclude "/migrations/" graphene_django examples

lint:
	flake8 graphene_django examples
