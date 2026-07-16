import json
import logging
import threading
from datetime import timedelta

from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from api.models import SyncJobLock
from api.operations.sync import Sync
from api.views.security import require_cron_secret

sync = Sync()
logger = logging.getLogger(__name__)
_sync_token_data_lock = threading.Lock()
_sync_token_data_thread = None
_recalculate_scores_lock = threading.Lock()
_recalculate_scores_thread = None
SYNC_JOB_LOCK_NAME = "token_data_sync"
RECALCULATE_SCORES_JOB_LOCK_NAME = "score_recalculation"
SYNC_JOB_STALE_AFTER = timedelta(hours=2)
RECALCULATE_SCORES_JOB_STALE_AFTER = timedelta(hours=2)


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
    result = sync.get_sync_status()
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
@require_cron_secret
def reset_in_use(request):
    result = sync.reset_all_stocks_in_use()
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
def recalculate_scores(request):
    global _recalculate_scores_thread

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

    score = payload.get("score")

    if not isinstance(score, str) or not score.strip():
        return JsonResponse(
            {
                "response": {
                    "status": False,
                    "message": "Field 'score' must be a non-empty string.",
                    "data": None,
                }
            },
            status=400,
        )

    normalized_score = score.strip()

    if not _acquire_job_lock(
        RECALCULATE_SCORES_JOB_LOCK_NAME,
        RECALCULATE_SCORES_JOB_STALE_AFTER,
    ):
        return JsonResponse(
            {
                "response": {
                    "status": False,
                    "message": "Score recalculation job still running.",
                    "data": {
                        "started": False,
                        "already_running": True,
                        "score": normalized_score,
                    },
                }
            },
            status=409,
        )

    with _recalculate_scores_lock:
        try:
            _recalculate_scores_thread = threading.Thread(
                target=_run_recalculate_scores,
                args=(normalized_score,),
                name="score-recalculation",
                daemon=True,
            )
            _recalculate_scores_thread.start()
        except Exception:
            _release_job_lock(RECALCULATE_SCORES_JOB_LOCK_NAME)
            _recalculate_scores_thread = None
            raise

    return JsonResponse(
        {
            "response": {
                "status": True,
                "message": f"Score recalculation started for {normalized_score}.",
                "data": {
                    "started": True,
                    "already_running": False,
                    "score": normalized_score,
                },
            }
        },
        status=200,
    )


# ***************
# *   Private   *
# ***************
def _run_token_data_sync():
    global _sync_token_data_thread

    try:
        result = sync.insert_tokens_data()
        _record_job_result(SYNC_JOB_LOCK_NAME, result)
        logger.info("Background token data sync finished. result=%s", result)
        logger.info(
            "Token data sync completion message: %s",
            result.get("message"),
        )
    except Exception:
        _record_job_result(
            SYNC_JOB_LOCK_NAME,
            {
                "status": False,
                "message": "Token data sync crashed before completion.",
                "data": None,
            }
        )
        logger.exception("Background token data sync crashed.")
    finally:
        _release_job_lock(SYNC_JOB_LOCK_NAME)
        with _sync_token_data_lock:
            _sync_token_data_thread = None


def _run_recalculate_scores(score):
    global _recalculate_scores_thread

    try:
        result = sync.recalculate_scores(score)
        _record_job_result(RECALCULATE_SCORES_JOB_LOCK_NAME, result)
        logger.info("Background score recalculation finished. score=%s result=%s", score, result)
    except Exception:
        _record_job_result(
            RECALCULATE_SCORES_JOB_LOCK_NAME,
            {
                "status": False,
                "message": f"Score recalculation for {score} crashed before completion.",
                "data": {"score": score},
            }
        )
        logger.exception("Background score recalculation crashed. score=%s", score)
    finally:
        _release_job_lock(RECALCULATE_SCORES_JOB_LOCK_NAME)
        with _recalculate_scores_lock:
            _recalculate_scores_thread = None


def _acquire_sync_job_lock():
    return _acquire_job_lock(SYNC_JOB_LOCK_NAME, SYNC_JOB_STALE_AFTER)


def _acquire_job_lock(job_name, stale_after):
    now = timezone.now()

    with transaction.atomic():
        lock, _ = SyncJobLock.objects.select_for_update().get_or_create(
            name=job_name,
            defaults={"is_running": False},
        )

        if lock.is_running and lock.started_at and now - lock.started_at <= stale_after:
            return False

        lock.is_running = True
        lock.started_at = now
        lock.save(update_fields=["is_running", "started_at", "updated_at"])
        return True


def _release_sync_job_lock():
    _release_job_lock(SYNC_JOB_LOCK_NAME)


def _release_job_lock(job_name):
    with transaction.atomic():
        lock = (
            SyncJobLock.objects.select_for_update()
            .filter(name=job_name)
            .first()
        )
        if lock is None:
            return

        lock.is_running = False
        lock.started_at = None
        lock.save(update_fields=["is_running", "started_at", "updated_at"])


def _record_sync_job_result(result):
    _record_job_result(SYNC_JOB_LOCK_NAME, result)


def _record_job_result(job_name, result):
    with transaction.atomic():
        lock, _ = SyncJobLock.objects.select_for_update().get_or_create(
            name=job_name,
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
