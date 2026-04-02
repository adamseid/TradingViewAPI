from django.utils import timezone
from tradingview_ta import Interval
import time
from api.clients.tradingview_client import TradingViewClient
from api.services.token_services.token_repository import TokenRepository
from api.services.token_services.token_score_calculator import TokenScoreCalculator


class TokenService:
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

    def __init__(self, client=None, repository=None, calculator=None):
        self.client = client or TradingViewClient()
        self.repository = repository or TokenRepository()
        self.calculator = calculator or TokenScoreCalculator()

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
        
    def insert_tokens_data(self):
        try:
            stocks = list(self.repository.list_stocks())

            if not stocks:
                return self.__service_response(
                    status=False,
                    message="No stocks found. Run insert_tokens first.",
                    data={
                        "total_stocks": 0,
                        "successfully_fetched_count": 0,
                        "failed_fetched_count": 0,
                    },
                )

            successfully_fetched_count = 0
            failed_fetched_count = 0
            timeout = None

            batch_size = self.client.analysis_batch_size
            delay_between_interval_requests_seconds = 30
            delay_between_batch_requests_seconds = 15
            delay_between_single_symbol_requests_seconds = 30

            max_batch_retries = 1
            max_single_retries = 1
            retry_delay_seconds = 30

            def symbol_key_for(stock):
                return self.client.build_symbol_key(stock.exchange, stock.ticker)

            def is_retryable_error(error_message: str) -> bool:
                message = (error_message or "").lower()
                retry_markers = [
                    "429",
                    "rate limit",
                    "too many requests",
                    "timeout",
                    "timed out",
                    "connection reset",
                    "temporarily unavailable",
                    "expecting value: line 1 column 1 (char 0)",
                ]
                return any(marker in message for marker in retry_markers)

            def get_batch_analysis_with_retry(stock_batch, interval):
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

                        if is_retryable_error(error_message) and attempt < max_batch_retries - 1:
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

            def get_single_analysis_with_retry(stock, interval):
                # delay = retry_delay_seconds
                symbol_key = symbol_key_for(stock)

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
                        print(
                            f"[BAD SYMBOL] {symbol_key} failed single fetch "
                            f"interval={interval} error={error_message}"
                        )

                        # if is_retryable_error(error_message) and attempt < max_single_retries - 1:
                        #     print(
                        #         f"[SINGLE RETRY] symbol={symbol_key} "
                        #         f"interval={interval} "
                        #         f"attempt={attempt + 1}/{max_single_retries} "
                        #         f"sleeping={delay}s error={error_message}"
                        #     )
                        #     time.sleep(delay)
                        #     delay *= 2
                        #     continue

                        raise

            def create_stock_data_from_analysis(stock, daily_stock_analysis, weekly_stock_analysis, current_date):
                nonlocal successfully_fetched_count, failed_fetched_count

                symbol_key = symbol_key_for(stock)

                try:
                    prev_stock_data = self.repository.get_latest_stock_data(stock)

                    support = daily_stock_analysis.indicators.get("Pivot.M.Classic.S1")
                    resistance = daily_stock_analysis.indicators.get("Pivot.M.Classic.R1")

                    if support is None or resistance is None:
                        failed_fetched_count += 1
                        print(
                            f"[BAD SYMBOL] {symbol_key} missing pivot indicators. "
                            f"support={support}, resistance={resistance}"
                        )
                        return

                    payload = self.__build_stock_data_payload(
                        daily_stock_analysis=daily_stock_analysis,
                        weekly_stock_analysis=weekly_stock_analysis,
                        current_date=current_date,
                        support=support,
                        resistance=resistance,
                        stock=stock,
                        prev_stock_data=prev_stock_data,
                    )

                    success = self.repository.create_stock_data(payload)

                    if success:
                        successfully_fetched_count += 1
                    else:
                        failed_fetched_count += 1
                        print(f"[BAD SYMBOL] {symbol_key} failed repository.create_stock_data(...)")

                except Exception as exc:
                    failed_fetched_count += 1
                    print(f"[BAD SYMBOL] {symbol_key} failed to create StockData: {str(exc)}")

            def fallback_batch_to_single(stock_batch, current_date, original_batch_error):
                nonlocal failed_fetched_count

                print(
                    f"[FALLBACK] switching failed batch to single-symbol mode. "
                    f"screener={stock_batch[0].screener} size={len(stock_batch)} "
                    f"error={original_batch_error}"
                )

                for index, stock in enumerate(stock_batch, start=1):
                    symbol_key = symbol_key_for(stock)

                    try:
                        print(
                            f"[FALLBACK] processing symbol {index}/{len(stock_batch)} "
                            f"{symbol_key}"
                        )

                        daily_stock_analysis = get_single_analysis_with_retry(
                            stock,
                            Interval.INTERVAL_1_DAY,
                        )

                        time.sleep(delay_between_interval_requests_seconds)

                        weekly_stock_analysis = get_single_analysis_with_retry(
                            stock,
                            Interval.INTERVAL_1_WEEK,
                        )

                        create_stock_data_from_analysis(
                            stock=stock,
                            daily_stock_analysis=daily_stock_analysis,
                            weekly_stock_analysis=weekly_stock_analysis,
                            current_date=current_date,
                        )

                    except Exception as exc:
                        failed_fetched_count += 1
                        print(
                            f"[BAD SYMBOL] {symbol_key} failed single-symbol fallback: {str(exc)}"
                        )

                    if index < len(stock_batch):
                        time.sleep(delay_between_single_symbol_requests_seconds)

            stocks_by_screener = {}
            for stock in stocks:
                screener = str(stock.screener).lower()
                stocks_by_screener.setdefault(screener, []).append(stock)

            for screener, screener_stocks in stocks_by_screener.items():
                screener_batches = list(self.client.chunked(screener_stocks, batch_size))

                for batch_index, stock_batch in enumerate(screener_batches, start=1):
                    current_date = timezone.now()

                    try:
                        batch_symbols = [symbol_key_for(stock) for stock in stock_batch]

                        print(
                            f"Processing screener={screener} "
                            f"batch {batch_index}/{len(screener_batches)} "
                            f"with {len(stock_batch)} symbols: {batch_symbols}"
                        )

                        daily_batch_analysis = get_batch_analysis_with_retry(
                            stock_batch,
                            Interval.INTERVAL_1_DAY,
                        )

                        if delay_between_interval_requests_seconds > 0:
                            time.sleep(delay_between_interval_requests_seconds)

                        weekly_batch_analysis = get_batch_analysis_with_retry(
                            stock_batch,
                            Interval.INTERVAL_1_WEEK,
                        )

                        for stock in stock_batch:
                            symbol_key = symbol_key_for(stock)

                            daily_stock_analysis = daily_batch_analysis.get(symbol_key)
                            weekly_stock_analysis = weekly_batch_analysis.get(symbol_key)

                            if daily_stock_analysis is None or weekly_stock_analysis is None:
                                failed_fetched_count += 1
                                print(
                                    f"[BAD SYMBOL] {symbol_key} missing analysis from successful batch. "
                                    f"daily_found={daily_stock_analysis is not None}, "
                                    f"weekly_found={weekly_stock_analysis is not None}"
                                )
                                continue

                            create_stock_data_from_analysis(
                                stock=stock,
                                daily_stock_analysis=daily_stock_analysis,
                                weekly_stock_analysis=weekly_stock_analysis,
                                current_date=current_date,
                            )

                    except Exception as exc:
                        print(
                            f"Failed batch for screener={screener}, "
                            f"batch={batch_index}, size={len(stock_batch)}: {str(exc)}"
                        )
                        fallback_batch_to_single(
                            stock_batch=stock_batch,
                            current_date=current_date,
                            original_batch_error=str(exc),
                        )

                    if batch_index < len(screener_batches):
                        time.sleep(delay_between_batch_requests_seconds)

            total_stocks = len(stocks)

            return self.__service_response(
                status=True,
                message=(
                    f"Token data insertion completed. "
                    f"Successful: {successfully_fetched_count}, "
                    f"Failed: {failed_fetched_count}"
                ),
                data={
                    "total_stocks": total_stocks,
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
            total_score = self.calculator.round_significant(stock_data.total_score)
            current_price = self.calculator.round_significant(stock_data.current_price)
            support_resistance_score = self.calculator.round_significant(stock_data.support_resistance_score)
            daily_macd_velocity = self.calculator.round_significant(stock_data.daily_macd_velocity)
            daily_macd_score = self.calculator.round_significant(stock_data.daily_macd_score)
            weekly_macd_velocity = self.calculator.round_significant(stock_data.weekly_macd_velocity)
            weekly_macd_score = self.calculator.round_significant(stock_data.weekly_macd_score)

            ma_50d_score = self.calculator.round_significant(stock_data.ma_50d_score)
            ma_100d_score = self.calculator.round_significant(stock_data.ma_100d_score)
            ma_200d_score = self.calculator.round_significant(stock_data.ma_200d_score)

            total_ma_score_raw = (
                (stock_data.ma_50d_score or 0)
                + (stock_data.ma_100d_score or 0)
                + (stock_data.ma_200d_score or 0)
            )
            ma_score = self.calculator.round_significant(total_ma_score_raw)

            daily_profit = None
            daily_return = None

            if stock_data.current_price is not None and stock_data.price_change is not None:
                daily_profit_raw = stock_data.current_price * (stock_data.price_change / 100)
                daily_profit = self.calculator.round_significant(daily_profit_raw)

                denominator = daily_profit_raw + stock_data.current_price
                if denominator != 0:
                    daily_return = self.calculator.round_significant(daily_profit_raw / denominator)

            item = {
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
                "direction": stock_data.direction,

                "current_price": current_price,
                "price_change": self.calculator.round_significant(stock_data.price_change),
                "daily_profit": daily_profit,
                "daily_return": daily_return,

                "support": self.calculator.round_significant(stock_data.support),
                "resistance": self.calculator.round_significant(stock_data.resistance),
                "support_resistance_score": support_resistance_score,

                "ma_50d_score": ma_50d_score,
                "ma_100d_score": ma_100d_score,
                "ma_200d_score": ma_200d_score,
                "ma_score": ma_score,

                "daily_macd_velocity": daily_macd_velocity,
                "daily_macd_score": daily_macd_score,
                "weekly_macd_velocity": weekly_macd_velocity,
                "weekly_macd_score": weekly_macd_score,

                "total_score": total_score,

                "kinematics_score": 0,
                "five_day_velocity_score": 0,
                "five_day_acceleration_score": 0,
            }

            if(stock_data.wishlist > 0):
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
            stock_data.append({
                "id": data.id,
                "date": data.date,
                "ticker": data.stock.ticker,
                "exchange": data.stock.exchange,
                "screener": data.stock.screener,
                "current_price": self.calculator.round_significant(data.current_price),
                "resistance": self.calculator.round_significant(data.resistance),
                "support": self.calculator.round_significant(data.support),
                "support_resistance_score": self.calculator.round_significant(data.support_resistance_score),
                "daily_macd_histogram": self.calculator.round_significant(data.daily_macd_histogram),
                "daily_macd_velocity": self.calculator.round_significant(data.daily_macd_velocity),
                "daily_macd_score": self.calculator.round_significant(data.daily_macd_score),
                "weekly_macd_histogram": self.calculator.round_significant(data.weekly_macd_histogram),
                "weekly_macd_velocity": self.calculator.round_significant(data.weekly_macd_velocity),
                "weekly_macd_score": self.calculator.round_significant(data.weekly_macd_score),
                "total_score": self.calculator.round_significant(data.total_score),
                "direction": data.direction,
            })

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

        daily_macd_histogram = (
            daily_stock_analysis.indicators["MACD.macd"]
            - daily_stock_analysis.indicators["MACD.signal"]
        )
        weekly_macd_histogram = (
            weekly_stock_analysis.indicators["MACD.macd"]
            - weekly_stock_analysis.indicators["MACD.signal"]
        )

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

            total_score = (
                support_resistance_score
                + ma_50d_score
                + ma_100d_score
                + ma_200d_score
                + daily_macd_score
                + weekly_macd_score
            )

            if total_score > 4:
                direction = 2
            elif total_score > 2:
                direction = 1
            elif total_score < -4:
                direction = -2
            elif total_score < -2:
                direction = -1
            else:
                direction = 0

        payload = {
            "date": current_date,
            "daily_macd_line": daily_stock_analysis.indicators["MACD.macd"],
            "daily_macd_signal": daily_stock_analysis.indicators["MACD.signal"],
            "daily_macd_histogram": daily_macd_histogram,
            "weekly_macd_line": weekly_stock_analysis.indicators["MACD.macd"],
            "weekly_macd_signal": weekly_stock_analysis.indicators["MACD.signal"],
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

        for model_field, indicator_key in self.DAILY_FIELD_MAP.items():
            payload[model_field] = daily_stock_analysis.indicators.get(indicator_key)

        return payload
    
    def __service_response(self, status, message, data=None):
        return {
            "status": status,
            "message": message,
            "data": data,
        }