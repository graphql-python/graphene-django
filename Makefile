dev-setup:
	pip install -e ".[test]"

tests:
	py.test graphene_django --cov=graphene_django -vv