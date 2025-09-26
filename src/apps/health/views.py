from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def health_check(_request):
    """Return a simple health payload used by uptime checks."""
    return Response({"status": "ok"})
