import json

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

User = get_user_model()


@csrf_exempt
@require_POST
def register_user(request):
    try:
        payload = json.loads(request.body or "{}")

        first_name = (payload.get("first_name") or "").strip()
        last_name = (payload.get("last_name") or "").strip()
        email = (payload.get("email") or "").strip().lower()
        password = payload.get("password") or ""

        if not first_name or not last_name or not email or not password:
            return __auth_response(False, "All fields are required.", None, 400)

        if User.objects.filter(username=email).exists():
            return __auth_response(False, "Email is already registered.", None, 400)

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        login(request, user)

        return __auth_response(
            True,
            "Registration successful.",
            {
                "user": {
                    "id": user.id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                }
            },
            201,
        )
    except Exception as exc:
        return __auth_response(False, f"Registration failed: {str(exc)}", None, 500)


@csrf_exempt
@require_POST
def login_user(request):
    try:
        payload = json.loads(request.body or "{}")

        email = (payload.get("email") or "").strip().lower()
        password = payload.get("password") or ""

        user = authenticate(request, username=email, password=password)

        if user is None:
            return __auth_response(False, "Invalid email or password.", None, 401)

        login(request, user)

        return __auth_response(
            True,
            "Login successful.",
            {
                "user": {
                    "id": user.id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                }
            },
            200,
        )
    except Exception as exc:
        return __auth_response(False, f"Login failed: {str(exc)}", None, 500)


@csrf_exempt
@require_POST
def logout_user(request):
    logout(request)
    return __auth_response(True, "Logout successful.", None, 200)


@require_GET
def current_user(request):
    if not request.user.is_authenticated:
        return __auth_response(
            True,
            "Anonymous user.",
            {
                "authenticated": False,
                "user": None,
            },
            200,
        )

    return __auth_response(
        True,
        "Authenticated user.",
        {
            "authenticated": True,
            "user": {
                "id": request.user.id,
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
                "email": request.user.email,
            },
        },
        200,
    )

def __auth_response(status, message, data=None, http_status=200):
    return JsonResponse(
        {
            "response": {
                "status": status,
                "message": message,
                "data": data,
            }
        },
        status=http_status,
    )