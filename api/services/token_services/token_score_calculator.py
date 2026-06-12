class TokenScoreCalculator:
    @staticmethod
    def get_support_resistance_score(support, resistance, price, support_resistance_broken=None):
        if support is None or resistance is None or price is None:
            return 0

        if price > resistance:
            return 2
        if price < support:
            return -2

        if support_resistance_broken:
            if support_resistance_broken.support == resistance:
                return -2
            if support_resistance_broken.resistance == support:
                return 2

        return 0

    @staticmethod
    def get_ma_score(ma, price):
        if ma is None or price is None:
            return 0
        if price > ma:
            return 1
        if price < ma:
            return -1
        return 0

    @staticmethod
    def get_macd_velocity(macd, previous_macd):
        if macd is None or previous_macd is None:
            return None
        return float(macd) - float(previous_macd)

    @staticmethod
    def get_macd_score(macd, macd_velocity):
        if macd is None or macd_velocity is None:
            return None
        if float(macd) > 0 and macd_velocity > 0:
            return 2
        if float(macd) < 0 and macd_velocity < 0:
            return -2
        return 0

    @staticmethod
    def get_current_price(close, high, low):
        if close is None or high is None or low is None:
            return None
        return (close + high + low) / 3

    @staticmethod
    def calculate_total_score(
        support_resistance_score,
        ma_50d_score,
        ma_100d_score,
        ma_200d_score,
        daily_macd_score,
        weekly_macd_score,
    ):
        if daily_macd_score is None or weekly_macd_score is None:
            return None

        return (
            support_resistance_score
            + ma_50d_score
            + ma_100d_score
            + ma_200d_score
            + daily_macd_score
            + weekly_macd_score
        )

    @staticmethod
    def calculate_direction(total_score):
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

    @staticmethod
    def round_significant(num, sig_digits=3):
        if num is None:
            return num
        elif num > 1 or num < -1:
            return round(num, sig_digits)
        elif num == 0:
            return round(num)
        else:
            return round(num, sig_digits)
