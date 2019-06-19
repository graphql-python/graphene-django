from setuptools import find_packages, setup
import sys
import ast
import re

_version_re = re.compile(r"__version__\s+=\s+(.*)")

with open("graphene_django/__init__.py", "rb") as f:
    version = str(
        ast.literal_eval(_version_re.search(f.read().decode("utf-8")).group(1))
    )

rest_framework_require = ["djangorestframework>=3.6.3"]


tests_require = [
    "pytest>=3.6.3",
    "pytest-cov",
    "coveralls",
    "mock",
    "pytz",
    "django-filter<2;python_version<'3'",
    "django-filter>=2;python_version>='3'",
    "pytest-django>=3.3.2",
] + rest_framework_require


dev_requires = [
    "black==19.3b0",
    "flake8==3.7.7",
    "flake8-black==0.1.0",
    "flake8-bugbear==19.3.0",
] + tests_require

setup(
    name="graphene-django",
    version=version,
    description="Graphene Django integration",
    long_description=open("README.rst").read(),
    url="https://github.com/graphql-python/graphene-django",
    author="Syrus Akbary",
    author_email="me@syrusakbary.com",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
    keywords="api graphql protocol rest relay graphene",
    packages=find_packages(exclude=["tests"]),
    install_requires=[
        "six>=1.10.0",
        "graphene>=2.1.3,<3",
        "graphql-core>=2.1.0,<3",
        "Django>=1.11",
        "singledispatch>=3.4.0.3",
        "promise>=2.1",
    ],
    setup_requires=["pytest-runner"],
    tests_require=tests_require,
    rest_framework_require=rest_framework_require,
    extras_require={
        "test": tests_require,
        "rest_framework": rest_framework_require,
        "dev": dev_requires,
    },
    include_package_data=True,
    zip_safe=False,
    platforms="any",
)
