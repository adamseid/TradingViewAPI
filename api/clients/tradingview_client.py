import logging

from tradingview_ta import TA_Handler, get_multiple_analysis
from tradingview_screener import Query
from typing import List, Dict, Any, Optional, Iterator

logger = logging.getLogger(__name__)

SP500_SYMBOLS = [
    'NVDA', 'AAPL', 'GOOG', 'GOOGL', 'MSFT', 'AMZN', 'AVGO', 'META', 'TSLA', 'BRK.B', 'WMT', 'LLY',
    'JPM', 'XOM', 'JNJ', 'V', 'COST', 'MA', 'CVX', 'ORCL', 'NFLX', 'ABBV', 'MU', 'BAC',
    'PG', 'PLTR', 'KO', 'HD', 'AMD', 'CAT', 'CSCO', 'MRK', 'GE', 'PM', 'AMAT', 'MS',
    'RTX', 'LRCX', 'GS', 'UNH', 'WFC', 'TMUS', 'LIN', 'IBM', 'GEV', 'MCD', 'PEP', 'VZ',
    'INTC', 'AXP', 'T', 'NEE', 'AMGN', 'C', 'KLAC', 'TMO', 'ABT', 'TJX', 'CRM', 'GILD',
    'TXN', 'DIS', 'SCHW', 'COP', 'ISRG', 'PFE', 'BLK', 'DE', 'BA', 'ADI', 'ANET', 'APH',
    'UBER', 'UNP', 'HON', 'LMT', 'WELL', 'BX', 'QCOM', 'ETN', 'BKNG', 'LOW', 'DHR', 'CB',
    'PANW', 'APP', 'SYK', 'SPGI', 'PLD', 'BMY', 'ACN', 'INTU', 'PGR', 'VRTX', 'MO', 'NEM',
    'MDT', 'COF', 'GLW', 'NOW', 'SO', 'PH', 'CEG', 'IBKR', 'CME', 'DELL', 'MCK', 'HCA',
    'CMCSA', 'DUK', 'SBUX', 'ADBE', 'CRWD', 'EQIX', 'NOC', 'BSX', 'WM', 'GD', 'TT', 'VRT',
    'ICE', 'HWM', 'CVS', 'WMB', 'WDC', 'MAR', 'MRSH', 'SNDK', 'ADP', 'FDX', 'PNC', 'UPS',
    'KKR', 'EOG', 'PWR', 'REGN', 'BK', 'AMT', 'USB', 'FCX', 'SHW', 'STX', 'JCI', 'ORLY',
    'SLB', 'MCO', 'NKE', 'ABNB', 'MMM', 'MDLZ', 'KMI', 'VLO', 'PSX', 'CSX', 'ECL', 'ITW',
    'CDNS', 'SNPS', 'MPC', 'AEP', 'RCL', 'MSI', 'CMI', 'MNST', 'AON', 'EMR', 'CL', 'RSG',
    'CI', 'HLT', 'CRH', 'CTAS', 'ROST', 'WBD', 'GM', 'OXY', 'APD', 'TDG', 'NSC', 'DASH',
    'APO', 'SRE', 'LHX', 'TRV', 'ELV', 'CVNA', 'COR', 'DLR', 'BKR', 'PCAR', 'FTNT', 'SPG',
    'OKE', 'TEL', 'HOOD', 'O', 'FANG', 'AFL', 'CTVA', 'TFC', 'AJG', 'AZO', 'D', 'ALL',
    'TGT', 'TRGP', 'FAST', 'CIEN', 'EA', 'EXC', 'ETR', 'GWW', 'VST', 'ADSK', 'XEL', 'MPWR',
    'ZTS', 'CAH', 'AME', 'NDAQ', 'NXPI', 'PSA', 'KR', 'LITE', 'EW', 'KEYS', 'CARR', 'URI',
    'FIX', 'F', 'IDXX', 'MET', 'BDX', 'GRMN', 'HSY', 'TER', 'YUM', 'COIN', 'DAL', 'ED',
    'PYPL', 'COHR', 'DDOG', 'PEG', 'CMG', 'WAB', 'FITB', 'EQT', 'AMP', 'VTR', 'ODFL', 'AIG',
    'EBAY', 'CBRE', 'ROK', 'MSCI', 'DHI', 'PCG', 'TKO', 'WEC', 'NUE', 'HIG', 'KDP', 'ROP',
    'TTWO', 'VMC', 'LVS', 'MLM', 'ADM', 'LYV', 'STT', 'CCI', 'XYZ', 'ACGL', 'PAYX', 'AXON',
    'KVUE', 'CCL', 'HAL', 'SYY', 'WDAY', 'PRU', 'TPL', 'SATS', 'MCHP', 'RMD', 'KMB', 'DVN',
    'A', 'CPRT', 'CHTR', 'GEHC', 'EME', 'ATO', 'HBAN', 'DTE', 'AEE', 'NRG', 'IR', 'MTB',
    'DOW', 'HPE', 'OTIS', 'CBOE', 'FE', 'FISV', 'IRM', 'CTSH', 'WAT', 'PPL', 'VICI', 'XYL',
    'IQV', 'CNP', 'EXPE', 'RJF', 'TPR', 'EIX', 'UAL', 'BIIB', 'WTW', 'CTRA', 'DOV', 'EXR',
    'AWK', 'TDY', 'EXE', 'LYB', 'KHC', 'STZ', 'JBL', 'DG', 'VRSK', 'ES', 'ROL', 'MTD',
    'NTRS', 'HUBB', 'STLD', 'WRB', 'FICO', 'BG', 'CFG', 'FIS', 'CINF', 'EL', 'FOX', 'FOXA',
    'TSCO', 'DXCM', 'ARES', 'CMS', 'OMC', 'PPG', 'VRSN', 'SYF', 'AVB', 'Q', 'DRI', 'CHD',
    'ULTA', 'BRO', 'NI', 'EQR', 'TSN', 'PHM', 'LH', 'L', 'ON', 'RF', 'DGX', 'STE',
    'EFX', 'VLTO', 'KEY', 'WSM', 'CF', 'LEN', 'ALB', 'DLTR', 'SW', 'HUM', 'NTAP', 'CPAY',
    'FSLR', 'RL', 'GIS', 'TROW', 'JBHT', 'LDOS', 'CHRW', 'PFG', 'BR', 'EXPD', 'MRNA', 'EVRG',
    'PKG', 'GPN', 'IP', 'SNA', 'LNT', 'NVR', 'IFF', 'DD', 'INCY', 'LUV', 'SBAC', 'WST',
    'LULU', 'AMCR', 'ZBH', 'HPQ', 'WY', 'CSGP', 'HOLX', 'FTV', 'PTC', 'AKAM', 'FFIV', 'CNC',
    'ESS', 'BALL', 'LII', 'APA', 'CDW', 'KIM', 'TXT', 'INVH', 'VTRS', 'TYL', 'J', 'PODD',
    'TRMB', 'NWSA', 'HII', 'NWS', 'MKC', 'GPC', 'NDSN', 'APTV', 'MAA', 'PNR', 'IEX', 'REG',
    'COO', 'DECK', 'CPT', 'BBY', 'EG', 'HST', 'AVY', 'HRL', 'HAS', 'SMCI', 'CLX', 'ALLE',
    'BF.B', 'PNW', 'MAS', 'BEN', 'DOC', 'ALGN', 'DPZ', 'ERIE', 'JKHY', 'IT', 'UHS', 'GEN',
    'UDR', 'SOLV', 'GDDY', 'GNRC', 'GL', 'AIZ', 'SWK', 'TTD', 'IVZ', 'DVA', 'SJM', 'WYNN',
    'AES', 'PSKY', 'ZBRA', 'RVTY', 'MGM', 'FRT', 'AOS', 'BLDR', 'TAP', 'HSIC', 'BXP', 'BAX',
    'TECH', 'NCLH', 'ARE', 'CRL', 'MOS', 'SWKS', 'FDS', 'CAG', 'POOL', 'EPAM', 'CPB',
]

