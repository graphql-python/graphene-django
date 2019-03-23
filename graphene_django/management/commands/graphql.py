import importlib
import json
import sys
import inspect
import os

from django.core.management.base import BaseCommand, CommandError
from graphene_django.settings import graphene_settings
from django.conf import settings

INSTALLED_APPS = [app for app in settings.INSTALLED_APPS if 'django' not in app]

PY_FILES = ['node.py', 'edge.py', '__init__.py', 'lib.py', 'resolvers.py']

pythonic_init = """from .node import {model_name}Node
"""

pythonic_node = """#encoding=utf-8

from lazy_import import lazy_module, lazy_callable
from graphene_django import DjangoObjectType
from graphene_django.relationship import EdgeNode # edge initialization
from graphene.relay import Node

# lazy_modules imports

from {application}.{model_module} import {model_name}


class {model_name}Node(DjangoObjectType):
    class Meta:
        interfaces = (
            Node,
        )
        model = {model_name}

        neomodel_filter_fields = {{
            # announce here dynamic filtering
        }}
        only_fields = ()
        exclude_fields = ()

"""


def get_models(application, model_name, model_module_name="models"):
    # get models from application
    from neomodel import StructuredNode  # noqa
    module_name = ".".join([application, model_module_name])
    for name, obj in inspect.getmembers(sys.modules[module_name]):
        if inspect.isclass(obj) and (StructuredNode in obj.__bases__):
            if model_name == ".":
                yield obj
            elif model_name.strip() == name:
                yield obj


class CommandArguments(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "-A",
            "--application",
            type=str,
            dest="application",
            required=True,
            help="Choose the django destination app",
        )
        parser.add_argument(
            "-M",
            "--model",
            type=str,
            dest="model",
            required=True,
            help="Choose the model, or type . (ALL models)",
        )
        parser.add_argument(
            "--app-module-models",
            type=str,
            dest="app_module_models",
            default="models",
            help="Choose the module of models",
        )
        parser.add_argument(
            '-O',
            "--output-application",
            type=str,
            dest="output_app",
            help="Choose the output application of graphQL nodes",
        )


class Command(CommandArguments):
    help = "Django-GraphQL management module"
    can_import_settings = True

    def interpretate_model_to_graphQL(self,
                                       model,
                                       out_application,
                                       application,
                                       app_module_models):
        # out_application(d) -> graphql(d) -> model(d)
        #       -> node.py (f)
        #       -> resolvers.py (f)
        #       -> lib.py (f)
        #       -> edge.py (f)
        package_dir = model.__name__.lower()
        output_path = os.path.join(settings.BASE_DIR, out_application, 'graphQL')
        if not os.path.exists(output_path):
            print("Does not exists", output_path, '. \nCreate...')
            os.mkdir(output_path)
            print("Directory graphQL in {} app created".format(out_application))
        package_path = os.path.join(output_path, package_dir)
        if os.path.exists(package_dir):
            raise CommandError('Files for %s model already exists' % package_dir.capitalize())
        try:
            print("Create path environment %s" % package_dir)
            os.mkdir(package_path)
            for file_name in PY_FILES:
                with open(os.path.join(package_path, file_name), 'w') as file:
                    if file_name == "node.py":
                        file.write(pythonic_node.format(application=application,
                            model_module=app_module_models,
                            model_name=model.__name__))
                    elif file_name == '__init__.py':
                        file.write(pythonic_init.format(model_name=model.__name__))
                    else:
                        file.write("")
        except:
            pass




    def handle(self, *args, **options):
        application = options.get('application')
        out_application = options.get('output_app', application)
        app_module_models = options.get('app_module_models', 'models')

        if application not in INSTALLED_APPS:
            raise CommandError('Application %s does\'nt exists' % application)
        else:
            models = list(get_models(application, options.get('model', '.'),
                                     app_module_models))
            if not models:
                raise CommandError('Application %s has not contains %s model'
                                   % (application, options.get('model')))
            if out_application not in INSTALLED_APPS:
                raise CommandError('Application %s does\'nt exists' % out_application)
            for model in models:
                self.interpretate_model_to_graphQL(model,
                                                  out_application,
                                                  application,
                                                  app_module_models)

