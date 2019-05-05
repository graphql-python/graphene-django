dev-setup:
	pip install -e ".[dev]"

tests:
	py.test graphene_django --cov=graphene_django -vv

format:
	black graphene_django

lint:
	flake8 graphene_django