TOP_50_CRYPTO_BASES = [
    "BTC", "ETH", "USDT", "BNB", "XRP", "USDC", "SOL", "TRX", "DOGE", "HYPE",
    "BCH", "LEO", "ADA", "LINK", "XMR", "USDE", "CC", "XLM", "DAI", "USD1",
    "LTC", "PYUSD", "HBAR", "AVAX", "ZEC", "SHIB", "SUI", "TAO", "TON", "M",
    "CRO", "WLFI", "XAUT", "PAXG", "MNT", "UNI", "DOT", "USDG", "OKB", "PI",
    "SKY", "ASTER", "NEAR", "AAVE", "RLUSD", "USDD", "PEPE", "BGB", "ONDO", "SIREN",
]

PREFERRED_CRYPTO_USD_EXCHANGES = [
    "COINBASE",
    "KRAKEN",
    "BITSTAMP",
    "GEMINI",
    "BITFINEX",
    "CRYPTOCOM",
    "BYBIT",
    "OKX",
]

STOCK_SCREENERS = [
    "america",
]

STOCK_COLUMNS = [
    "name",
    "exchange",
    "sector",
    "industry",
    "type",
]

CRYPTO_COLUMNS = [
    "name",
    "exchange",
]

class TradingViewClient:

    def __init__(
        self,
        default_batch_size: int = 500,
        default_timeout: int = 10,
        analysis_batch_size: int = 10,
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
                raise ValueError(
                    "All stocks in a batch must have the same screener."
                )

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

    def _get_stock_rows(self, seen: set) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        sp500_order = [symbol.upper() for symbol in SP500_SYMBOLS]
        sp500_set = set(sp500_order)
        buckets: Dict[str, List[Dict[str, Any]]] = {symbol: [] for symbol in sp500_order}

        for screener in STOCK_SCREENERS:
            try:
                query = (
                    Query()
                    .select(*STOCK_COLUMNS)
                    .set_markets(screener)
                    .limit(5000)
                )

                _, df = query.get_scanner_data()

            except Exception:
                logger.exception(
                    "TradingView screener query failed for screener=%s",
                    screener,
                )
                continue

            if df is None or df.empty:
                continue

            for _, row in df.iterrows():
                ticker = self._extract_symbol(row.get("ticker"))
                exchange = self._clean_value(row.get("exchange"))

                if not ticker or not exchange:
                    continue

                ticker_upper = ticker.upper()
                exchange_upper = exchange.upper()

                if ticker_upper not in sp500_set:
                    continue

                buckets[ticker_upper].append({
                    "ticker": ticker_upper,
                    "name": self._clean_value(row.get("name")),
                    "screener": screener,
                    "exchange": exchange_upper,
                    "category": self._clean_value(row.get("type")),
                    "sector": self._clean_value(row.get("sector")),
                    "industry": self._clean_value(row.get("industry")),
                    "image_url": None,
                })

        for symbol in sp500_order:
            candidates = buckets.get(symbol, [])
            if not candidates:
                logger.warning("No TradingView row found for SP500 symbol=%s", symbol)
                continue

            # If multiple rows exist for the same ticker, keep the first unseen one.
            for candidate in candidates:
                unique_key = (candidate["ticker"], candidate["exchange"], candidate["screener"])
                if unique_key in seen:
                    continue

                seen.add(unique_key)
                rows.append(candidate)
                break

        return rows

    def _get_crypto_rows(self, seen: set) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        desired_symbols = [symbol.upper() for symbol in TOP_50_CRYPTO_BASES]
        desired_set = set(desired_symbols)
        buckets: Dict[str, List[Dict[str, Any]]] = {symbol: [] for symbol in desired_symbols}

        try:
            query = (
                Query()
                .select("name", "exchange")
                .set_markets("crypto")
                .limit(5000)
            )

            _, df = query.get_scanner_data()

            if df is None or df.empty:
                return rows

            for _, row in df.iterrows():
                ticker = self._extract_symbol(row.get("ticker"))
                exchange = self._clean_value(row.get("exchange"))
                name = self._clean_value(row.get("name"))

                if not ticker or not exchange:
                    continue

                ticker = ticker.upper()
                exchange = exchange.upper()

                if not ticker.endswith("USD"):
                    continue

                base_symbol = ticker[:-3]
                if base_symbol not in desired_set:
                    continue

                buckets[base_symbol].append({
                    "ticker": ticker,
                    "name": name,
                    "exchange": exchange,
                })

            for base_symbol in desired_symbols:
                candidates = buckets.get(base_symbol, [])
                if not candidates:
                    logger.warning(
                        "No TradingView USD pair found for top-50 crypto symbol=%s",
                        base_symbol,
                    )
                    continue

                candidates.sort(
                    key=lambda item: (
                        PREFERRED_CRYPTO_USD_EXCHANGES.index(item["exchange"])
                        if item["exchange"] in PREFERRED_CRYPTO_USD_EXCHANGES
                        else 999,
                        item["exchange"],
                    )
                )

                for candidate in candidates:
                    unique_key = (candidate["ticker"], candidate["exchange"], "crypto")
                    if unique_key in seen:
                        continue

                    seen.add(unique_key)
                    rows.append({
                        "ticker": candidate["ticker"],
                        "name": candidate["name"],
                        "screener": "crypto",
                        "exchange": candidate["exchange"],
                        "category": "crypto",
                        "sector": None,
                        "industry": None,
                        "image_url": None,
                    })
                    break

            return rows

        except Exception as exc:
            raise RuntimeError(f"Failed to fetch crypto rows: {str(exc)}") from exc