from django.http import JsonResponse
from django.views import View
from django.utils import timezone
import sys
import django


class HealthCheckView(View):
    """
    Simple health check endpoint for testing server availability
    """

    def get(self, request):
        """
        Returns basic health information about the Django application
        """
        return JsonResponse(
            {
                "status": "healthy",
                "timestamp": timezone.now().isoformat(),
                "message": "Django server is running",
                "python_version": sys.version,
                "django_version": django.get_version(),
            }
        )
