import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from api.services.wishlist_services.wishlist_services import WishlistService

wishlist_service = WishlistService()


@csrf_exempt
@require_POST
def toggle_wishlist(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {
                "response": {
                    "status": False,
                    "message": "Authentication required.",
                    "data": None,
                }
            },
            status=401,
        )

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

    stock_id = payload.get("stock_id")

    try:
        stock_id = int(stock_id)
    except (TypeError, ValueError):
        return JsonResponse(
            {
                "response": {
                    "status": False,
                    "message": "stock_id must be a valid integer.",
                    "data": None,
                }
            },
            status=400,
        )

    result = wishlist_service.toggle_wishlist(user=request.user, stock_id=stock_id)
    return __service_json_response(result)

def __service_json_response(result):
    status_code = result.get("http_status", 200 if result["status"] else 500)

    response_payload = {
        "status": result["status"],
        "message": result["message"],
        "data": result["data"],
    }

    return JsonResponse({"response": response_payload}, status=status_code)