import logging

from django.db.models import Case, Exists, IntegerField, OuterRef, Q, Subquery, Value, When
from django.utils.text import slugify

from api.models import Stock, StockData, Wishlist

ALLOWED_MANUAL_SCREENERS = {"america", "canada", "crypto"}

logger = logging.getLogger(__name__)


class Token:
    def token_list(self, user=None):
        latest_stock_data_subquery = (
            StockData.objects.filter(stock=OuterRef("stock"))
            .order_by("-id")
            .values("id")[:1]
        )

        most_recent_stock_data = (
            StockData.objects.filter(
                id=Subquery(latest_stock_data_subquery),
                stock__in_use=True,
            )
            .select_related("stock")
            .order_by("stock__ticker", "stock__exchange", "stock__screener")
        )

        if user is not None and user.is_authenticated:
            wishlist_subquery = Wishlist.objects.filter(
                user=user,
                stock_id=OuterRef("stock_id"),
            )

            most_recent_stock_data = most_recent_stock_data.annotate(
                wishlist=Case(
                    When(Exists(wishlist_subquery), then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            )
        else:
            most_recent_stock_data = most_recent_stock_data.annotate(
                wishlist=Value(0, output_field=IntegerField())
            )

        stock_list = {}
        crypto_list = []
        wishlist = []

        for stock_data in most_recent_stock_data:
            item = self._present_latest_stock_item(stock_data)

            if stock_data.wishlist > 0:
                wishlist.append(item)
            elif str(stock_data.stock.screener).lower() == "crypto":
                crypto_list.append(item)
            else:
                sector = stock_data.stock.sector or "Uncategorized"
                stock_list.setdefault(sector, []).append(item)

        return {
            "status": True,
            "message": "success",
            "data": {
                "stock_list": stock_list,
                "crypto_list": crypto_list,
                "wishlist": wishlist,
            },
            "http_status": 200,
        }

    def token_detail(self, ticker):
        stock_rows = self._list_stock_data_by_ticker(ticker)

        if len(stock_rows) == 0:
            return {
                "status": False,
                "message": "No Stock Data found",
                "data": None,
                "http_status": 404,
            }

        stock_data = []
        for data in stock_rows:
            stock_data.append(self._present_token_detail_item(data))

        return {
            "status": True,
            "message": "success",
            "data": {
                "stock_data": stock_data,
            },
            "http_status": 200,
        }

    def search_tickers(self, query):
        try:
            tickers = self._search_tickers(query)

            return {
                "status": True,
                "message": "success",
                "data": {"tickers": tickers},
                "http_status": 200,
            }
        except Exception as exc:
            return {
                "status": False,
                "message": f"Failed to search tickers: {str(exc)}",
                "data": None,
                "http_status": 500,
            }

    def insert_individual_token(
        self,
        *,
        ticker,
        name,
        exchange,
        screener,
        category,
        sector,
        industry,
    ):
        try:
            if self._stock_exists_by_ticker(ticker):
                return {
                    "status": False,
                    "message": f"{ticker} already exists.",
                    "data": None,
                    "http_status": 409,
                }

            stock = self._insert_individual_stock(
                ticker=ticker,
                name=name,
                screener=screener,
                exchange=exchange,
                category=category,
                sector=sector,
                industry=industry,
            )

            if stock is None:
                return {
                    "status": False,
                    "message": "Failed to insert stock.",
                    "data": None,
                    "http_status": 500,
                }

            return {
                "status": True,
                "message": f"{ticker} created successfully.",
                "data": {
                    "stock": self._present_stock_for_response(stock),
                },
                "http_status": 201,
            }
        except Exception as exc:
            return {
                "status": False,
                "message": f"Failed to insert stock: {str(exc)}",
                "data": None,
                "http_status": 500,
            }

    def list_all_stocks_for_edit(self):
        try:
            stocks = self._list_stocks()

            return {
                "status": True,
                "message": "success",
                "data": {
                    "stocks": [self._present_stock_for_edit(stock) for stock in stocks]
                },
                "http_status": 200,
            }
        except Exception as exc:
            return {
                "status": False,
                "message": f"Failed to load stocks: {str(exc)}",
                "data": None,
                "http_status": 500,
            }

    def update_individual_token(
        self,
        *,
        stock_id,
        ticker,
        name,
        screener,
        exchange,
        category,
        sector,
        industry,
        in_use,
    ):
        try:
            stock = self._get_stock_by_id(stock_id)
            if stock is None:
                return {
                    "status": False,
                    "message": "Stock not found.",
                    "data": None,
                    "http_status": 404,
                }

            if self._stock_exists_by_ticker_excluding_id(stock_id, ticker):
                return {
                    "status": False,
                    "message": f"{ticker} already exists.",
                    "data": None,
                    "http_status": 409,
                }

            updated_stock = self._update_stock(
                stock,
                ticker=ticker,
                name=name,
                screener=screener,
                exchange=exchange,
                category=category,
                sector=sector,
                industry=industry,
                in_use=in_use,
            )

            if updated_stock is None:
                return {
                    "status": False,
                    "message": "Failed to update stock.",
                    "data": None,
                    "http_status": 500,
                }

            return {
                "status": True,
                "message": f"{updated_stock.ticker} updated successfully.",
                "data": {"stock": self._present_stock_for_edit(updated_stock)},
                "http_status": 200,
            }
        except Exception as exc:
            return {
                "status": False,
                "message": f"Failed to update stock: {str(exc)}",
                "data": None,
                "http_status": 500,
            }

    # ***************
    # *   Private   *
    # ***************
    def _normalize_ticker(self, ticker):
        return str(ticker).strip().upper()

    def _normalize_exchange(self, exchange):
        return str(exchange).strip().upper()

    def _normalize_screener(self, screener):
        return str(screener).strip().lower()

    def _list_stocks(self):
        return Stock.objects.all().order_by("ticker", "exchange", "screener")

    def _get_stock_by_id(self, stock_id):
        return Stock.objects.filter(id=stock_id).first()

    def _stock_exists_by_ticker(self, ticker):
        return Stock.objects.filter(
            ticker=self._normalize_ticker(ticker)
        ).exists()

    def _stock_exists_by_ticker_excluding_id(self, stock_id, ticker):
        return (
            Stock.objects.filter(ticker=self._normalize_ticker(ticker))
            .exclude(id=stock_id)
            .exists()
        )

    def _search_tickers(self, query):
        normalized_query = self._normalize_ticker(query)

        if not normalized_query:
            return []

        startswith_matches = list(
            Stock.objects.filter(ticker__istartswith=normalized_query)
            .order_by("ticker")
            .values_list("ticker", flat=True)
            .distinct()
        )

        contains_matches = list(
            Stock.objects.filter(
                Q(ticker__icontains=normalized_query) & ~Q(ticker__istartswith=normalized_query)
            )
            .order_by("ticker")
            .values_list("ticker", flat=True)
            .distinct()
        )

        return startswith_matches + contains_matches

    def _insert_individual_stock(
        self,
        *,
        ticker,
        name,
        screener,
        exchange,
        category,
        sector,
        industry,
    ):
        try:
            return Stock.objects.create(
                ticker=self._normalize_ticker(ticker),
                name=name,
                screener=self._normalize_screener(screener),
                exchange=self._normalize_exchange(exchange),
                category=category,
                sector=sector,
                industry=industry,
                in_use=True,
            )
        except Exception:
            logger.exception(
                "Failed to insert individual stock. ticker=%s, exchange=%s, screener=%s",
                ticker,
                exchange,
                screener,
            )
            return None

    def _update_stock(
        self,
        stock,
        *,
        ticker,
        name,
        screener,
        exchange,
        category,
        sector,
        industry,
        in_use,
    ):
        try:
            stock.ticker = self._normalize_ticker(ticker)
            stock.name = name
            stock.screener = self._normalize_screener(screener)
            stock.exchange = self._normalize_exchange(exchange)
            stock.category = category
            stock.sector = sector
            stock.industry = industry
            stock.in_use = in_use
            stock.save()
            return stock
        except Exception:
            logger.exception(
                "Failed to update stock. stock_id=%s ticker=%s exchange=%s screener=%s",
                getattr(stock, "id", None),
                ticker,
                exchange,
                screener,
            )
            return None

    def _list_stock_data_by_ticker(self, ticker):
        normalized_ticker = self._normalize_ticker(ticker)

        return (
            StockData.objects.filter(stock__ticker=normalized_ticker)
            .select_related("stock")
            .order_by("stock__exchange", "stock__screener", "-date")
        )

    def _present_latest_stock_item(self, stock_data):
        strategy_one_score = (
            None
            if stock_data.strategy_one_score is None
            else round(stock_data.strategy_one_score, 3)
        )
        strategy_two_score = (
            None
            if stock_data.strategy_two_score is None
            else round(stock_data.strategy_two_score, 3)
        )
        current_price = None if stock_data.current_price is None else round(stock_data.current_price, 3)
        support_resistance_score = (
            None
            if stock_data.support_resistance_score is None
            else round(stock_data.support_resistance_score, 3)
        )
        daily_macd_velocity = (
            None
            if stock_data.daily_macd_velocity is None
            else round(stock_data.daily_macd_velocity, 3)
        )
        daily_macd_score = (
            None
            if stock_data.daily_macd_score is None
            else round(stock_data.daily_macd_score, 3)
        )
        weekly_macd_velocity = (
            None
            if stock_data.weekly_macd_velocity is None
            else round(stock_data.weekly_macd_velocity, 3)
        )
        weekly_macd_score = (
            None
            if stock_data.weekly_macd_score is None
            else round(stock_data.weekly_macd_score, 3)
        )

        ma_50d_score = None if stock_data.ma_50d_score is None else round(stock_data.ma_50d_score, 3)
        ma_100d_score = None if stock_data.ma_100d_score is None else round(stock_data.ma_100d_score, 3)
        ma_200d_score = None if stock_data.ma_200d_score is None else round(stock_data.ma_200d_score, 3)
        ma_score_raw = (
            (stock_data.ma_50d_score or 0)
            + (stock_data.ma_100d_score or 0)
            + (stock_data.ma_200d_score or 0)
        )
        ma_score = round(ma_score_raw, 3)

        daily_profit = None
        daily_return = None
        if stock_data.current_price is not None and stock_data.price_change is not None:
            daily_profit_raw = stock_data.current_price * (stock_data.price_change / 100)
            daily_profit = round(daily_profit_raw, 3)

            denominator = daily_profit_raw + stock_data.current_price
            if denominator != 0:
                daily_return = round(daily_profit_raw / denominator, 3)

        return {
            "stock_id": stock_data.stock.id,
            "wishlist": int(stock_data.wishlist > 0),
            "ticker": stock_data.stock.ticker,
            "name": stock_data.stock.name,
            "exchange": stock_data.stock.exchange,
            "screener": stock_data.stock.screener,
            "category": stock_data.stock.category,
            "sector": stock_data.stock.sector,
            "industry": stock_data.stock.industry,
            "image_url": stock_data.stock.image_url,
            "date": stock_data.date,
            "strategy_one_direction": self._calculate_direction(stock_data.strategy_one_score),
            "strategy_two_direction": self._calculate_direction(stock_data.strategy_two_score),
            "current_price": current_price,
            "price_change": None if stock_data.price_change is None else round(stock_data.price_change, 3),
            "daily_profit": daily_profit,
            "daily_return": daily_return,
            "support": None if stock_data.support is None else round(stock_data.support, 3),
            "resistance": None if stock_data.resistance is None else round(stock_data.resistance, 3),
            "support_resistance_score": support_resistance_score,
            "ma_50d_score": ma_50d_score,
            "ma_100d_score": ma_100d_score,
            "ma_200d_score": ma_200d_score,
            "ma_score": ma_score,
            "daily_macd_velocity": daily_macd_velocity,
            "daily_macd_score": daily_macd_score,
            "weekly_macd_velocity": weekly_macd_velocity,
            "weekly_macd_score": weekly_macd_score,
            "strategy_one_score": strategy_one_score,
            "strategy_two_score": strategy_two_score,
            "kinematics_score": 0,
            "five_day_velocity_score": 0,
            "five_day_acceleration_score": 0,
        }

    def _present_token_detail_item(self, stock_data):
        ma_score = round(
            (stock_data.ma_50d_score or 0)
            + (stock_data.ma_100d_score or 0)
            + (stock_data.ma_200d_score or 0),
            3,
        )

        return {
            "id": stock_data.id,
            "date": stock_data.date,
            "ticker": stock_data.stock.ticker,
            "exchange": stock_data.stock.exchange,
            "screener": stock_data.stock.screener,
            "current_price": None if stock_data.current_price is None else round(stock_data.current_price, 3),
            "resistance": None if stock_data.resistance is None else round(stock_data.resistance, 3),
            "support": None if stock_data.support is None else round(stock_data.support, 3),
            "sma_200": None if stock_data.sma_200 is None else round(stock_data.sma_200, 3),
            "ma_score": ma_score,
            "support_resistance_score": (
                None
                if stock_data.support_resistance_score is None
                else round(stock_data.support_resistance_score, 3)
            ),
            "daily_macd_histogram": (
                None
                if stock_data.daily_macd_histogram is None
                else round(stock_data.daily_macd_histogram, 3)
            ),
            "daily_macd_velocity": (
                None
                if stock_data.daily_macd_velocity is None
                else round(stock_data.daily_macd_velocity, 3)
            ),
            "daily_macd_score": (
                None
                if stock_data.daily_macd_score is None
                else round(stock_data.daily_macd_score, 3)
            ),
            "weekly_macd_histogram": (
                None
                if stock_data.weekly_macd_histogram is None
                else round(stock_data.weekly_macd_histogram, 3)
            ),
            "weekly_macd_velocity": (
                None
                if stock_data.weekly_macd_velocity is None
                else round(stock_data.weekly_macd_velocity, 3)
            ),
            "weekly_macd_score": (
                None
                if stock_data.weekly_macd_score is None
                else round(stock_data.weekly_macd_score, 3)
            ),
            "strategy_one_score": (
                None
                if stock_data.strategy_one_score is None
                else round(stock_data.strategy_one_score, 3)
            ),
            "strategy_two_score": (
                None
                if stock_data.strategy_two_score is None
                else round(stock_data.strategy_two_score, 3)
            ),
            "strategy_one_direction": self._calculate_direction(stock_data.strategy_one_score),
            "strategy_two_direction": self._calculate_direction(stock_data.strategy_two_score),
        }

    def _calculate_direction(self, total_score):
        if total_score is None:
            return None
        if total_score > 4:
            return 2
        if total_score > 2:
            return 1
        if total_score < -4:
            return -2
        if total_score < -2:
            return -1
        return 0

    def _present_stock_for_response(self, stock):
        return {
            "id": stock.id,
            "ticker": stock.ticker,
            "slug": slugify(stock.ticker),
            "name": stock.name,
            "screener": stock.screener,
            "exchange": stock.exchange,
            "category": stock.category,
            "sector": stock.sector,
            "industry": stock.industry,
            "in_use": stock.in_use,
        }

    def _present_stock_for_edit(self, stock):
        return {
            "id": stock.id,
            "ticker": stock.ticker,
            "name": stock.name,
            "screener": stock.screener,
            "exchange": stock.exchange,
            "category": stock.category,
            "sector": stock.sector,
            "industry": stock.industry,
            "in_use": stock.in_use,
            "image_url": stock.image_url,
        }
