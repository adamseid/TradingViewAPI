import json

from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from api.operations.auth import Auth

User = get_user_model()
auth = Auth()


@csrf_exempt
@require_POST
def register_user(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {
                "response": {
                    "status": False,
                    "message": "Invalid JSON body.",
                    "data": None,
                }
            },
            status=400,
        )

    first_name = (payload.get("first_name") or "").strip()
    last_name = (payload.get("last_name") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    if not first_name or not last_name or not email or not password:
        return JsonResponse(
            {
                "response": {
                    "status": False,
                    "message": "All fields are required.",
                    "data": None,
                }
            },
            status=400,
        )

    if User.objects.filter(username=email).exists():
        return JsonResponse(
            {
                "response": {
                    "status": False,
                    "message": "Email is already registered.",
                    "data": None,
                }
            },
            status=400,
        )

    result = auth.register_user(
        request=request,
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=password,
    )
    return JsonResponse(
        {
            "response": {
                "status": result["status"],
                "message": result["message"],
                "data": result["data"],
            }
        },
        status=result.get("http_status", 200 if result["status"] else 500),
    )


@csrf_exempt
@require_POST
def login_user(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {
                "response": {
                    "status": False,
                    "message": "Invalid JSON body.",
                    "data": None,
                }
            },
            status=400,
        )

    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    result = auth.login_user(
        request=request,
        email=email,
        password=password,
    )
    return JsonResponse(
        {
            "response": {
                "status": result["status"],
                "message": result["message"],
                "data": result["data"],
            }
        },
        status=result.get("http_status", 200 if result["status"] else 500),
    )


@csrf_exempt
@require_POST
def logout_user(request):
    result = auth.logout_user(request=request)
    return JsonResponse(
        {
            "response": {
                "status": result["status"],
                "message": result["message"],
                "data": result["data"],
            }
        },
        status=result.get("http_status", 200 if result["status"] else 500),
    )


@require_GET
def current_user(request):
    result = auth.current_user(user=request.user)
    return JsonResponse(
        {
            "response": {
                "status": result["status"],
                "message": result["message"],
                "data": result["data"],
            }
        },
        status=result.get("http_status", 200 if result["status"] else 500),
    )