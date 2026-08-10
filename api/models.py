from django.db import models
from django.conf import settings

class Stock(models.Model):
    ticker = models.CharField(max_length=200)
    name = models.CharField(max_length=200, blank=True, null=True)
    screener = models.CharField(max_length=200)
    exchange = models.CharField(max_length=200)
    category = models.CharField(max_length=200, null=True)
    sector = models.CharField(max_length=200, null=True)
    industry = models.CharField(max_length=200, null=True)
    image_url = models.CharField(max_length=500, blank=True, null=True)
    in_use = models.BooleanField(default=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "stocks"

    def __str__(self):
        return f"{self.ticker} ({self.exchange})"

class StockData(models.Model):
    stock = models.ForeignKey(
        Stock, 
        on_delete=models.CASCADE,  # Deletes related StockData when Stock is deleted
        related_name='stock_data'  # Enables reverse lookup: Stock.stock_data.all()
    )
    date = models.DateTimeField()
    current_price = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    recommend_all = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    recommend_ma = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    recommend_other = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    rsi = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    yesterday_rsi = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    stoch_k = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    stoch_d =  models.DecimalField(max_digits=15, decimal_places=6, null=True)
    yesterday_stoch_k = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    yesterday_stoch_d =  models.DecimalField(max_digits=15, decimal_places=6, null=True)
    commodity_channel_index = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    yesterday_commodity_channel_index = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    adx = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    adx_di_positive = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    adx_di_negative = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    yesterday_adx_di_positive = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    yesterday_adx_di_negative = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    awesome_oscillator = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    yesterday_awesome_oscillator = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    two_days_ago_awesome_oscillator = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    momentum = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    yesterday_momentum = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    daily_macd_line = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    daily_macd_signal = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    daily_macd_histogram = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    weekly_macd_line = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    weekly_macd_signal = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    weekly_macd_histogram = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    stoch_rsi = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    stoch_rsi_k = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    williams_r_recommendation = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    williams_r = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    bollinger_bands_recommendation = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    bollinger_bands_power = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    bollinger_bands_lower = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    bollinger_bands_upper = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    ultimate_oscillator_recommendation = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    ultimate_oscillator = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    close = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    ema_5 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    ema_10 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    ema_20 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    ema_30 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    ema_50 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    ema_100 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    ema_200 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    sma_5 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    sma_10 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    sma_20 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    sma_30 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    sma_50 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    sma_100 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    sma_200 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    ichimoku_recommendation = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    ichimoku_base_line = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    volume_weighted_moving_average = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    volume_weighted_moving_average_recommendation = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    hull_moving_average = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    hull_moving_average_recommendation = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_classic_s3 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_classic_s2 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_classic_s1 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_classic_middle = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_classic_r1 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_classic_r2 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_classic_r3 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_fibonacci_s3 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_fibonacci_s2 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_fibonacci_s1 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_fibonacci_middle = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_fibonacci_r1 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_fibonacci_r2 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_fibonacci_r3 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_camarilla_s3 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_camarilla_s2 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_camarilla_s1 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_camarilla_middle = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_camarilla_r1 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_camarilla_r2 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_camarilla_r3 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_woodie_s3 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_woodie_s2 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_woodie_s1 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_woodie_middle = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_woodie_r1 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_woodie_r2 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_woodie_r3 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_demark_s1 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_demark_middle = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    pivot_demark_r1 = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    parabolic_sar = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    open = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    volume = models.DecimalField(max_digits=20, decimal_places=6, null=True)
    low = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    high = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    price_change = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    support = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    resistance = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    support_resistance_score = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    ma_100d_score = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    ma_200d_score = models.DecimalField(max_digits=15, decimal_places=6, null=True) 
    ma_50d_score = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    daily_macd_velocity = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    daily_macd_score = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    weekly_macd_velocity = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    weekly_macd_score = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    original_strategy_score = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    macd_strategy_score = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    strategy_three_score = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    market_regime = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        db_table = "stock_data"

    def __str__(self):
        return f"Data for {self.stock.ticker} on {self.date}"

class Wishlist(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlist_items",
    )
    stock = models.ForeignKey(
        "Stock",
        on_delete=models.CASCADE,
        related_name="wishlisted_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "wishlists"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "stock"],
                name="unique_user_stock_wishlist",
            )
        ]

    def __str__(self):
        return f"{self.user_id} - {self.stock_id}"


class SyncJobLock(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_running = models.BooleanField(default=False)
    started_at = models.DateTimeField(blank=True, null=True)
    last_finished_at = models.DateTimeField(blank=True, null=True)
    last_status = models.BooleanField(blank=True, null=True)
    last_message = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sync_job_locks"

    def __str__(self):
        return f"{self.name} ({'running' if self.is_running else 'idle'})"

