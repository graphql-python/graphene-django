from setuptools import find_packages, setup
import sys
import ast
import re

_version_re = re.compile(r"__version__\s+=\s+(.*)")

with open("graphene_django/__init__.py", "rb") as f:
    version = str(
        ast.literal_eval(_version_re.search(f.read().decode("utf-8")).group(1))
    )

neomodel_require = [
    "neomodel-next==3.3.0",
]

tests_require = [
    "pytest>=3.6.3",
    "pytest-cov",
    "coveralls",
    "mock",
    "pytz",
    "django-filter<2;python_version<'3'",
    "pytest-django>=3.3.2",
]


dev_requires = [
    "black==19.3b0",
    "flake8==3.7.7",
] + tests_require

setup(
    name="graphene-neo4j",
    version=version,
    description="Graphene Django-Neo4J (neomodel) integration",
    long_description=open("README.rst").read(),
    url="https://github.com/MardanovTimur/graphene-neo4j",
    author="Syrus Akbary; Mardanov Timur",
    author_email="timurmardanov97@gmail.com",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
    keywords="api graphql protocol rest relay graphene",
    packages=find_packages(exclude=["tests"]),
    install_requires=[
        "six>=1.10.0",
        #  "graphene>=2.1.3,<3",
        "graphql-core>=2.1.0,<3",
        "Django>=1.11",
        "singledispatch>=3.4.0.3",
        "promise>=2.1",
        "lazy-import==0.2.2",
        "neomodel-next>=3.3.0",
        #  "django-filter @ git+https://github.com/MardanovTimur/django-filter@neomodel#egg=foo-9999",
        #  "graphene @ git+https://github.com/MardanovTimur/graphene@master#eqq-123",
    ],
    setup_requires=["pytest-runner"],
    tests_require=tests_require,
    extras_require={"test": tests_require},
    include_package_data=True,
    zip_safe=False,
    platforms="any",
)
