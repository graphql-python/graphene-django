import json
import logging

from django.utils.log import log_response

logger = logging.getLogger("django.graphene")


class ClientErrorLogMiddleware:
    """
    Logs graphql requests 4xx errors. (Except 401, 403)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        try:
            if (
                400 <= response.status_code < 500
                and response.status_code not in (401, 403)
                and "graphql" in request.path.lower()
            ):
                response_json = json.loads(response.content)

                if "errors" in response_json:
                    log_response(
                        message=(
                            f"Graphql Error: {response_json['errors']}\n"
                            f"The Query is: {json.loads(request.body)}"
                        ),
                        response=response,
                    )
        except Exception:
            logger.error(f"Error logging graphql error.", exc_info=True)

        return response
