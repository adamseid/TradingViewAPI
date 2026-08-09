import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, time as datetime_time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db.models import Case, F, IntegerField, Q, Value, When, Window
from django.db.models.functions import DenseRank, RowNumber, TruncDate
from django.utils import timezone
from tradingview_ta import Interval, TA_Handler, get_multiple_analysis

from api.models import Stock, StockData, SyncJobLock

logger = logging.getLogger(__name__)
MARKET_TIMEZONE = ZoneInfo("America/New_York")
MARKET_OPEN_TIME = datetime_time(hour=9, minute=30)
MARKET_CLOSE_TIME = datetime_time(hour=16, minute=0)
SYNC_JOB_LOCK_NAME = "token_data_sync"
NYSE_MARKET_HOLIDAYS = {
    date(2024, 1, 1),
    date(2024, 1, 15),
    date(2024, 2, 19),
    date(2024, 3, 29),
    date(2024, 5, 27),
    date(2024, 6, 19),
    date(2024, 7, 4),
    date(2024, 9, 2),
    date(2024, 11, 28),
    date(2024, 12, 25),
    date(2025, 1, 1),
    date(2025, 1, 20),
    date(2025, 2, 17),
    date(2025, 4, 18),
    date(2025, 5, 26),
    date(2025, 6, 19),
    date(2025, 7, 4),
    date(2025, 9, 1),
    date(2025, 11, 27),
    date(2025, 12, 25),
    date(2026, 1, 1),
    date(2026, 1, 19),
    date(2026, 2, 16),
    date(2026, 4, 3),
    date(2026, 5, 25),
    date(2026, 6, 19),
    date(2026, 7, 3),
    date(2026, 9, 7),
    date(2026, 11, 26),
    date(2026, 12, 25),
    date(2027, 1, 1),
    date(2027, 1, 18),
    date(2027, 2, 15),
    date(2027, 3, 26),
    date(2027, 5, 31),
    date(2027, 6, 18),
    date(2027, 7, 5),
    date(2027, 9, 6),
    date(2027, 11, 25),
    date(2027, 12, 24),
    date(2027, 12, 31),
    date(2028, 1, 17),
    date(2028, 2, 21),
    date(2028, 4, 14),
    date(2028, 5, 29),
    date(2028, 6, 19),
    date(2028, 7, 4),
    date(2028, 9, 4),
    date(2028, 11, 23),
    date(2028, 12, 25),
    date(2029, 1, 1),
    date(2029, 1, 15),
    date(2029, 2, 19),
    date(2029, 3, 30),
    date(2029, 5, 28),
    date(2029, 6, 19),
    date(2029, 7, 4),
    date(2029, 9, 3),
    date(2029, 11, 22),
    date(2029, 12, 25),
    date(2030, 1, 1),
    date(2030, 1, 21),
    date(2030, 2, 18),
    date(2030, 4, 19),
    date(2030, 5, 27),
    date(2030, 6, 19),
    date(2030, 7, 4),
    date(2030, 9, 2),
    date(2030, 11, 28),
    date(2030, 12, 25),
    date(2031, 1, 1),
    date(2031, 1, 20),
    date(2031, 2, 17),
    date(2031, 4, 11),
    date(2031, 5, 26),
    date(2031, 6, 19),
    date(2031, 7, 4),
    date(2031, 9, 1),
    date(2031, 11, 27),
    date(2031, 12, 25),
    date(2032, 1, 1),
    date(2032, 1, 19),
    date(2032, 2, 16),
    date(2032, 3, 26),
    date(2032, 5, 31),
    date(2032, 6, 18),
    date(2032, 7, 5),
    date(2032, 9, 6),
    date(2032, 11, 25),
    date(2032, 12, 24),
    date(2032, 12, 31),
}

DAILY_FIELD_MAP = {
    "recommend_all": "Recommend.All",
    "recommend_ma": "Recommend.MA",
    "recommend_other": "Recommend.Other",
    "rsi": "RSI",
    "yesterday_rsi": "RSI[1]",
    "stoch_k": "Stoch.K",
    "stoch_d": "Stoch.D",
    "yesterday_stoch_k": "Stoch.K[1]",
    "yesterday_stoch_d": "Stoch.D[1]",
    "commodity_channel_index": "CCI20",
    "yesterday_commodity_channel_index": "CCI20[1]",
    "adx": "ADX",
    "adx_di_positive": "ADX+DI",
    "adx_di_negative": "ADX-DI",
    "yesterday_adx_di_positive": "ADX+DI[1]",
    "yesterday_adx_di_negative": "ADX-DI[1]",
    "awesome_oscillator": "AO",
    "yesterday_awesome_oscillator": "AO[1]",
    "two_days_ago_awesome_oscillator": "AO[2]",
    "momentum": "Mom",
    "yesterday_momentum": "Mom[1]",
    "stoch_rsi": "Stoch.RSI.K",
    "stoch_rsi_k": "Stoch.RSI.K",
    "williams_r_recommendation": "Rec.WR",
    "williams_r": "W.R",
    "bollinger_bands_recommendation": "Rec.BBPower",
    "bollinger_bands_power": "BBPower",
    "bollinger_bands_lower": "BB.lower",
    "bollinger_bands_upper": "BB.upper",
    "ultimate_oscillator_recommendation": "Rec.UO",
    "ultimate_oscillator": "UO",
    "ema_5": "EMA5",
    "ema_10": "EMA10",
    "ema_20": "EMA20",
    "ema_30": "EMA30",
    "ema_50": "EMA50",
    "ema_100": "EMA100",
    "ema_200": "EMA200",
    "sma_5": "SMA5",
    "sma_10": "SMA10",
    "sma_20": "SMA20",
    "sma_30": "SMA30",
    "sma_50": "SMA50",
    "sma_100": "SMA100",
    "sma_200": "SMA200",
    "ichimoku_recommendation": "Rec.Ichimoku",
    "ichimoku_base_line": "Ichimoku.BLine",
    "volume_weighted_moving_average_recommendation": "Rec.VWMA",
    "volume_weighted_moving_average": "VWMA",
    "hull_moving_average_recommendation": "Rec.HullMA9",
    "hull_moving_average": "HullMA9",
    "pivot_classic_s3": "Pivot.M.Classic.S3",
    "pivot_classic_s2": "Pivot.M.Classic.S2",
    "pivot_classic_s1": "Pivot.M.Classic.S1",
    "pivot_classic_middle": "Pivot.M.Classic.Middle",
    "pivot_classic_r1": "Pivot.M.Classic.R1",
    "pivot_classic_r2": "Pivot.M.Classic.R2",
    "pivot_classic_r3": "Pivot.M.Classic.R3",
    "pivot_fibonacci_s3": "Pivot.M.Fibonacci.S3",
    "pivot_fibonacci_s2": "Pivot.M.Fibonacci.S2",
    "pivot_fibonacci_s1": "Pivot.M.Fibonacci.S1",
    "pivot_fibonacci_middle": "Pivot.M.Fibonacci.Middle",
    "pivot_fibonacci_r1": "Pivot.M.Fibonacci.R1",
    "pivot_fibonacci_r2": "Pivot.M.Fibonacci.R2",
    "pivot_fibonacci_r3": "Pivot.M.Fibonacci.R3",
    "pivot_camarilla_s3": "Pivot.M.Camarilla.S3",
    "pivot_camarilla_s2": "Pivot.M.Camarilla.S2",
    "pivot_camarilla_s1": "Pivot.M.Camarilla.S1",
    "pivot_camarilla_middle": "Pivot.M.Camarilla.Middle",
    "pivot_camarilla_r1": "Pivot.M.Camarilla.R1",
    "pivot_camarilla_r2": "Pivot.M.Camarilla.R2",
    "pivot_camarilla_r3": "Pivot.M.Camarilla.R3",
    "pivot_woodie_s3": "Pivot.M.Woodie.S3",
    "pivot_woodie_s2": "Pivot.M.Woodie.S2",
    "pivot_woodie_s1": "Pivot.M.Woodie.S1",
    "pivot_woodie_middle": "Pivot.M.Woodie.Middle",
    "pivot_woodie_r1": "Pivot.M.Woodie.R1",
    "pivot_woodie_r2": "Pivot.M.Woodie.R2",
    "pivot_woodie_r3": "Pivot.M.Woodie.R3",
    "pivot_demark_s1": "Pivot.M.Demark.S1",
    "pivot_demark_middle": "Pivot.M.Demark.Middle",
    "pivot_demark_r1": "Pivot.M.Demark.R1",
    "parabolic_sar": "P.SAR",
    "price_change": "change",
    "open": "open",
    "close": "close",
    "high": "high",
    "low": "low",
    "volume": "volume",
}

RATE_LIMIT_MARKERS = (
    "429",
    "rate limit",
    "too many requests",
)

RETRYABLE_ERROR_MARKERS = (
    *RATE_LIMIT_MARKERS,
    "timeout",
    "timed out",
    "connection reset",
    "temporarily unavailable",
    "expecting value: line 1 column 1 (char 0)",
)

RECENT_HISTORY_MARKET_DAYS = 20


@dataclass(frozen=True)
class SyncConfig:
    max_batches_per_run: int = 20
    delay_between_interval_requests_seconds: int = 45
    delay_between_batch_requests_seconds: int = 15
    delay_between_single_symbol_requests_seconds: int = 30
    max_batch_retries: int = 1
    max_single_retries: int = 1
    retry_delay_seconds: int = 30
    timeout: int | None = None


