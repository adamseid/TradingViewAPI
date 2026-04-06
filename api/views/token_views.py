from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
import logging
import threading

from api.utils.security import require_cron_secret
from api.services.token_services.token_service import TokenService

token_service = TokenService()
logger = logging.getLogger(__name__)
_sync_token_data_lock = threading.Lock()
_sync_token_data_thread = None


def _run_token_data_sync():
    global _sync_token_data_thread

    try:
        result = token_service.insert_tokens_data()
        logger.info("Background token data sync finished. result=%s", result)
    except Exception:
        logger.exception("Background token data sync crashed.")
    finally:
        with _sync_token_data_lock:
            _sync_token_data_thread = None


@require_GET
def home_page(request):
    result = token_service.token_list(user=request.user)
    return __service_json_response(result)


@require_GET
def token_detail(request, ticker):
    result = token_service.stock_detail(ticker)
    return __service_json_response(result)


@csrf_exempt
@require_POST
@require_cron_secret
def sync_tokens(request):
    result = token_service.insert_tokens()
    return __service_json_response(result)


@csrf_exempt
@require_POST
@require_cron_secret
def sync_token_data(request):
    global _sync_token_data_thread

    with _sync_token_data_lock:
        if _sync_token_data_thread is not None and _sync_token_data_thread.is_alive():
            return JsonResponse(
                {
                    "response": {
                        "status": True,
                        "message": "Token data sync already running.",
                        "data": {"started": False, "already_running": True},
                    }
                },
                status=200,
            )

        _sync_token_data_thread = threading.Thread(
            target=_run_token_data_sync,
            name="token-data-sync",
            daemon=True,
        )
        _sync_token_data_thread.start()

    return JsonResponse(
        {
            "response": {
                "status": True,
                "message": "Token data sync started.",
                "data": {"started": True, "already_running": False},
            }
        },
        status=200,
    )

@csrf_exempt
@require_POST
@require_cron_secret
def reset_in_use(request):
    result = token_service.reset_all_stocks_in_use()
    return __service_json_response(result)

def __service_json_response(result):
    status_code = 200 if result["status"] else 500
    return JsonResponse({"response": result}, status=status_code)
