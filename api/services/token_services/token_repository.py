from api.models import Stock, StockData, Wishlist
from django.db.models import OuterRef, Subquery, Exists, IntegerField, Case, When, Value
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class TokenRepository:
    def normalize_ticker(self, ticker):
        return str(ticker).strip().upper()

    def normalize_exchange(self, exchange):
        return str(exchange).strip().upper()

    def normalize_screener(self, screener):
        return str(screener).strip().lower()

    def clear_all_stock_data_and_stocks(self):
        try:
            StockData.objects.all().delete()
            Stock.objects.all().delete()
            return True
        except Exception:
            logger.exception("Failed to clear StockData and Stock tables")
            return False

    def insert_stock(
        self,
        ticker,
        screener,
        exchange,
        name=None,
        category=None,
        sector=None,
        industry=None,
        image_url=None,
    ):
        try:
            normalized_ticker = self.normalize_ticker(ticker)
            normalized_exchange = self.normalize_exchange(exchange)
            normalized_screener = self.normalize_screener(screener)

            stock, created = Stock.objects.get_or_create(
                ticker=normalized_ticker,
                exchange=normalized_exchange,
                screener=normalized_screener,
                defaults={
                    "name": name,
                    "category": category,
                    "sector": sector,
                    "industry": industry,
                    "image_url": image_url,
                },
            )

            if created:
                return {
                    "status": True,
                    "action": "created",
                    "stock": stock,
                }

            return {
                "status": True,
                "action": "duplicate",
                "stock": stock,
            }

        except Exception:
            logger.exception(
                "Failed to insert stock. ticker=%s, exchange=%s, screener=%s",
                ticker,
                exchange,
                screener,
            )
            return {
                "status": False,
                "action": "error",
                "stock": None,
            }

    def list_stocks(self): 
        return Stock.objects.all().order_by("ticker", "exchange", "screener")

    def get_stock(self, ticker, exchange, screener):
        return Stock.objects.filter(
            ticker=self.normalize_ticker(ticker),
            exchange=self.normalize_exchange(exchange),
            screener=self.normalize_screener(screener),
        ).first()

    def get_stock_by_ticker(self, ticker):
        return Stock.objects.filter(
            ticker=self.normalize_ticker(ticker)
        ).order_by("exchange", "screener")

    def create_stock_data(self, payload):
        try:
            StockData.objects.create(**payload)
            return True
        except Exception:
            logger.exception("Failed to create StockData")
            return False

    def get_previous_support_resistance_in_range(self, stock, support, resistance, current_price):
        return (
            StockData.objects.filter(
                stock=stock,
                support__lt=current_price,
                resistance__gt=current_price,
            )
            .exclude(support=support, resistance=resistance)
            .order_by("-date")
            .first()
        )

    def get_latest_stock_data(self, stock):
        return StockData.objects.filter(stock=stock).order_by("-date").first()
    
    def list_stock_data_by_ticker(self, ticker):
        normalized_ticker = self.normalize_ticker(ticker)

        return (
            StockData.objects.filter(stock__ticker=normalized_ticker)
            .select_related("stock")
            .order_by("stock__exchange", "stock__screener", "-date")
        )

    def get_latest_broken_support_resistance(self, stock, support, resistance):
        return (
            StockData.objects.filter(stock=stock)
            .exclude(support=support, resistance=resistance)
            .filter(support__isnull=False, resistance__isnull=False)
            .order_by("-date")
            .first()
        )

    def get_latest_stock_data_subquery(self):
        return (
            StockData.objects.filter(stock=OuterRef("stock"))
            .order_by("-date", "-id")
            .values("id")[:1]
        )

    def list_latest_stock_data(self, user=None):
        latest_stock_data_subquery = self.get_latest_stock_data_subquery()

        queryset = (
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

            queryset = queryset.annotate(
                wishlist=Case(
                    When(Exists(wishlist_subquery), then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            )
        else:
            queryset = queryset.annotate(
                wishlist=Value(0, output_field=IntegerField())
            )

        return queryset
    
    def update_stock_data(self, stock_data, payload):
        for field, value in payload.items():
            setattr(stock_data, field, value)
        stock_data.save()
        return stock_data
    
    def list_stocks_for_sync(self, max_batches=10, batch_size=10):
        limit = max_batches * batch_size

        return (
            Stock.objects.filter(in_use=True)
            .annotate(
                updated_at_isnull=Case(
                    When(updated_at__isnull=True, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                )
            )
            .order_by(
                "updated_at_isnull",
                "updated_at",
                "ticker",
                "exchange",
                "screener",
            )[:limit]
        )

    def touch_stock_updated_at(self, stock, updated_at=None):
        stock.updated_at = updated_at or timezone.now()
        stock.save(update_fields=["updated_at"])
        return stock

    def disable_stock(self, stock):
        stock.in_use = False
        stock.save(update_fields=["in_use"])
        return stock
    
    def reset_all_stocks_in_use(self):
        return Stock.objects.update(in_use=True)