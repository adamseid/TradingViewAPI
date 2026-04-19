from django.utils import timezone
from tradingview_ta import Interval
import time
import logging
from api.clients.tradingview_client import TradingViewClient
from api.services.token_services.constants import (
    DAILY_FIELD_MAP,
    RATE_LIMIT_MARKERS,
    RETRYABLE_ERROR_MARKERS,
    TokenSyncConfig,
)
from api.services.token_services.presenters import TokenPresenter
from api.services.token_services.token_repository import TokenRepository
from api.services.token_services.token_score_calculator import TokenScoreCalculator

logger = logging.getLogger(__name__)


class TokenService:
    def __init__(self, client=None, repository=None, calculator=None):
        self.client = client or TradingViewClient()
        self.repository = repository or TokenRepository()
        self.calculator = calculator or TokenScoreCalculator()
        self.presenter = TokenPresenter(self.calculator)
        self.sync_config = TokenSyncConfig()

    def insert_tokens(self):
        try:
            assets = self.client.get_all_assets()

            successfully_fetched_count = 0
            failed_fetched_count = 0
            skipped_duplicate_count = 0

            seen_keys = set()

            for asset in assets:
                ticker = self.repository.normalize_ticker(asset["ticker"])
                exchange = self.repository.normalize_exchange(asset["exchange"])
                screener = self.repository.normalize_screener(asset["screener"])

                unique_key = (ticker, exchange, screener)

                if unique_key in seen_keys:
                    skipped_duplicate_count += 1
                    continue

                seen_keys.add(unique_key)

                result = self.repository.insert_stock(
                    ticker=ticker,
                    screener=screener,
                    exchange=exchange,
                    name=asset.get("name"),
                    category=asset.get("category"),
                    sector=asset.get("sector"),
                    industry=asset.get("industry"),
                    image_url=asset.get("image_url"),
                )

                if not result["status"]:
                    failed_fetched_count += 1
                elif result["action"] == "duplicate":
                    skipped_duplicate_count += 1
                else:
                    successfully_fetched_count += 1

            return self.__service_response(
                status=True,
                message="Tokens inserted successfully",
                data={
                    "total_fetched": len(assets),
                    "successfully_fetched_count": successfully_fetched_count,
                    "failed_fetched_count": failed_fetched_count,
                    "skipped_duplicate_count": skipped_duplicate_count,
                },
            )

        except Exception as exc:
            return self.__service_response(
                status=False,
                message=f"Failed to insert tokens: {str(exc)}",
                data=None,
            )
        
    def __symbol_key_for(self, stock):
        return self.client.build_symbol_key(stock.exchange, stock.ticker)

    def __is_rate_limit_error(self, error_message: str) -> bool:
        message = (error_message or "").lower()
        return any(marker in message for marker in RATE_LIMIT_MARKERS)

    def __is_retryable_error(self, error_message: str) -> bool:
        message = (error_message or "").lower()
        return any(marker in message for marker in RETRYABLE_ERROR_MARKERS)

    def __disable_stock_for_sync_failure(self, stock, reason, log_prefix="[BAD SYMBOL]"):
        symbol_key = self.__symbol_key_for(stock)
        changed = self.repository.disable_stock(stock)

        if changed:
            print(f"{log_prefix} {symbol_key} in_use set to False. reason={reason}")
        else:
            print(f"{log_prefix} {symbol_key} already disabled. reason={reason}")

    def __get_missing_required_indicators(self, daily_stock_analysis, weekly_stock_analysis):
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

    def __get_batch_analysis_with_retry(
        self,
        stock_batch,
        interval,
        timeout,
        max_batch_retries,
        retry_delay_seconds,
    ):
        delay = retry_delay_seconds

        for attempt in range(max_batch_retries):
            try:
                return self.client.get_analysis_batch(
                    stock_batch,
                    interval,
                    timeout,
                )
            except Exception as exc:
                error_message = str(exc)

                if self.__is_retryable_error(error_message) and attempt < max_batch_retries - 1:
                    print(
                        f"[BATCH RETRY] screener={stock_batch[0].screener} "
                        f"interval={interval} size={len(stock_batch)} "
                        f"attempt={attempt + 1}/{max_batch_retries} "
                        f"sleeping={delay}s error={error_message}"
                    )
                    time.sleep(delay)
                    delay *= 2
                    continue

                raise

    def __get_single_analysis_with_retry(
        self,
        stock,
        interval,
        timeout,
        max_single_retries,
        retry_delay_seconds,
    ):
        symbol_key = self.__symbol_key_for(stock)
        delay = retry_delay_seconds

        for attempt in range(max_single_retries):
            try:
                return self.client.get_analysis(
                    ticker=stock.ticker,
                    exchange=stock.exchange,
                    screener=stock.screener,
                    interval=interval,
                    timeout=timeout,
                )
            except Exception as exc:
                error_message = str(exc)

                if self.__is_retryable_error(error_message) and attempt < max_single_retries - 1:
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

    def __create_stock_data_from_analysis(
        self,
        stock,
        daily_stock_analysis,
        weekly_stock_analysis,
        current_date,
        disable_on_failure=False,
    ):
        symbol_key = self.__symbol_key_for(stock)

        try:
            prev_stock_data = self.repository.get_latest_stock_data(stock)

            missing_daily, missing_weekly = self.__get_missing_required_indicators(
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
                    self.__disable_stock_for_sync_failure(stock, reason)
                return False, 1

            payload = self.__build_stock_data_payload(
                daily_stock_analysis=daily_stock_analysis,
                weekly_stock_analysis=weekly_stock_analysis,
                current_date=current_date,
                support=daily_stock_analysis.indicators.get("Pivot.M.Classic.S1"),
                resistance=daily_stock_analysis.indicators.get("Pivot.M.Classic.R1"),
                stock=stock,
                prev_stock_data=prev_stock_data,
            )

            success = self.repository.create_stock_data(payload)

            if success:
                self.repository.touch_stock_updated_at(stock, current_date)
                return True, 0

            print(f"[BAD SYMBOL] {symbol_key} failed repository.create_stock_data(.)")
            if disable_on_failure:
                self.__disable_stock_for_sync_failure(
                    stock,
                    "repository.create_stock_data returned False",
                )
            return False, 1

        except Exception as exc:
            print(f"[BAD SYMBOL] {symbol_key} failed to create StockData: {str(exc)}")
            if disable_on_failure:
                self.__disable_stock_for_sync_failure(stock, str(exc))
            return False, 1

    def __process_successful_batch(
        self,
        stock_batch,
        daily_batch_analysis,
        weekly_batch_analysis,
        current_date,
    ):
        success_count = 0
        failed_count = 0

        for stock in stock_batch:
            symbol_key = self.__symbol_key_for(stock)

            daily_stock_analysis = daily_batch_analysis.get(symbol_key)
            weekly_stock_analysis = weekly_batch_analysis.get(symbol_key)

            if daily_stock_analysis is None or weekly_stock_analysis is None:
                failed_count += 1
                reason = (
                    "missing analysis from successful batch. "
                    f"daily_found={daily_stock_analysis is not None}, "
                    f"weekly_found={weekly_stock_analysis is not None}"
                )
                print(
                    f"[BAD SYMBOL] {symbol_key} {reason}"
                )
                self.__disable_stock_for_sync_failure(stock, reason)
                continue

            created, failed_increment = self.__create_stock_data_from_analysis(
                stock=stock,
                daily_stock_analysis=daily_stock_analysis,
                weekly_stock_analysis=weekly_stock_analysis,
                current_date=current_date,
                disable_on_failure=True,
            )

            if created:
                success_count += 1
            failed_count += failed_increment

        return success_count, failed_count

    def __fallback_batch_to_single(
        self,
        stock_batch,
        current_date,
        original_batch_error,
        timeout,
        delay_between_interval_requests_seconds,
        delay_between_single_symbol_requests_seconds,
        max_single_retries,
        retry_delay_seconds,
    ):
        success_count = 0
        failed_count = 0

        print(
            f"[FALLBACK] switching failed batch to single-symbol mode. "
            f"screener={stock_batch[0].screener} size={len(stock_batch)} "
            f"error={original_batch_error}"
        )

        for index, stock in enumerate(stock_batch, start=1):
            symbol_key = self.__symbol_key_for(stock)

            try:
                print(
                    f"[FALLBACK] processing symbol {index}/{len(stock_batch)} "
                    f"{symbol_key}"
                )

                time.sleep(delay_between_interval_requests_seconds)

                daily_stock_analysis = self.__get_single_analysis_with_retry(
                    stock=stock,
                    interval=Interval.INTERVAL_1_DAY,
                    timeout=timeout,
                    max_single_retries=max_single_retries,
                    retry_delay_seconds=retry_delay_seconds,
                )

                time.sleep(delay_between_interval_requests_seconds)

                weekly_stock_analysis = self.__get_single_analysis_with_retry(
                    stock=stock,
                    interval=Interval.INTERVAL_1_WEEK,
                    timeout=timeout,
                    max_single_retries=max_single_retries,
                    retry_delay_seconds=retry_delay_seconds,
                )

                created, failed_increment = self.__create_stock_data_from_analysis(
                    stock=stock,
                    daily_stock_analysis=daily_stock_analysis,
                    weekly_stock_analysis=weekly_stock_analysis,
                    current_date=current_date,
                )

                if created:
                    success_count += 1
                failed_count += failed_increment

            except Exception as exc:
                failed_count += 1
                error_message = str(exc)

                if self.__is_rate_limit_error(error_message):
                    print(
                        f"[RATE LIMITED] {symbol_key} single-symbol fallback hit a rate-limit error. "
                        f"Stopping all remaining sync work for this run. "
                        f"error={error_message}"
                    )
                    return success_count, failed_count, True

                self.__disable_stock_for_sync_failure(
                    stock,
                    f"single-symbol fallback failure: {error_message}",
                )

            if index < len(stock_batch):
                time.sleep(delay_between_single_symbol_requests_seconds)

        return success_count, failed_count, False

    def insert_tokens_data(self):
        try:
            max_batches_per_run = self.sync_config.max_batches_per_run
            batch_size = self.client.analysis_batch_size

            stocks = list(
                self.repository.list_stocks_for_sync(
                    max_batches=max_batches_per_run,
                    batch_size=batch_size,
                )
            )

            if not stocks:
                return self.__service_response(
                    status=True,
                    message="No active stocks are due for sync.",
                    data={
                        "total_stocks_selected": 0,
                        "processed_batches": 0,
                        "successfully_fetched_count": 0,
                        "failed_fetched_count": 0,
                    },
                )

            successfully_fetched_count = 0
            failed_fetched_count = 0
            processed_batches = 0
            timeout = self.sync_config.timeout

            stocks_by_screener = {}
            for stock in stocks:
                screener = str(stock.screener).lower()
                stocks_by_screener.setdefault(screener, []).append(stock)

            stop_processing = False

            for screener, screener_stocks in stocks_by_screener.items():
                screener_batches = list(self.client.chunked(screener_stocks, batch_size))

                for batch_index, stock_batch in enumerate(screener_batches, start=1):
                    if processed_batches >= max_batches_per_run:
                        stop_processing = True
                        break

                    processed_batches += 1
                    current_date = timezone.now()

                    try:
                        batch_symbols = [self.__symbol_key_for(stock) for stock in stock_batch]

                        print(
                            f"Processing screener={screener} "
                            f"batch {batch_index}/{len(screener_batches)} "
                            f"(run batch {processed_batches}/{max_batches_per_run}) "
                            f"with {len(stock_batch)} symbols: {batch_symbols}"
                        )

                        daily_batch_analysis = self.__get_batch_analysis_with_retry(
                            stock_batch=stock_batch,
                            interval=Interval.INTERVAL_1_DAY,
                            timeout=timeout,
                            max_batch_retries=self.sync_config.max_batch_retries,
                            retry_delay_seconds=self.sync_config.retry_delay_seconds,
                        )

                        if self.sync_config.delay_between_interval_requests_seconds > 0:
                            time.sleep(self.sync_config.delay_between_interval_requests_seconds)

                        weekly_batch_analysis = self.__get_batch_analysis_with_retry(
                            stock_batch=stock_batch,
                            interval=Interval.INTERVAL_1_WEEK,
                            timeout=timeout,
                            max_batch_retries=self.sync_config.max_batch_retries,
                            retry_delay_seconds=self.sync_config.retry_delay_seconds,
                        )

                        batch_success, batch_failed = self.__process_successful_batch(
                            stock_batch=stock_batch,
                            daily_batch_analysis=daily_batch_analysis,
                            weekly_batch_analysis=weekly_batch_analysis,
                            current_date=current_date,
                        )

                        successfully_fetched_count += batch_success
                        failed_fetched_count += batch_failed

                    except Exception as exc:
                        error_message = str(exc)

                        print(
                            f"Failed batch for screener={screener}, "
                            f"batch={batch_index}, size={len(stock_batch)}: {error_message}"
                        )

                        if self.__is_rate_limit_error(error_message):
                            print(
                                f"[RATE LIMITED] Batch sync halted for screener={screener}, "
                                f"batch={batch_index}, error={error_message}"
                            )
                            return self.__service_response(
                                status=False,
                                message=(
                                    f"Token data insertion aborted due to rate limit. "
                                    f"Processed batches: {processed_batches}/{max_batches_per_run}. "
                                    f"Successful: {successfully_fetched_count}, "
                                    f"Failed: {failed_fetched_count}. "
                                    f"Last error: {error_message}"
                                ),
                                data={
                                    "total_stocks_selected": len(stocks),
                                    "processed_batches": processed_batches,
                                    "max_batches_per_run": max_batches_per_run,
                                    "successfully_fetched_count": successfully_fetched_count,
                                    "failed_fetched_count": failed_fetched_count,
                                    "aborted_due_to_rate_limit": True,
                                    "last_error": error_message,
                                },
                            )

                        fallback_success, fallback_failed, aborted_due_to_rate_limit = self.__fallback_batch_to_single(
                            stock_batch=stock_batch,
                            current_date=current_date,
                            original_batch_error=error_message,
                            timeout=timeout,
                            delay_between_interval_requests_seconds=self.sync_config.delay_between_interval_requests_seconds,
                            delay_between_single_symbol_requests_seconds=self.sync_config.delay_between_single_symbol_requests_seconds,
                            max_single_retries=self.sync_config.max_single_retries,
                            retry_delay_seconds=self.sync_config.retry_delay_seconds,
                        )

                        successfully_fetched_count += fallback_success
                        failed_fetched_count += fallback_failed

                        if aborted_due_to_rate_limit:
                            return self.__service_response(
                                status=False,
                                message=(
                                    f"Token data insertion aborted due to rate limit during single-symbol fallback. "
                                    f"Processed batches: {processed_batches}/{max_batches_per_run}. "
                                    f"Successful: {successfully_fetched_count}, "
                                    f"Failed: {failed_fetched_count}."
                                ),
                                data={
                                    "total_stocks_selected": len(stocks),
                                    "processed_batches": processed_batches,
                                    "max_batches_per_run": max_batches_per_run,
                                    "successfully_fetched_count": successfully_fetched_count,
                                    "failed_fetched_count": failed_fetched_count,
                                    "aborted_due_to_rate_limit": True,
                                    "last_error": error_message,
                                },
                            )

                    if processed_batches < max_batches_per_run:
                        time.sleep(self.sync_config.delay_between_batch_requests_seconds)

                if stop_processing:
                    break

            return self.__service_response(
                status=True,
                message=(
                    f"Token data insertion completed. "
                    f"Selected: {len(stocks)}, "
                    f"Processed batches: {processed_batches}/{max_batches_per_run}, "
                    f"Successful: {successfully_fetched_count}, "
                    f"Failed: {failed_fetched_count}"
                ),
                data={
                    "total_stocks_selected": len(stocks),
                    "processed_batches": processed_batches,
                    "max_batches_per_run": max_batches_per_run,
                    "successfully_fetched_count": successfully_fetched_count,
                    "failed_fetched_count": failed_fetched_count,
                },
            )

        except Exception as exc:
            return self.__service_response(
                status=False,
                message=f"Failed to insert token data: {str(exc)}",
                data=None,
            )

    def token_list(self, user=None):
        most_recent_stock_data = self.repository.list_latest_stock_data(user=user)

        stock_list = []
        crypto_list = []
        wishlist = []

        for stock_data in most_recent_stock_data:
            item = self.presenter.present_latest_stock_item(stock_data)

            if stock_data.wishlist > 0:
                wishlist.append(item)
            elif str(stock_data.stock.screener).lower() == "crypto":
                crypto_list.append(item)
            else:
                stock_list.append(item)

        return self.__service_response(
            status=True,
            message="success",
            data={
                "stock_list": stock_list,
                "crypto_list": crypto_list,
                "wishlist": wishlist
            },
        )
    
    def reset_all_stocks_in_use(self):
        try:
            updated_count = self.repository.reset_all_stocks_in_use()

            return self.__service_response(
                status=True,
                message=f"Reset in_use=True for {updated_count} stocks.",
                data={"updated_count": updated_count},
            )
        except Exception as exc:
            return self.__service_response(
                status=False,
                message=f"Failed to reset stocks in_use flag: {str(exc)}",
                data=None,
            )
    
    def stock_detail(self, ticker):
        stock_rows = self.repository.list_stock_data_by_ticker(ticker)

        if(len(stock_rows) == 0):
            return self.__service_response(
                status=False,
                message="No Stock Data found",
                data= None,
            )

        stock_data = []
        for data in stock_rows:
            stock_data.append(self.presenter.present_stock_detail_item(data))

        return self.__service_response(
            status=True,
            message="success",
            data={
                "stock_data": stock_data,
            },
        )

    def __build_stock_data_payload(
        self,
        daily_stock_analysis,
        weekly_stock_analysis,
        current_date,
        support,
        resistance,
        stock,
        prev_stock_data,
    ):
        current_price = daily_stock_analysis.indicators["close"]

        support_resistance_broken = self.repository.get_latest_broken_support_resistance(
            stock=stock,
            support=support,
            resistance=resistance,
        )

        support_resistance_score = self.calculator.get_support_resistance_score(
            support,
            resistance,
            current_price,
            support_resistance_broken,
        )

        if support_resistance_score == 2 or support_resistance_score == -2:
            support = daily_stock_analysis.indicators["Pivot.M.Classic.S1"]
            resistance = daily_stock_analysis.indicators["Pivot.M.Classic.R1"]

        ma_100d_score = self.calculator.get_ma_score(
            daily_stock_analysis.indicators["SMA100"],
            current_price,
        )
        ma_200d_score = self.calculator.get_ma_score(
            daily_stock_analysis.indicators["SMA200"],
            current_price,
        )
        ma_50d_score = self.calculator.get_ma_score(
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
        direction = None
        total_score = None

        if prev_stock_data is not None:
            daily_macd_velocity = self.calculator.get_macd_velocity(
                daily_macd_histogram,
                prev_stock_data,
            )
            weekly_macd_velocity = self.calculator.get_macd_velocity(
                weekly_macd_histogram,
                prev_stock_data,
            )
            daily_macd_score = self.calculator.get_macd_score(
                daily_macd_histogram,
                daily_macd_velocity,
            )
            weekly_macd_score = self.calculator.get_macd_score(
                weekly_macd_histogram,
                weekly_macd_velocity,
            )

            total_score = self.calculator.calculate_total_score(
                support_resistance_score=support_resistance_score,
                ma_50d_score=ma_50d_score,
                ma_100d_score=ma_100d_score,
                ma_200d_score=ma_200d_score,
                daily_macd_score=daily_macd_score,
                weekly_macd_score=weekly_macd_score,
            )
            direction = self.calculator.calculate_direction(total_score)

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
            "total_score": total_score,
            "direction": direction,
            "stock": stock,
        }

        for model_field, indicator_key in DAILY_FIELD_MAP.items():
            payload[model_field] = daily_stock_analysis.indicators.get(indicator_key)

        return payload
    
    def __service_response(self, status, message, data=None):
        return {
            "status": status,
            "message": message,
            "data": data,
        }