class Sync:
    def __init__(
        self,
        default_timeout=10,
        analysis_batch_size=10,
        proxies=None,
    ):
        self.default_timeout = default_timeout
        self.analysis_batch_size = analysis_batch_size
        self.proxies = proxies
        self.sync_config = SyncConfig()

    # Insert token data for stocks marked as in_use
    def insert_tokens_data(self):
        try:
            # Initialize batch size, limit, and fetch stocks for sync
            max_batches_per_run = self.sync_config.max_batches_per_run
            batch_size = self.analysis_batch_size
            limit = max_batches_per_run * batch_size

            # Check if the current time is within trading hours (9:30 AM to 4:00 PM EST) and if today is a market open day
            current_date = timezone.now()
            market_now = timezone.localtime(current_date, MARKET_TIMEZONE)
            market_date = market_now.date()
            market_time = market_now.time()
            is_market_open_day = (
                market_date.weekday() < 5 and market_date not in NYSE_MARKET_HOLIDAYS
            )
            is_trading_hours = (
                is_market_open_day and MARKET_OPEN_TIME <= market_time < MARKET_CLOSE_TIME
            )

            # Fetch stocks that are marked as in_use and order them by updated_at and other criteria
            stock_queryset = (
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
                )
            )

            if not is_trading_hours:
                stock_queryset = stock_queryset.filter(
                    Q(screener__iexact="crypto") | Q(updated_at__isnull=True) | Q(updated_at__lt=self._last_market_close_at(current_date))
                )

            stocks = list(stock_queryset[:limit])

            if not stocks:
                return {
                    "status": True,
                    "message": "No active stocks are due for sync.",
                    "data": {
                        "total_stocks_selected": 0,
                        "processed_batches": 0,
                        "successfully_fetched_count": 0,
                        "failed_fetched_count": 0,
                    },
                    "http_status": None,
                }

            recent_stock_data_by_stock_id = self._get_recent_stock_data_by_stock_id(stocks)

            # Initialize counters for tracking the number of successfully and failed fetched stocks,
            # as well as the number of processed batches
            successfully_fetched_count = 0
            failed_fetched_count = 0
            processed_batches = 0
            timeout = self.sync_config.timeout
            # Group stocks by screener to ensure that all stocks in a batch have the same screener
            stocks_by_screener = {}
            for stock in stocks:
                screener = str(stock.screener).lower()
                stocks_by_screener.setdefault(screener, []).append(stock)

            stop_processing = False

            for screener, screener_stocks in stocks_by_screener.items():
                
                # Split the stocks for the current screener into batches of the specified size
                screener_batches = [
                    screener_stocks[index:index + batch_size]
                    for index in range(0, len(screener_stocks), batch_size)
                ]

                for batch_index, stock_batch in enumerate(screener_batches, start=1):
                    if processed_batches >= max_batches_per_run:
                        stop_processing = True
                        break

                    current_date = timezone.now()
                    processed_batches += 1

                    try:
                        batch_symbols = [
                            f"{str(stock.exchange).upper()}:{str(stock.ticker).upper()}"
                            for stock in stock_batch
                        ]

                        print(
                            f"Processing screener={screener} "
                            f"batch {batch_index}/{len(screener_batches)} "
                            f"(run batch {processed_batches}/{max_batches_per_run}) "
                            f"with {len(stock_batch)} symbols: {batch_symbols}"
                        )

                        # Fetch daily batch analysis for the current stock batch
                        daily_batch_analysis = self._get_batch_analysis_with_retry(
                            stock_batch=stock_batch,
                            interval=Interval.INTERVAL_1_DAY,
                            timeout=timeout,
                            max_batch_retries=self.sync_config.max_batch_retries,
                            retry_delay_seconds=self.sync_config.retry_delay_seconds,
                        )

                        if self.sync_config.delay_between_interval_requests_seconds > 0:
                            time.sleep(self.sync_config.delay_between_interval_requests_seconds)

                        # Fetch weekly batch analysis for the current stock batch
                        weekly_batch_analysis = self._get_batch_analysis_with_retry(
                            stock_batch=stock_batch,
                            interval=Interval.INTERVAL_1_WEEK,
                            timeout=timeout,
                            max_batch_retries=self.sync_config.max_batch_retries,
                            retry_delay_seconds=self.sync_config.retry_delay_seconds,
                        )

                        # Process the successfully fetched batch and update the counters for successful and failed fetches
                        batch_success, batch_failed = self._process_successful_batch(
                            stock_batch=stock_batch,
                            daily_batch_analysis=daily_batch_analysis,
                            weekly_batch_analysis=weekly_batch_analysis,
                            current_date=current_date,
                            recent_stock_data_by_stock_id=recent_stock_data_by_stock_id,
                        )

                        successfully_fetched_count += batch_success
                        failed_fetched_count += batch_failed

                    except Exception as exc:
                        error_message = str(exc)

                        print(
                            f"Failed batch for screener={screener}, "
                            f"batch={batch_index}, size={len(stock_batch)}: {error_message}"
                        )

                        # If a rate limit error is detected, halt the batch sync and return an appropriate message
                        if any(
                            marker in (error_message or "").lower()
                            for marker in RATE_LIMIT_MARKERS
                        ):
                            print(
                                f"[RATE LIMITED] Batch sync halted for screener={screener}, "
                                f"batch={batch_index}, error={error_message}"
                            )
                            return {
                                "status": False,
                                "message": (
                                    f"Token data insertion aborted due to rate limit. "
                                    f"Processed batches: {processed_batches}/{max_batches_per_run}. "
                                    f"Successful: {successfully_fetched_count}, "
                                    f"Failed: {failed_fetched_count}. "
                                    f"Last error: {error_message}"
                                ),
                                "data": {
                                    "total_stocks_selected": len(stocks),
                                    "processed_batches": processed_batches,
                                    "max_batches_per_run": max_batches_per_run,
                                    "successfully_fetched_count": successfully_fetched_count,
                                    "failed_fetched_count": failed_fetched_count,
                                    "aborted_due_to_rate_limit": True,
                                    "last_error": error_message,
                                },
                                "http_status": None,
                            }

                        # If the batch fetch fails, attempt to fallback to single-symbol fetches for each stock in the batch
                        fallback_success, fallback_failed, aborted_due_to_rate_limit = self._fallback_batch_to_single(
                            stock_batch=stock_batch,
                            current_date=current_date,
                            original_batch_error=error_message,
                            timeout=timeout,
                            delay_between_interval_requests_seconds=self.sync_config.delay_between_interval_requests_seconds,
                            delay_between_single_symbol_requests_seconds=self.sync_config.delay_between_single_symbol_requests_seconds,
                            max_single_retries=self.sync_config.max_single_retries,
                            retry_delay_seconds=self.sync_config.retry_delay_seconds,
                            recent_stock_data_by_stock_id=recent_stock_data_by_stock_id,
                        )

                        successfully_fetched_count += fallback_success
                        failed_fetched_count += fallback_failed

                        # Aborted due to rate limit during single-symbol fallback
                        if aborted_due_to_rate_limit:
                            return {
                                "status": False,
                                "message": (
                                    f"Token data insertion aborted due to rate limit during single-symbol fallback. "
                                    f"Processed batches: {processed_batches}/{max_batches_per_run}. "
                                    f"Successful: {successfully_fetched_count}, "
                                    f"Failed: {failed_fetched_count}."
                                ),
                                "data": {
                                    "total_stocks_selected": len(stocks),
                                    "processed_batches": processed_batches,
                                    "max_batches_per_run": max_batches_per_run,
                                    "successfully_fetched_count": successfully_fetched_count,
                                    "failed_fetched_count": failed_fetched_count,
                                    "aborted_due_to_rate_limit": True,
                                    "last_error": error_message,
                                },
                                "http_status": None,
                            }

                    if processed_batches < max_batches_per_run:
                        time.sleep(self.sync_config.delay_between_batch_requests_seconds)

                if stop_processing:
                    break

            return {
                "status": True,
                "message": (
                    f"Token data insertion completed. "
                    f"Selected: {len(stocks)}, "
                    f"Processed batches: {processed_batches}/{max_batches_per_run}, "
                    f"Successful: {successfully_fetched_count}, "
                    f"Failed: {failed_fetched_count}"
                ),
                "data": {
                    "total_stocks_selected": len(stocks),
                    "processed_batches": processed_batches,
                    "max_batches_per_run": max_batches_per_run,
                    "successfully_fetched_count": successfully_fetched_count,
                    "failed_fetched_count": failed_fetched_count,
                },
                "http_status": None,
            }

        except Exception as exc:
            return {
                "status": False,
                "message": f"Failed to insert token data: {str(exc)}",
                "data": None,
                "http_status": None,
            }

    # Get the sync status
    def get_sync_status(self):
        lock = SyncJobLock.objects.filter(name=SYNC_JOB_LOCK_NAME).first()

        return {
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
            "http_status": 200,
        }

    # Reset all stocks in_use flag to True
    def reset_all_stocks_in_use(self):
        try:
            updated_count = Stock.objects.update(in_use=True)

            return {
                "status": True,
                "message": f"Reset in_use=True for {updated_count} stocks.",
                "data": {"updated_count": updated_count},
                "http_status": None,
            }
        except Exception as exc:
            return {
                "status": False,
                "message": f"Failed to reset stocks in_use flag: {str(exc)}",
                "data": None,
                "http_status": None,
            }

    def recalculate_scores(self, score):
        valid_scores = {
            "original_strategy_score",
            "macd_strategy_score",
            "strategy_three_score",
        }

        if score not in valid_scores:
            return {
                "status": False,
                "message": (
                    f"Invalid score '{score}'. Expected one of: "
                    "original_strategy_score, macd_strategy_score, strategy_three_score."
                ),
                "data": None,
                "http_status": 400,
            }

        try:
            stock_data_rows = list(
                StockData.objects.order_by("stock_id", "date", "id")
            )

            if not stock_data_rows:
                return {
                    "status": True,
                    "message": "No stock data rows found to recalculate.",
                    "data": {"updated_count": 0, "score": score},
                    "http_status": 200,
                }

            recent_macd_history_by_stock_id = {}

            fields_to_update = [
                "support_resistance_score",
                "ma_100d_score",
                "ma_200d_score",
                "ma_50d_score",
                "daily_macd_score",
                "weekly_macd_score",
                score,
            ]

            for stock_data in stock_data_rows:
                recalculated_values = self._build_recalculated_score_values(
                    stock_data=stock_data,
                    previous_stock_data=recent_macd_history_by_stock_id.get(stock_data.stock_id, []),
                )

                stock_data.support_resistance_score = recalculated_values["support_resistance_score"]
                stock_data.ma_100d_score = recalculated_values["ma_100d_score"]
                stock_data.ma_200d_score = recalculated_values["ma_200d_score"]
                stock_data.ma_50d_score = recalculated_values["ma_50d_score"]
                stock_data.daily_macd_score = recalculated_values["daily_macd_score"]
                stock_data.weekly_macd_score = recalculated_values["weekly_macd_score"]

                if score == "original_strategy_score":
                    stock_data.original_strategy_score = recalculated_values["original_strategy_score"]
                elif score == "macd_strategy_score":
                    stock_data.macd_strategy_score = recalculated_values["macd_strategy_score"]
                else:
                    stock_data.strategy_three_score = recalculated_values["strategy_three_score"]

                recent_macd_history = recent_macd_history_by_stock_id.setdefault(stock_data.stock_id, [])
                recent_macd_history.append(self._build_history_snapshot(stock_data))
                recent_macd_history_by_stock_id[stock_data.stock_id] = self._limit_recent_history_to_market_days(
                    recent_macd_history,
                    RECENT_HISTORY_MARKET_DAYS,
                )

            StockData.objects.bulk_update(
                stock_data_rows,
                fields_to_update,
                batch_size=1000,
            )

            return {
                "status": True,
                "message": f"Recalculated {score} for {len(stock_data_rows)} stock data rows.",
                "data": {
                    "updated_count": len(stock_data_rows),
                    "score": score,
                    "updated_fields": fields_to_update,
                },
                "http_status": 200,
            }
        except Exception as exc:
            return {
                "status": False,
                "message": f"Failed to recalculate {score}: {str(exc)}",
                "data": None,
                "http_status": None,
            }

    # ***************
    # *   Private   *
    # ***************
            
    # Process a successful batch 
    def _process_successful_batch(
        self,
        stock_batch,
        daily_batch_analysis,
        weekly_batch_analysis,
        current_date,
        recent_stock_data_by_stock_id,
    ):
        success_count = 0
        failed_count = 0

        for stock in stock_batch:
            symbol_key = f"{str(stock.exchange).upper()}:{str(stock.ticker).upper()}"

            daily_stock_analysis = daily_batch_analysis.get(symbol_key)
            weekly_stock_analysis = weekly_batch_analysis.get(symbol_key)

            if daily_stock_analysis is None or weekly_stock_analysis is None:
                reason = (
                    "missing analysis from successful batch. "
                    f"daily_found={daily_stock_analysis is not None}, "
                    f"weekly_found={weekly_stock_analysis is not None}"
                )
                print(
                    f"[BAD SYMBOL] {symbol_key} {reason}"
                )

                try:
                    if daily_stock_analysis is None:
                        daily_stock_analysis = self._get_single_analysis_with_retry(
                            stock=stock,
                            interval=Interval.INTERVAL_1_DAY,
                            timeout=self.sync_config.timeout,
                            max_single_retries=self.sync_config.max_single_retries,
                            retry_delay_seconds=self.sync_config.retry_delay_seconds,
                        )

                    if (
                        weekly_stock_analysis is None
                        and self.sync_config.delay_between_interval_requests_seconds > 0
                    ):
                        time.sleep(self.sync_config.delay_between_interval_requests_seconds)

                    if weekly_stock_analysis is None:
                        weekly_stock_analysis = self._get_single_analysis_with_retry(
                            stock=stock,
                            interval=Interval.INTERVAL_1_WEEK,
                            timeout=self.sync_config.timeout,
                            max_single_retries=self.sync_config.max_single_retries,
                            retry_delay_seconds=self.sync_config.retry_delay_seconds,
                        )
                except Exception as exc:
                    failed_count += 1
                    self._disable_stock_for_sync_failure(
                        stock,
                        f"{reason}; single-symbol recovery failed: {str(exc)}",
                    )
                    continue

            created, failed_increment = self._create_stock_data_from_analysis(
                stock=stock,
                daily_stock_analysis=daily_stock_analysis,
                weekly_stock_analysis=weekly_stock_analysis,
                current_date=current_date,
                recent_stock_data=recent_stock_data_by_stock_id.get(stock.id, []),
                disable_on_failure=True,
            )

            if created:
                success_count += 1
            failed_count += failed_increment

        return success_count, failed_count

    # Fallback batch to single-symbol mode
    def _fallback_batch_to_single(
        self,
        stock_batch,
        current_date,
        original_batch_error,
        timeout,
        delay_between_interval_requests_seconds,
        delay_between_single_symbol_requests_seconds,
        max_single_retries,
        retry_delay_seconds,
        recent_stock_data_by_stock_id,
    ):
        success_count = 0
        failed_count = 0

        print(
            f"[FALLBACK] switching failed batch to single-symbol mode. "
            f"screener={stock_batch[0].screener} size={len(stock_batch)} "
            f"error={original_batch_error}"
        )

        for index, stock in enumerate(stock_batch, start=1):
            symbol_key = f"{str(stock.exchange).upper()}:{str(stock.ticker).upper()}"

            try:
                print(
                    f"[FALLBACK] processing symbol {index}/{len(stock_batch)} "
                    f"{symbol_key}"
                )

                time.sleep(delay_between_interval_requests_seconds)

                daily_stock_analysis = self._get_single_analysis_with_retry(
                    stock=stock,
                    interval=Interval.INTERVAL_1_DAY,
                    timeout=timeout,
                    max_single_retries=max_single_retries,
                    retry_delay_seconds=retry_delay_seconds,
                )

                time.sleep(delay_between_interval_requests_seconds)

                weekly_stock_analysis = self._get_single_analysis_with_retry(
                    stock=stock,
                    interval=Interval.INTERVAL_1_WEEK,
                    timeout=timeout,
                    max_single_retries=max_single_retries,
                    retry_delay_seconds=retry_delay_seconds,
                )

                created, failed_increment = self._create_stock_data_from_analysis(
                    stock=stock,
                    daily_stock_analysis=daily_stock_analysis,
                    weekly_stock_analysis=weekly_stock_analysis,
                    current_date=current_date,
                    recent_stock_data=recent_stock_data_by_stock_id.get(stock.id, []),
                )

                if created:
                    success_count += 1
                failed_count += failed_increment

            except Exception as exc:
                failed_count += 1
                error_message = str(exc)

                if any(
                    marker in (error_message or "").lower()
                    for marker in RATE_LIMIT_MARKERS
                ):
                    print(
                        f"[RATE LIMITED] {symbol_key} single-symbol fallback hit a rate-limit error. "
                        f"Stopping all remaining sync work for this run. "
                        f"error={error_message}"
                    )
                    return success_count, failed_count, True

                self._disable_stock_for_sync_failure(
                    stock,
                    f"single-symbol fallback failure: {error_message}",
                )

            if index < len(stock_batch):
                time.sleep(delay_between_single_symbol_requests_seconds)

        return success_count, failed_count, False  
    
    # Get single analysis with retry
    def _get_single_analysis_with_retry(
        self,
        stock,
        interval,
        timeout,
        max_single_retries,
        retry_delay_seconds,
    ):
        symbol_key = f"{str(stock.exchange).upper()}:{str(stock.ticker).upper()}"
        delay = retry_delay_seconds

        for attempt in range(max_single_retries):
            try:
                return self._get_analysis(
                    ticker=stock.ticker,
                    exchange=stock.exchange,
                    screener=stock.screener,
                    interval=interval,
                    timeout=timeout,
                )
            except Exception as exc:
                error_message = str(exc)

                if (
                    any(marker in (error_message or "").lower() for marker in RETRYABLE_ERROR_MARKERS)
                    and attempt < max_single_retries - 1
                ):
                    print(
                        f"[SINGLE RETRY] symbol={symbol_key} "
                        f"interval={interval} "
                        f"attempt={attempt + 1}/{max_single_retries} "
                        f"sleeping={delay}s error={error_message}"
                    )
                    time.sleep(delay)
                    delay *= 2
                    continue

                print(
                    f"[BAD SYMBOL] {symbol_key} failed single fetch "
                    f"interval={interval} error={error_message}"
                )
                raise

    # Create stock data from analysis
    def _create_stock_data_from_analysis(
        self,
        stock,
        daily_stock_analysis,
        weekly_stock_analysis,
        current_date,
        recent_stock_data,
        disable_on_failure=False,
    ):
        symbol_key = f"{str(stock.exchange).upper()}:{str(stock.ticker).upper()}"

        try:
            missing_daily, missing_weekly = self._get_missing_required_indicators(
                daily_stock_analysis=daily_stock_analysis,
                weekly_stock_analysis=weekly_stock_analysis,
            )

            if missing_daily or missing_weekly:
                reason = (
                    f"missing indicators daily={missing_daily or '[]'} "
                    f"weekly={missing_weekly or '[]'}"
                )
                print(
                    f"[BAD SYMBOL] {symbol_key} missing required indicators. {reason}"
                )
                if disable_on_failure:
                    self._disable_stock_for_sync_failure(stock, reason)
                return False, 1

            payload = self._build_stock_data_score_payload(
                daily_stock_analysis=daily_stock_analysis,
                weekly_stock_analysis=weekly_stock_analysis,
                current_date=current_date,
                support=daily_stock_analysis.indicators.get("Pivot.M.Classic.S1"),
                resistance=daily_stock_analysis.indicators.get("Pivot.M.Classic.R1"),
                stock=stock,
                recent_stock_data=recent_stock_data,
            )

            for model_field, indicator_key in DAILY_FIELD_MAP.items():
                payload[model_field] = daily_stock_analysis.indicators.get(indicator_key)

            try:
                StockData.objects.create(**payload)
                success = True
            except Exception:
                logger.exception("Failed to create StockData")
                success = False

            if success:
                stock.updated_at = current_date or timezone.now()
                stock.save(update_fields=["updated_at"])
                return True, 0

            print(f"[BAD SYMBOL] {symbol_key} failed create_stock_data(.)")
            if disable_on_failure:
                self._disable_stock_for_sync_failure(
                    stock,
                    "create_stock_data returned False",
                )
            return False, 1

        except Exception as exc:
            print(f"[BAD SYMBOL] {symbol_key} failed to create StockData: {str(exc)}")
            if disable_on_failure:
                self._disable_stock_for_sync_failure(stock, str(exc))
            return False, 1
    
    # Build stock data score payload
    def _build_stock_data_score_payload(
        self,
        daily_stock_analysis,
        weekly_stock_analysis,
        current_date,
        support,
        resistance,
        stock,
        recent_stock_data,
    ):
        prev_stock_data = recent_stock_data[0] if recent_stock_data else None
        current_price = daily_stock_analysis.indicators["close"]

        support_resistance_score = self._get_support_resistance_score(
            support,
            resistance,
            current_price
        )

        ma_100d_score = self._get_ma_score(
            daily_stock_analysis.indicators["SMA100"],
            current_price,
        )
        ma_200d_score = self._get_ma_score(
            daily_stock_analysis.indicators["SMA200"],
            current_price,
        )
        ma_50d_score = self._get_ma_score(
            daily_stock_analysis.indicators["SMA50"],
            current_price,
        )

        daily_macd_line = daily_stock_analysis.indicators.get("MACD.macd")
        daily_macd_signal = daily_stock_analysis.indicators.get("MACD.signal")
        weekly_macd_line = weekly_stock_analysis.indicators.get("MACD.macd")
        weekly_macd_signal = weekly_stock_analysis.indicators.get("MACD.signal")

        daily_macd_histogram = daily_macd_line - daily_macd_signal
        weekly_macd_histogram = weekly_macd_line - weekly_macd_signal

        daily_macd_velocity = None
        weekly_macd_velocity = None
        daily_macd_score = None
        weekly_macd_score = None
        original_strategy_score = None
        macd_strategy_score = None
        strategy_three_score = None

        if prev_stock_data is not None:
            daily_macd_velocity = self._get_macd_velocity(
                daily_macd_histogram,
                prev_stock_data.get("daily_macd_histogram"),
            )
            weekly_macd_velocity = self._get_macd_velocity(
                weekly_macd_histogram,
                prev_stock_data.get("weekly_macd_histogram"),
            )
            daily_macd_score = self._get_macd_score(
                daily_macd_histogram,
                daily_macd_velocity,
            )
            weekly_macd_score = self._get_macd_score(
                weekly_macd_histogram,
                weekly_macd_velocity,
            )

            raw_original_strategy_score = self._calculate_original_strategy_score(
                support_resistance_score=support_resistance_score,
                ma_50d_score=ma_50d_score,
                ma_100d_score=ma_100d_score,
                ma_200d_score=ma_200d_score,
                daily_macd_score=daily_macd_score,
                weekly_macd_score=weekly_macd_score,
            )

            raw_macd_strategy_score = self._calculate_macd_strategy_score(
                current_date,
                recent_stock_data,
                daily_macd_histogram,
                weekly_macd_histogram,
                daily_macd_velocity,
                weekly_macd_velocity,
            )

            original_strategy_score = self._normalizeScore(raw_original_strategy_score, -9, 9)
            macd_strategy_score = self._normalizeScore(raw_macd_strategy_score, -4, 4)

        strategy_three_regime = self._detect_market_regime(
            recent_stock_data=recent_stock_data,
            current_price=current_price,
            adx=daily_stock_analysis.indicators.get("ADX"),
            daily_macd_histogram=daily_macd_histogram,
            weekly_macd_histogram=weekly_macd_histogram,
            ema_20=daily_stock_analysis.indicators.get("EMA20"),
            ema_50=daily_stock_analysis.indicators.get("EMA50"),
            ema_100=daily_stock_analysis.indicators.get("EMA100"),
            bollinger_bands_lower=daily_stock_analysis.indicators.get("BB.lower"),
            bollinger_bands_upper=daily_stock_analysis.indicators.get("BB.upper"),
        )
        raw_strategy_three_score = self._calculate_strategy_three_score(
            recent_stock_data=recent_stock_data,
            current_price=current_price,
            support=support,
            resistance=resistance,
            pivot_classic_middle=daily_stock_analysis.indicators.get("Pivot.M.Classic.Middle"),
            pivot_classic_s2=daily_stock_analysis.indicators.get("Pivot.M.Classic.S2"),
            pivot_classic_s3=daily_stock_analysis.indicators.get("Pivot.M.Classic.S3"),
            pivot_classic_r2=daily_stock_analysis.indicators.get("Pivot.M.Classic.R2"),
            pivot_classic_r3=daily_stock_analysis.indicators.get("Pivot.M.Classic.R3"),
            daily_macd_histogram=daily_macd_histogram,
            weekly_macd_histogram=weekly_macd_histogram,
            daily_macd_velocity=daily_macd_velocity,
            weekly_macd_velocity=weekly_macd_velocity,
            rsi=daily_stock_analysis.indicators.get("RSI"),
            yesterday_rsi=daily_stock_analysis.indicators.get("RSI[1]"),
            stoch_rsi_k=daily_stock_analysis.indicators.get("Stoch.RSI.K"),
            adx=daily_stock_analysis.indicators.get("ADX"),
            adx_di_positive=daily_stock_analysis.indicators.get("ADX+DI"),
            adx_di_negative=daily_stock_analysis.indicators.get("ADX-DI"),
            ema_20=daily_stock_analysis.indicators.get("EMA20"),
            ema_50=daily_stock_analysis.indicators.get("EMA50"),
            ema_100=daily_stock_analysis.indicators.get("EMA100"),
            ema_200=daily_stock_analysis.indicators.get("EMA200"),
            bollinger_bands_lower=daily_stock_analysis.indicators.get("BB.lower"),
            bollinger_bands_upper=daily_stock_analysis.indicators.get("BB.upper"),
        )
        strategy_three_minimum, strategy_three_maximum = self._get_strategy_three_score_bounds(
            strategy_three_regime
        )
        strategy_three_score = self._normalizeScore(
            raw_strategy_three_score,
            strategy_three_minimum,
            strategy_three_maximum,
        )

        payload = {
            "date": current_date,
            "daily_macd_line": daily_macd_line,
            "daily_macd_signal": daily_macd_signal,
            "daily_macd_histogram": daily_macd_histogram,
            "weekly_macd_line": weekly_macd_line,
            "weekly_macd_signal": weekly_macd_signal,
            "weekly_macd_histogram": weekly_macd_histogram,
            "support": support,
            "resistance": resistance,
            "current_price": current_price,
            "support_resistance_score": support_resistance_score,
            "ma_100d_score": ma_100d_score,
            "ma_200d_score": ma_200d_score,
            "ma_50d_score": ma_50d_score,
            "daily_macd_velocity": daily_macd_velocity,
            "daily_macd_score": daily_macd_score,
            "weekly_macd_velocity": weekly_macd_velocity,
            "weekly_macd_score": weekly_macd_score,
            "original_strategy_score": original_strategy_score,
            "macd_strategy_score": macd_strategy_score,
            "strategy_three_score": strategy_three_score,
            "stock": stock,
        }

        return payload
    
    # Get the last market close time
    def _last_market_close_at(self, current_date=None):
        current_date = current_date or timezone.now()
        market_now = timezone.localtime(current_date, MARKET_TIMEZONE)
        market_date = market_now.date()
        market_time = market_now.time()
        is_market_open_day = (
            market_date.weekday() < 5 and market_date not in NYSE_MARKET_HOLIDAYS
        )

        if is_market_open_day and market_time >= MARKET_CLOSE_TIME:
            close_date = market_date
        else:
            close_date = market_date - timedelta(days=1)
            while close_date.weekday() >= 5 or close_date in NYSE_MARKET_HOLIDAYS:
                close_date -= timedelta(days=1)

        return timezone.make_aware(
            datetime.combine(close_date, MARKET_CLOSE_TIME),
            MARKET_TIMEZONE,
        )

    # Get recent stock data by stock ID
    def _get_recent_stock_data_by_stock_id(self, stocks):
        stock_ids = [stock.id for stock in stocks]

        if not stock_ids:
            return {}

        recent_stock_data_by_stock_id = {}
        recent_stock_data = (
            StockData.objects.filter(stock_id__in=stock_ids)
            .annotate(
                market_day=TruncDate("date", tzinfo=MARKET_TIMEZONE),
                day_rank=Window(
                    expression=DenseRank(),
                    partition_by=[F("stock_id")],
                    order_by=[F("market_day").desc()],
                ),
                row_number=Window(
                    expression=RowNumber(),
                    partition_by=[F("stock_id")],
                    order_by=[F("date").desc(), F("id").desc()],
                )
            )
            .filter(day_rank__lte=RECENT_HISTORY_MARKET_DAYS)
            .order_by("stock_id", "-market_day", "row_number")
        )

        for stock_data in recent_stock_data:
            recent_stock_data_by_stock_id.setdefault(stock_data.stock_id, []).append(
                self._build_history_snapshot(stock_data)
            )

        return recent_stock_data_by_stock_id
    
    # Disable stock for sync failure
    def _disable_stock_for_sync_failure(self, stock, reason, log_prefix="[BAD SYMBOL]"):
        symbol_key = f"{str(stock.exchange).upper()}:{str(stock.ticker).upper()}"

        if not stock.in_use:
            changed = False
        else:
            stock.in_use = False
            stock.save(update_fields=["in_use"])
            logger.warning(
                "Stock disabled for sync. stock_id=%s symbol=%s:%s screener=%s",
                stock.id,
                stock.exchange,
                stock.ticker,
                stock.screener,
            )
            changed = True

        if changed:
            print(f"{log_prefix} {symbol_key} in_use set to False. reason={reason}")
        else:
            print(f"{log_prefix} {symbol_key} already disabled. reason={reason}")

    # **************************
    # *   Trading-view Calls   *
    # **************************
    
    # Get analysis for a single stock
    def _get_analysis(self, ticker, exchange, screener, interval, timeout=None):
        handler = TA_Handler(
            symbol=ticker,
            exchange=exchange,
            screener=screener,
            interval=interval,
            timeout=timeout if timeout is not None else self.default_timeout,
            proxies=self.proxies,
        )

        try:
            return handler.get_analysis()
        except Exception as exc:
            raise RuntimeError(f"Error when fetching {ticker}: {str(exc)}") from exc
    
    # Conduct batch analysis with retry 
    def _get_batch_analysis_with_retry(
        self,
        stock_batch,
        interval,
        timeout,
        max_batch_retries,
        retry_delay_seconds,
    ):
        delay = retry_delay_seconds
        screener = str(stock_batch[0].screener).lower() if stock_batch else None

        if not stock_batch:
            return {}

        symbols = [
            f"{str(stock.exchange).upper()}:{str(stock.ticker).upper()}"
            for stock in stock_batch
        ]

        for attempt in range(max_batch_retries):
            try:
                return get_multiple_analysis(
                    screener=screener,
                    interval=interval,
                    symbols=symbols,
                    timeout=timeout if timeout is not None else self.default_timeout,
                    proxies=self.proxies,
                )
            except Exception as exc:
                error_message = (
                    f"Error when batch fetching {len(symbols)} symbols "
                    f"for screener={screener}, interval={interval}: {str(exc)}"
                )

                if (
                    any(marker in (error_message or "").lower() for marker in RETRYABLE_ERROR_MARKERS)
                    and attempt < max_batch_retries - 1
                ):
                    print(
                        f"[BATCH RETRY] screener={stock_batch[0].screener} "
                        f"interval={interval} size={len(stock_batch)} "
                        f"attempt={attempt + 1}/{max_batch_retries} "
                        f"sleeping={delay}s error={error_message}"
                    )
                    time.sleep(delay)
                    delay *= 2
                    continue

                raise RuntimeError(error_message) from exc

    # ****************
    # *  Calculation *
    # ****************

    def _get_support_resistance_score(self, support, resistance, price):
        if support is None or resistance is None or price is None:
            return 0

        if price > resistance:
            return 2
        if price < support:
            return -2

        return 0

    def _get_ma_score(self, ma, price):
        if ma is None or price is None:
            return 0
        if price > ma:
            return 1
        if price < ma:
            return -1
        return 0

    def _get_missing_required_indicators(self, daily_stock_analysis, weekly_stock_analysis):
        required_daily_indicators = {
            "Pivot.M.Classic.S1": daily_stock_analysis.indicators.get("Pivot.M.Classic.S1"),
            "Pivot.M.Classic.R1": daily_stock_analysis.indicators.get("Pivot.M.Classic.R1"),
            "MACD.macd": daily_stock_analysis.indicators.get("MACD.macd"),
            "MACD.signal": daily_stock_analysis.indicators.get("MACD.signal"),
        }
        required_weekly_indicators = {
            "MACD.macd": weekly_stock_analysis.indicators.get("MACD.macd"),
            "MACD.signal": weekly_stock_analysis.indicators.get("MACD.signal"),
        }

        missing_daily = [
            indicator_key
            for indicator_key, value in required_daily_indicators.items()
            if value is None
        ]
        missing_weekly = [
            indicator_key
            for indicator_key, value in required_weekly_indicators.items()
            if value is None
        ]

        return missing_daily, missing_weekly

    def _build_recalculated_score_values(
        self,
        stock_data,
        previous_stock_data,
    ):
        support_resistance_score = self._get_support_resistance_score(
            stock_data.support,
            stock_data.resistance,
            stock_data.current_price,
        )
        ma_100d_score = self._get_ma_score(stock_data.sma_100, stock_data.current_price)
        ma_200d_score = self._get_ma_score(stock_data.sma_200, stock_data.current_price)
        ma_50d_score = self._get_ma_score(stock_data.sma_50, stock_data.current_price)

        daily_macd_score = self._get_macd_score(
            stock_data.daily_macd_histogram,
            stock_data.daily_macd_velocity,
        )
        weekly_macd_score = self._get_macd_score(
            stock_data.weekly_macd_histogram,
            stock_data.weekly_macd_velocity,
        )

        raw_original_strategy_score = self._calculate_original_strategy_score(
            support_resistance_score=support_resistance_score,
            ma_50d_score=ma_50d_score,
            ma_100d_score=ma_100d_score,
            ma_200d_score=ma_200d_score,
            daily_macd_score=daily_macd_score,
            weekly_macd_score=weekly_macd_score,
        )

        raw_macd_strategy_score = self._calculate_macd_strategy_score(
            stock_data.date,
            previous_stock_data,
            stock_data.daily_macd_histogram,
            stock_data.weekly_macd_histogram,
            stock_data.daily_macd_velocity,
            stock_data.weekly_macd_velocity,
        )
        strategy_three_regime = self._detect_market_regime(
            recent_stock_data=previous_stock_data,
            current_price=stock_data.current_price,
            adx=stock_data.adx,
            daily_macd_histogram=stock_data.daily_macd_histogram,
            weekly_macd_histogram=stock_data.weekly_macd_histogram,
            ema_20=stock_data.ema_20,
            ema_50=stock_data.ema_50,
            ema_100=stock_data.ema_100,
            bollinger_bands_lower=stock_data.bollinger_bands_lower,
            bollinger_bands_upper=stock_data.bollinger_bands_upper,
        )
        raw_strategy_three_score = self._calculate_strategy_three_score(
            recent_stock_data=previous_stock_data,
            current_price=stock_data.current_price,
            support=stock_data.support,
            resistance=stock_data.resistance,
            pivot_classic_middle=stock_data.pivot_classic_middle,
            pivot_classic_s2=stock_data.pivot_classic_s2,
            pivot_classic_s3=stock_data.pivot_classic_s3,
            pivot_classic_r2=stock_data.pivot_classic_r2,
            pivot_classic_r3=stock_data.pivot_classic_r3,
            daily_macd_histogram=stock_data.daily_macd_histogram,
            weekly_macd_histogram=stock_data.weekly_macd_histogram,
            daily_macd_velocity=stock_data.daily_macd_velocity,
            weekly_macd_velocity=stock_data.weekly_macd_velocity,
            rsi=stock_data.rsi,
            yesterday_rsi=stock_data.yesterday_rsi,
            stoch_rsi_k=stock_data.stoch_rsi_k,
            adx=stock_data.adx,
            adx_di_positive=stock_data.adx_di_positive,
            adx_di_negative=stock_data.adx_di_negative,
            ema_20=stock_data.ema_20,
            ema_50=stock_data.ema_50,
            ema_100=stock_data.ema_100,
            ema_200=stock_data.ema_200,
            bollinger_bands_lower=stock_data.bollinger_bands_lower,
            bollinger_bands_upper=stock_data.bollinger_bands_upper,
        )

        original_strategy_score = self._normalizeScore(raw_original_strategy_score, -9, 9)
        macd_strategy_score = self._normalizeScore(raw_macd_strategy_score, -4, 4)
        strategy_three_minimum, strategy_three_maximum = self._get_strategy_three_score_bounds(
            strategy_three_regime
        )
        strategy_three_score = self._normalizeScore(
            raw_strategy_three_score,
            strategy_three_minimum,
            strategy_three_maximum,
        )

        return {
            "support_resistance_score": support_resistance_score,
            "ma_100d_score": ma_100d_score,
            "ma_200d_score": ma_200d_score,
            "ma_50d_score": ma_50d_score,
            "daily_macd_score": daily_macd_score,
            "weekly_macd_score": weekly_macd_score,
            "original_strategy_score": original_strategy_score,
            "macd_strategy_score": macd_strategy_score,
            "strategy_three_score": strategy_three_score,
        }

    def _get_macd_velocity(self, macd, previous_macd):
        if macd is None or previous_macd is None:
            return 0
        return float(macd) - float(previous_macd)

    def _get_macd_score(self, macd, macd_velocity):
        if macd is None or macd_velocity is None:
            return 0
        if float(macd) > 0 and macd_velocity > 0:
            return 2
        if float(macd) < 0 and macd_velocity < 0:
            return -2
        return 0

    def _calculate_original_strategy_score(
        self,
        support_resistance_score,
        ma_50d_score,
        ma_100d_score,
        ma_200d_score,
        daily_macd_score,
        weekly_macd_score,
    ):
        return (
            support_resistance_score
            + ma_50d_score
            + ma_100d_score
            + ma_200d_score
            + daily_macd_score
            + weekly_macd_score
        )

    def _normalizeScore(self, score, minimum, maximum):
        if score is None:
            return None

        minimum_decimal = Decimal(str(minimum))
        maximum_decimal = Decimal(str(maximum))

        if maximum_decimal == minimum_decimal:
            return None

        normalized_score = ((Decimal(str(score)) - minimum_decimal) / (maximum_decimal - minimum_decimal)) * Decimal("100")

        if normalized_score < Decimal("0"):
            return Decimal("0")
        if normalized_score > Decimal("100"):
            return Decimal("100")

        return normalized_score

    def _to_decimal(self, value):
        if value is None:
            return None

        try:
            return Decimal(str(value))
        except Exception:
            return None

    def _build_history_snapshot(self, stock_data):
        return {
            "date": stock_data.date,
            "current_price": stock_data.current_price,
            "support": stock_data.support,
            "resistance": stock_data.resistance,
            "pivot_classic_middle": stock_data.pivot_classic_middle,
            "pivot_classic_s2": stock_data.pivot_classic_s2,
            "pivot_classic_s3": stock_data.pivot_classic_s3,
            "pivot_classic_r2": stock_data.pivot_classic_r2,
            "pivot_classic_r3": stock_data.pivot_classic_r3,
            "rsi": stock_data.rsi,
            "stoch_rsi_k": stock_data.stoch_rsi_k,
            "adx": stock_data.adx,
            "adx_di_positive": stock_data.adx_di_positive,
            "adx_di_negative": stock_data.adx_di_negative,
            "ema_20": stock_data.ema_20,
            "ema_50": stock_data.ema_50,
            "ema_100": stock_data.ema_100,
            "ema_200": stock_data.ema_200,
            "bollinger_bands_lower": stock_data.bollinger_bands_lower,
            "bollinger_bands_upper": stock_data.bollinger_bands_upper,
            "daily_macd_histogram": stock_data.daily_macd_histogram,
            "weekly_macd_histogram": stock_data.weekly_macd_histogram,
            "daily_macd_velocity": stock_data.daily_macd_velocity,
            "weekly_macd_velocity": stock_data.weekly_macd_velocity,
        }

    def _get_recent_history_by_market_day(self, recent_stock_data):
        latest_by_market_day = {}

        for history_item in recent_stock_data:
            market_day = self._get_market_day(history_item.get("date"))
            if market_day is None:
                continue

            existing = latest_by_market_day.get(market_day)
            if existing is None or history_item.get("date") > existing.get("date"):
                latest_by_market_day[market_day] = history_item

        return [
            latest_by_market_day[market_day]
            for market_day in sorted(latest_by_market_day.keys(), reverse=True)
        ]

    def _get_history_item_by_market_day_offset(self, recent_stock_data, market_day_offset):
        history_by_market_day = self._get_recent_history_by_market_day(recent_stock_data)

        if market_day_offset < 0 or market_day_offset >= len(history_by_market_day):
            return None

        return history_by_market_day[market_day_offset]

    def _get_history_value(self, recent_stock_data, field_name, market_day_offset):
        history_item = self._get_history_item_by_market_day_offset(
            recent_stock_data,
            market_day_offset,
        )
        if history_item is None:
            return None
        return history_item.get(field_name)

    def _get_velocity_from_history(
        self,
        current_value,
        recent_stock_data,
        field_name,
        market_day_offset,
        current_price,
    ):
        current_decimal = self._to_decimal(current_value)
        reference_decimal = self._to_decimal(
            self._get_history_value(recent_stock_data, field_name, market_day_offset)
        )
        price_decimal = self._to_decimal(current_price)

        if (
            current_decimal is None
            or reference_decimal is None
            or price_decimal is None
            or price_decimal == Decimal("0")
        ):
            return None

        return (current_decimal - reference_decimal) / price_decimal

    def _get_bollinger_width(self, current_price, bollinger_bands_lower, bollinger_bands_upper):
        price_decimal = self._to_decimal(current_price)
        lower_decimal = self._to_decimal(bollinger_bands_lower)
        upper_decimal = self._to_decimal(bollinger_bands_upper)

        if (
            price_decimal is None
            or price_decimal == Decimal("0")
            or lower_decimal is None
            or upper_decimal is None
        ):
            return None

        return (upper_decimal - lower_decimal) / price_decimal

    def _get_average_history_bollinger_width(self, recent_stock_data, limit=5):
        widths = []

        for history_item in self._get_recent_history_by_market_day(recent_stock_data)[:limit]:
            width = self._get_bollinger_width(
                history_item.get("current_price"),
                history_item.get("bollinger_bands_lower"),
                history_item.get("bollinger_bands_upper"),
            )
            if width is not None:
                widths.append(width)

        if not widths:
            return None

        return sum(widths, Decimal("0")) / Decimal(str(len(widths)))

    def _get_distance_percent(self, current_price, level):
        price_decimal = self._to_decimal(current_price)
        level_decimal = self._to_decimal(level)

        if (
            price_decimal is None
            or price_decimal == Decimal("0")
            or level_decimal is None
        ):
            return None

        return abs(price_decimal - level_decimal) / price_decimal

    def _get_level_side(self, current_price, level):
        price_decimal = self._to_decimal(current_price)
        level_decimal = self._to_decimal(level)

        if price_decimal is None or level_decimal is None:
            return None
        if level_decimal < price_decimal:
            return "support"
        if level_decimal > price_decimal:
            return "resistance"
        return "at_price"

    def _get_nearest_price_levels(
        self,
        current_price,
        support,
        resistance,
        pivot_classic_middle,
        pivot_classic_s2,
        pivot_classic_s3,
        pivot_classic_r2,
        pivot_classic_r3,
    ):
        levels = [
            support,
            resistance,
            pivot_classic_middle,
            pivot_classic_s2,
            pivot_classic_s3,
            pivot_classic_r2,
            pivot_classic_r3,
        ]
        nearest_support = None
        nearest_resistance = None
        nearest_support_distance = None
        nearest_resistance_distance = None

        for level in levels:
            distance = self._get_distance_percent(current_price, level)
            side = self._get_level_side(current_price, level)

            if distance is None or side == "at_price":
                continue

            if side == "support" and (
                nearest_support_distance is None or distance < nearest_support_distance
            ):
                nearest_support = level
                nearest_support_distance = distance

            if side == "resistance" and (
                nearest_resistance_distance is None or distance < nearest_resistance_distance
            ):
                nearest_resistance = level
                nearest_resistance_distance = distance

        return {
            "support": nearest_support,
            "support_distance": nearest_support_distance,
            "resistance": nearest_resistance,
            "resistance_distance": nearest_resistance_distance,
        }

    def _get_strategy_three_score_bounds(self, regime):
        if regime == "trend":
            return -10, 10
        if regime == "range":
            return -8, 8
        return -6, 6

    def _get_market_day(self, value):
        if value is None:
            return None

        # Django timezone.localtime() will convert the value to the MARKET_TIMEZONE.
        localized_value = timezone.localtime(value, MARKET_TIMEZONE)

        # return a date object representing the market day (ignoring time)
        return localized_value.date()

    def _limit_recent_history_to_market_days(self, history, day_count):
        recent_history = []
        seen_market_days = []

        for history_item in reversed(history):
            market_day = self._get_market_day(history_item.get("date"))
            if market_day is None:
                continue

            if market_day not in seen_market_days:
                if len(seen_market_days) >= day_count:
                    break
                seen_market_days.append(market_day)

            recent_history.append(history_item)

        recent_history.reverse()
        return recent_history

    def _get_three_day_average_velocity(
        self,
        current_date,
        recent_stock_data,
        field_name,
        current_value,
    ):
        # Array of values. key is market date, value is array of velocity values
        values_by_market_day = {}
        current_market_day = self._get_market_day(current_date)

        if current_market_day is not None and current_value is not None:

            # Build dict (date -> velocity)
            values_by_market_day.setdefault(current_market_day, []).append(
                Decimal(str(current_value))
            )

        for history_item in recent_stock_data:
            market_day = self._get_market_day(history_item.get("date"))
            metric_value = history_item.get(field_name)

            if market_day is None or metric_value is None:
                continue

            values_by_market_day.setdefault(market_day, []).append(
                Decimal(str(metric_value))
            )

        recent_market_days = sorted(values_by_market_day.keys(), reverse=True)[:3]
        recent_values = [
            metric_value
            for market_day in recent_market_days
            for metric_value in values_by_market_day[market_day]
        ]

        if not recent_values:
            return None

        return sum(recent_values, Decimal("0")) / Decimal(str(len(recent_values)))

    def _score_from_sign(self, value):
        if value is None:
            return 0

        numeric_value = Decimal(str(value))
        if numeric_value > 0:
            return 1
        if numeric_value < 0:
            return -1
        return 0

    def _detect_market_regime(
        self,
        recent_stock_data,
        current_price,
        adx,
        daily_macd_histogram,
        weekly_macd_histogram,
        ema_20,
        ema_50,
        ema_100,
        bollinger_bands_lower,
        bollinger_bands_upper,
    ):
        adx_decimal = self._to_decimal(adx)
        current_width = self._get_bollinger_width(
            current_price,
            bollinger_bands_lower,
            bollinger_bands_upper,
        )
        recent_width_average = self._get_average_history_bollinger_width(recent_stock_data)
        ema_20_velocity_5d = self._get_velocity_from_history(
            ema_20,
            recent_stock_data,
            "ema_20",
            4,
            current_price,
        )
        ema_50_velocity_10d = self._get_velocity_from_history(
            ema_50,
            recent_stock_data,
            "ema_50",
            9,
            current_price,
        )
        ema_100_velocity_15d = self._get_velocity_from_history(
            ema_100,
            recent_stock_data,
            "ema_100",
            14,
            current_price,
        )

        trend_checks = 0
        range_checks = 0
        daily_macd_sign = self._score_from_sign(daily_macd_histogram)
        weekly_macd_sign = self._score_from_sign(weekly_macd_histogram)

        if adx_decimal is not None and adx_decimal >= Decimal("25"):
            trend_checks += 1
        if adx_decimal is not None and adx_decimal < Decimal("18"):
            range_checks += 1

        if daily_macd_sign != 0 and daily_macd_sign == weekly_macd_sign:
            trend_checks += 1
        if daily_macd_sign == 0 or weekly_macd_sign == 0 or daily_macd_sign != weekly_macd_sign:
            range_checks += 1

        if (
            ema_50_velocity_10d is not None
            and ema_100_velocity_15d is not None
            and abs(ema_50_velocity_10d) >= Decimal("0.003")
            and abs(ema_100_velocity_15d) >= Decimal("0.003")
            and self._score_from_sign(ema_50_velocity_10d) == self._score_from_sign(ema_100_velocity_15d)
        ):
            trend_checks += 1

        if (
            ema_20_velocity_5d is not None
            and ema_50_velocity_10d is not None
            and abs(ema_20_velocity_5d) <= Decimal("0.004")
            and abs(ema_50_velocity_10d) <= Decimal("0.004")
        ):
            range_checks += 1

        if (
            current_width is not None
            and recent_width_average is not None
            and current_width >= recent_width_average * Decimal("0.90")
        ):
            trend_checks += 1

        if (
            current_width is not None
            and recent_width_average is not None
            and current_width <= recent_width_average * Decimal("1.10")
        ):
            range_checks += 1

        if trend_checks >= 3 and trend_checks > range_checks:
            return "trend"
        if range_checks >= 3 and range_checks > trend_checks:
            return "range"
        return "transition"

    def _calculate_trend_algo_score(
        self,
        recent_stock_data,
        current_price,
        support,
        resistance,
        daily_macd_histogram,
        weekly_macd_histogram,
        daily_macd_velocity,
        adx,
        adx_di_positive,
        adx_di_negative,
        ema_20,
        ema_50,
        ema_100,
        ema_200,
        rsi,
    ):
        score = 0
        ema_20_decimal = self._to_decimal(ema_20)
        ema_50_decimal = self._to_decimal(ema_50)
        ema_100_decimal = self._to_decimal(ema_100)
        ema_200_decimal = self._to_decimal(ema_200)
        current_price_decimal = self._to_decimal(current_price)
        adx_decimal = self._to_decimal(adx)
        adx_di_positive_decimal = self._to_decimal(adx_di_positive)
        adx_di_negative_decimal = self._to_decimal(adx_di_negative)
        rsi_decimal = self._to_decimal(rsi)

        bullish_weekly_bias = 0
        bearish_weekly_bias = 0

        if (
            ema_50_decimal is not None
            and ema_100_decimal is not None
            and ema_50_decimal > ema_100_decimal
        ):
            bullish_weekly_bias += 1
        elif (
            ema_50_decimal is not None
            and ema_100_decimal is not None
            and ema_50_decimal < ema_100_decimal
        ):
            bearish_weekly_bias += 1

        if (
            ema_100_decimal is not None
            and ema_200_decimal is not None
            and ema_100_decimal > ema_200_decimal
        ):
            bullish_weekly_bias += 1
        elif (
            ema_100_decimal is not None
            and ema_200_decimal is not None
            and ema_100_decimal < ema_200_decimal
        ):
            bearish_weekly_bias += 1

        weekly_macd_sign = self._score_from_sign(weekly_macd_histogram)
        if weekly_macd_sign > 0:
            bullish_weekly_bias += 1
        elif weekly_macd_sign < 0:
            bearish_weekly_bias += 1

        if bullish_weekly_bias > bearish_weekly_bias:
            score += bullish_weekly_bias
        elif bearish_weekly_bias > bullish_weekly_bias:
            score -= bearish_weekly_bias

        bias_sign = 1 if score > 0 else -1 if score < 0 else 0

        ema_50_velocity_10d = self._get_velocity_from_history(
            ema_50,
            recent_stock_data,
            "ema_50",
            9,
            current_price,
        )
        ema_100_velocity_15d = self._get_velocity_from_history(
            ema_100,
            recent_stock_data,
            "ema_100",
            14,
            current_price,
        )

        if (
            ema_50_velocity_10d is not None
            and ema_100_velocity_15d is not None
            and self._score_from_sign(ema_50_velocity_10d) == self._score_from_sign(ema_100_velocity_15d)
        ):
            velocity_sign = self._score_from_sign(ema_50_velocity_10d)
            if velocity_sign > 0 and abs(ema_50_velocity_10d) >= Decimal("0.003"):
                score += 2
            elif velocity_sign < 0 and abs(ema_50_velocity_10d) >= Decimal("0.003"):
                score -= 2

        daily_hist_sign = self._score_from_sign(daily_macd_histogram)
        daily_velocity_sign = self._score_from_sign(daily_macd_velocity)
        if daily_hist_sign > 0 and daily_velocity_sign > 0:
            score += 2
        elif daily_hist_sign < 0 and daily_velocity_sign < 0:
            score -= 2
        elif daily_hist_sign > 0 or daily_velocity_sign > 0:
            score += 1
        elif daily_hist_sign < 0 or daily_velocity_sign < 0:
            score -= 1

        support_distance = self._get_distance_percent(current_price, support)
        resistance_distance = self._get_distance_percent(current_price, resistance)
        ema_20_distance = self._get_distance_percent(current_price, ema_20)
        if (
            bias_sign > 0
            and current_price_decimal is not None
            and ema_50_decimal is not None
            and current_price_decimal >= ema_50_decimal
            and rsi_decimal is not None
            and rsi_decimal <= Decimal("65")
            and (
                (ema_20_distance is not None and ema_20_distance <= Decimal("0.02"))
                or (support_distance is not None and support_distance <= Decimal("0.02"))
            )
        ):
            score += 2
        elif (
            bias_sign < 0
            and current_price_decimal is not None
            and ema_50_decimal is not None
            and current_price_decimal <= ema_50_decimal
            and rsi_decimal is not None
            and rsi_decimal >= Decimal("35")
            and (
                (ema_20_distance is not None and ema_20_distance <= Decimal("0.02"))
                or (resistance_distance is not None and resistance_distance <= Decimal("0.02"))
            )
        ):
            score -= 2

        if (
            adx_decimal is not None
            and adx_decimal >= Decimal("30")
            and adx_di_positive_decimal is not None
            and adx_di_negative_decimal is not None
        ):
            if adx_di_positive_decimal > adx_di_negative_decimal:
                score += 1
            elif adx_di_negative_decimal > adx_di_positive_decimal:
                score -= 1

        return max(-10, min(10, score))

    def _calculate_range_algo_score(
        self,
        current_price,
        support,
        resistance,
        pivot_classic_middle,
        pivot_classic_s2,
        pivot_classic_s3,
        pivot_classic_r2,
        pivot_classic_r3,
        daily_macd_velocity,
        rsi,
        stoch_rsi_k,
        adx,
    ):
        score = 0
        level_data = self._get_nearest_price_levels(
            current_price,
            support,
            resistance,
            pivot_classic_middle,
            pivot_classic_s2,
            pivot_classic_s3,
            pivot_classic_r2,
            pivot_classic_r3,
        )
        rsi_decimal = self._to_decimal(rsi)
        stoch_rsi_decimal = self._to_decimal(stoch_rsi_k)
        adx_decimal = self._to_decimal(adx)
        location_bias = 0

        support_distance = level_data["support_distance"]
        resistance_distance = level_data["resistance_distance"]

        if support_distance is not None and support_distance <= Decimal("0.01"):
            score += 3
            location_bias = 1
        elif support_distance is not None and support_distance <= Decimal("0.02"):
            score += 2
            location_bias = 1
        elif support_distance is not None and support_distance <= Decimal("0.03"):
            score += 1
            location_bias = 1

        if resistance_distance is not None and resistance_distance <= Decimal("0.01"):
            score -= 3
            location_bias = -1
        elif resistance_distance is not None and resistance_distance <= Decimal("0.02"):
            score -= 2
            location_bias = -1
        elif resistance_distance is not None and resistance_distance <= Decimal("0.03"):
            score -= 1
            location_bias = -1

        if (
            support_distance is not None
            and resistance_distance is not None
            and support_distance < resistance_distance
        ):
            location_bias = 1
        elif (
            support_distance is not None
            and resistance_distance is not None
            and resistance_distance < support_distance
        ):
            location_bias = -1

        if rsi_decimal is not None:
            if rsi_decimal <= Decimal("30"):
                score += 2
            elif rsi_decimal <= Decimal("35"):
                score += 1
            elif rsi_decimal >= Decimal("70"):
                score -= 2
            elif rsi_decimal >= Decimal("65"):
                score -= 1

        if stoch_rsi_decimal is not None:
            if stoch_rsi_decimal <= Decimal("20") and self._score_from_sign(daily_macd_velocity) > 0:
                score += 1
            elif stoch_rsi_decimal >= Decimal("80") and self._score_from_sign(daily_macd_velocity) < 0:
                score -= 1

        if adx_decimal is not None and adx_decimal < Decimal("18") and location_bias != 0:
            score += location_bias

        if location_bias > 0 and self._score_from_sign(daily_macd_velocity) > 0:
            score += 1
        elif location_bias < 0 and self._score_from_sign(daily_macd_velocity) < 0:
            score -= 1

        return max(-8, min(8, score))

    def _calculate_transition_algo_score(
        self,
        recent_stock_data,
        current_price,
        support,
        resistance,
        pivot_classic_middle,
        daily_macd_histogram,
        daily_macd_velocity,
        rsi,
        yesterday_rsi,
        adx,
        ema_20,
        ema_50,
    ):
        score = 0
        adx_decimal = self._to_decimal(adx)
        rsi_decimal = self._to_decimal(rsi)
        yesterday_rsi_decimal = self._to_decimal(yesterday_rsi)
        current_price_decimal = self._to_decimal(current_price)
        pivot_middle_decimal = self._to_decimal(pivot_classic_middle)
        support_decimal = self._to_decimal(support)
        resistance_decimal = self._to_decimal(resistance)

        daily_hist_sign = self._score_from_sign(daily_macd_histogram)
        daily_velocity_sign = self._score_from_sign(daily_macd_velocity)
        if daily_hist_sign > 0 and daily_velocity_sign > 0:
            score += 2
        elif daily_hist_sign < 0 and daily_velocity_sign < 0:
            score -= 2
        elif daily_velocity_sign > 0:
            score += 1
        elif daily_velocity_sign < 0:
            score -= 1

        previous_adx = self._to_decimal(self._get_history_value(recent_stock_data, "adx", 4))
        if (
            adx_decimal is not None
            and previous_adx is not None
            and previous_adx < Decimal("20")
            and adx_decimal > previous_adx
        ):
            score += daily_velocity_sign

        ema_20_velocity_5d = self._get_velocity_from_history(
            ema_20,
            recent_stock_data,
            "ema_20",
            4,
            current_price,
        )
        ema_50_velocity_10d = self._get_velocity_from_history(
            ema_50,
            recent_stock_data,
            "ema_50",
            9,
            current_price,
        )
        if (
            ema_20_velocity_5d is not None
            and ema_50_velocity_10d is not None
            and self._score_from_sign(ema_20_velocity_5d) == self._score_from_sign(daily_macd_velocity)
            and abs(ema_20_velocity_5d) > abs(ema_50_velocity_10d)
        ):
            score += self._score_from_sign(ema_20_velocity_5d)

        if (
            current_price_decimal is not None
            and pivot_middle_decimal is not None
            and daily_velocity_sign != 0
        ):
            if current_price_decimal > pivot_middle_decimal and daily_velocity_sign > 0:
                score += 1
            elif current_price_decimal < pivot_middle_decimal and daily_velocity_sign < 0:
                score -= 1
            elif (
                resistance_decimal is not None
                and current_price_decimal > resistance_decimal
                and daily_velocity_sign > 0
            ):
                score += 1
            elif (
                support_decimal is not None
                and current_price_decimal < support_decimal
                and daily_velocity_sign < 0
            ):
                score -= 1

        if rsi_decimal is not None and yesterday_rsi_decimal is not None:
            if (
                yesterday_rsi_decimal <= Decimal("35")
                and rsi_decimal > yesterday_rsi_decimal
                and daily_velocity_sign > 0
            ):
                score += 1
            elif (
                yesterday_rsi_decimal >= Decimal("65")
                and rsi_decimal < yesterday_rsi_decimal
                and daily_velocity_sign < 0
            ):
                score -= 1

        return max(-6, min(6, score))

    def _calculate_strategy_three_score(
        self,
        recent_stock_data,
        current_price,
        support,
        resistance,
        pivot_classic_middle,
        pivot_classic_s2,
        pivot_classic_s3,
        pivot_classic_r2,
        pivot_classic_r3,
        daily_macd_histogram,
        weekly_macd_histogram,
        daily_macd_velocity,
        weekly_macd_velocity,
        rsi,
        yesterday_rsi,
        stoch_rsi_k,
        adx,
        adx_di_positive,
        adx_di_negative,
        ema_20,
        ema_50,
        ema_100,
        ema_200,
        bollinger_bands_lower,
        bollinger_bands_upper,
    ):
        regime = self._detect_market_regime(
            recent_stock_data=recent_stock_data,
            current_price=current_price,
            adx=adx,
            daily_macd_histogram=daily_macd_histogram,
            weekly_macd_histogram=weekly_macd_histogram,
            ema_20=ema_20,
            ema_50=ema_50,
            ema_100=ema_100,
            bollinger_bands_lower=bollinger_bands_lower,
            bollinger_bands_upper=bollinger_bands_upper,
        )

        if regime == "trend":
            return self._calculate_trend_algo_score(
                recent_stock_data=recent_stock_data,
                current_price=current_price,
                support=support,
                resistance=resistance,
                daily_macd_histogram=daily_macd_histogram,
                weekly_macd_histogram=weekly_macd_histogram,
                daily_macd_velocity=daily_macd_velocity,
                adx=adx,
                adx_di_positive=adx_di_positive,
                adx_di_negative=adx_di_negative,
                ema_20=ema_20,
                ema_50=ema_50,
                ema_100=ema_100,
                ema_200=ema_200,
                rsi=rsi,
            )

        if regime == "range":
            return self._calculate_range_algo_score(
                current_price=current_price,
                support=support,
                resistance=resistance,
                pivot_classic_middle=pivot_classic_middle,
                pivot_classic_s2=pivot_classic_s2,
                pivot_classic_s3=pivot_classic_s3,
                pivot_classic_r2=pivot_classic_r2,
                pivot_classic_r3=pivot_classic_r3,
                daily_macd_velocity=daily_macd_velocity,
                rsi=rsi,
                stoch_rsi_k=stoch_rsi_k,
                adx=adx,
            )

        return self._calculate_transition_algo_score(
            recent_stock_data=recent_stock_data,
            current_price=current_price,
            support=support,
            resistance=resistance,
            pivot_classic_middle=pivot_classic_middle,
            daily_macd_histogram=daily_macd_histogram,
            daily_macd_velocity=daily_macd_velocity,
            rsi=rsi,
            yesterday_rsi=yesterday_rsi,
            adx=adx,
            ema_20=ema_20,
            ema_50=ema_50,
        )

    def _calculate_macd_strategy_score(
        self,
        current_date,
        recent_stock_data,
        daily_macd_histogram,
        weekly_macd_histogram,
        daily_macd_velocity,
        weekly_macd_velocity,
    ):
        daily_three_day_velocity = self._get_three_day_average_velocity(
            current_date=current_date,
            recent_stock_data=recent_stock_data,
            field_name="daily_macd_velocity",
            current_value=daily_macd_velocity,
        )
        weekly_three_day_velocity = self._get_three_day_average_velocity(
            current_date=current_date,
            recent_stock_data=recent_stock_data,
            field_name="weekly_macd_velocity",
            current_value=weekly_macd_velocity,
        )

        return (
            self._score_from_sign(daily_macd_histogram)
            + self._score_from_sign(weekly_macd_histogram)
            + self._score_from_sign(daily_three_day_velocity)
            + self._score_from_sign(weekly_three_day_velocity)
        )
