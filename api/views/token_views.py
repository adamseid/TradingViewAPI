from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.db import transaction
from django.utils import timezone
import json
import logging
import threading
from datetime import timedelta

from api.utils.security import require_cron_secret
from api.services.token_services.token_service import TokenService
from api.models import SyncJobLock

token_service = TokenService()
logger = logging.getLogger(__name__)
_sync_token_data_lock = threading.Lock()
_sync_token_data_thread = None
SYNC_JOB_LOCK_NAME = "token_data_sync"
SYNC_JOB_STALE_AFTER = timedelta(hours=2)


def _run_token_data_sync():
    global _sync_token_data_thread

    try:
        result = token_service.insert_tokens_data()
        _record_sync_job_result(result)
        logger.info("Background token data sync finished. result=%s", result)
        logger.info(
            "Token data sync completion message: %s",
            result.get("message"),
        )
    except Exception:
        _record_sync_job_result(
            {
                "status": False,
                "message": "Token data sync crashed before completion.",
                "data": None,
            }
        )
        logger.exception("Background token data sync crashed.")
    finally:
        _release_sync_job_lock()
        with _sync_token_data_lock:
            _sync_token_data_thread = None


def _acquire_sync_job_lock():
    now = timezone.now()

    with transaction.atomic():
        lock, _ = SyncJobLock.objects.select_for_update().get_or_create(
            name=SYNC_JOB_LOCK_NAME,
            defaults={"is_running": False},
        )

        if lock.is_running and lock.started_at and now - lock.started_at <= SYNC_JOB_STALE_AFTER:
            return False

        lock.is_running = True
        lock.started_at = now
        lock.save(update_fields=["is_running", "started_at", "updated_at"])
        return True


def _release_sync_job_lock():
    with transaction.atomic():
        lock = (
            SyncJobLock.objects.select_for_update()
            .filter(name=SYNC_JOB_LOCK_NAME)
            .first()
        )
        if lock is None:
            return

        lock.is_running = False
        lock.started_at = None
        lock.save(update_fields=["is_running", "started_at", "updated_at"])


def _record_sync_job_result(result):
    with transaction.atomic():
        lock, _ = SyncJobLock.objects.select_for_update().get_or_create(
            name=SYNC_JOB_LOCK_NAME,
            defaults={"is_running": False},
        )
        lock.last_finished_at = timezone.now()
        lock.last_status = result.get("status")
        lock.last_message = result.get("message")
        lock.save(
            update_fields=[
                "last_finished_at",
                "last_status",
                "last_message",
                "updated_at",
            ]
        )


@require_GET
def home_page(request):
    result = token_service.token_list(user=request.user)
    return __service_json_response(result)


@require_GET
def token_detail(request, ticker):
    result = token_service.stock_detail(ticker)
    return __service_json_response(result)


@require_GET
def token_search(request):
    query = request.GET.get("q", "")
    result = token_service.search_tickers(query)
    return __service_json_response(result)


@require_GET
def list_stocks_for_edit(request):
    result = token_service.list_all_stocks_for_edit()
    return __service_json_response(result)


@require_POST
def insert_individual_token(request):
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

    result = token_service.insert_individual_token(payload)
    return __service_json_response(result)


@require_POST
def update_individual_token(request, stock_id):
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

    result = token_service.update_individual_token(stock_id, payload)
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

    if not _acquire_sync_job_lock():
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

    with _sync_token_data_lock:
        try:
            _sync_token_data_thread = threading.Thread(
                target=_run_token_data_sync,
                name="token-data-sync",
                daemon=True,
            )
            _sync_token_data_thread.start()
        except Exception:
            _release_sync_job_lock()
            _sync_token_data_thread = None
            raise

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


@require_GET
@require_cron_secret
def sync_token_data_status(request):
    lock = SyncJobLock.objects.filter(name=SYNC_JOB_LOCK_NAME).first()

    return JsonResponse(
        {
            "response": {
                "status": True,
                "message": (
                    lock.last_message
                    if lock and lock.last_message
                    else "No token data sync has completed yet."
                ),
                "data": {
                    "is_running": bool(lock and lock.is_running),
                    "started_at": lock.started_at if lock else None,
                    "last_finished_at": lock.last_finished_at if lock else None,
                    "last_status": lock.last_status if lock else None,
                    "last_message": lock.last_message if lock else None,
                },
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
    status_code = result.get("http_status", 200 if result["status"] else 500)
    return JsonResponse({"response": result}, status=status_code)
