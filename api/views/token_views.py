from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from api.services.token_services.token_service import TokenService

token_service = TokenService()

@require_GET
def home_page(request):
    result = token_service.token_list(user=request.user)
    return __service_json_response(result)

@require_GET
def token_detail(request, ticker):
    result = token_service.stock_detail(ticker)
    return __service_json_response(result)

@require_GET
def sync_tokens(request):
    result = token_service.insert_tokens()
    return __service_json_response(result)

@require_GET
def sync_token_data(request):
    result = token_service.insert_tokens_data()
    return __service_json_response(result)

def __service_json_response(result):
    status_code = 200 if result["status"] else 500
    return JsonResponse({"response": result}, status=status_code)
