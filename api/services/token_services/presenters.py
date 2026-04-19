class TokenPresenter:
    def __init__(self, calculator):
        self.calculator = calculator

    def present_latest_stock_item(self, stock_data):
        total_score = self.calculator.round_significant(stock_data.total_score)
        current_price = self.calculator.round_significant(stock_data.current_price)
        support_resistance_score = self.calculator.round_significant(
            stock_data.support_resistance_score
        )
        daily_macd_velocity = self.calculator.round_significant(
            stock_data.daily_macd_velocity
        )
        daily_macd_score = self.calculator.round_significant(stock_data.daily_macd_score)
        weekly_macd_velocity = self.calculator.round_significant(
            stock_data.weekly_macd_velocity
        )
        weekly_macd_score = self.calculator.round_significant(
            stock_data.weekly_macd_score
        )

        ma_50d_score = self.calculator.round_significant(stock_data.ma_50d_score)
        ma_100d_score = self.calculator.round_significant(stock_data.ma_100d_score)
        ma_200d_score = self.calculator.round_significant(stock_data.ma_200d_score)
        ma_score = self.calculator.round_significant(
            (stock_data.ma_50d_score or 0)
            + (stock_data.ma_100d_score or 0)
            + (stock_data.ma_200d_score or 0)
        )

        daily_profit = None
        daily_return = None
        if stock_data.current_price is not None and stock_data.price_change is not None:
            daily_profit_raw = stock_data.current_price * (stock_data.price_change / 100)
            daily_profit = self.calculator.round_significant(daily_profit_raw)

            denominator = daily_profit_raw + stock_data.current_price
            if denominator != 0:
                daily_return = self.calculator.round_significant(
                    daily_profit_raw / denominator
                )

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

    def present_stock_detail_item(self, stock_data):
        return {
            "id": stock_data.id,
            "date": stock_data.date,
            "ticker": stock_data.stock.ticker,
            "exchange": stock_data.stock.exchange,
            "screener": stock_data.stock.screener,
            "current_price": self.calculator.round_significant(stock_data.current_price),
            "resistance": self.calculator.round_significant(stock_data.resistance),
            "support": self.calculator.round_significant(stock_data.support),
            "support_resistance_score": self.calculator.round_significant(
                stock_data.support_resistance_score
            ),
            "daily_macd_histogram": self.calculator.round_significant(
                stock_data.daily_macd_histogram
            ),
            "daily_macd_velocity": self.calculator.round_significant(
                stock_data.daily_macd_velocity
            ),
            "daily_macd_score": self.calculator.round_significant(
                stock_data.daily_macd_score
            ),
            "weekly_macd_histogram": self.calculator.round_significant(
                stock_data.weekly_macd_histogram
            ),
            "weekly_macd_velocity": self.calculator.round_significant(
                stock_data.weekly_macd_velocity
            ),
            "weekly_macd_score": self.calculator.round_significant(
                stock_data.weekly_macd_score
            ),
            "total_score": self.calculator.round_significant(stock_data.total_score),
            "direction": stock_data.direction,
        }
