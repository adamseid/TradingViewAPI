from typing import List, Dict, Any, Optional, Iterator

class TradingViewClient:
    def __init__(
        self,
        default_batch_size: int = 500,
        default_timeout: int = 10,
        analysis_batch_size: int = 20,
        proxies: Optional[Dict[str, str]] = None,
    ):
        self.default_batch_size = default_batch_size
        self.default_timeout = default_timeout
        self.analysis_batch_size = analysis_batch_size
        self.proxies = proxies

    def get_all_assets(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        seen = set()

        rows.extend(self._get_stock_rows(seen))
        rows.extend(self._get_crypto_rows(seen))

        return rows
    
    def get_analysis(self, ticker, exchange, screener, interval, timeout=10):
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

    def get_analysis_batch(self, stocks, interval, timeout=None):
        if not stocks:
            return {}

        screener = str(stocks[0].screener).lower()

        for stock in stocks:
            if str(stock.screener).lower() != screener:
                raise ValueError("All stocks in a batch must have the same screener.")

        symbols = [
            self.build_symbol_key(stock.exchange, stock.ticker)
            for stock in stocks
        ]

        try:
            return get_multiple_analysis(
                screener=screener,
                interval=interval,
                symbols=symbols,
                timeout=timeout if timeout is not None else self.default_timeout,
                proxies=self.proxies,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Error when batch fetching {len(symbols)} symbols "
                f"for screener={screener}, interval={interval}: {str(exc)}"
            ) from exc

    @staticmethod
    def chunked(items: List[Any], size: int) -> Iterator[List[Any]]:
        for i in range(0, len(items), size):
            yield items[i:i + size]

    @staticmethod
    def build_symbol_key(exchange: str, ticker: str) -> str:
        return f"{str(exchange).upper()}:{str(ticker).upper()}"
    
    @staticmethod
    def _extract_symbol(ticker_value: Any) -> Optional[str]:
        if ticker_value is None:
            return None

        ticker_str = str(ticker_value).strip()
        if ":" in ticker_str:
            return ticker_str.split(":", 1)[1]
        return ticker_str

    @staticmethod
    def _clean_value(value: Any) -> Optional[str]:
        if value is None:
            return None

        value_str = str(value).strip()
        if value_str == "" or value_str.lower() == "nan":
            return None

        return value_str