import json

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from api.operations.token import ALLOWED_MANUAL_SCREENERS, Token

token = Token()


@require_GET
def home_page(request):
    result = token.token_list(user=request.user)
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
def token_detail(request, ticker):
    result = token.token_detail(ticker=ticker)
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
def token_search(request):
    query = request.GET.get("q", "")
    result = token.search_tickers(query=query)
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
def list_stocks_for_edit(request):
    result = token.list_all_stocks_for_edit()
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

    ticker = (payload.get("ticker") or "").strip().upper()
    name = (payload.get("name") or "").strip() or None
    exchange = (payload.get("exchange") or "").strip().upper()
    screener = (payload.get("screener") or "america").strip().lower()
    category = (payload.get("category") or "").strip() or None
    sector = (payload.get("sector") or "").strip() or None
    industry = (payload.get("industry") or "").strip() or None

    if not ticker:
        return JsonResponse(
            {
                "response": {
                    "status": False,
                    "message": "Ticker is required.",
                    "data": None,
                }
            },
            status=400,
        )

    if not exchange:
        return JsonResponse(
            {
                "response": {
                    "status": False,
                    "message": "Exchange is required.",
                    "data": None,
                }
            },
            status=400,
        )

    if screener not in ALLOWED_MANUAL_SCREENERS:
        return JsonResponse(
            {
                "response": {
                    "status": False,
                    "message": "Screener must be one of america, canada, or crypto.",
                    "data": None,
                }
            },
            status=400,
        )

    result = token.insert_individual_token(
        ticker=ticker,
        name=name,
        exchange=exchange,
        screener=screener,
        category=category,
        sector=sector,
        industry=industry,
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

    ticker = (payload.get("ticker") or "").strip().upper()
    name = (payload.get("name") or "").strip() or None
    screener = (payload.get("screener") or "america").strip().lower()
    exchange = (payload.get("exchange") or "").strip().upper()
    category = (payload.get("category") or "").strip() or None
    sector = (payload.get("sector") or "").strip() or None
    industry = (payload.get("industry") or "").strip() or None
    in_use = bool(payload.get("in_use", False))

    if not ticker:
        return JsonResponse(
            {
                "response": {
                    "status": False,
                    "message": "Ticker is required.",
                    "data": None,
                }
            },
            status=400,
        )

    if not exchange:
        return JsonResponse(
            {
                "response": {
                    "status": False,
                    "message": "Exchange is required.",
                    "data": None,
                }
            },
            status=400,
        )

    if screener not in ALLOWED_MANUAL_SCREENERS:
        return JsonResponse(
            {
                "response": {
                    "status": False,
                    "message": "Screener must be one of america, canada, or crypto.",
                    "data": None,
                }
            },
            status=400,
        )

    result = token.update_individual_token(
        stock_id=stock_id,
        ticker=ticker,
        name=name,
        screener=screener,
        exchange=exchange,
        category=category,
        sector=sector,
        industry=industry,
        in_use=in_use,
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