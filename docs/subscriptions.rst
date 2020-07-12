Subscriptions
=============

The ``graphene-django`` project does not currently support GraphQL subscriptions out of the box. However, there are
several community-driven modules for adding subscription support, and the provided GraphiQL interface supports
running subscription operations over a websocket.

To implement websocket-based support for GraphQL subscriptions, you’ll need to do the following:

1. Install and configure `django-channels <https://channels.readthedocs.io/en/latest/installation.html>`_.
2. Install and configure* a third-party module for adding subscription support over websockets. A few options include:

   -  `graphql-python/graphql-ws <https://github.com/graphql-python/graphql-ws>`_
   -  `datavance/django-channels-graphql-ws <https://github.com/datadvance/DjangoChannelsGraphqlWs>`_
   -  `jaydenwindle/graphene-subscriptions <https://github.com/jaydenwindle/graphene-subscriptions>`_

3. Ensure that your application (or at least your GraphQL endpoint) is being served via an ASGI protocol server like
   daphne (built in to ``django-channels``), `uvicorn <https://www.uvicorn.org/>`_, or
   `hypercorn <https://pgjones.gitlab.io/hypercorn/>`_.

..

   *** Note:** By default, the GraphiQL interface that comes with
   ``graphene-django`` assumes that you are handling subscriptions at
   the same path as any other operation (i.e., you configured both
   ``urls.py`` and ``routing.py`` to handle GraphQL operations at the
   same path, like ``/graphql``).

   If these URLs differ, GraphiQL will try to run your subscription over
   HTTP, which will produce an error. If you need to use a different URL
   for handling websocket connections, you can configure
   ``SUBSCRIPTION_PATH`` in your ``settings.py``:

   .. code:: python

      GRAPHENE = {
          # ...
          "SUBSCRIPTION_PATH": "/ws/graphql"  # The path you configured in `routing.py`, including a leading slash.
      }

Once your application is properly configured to handle subscriptions, you can use the GraphiQL interface to test
subscriptions like any other operation.
