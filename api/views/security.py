from functools import wraps
from secrets import compare_digest

from django.conf import settings
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET


@require_GET
@ensure_csrf_cookie
def csrf_token(request):
    return JsonResponse({"csrfToken": get_token(request)})


def require_cron_secret(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        supplied = request.headers.get("X-Cron-Secret", "")
        expected = settings.CRON_SECRET or ""

        if not expected or not compare_digest(supplied, expected):
            return JsonResponse({"error": "Unauthorized"}, status=401)

        return view_func(request, *args, **kwargs)

    return wrapper
