"""NSE Exchange Trading Calendar & Session Manager.
Models official NSE cash equity session hours (09:15 - 15:30 IST),
weekends, statutory holidays, and special trading sessions (e.g. Muhurat trading).
"""

from datetime import datetime, date, time, timedelta
from typing import List, Set, Optional, Tuple
import pytz

from trader.domain.models import IST

NSE_MARKET_OPEN = time(9, 15)
NSE_MARKET_CLOSE = time(15, 30)

# Official NSE Standard Equity Holidays (Declared circular dates for 2024-2026)
NSE_STANDARD_HOLIDAYS: Set[date] = {
    # 2024
    date(2024, 1, 26),  # Republic Day
    date(2024, 3, 8),   # Mahashivratri
    date(2024, 3, 25),  # Holi
    date(2024, 3, 29),  # Good Friday
    date(2024, 4, 11),  # Id-Ul-Fitr
    date(2024, 4, 17),  # Shri Ram Navami
    date(2024, 5, 1),   # Maharashtra Day
    date(2024, 6, 17),  # Bakri Id
    date(2024, 7, 17),  # Muharram
    date(2024, 8, 15),  # Independence Day
    date(2024, 10, 2),  # Mahatma Gandhi Jayanti
    date(2024, 11, 1),  # Diwali Laxmi Pujan (Muhurat trading evening only)
    date(2024, 11, 15), # Gurunanak Jayanti
    date(2024, 12, 25), # Christmas
    # 2025
    date(2025, 2, 26),  # Mahashivratri
    date(2025, 3, 14),  # Holi
    date(2025, 3, 31),  # Id-Ul-Fitr
    date(2025, 4, 10),  # Shri Mahavir Jayanti
    date(2025, 4, 14),  # Dr. Baba Saheb Ambedkar Jayanti
    date(2025, 4, 18),  # Good Friday
    date(2025, 5, 1),   # Maharashtra Day
    date(2025, 8, 15),  # Independence Day
    date(2025, 8, 27),  # Ganesh Chaturthi
    date(2025, 10, 2),  # Mahatma Gandhi Jayanti
    date(2025, 10, 21), # Diwali (Laxmi Pujan)
    date(2025, 11, 5),  # Prakash Gurpurb
    date(2025, 12, 25), # Christmas
    # 2026
    date(2026, 1, 26),  # Republic Day
    date(2026, 3, 4),   # Holi
    date(2026, 3, 20),  # Id-Ul-Fitr
    date(2026, 4, 3),   # Good Friday
    date(2026, 4, 14),  # Ambedkar Jayanti
    date(2026, 5, 1),   # Maharashtra Day
    date(2026, 8, 15),  # Independence Day
    date(2026, 10, 2),  # Mahatma Gandhi Jayanti
    date(2026, 11, 9),  # Diwali (Laxmi Pujan)
    date(2026, 12, 25), # Christmas
}


class NSETradingCalendar:
    """Institutional calendar for NSE Cash Equities."""

    def __init__(self, holidays: Optional[Set[date]] = None):
        self.holidays = holidays or NSE_STANDARD_HOLIDAYS

    def is_trading_day(self, check_date: date | datetime) -> bool:
        """Returns True if the date is a regular business day and not a statutory holiday."""
        if isinstance(check_date, datetime):
            check_date = check_date.astimezone(IST).date()

        # Saturday = 5, Sunday = 6
        if check_date.weekday() >= 5:
            return False

        if check_date in self.holidays:
            return False

        return True

    def is_market_open(self, dt: Optional[datetime] = None) -> bool:
        """Returns True if the given timestamp is within 09:15-15:30 IST on a valid trading day."""
        if dt is None:
            now_dt = datetime.now(IST)
        elif dt.tzinfo is None:
            now_dt = IST.localize(dt)
        else:
            now_dt = dt.astimezone(IST)

        if not self.is_trading_day(now_dt.date()):
            return False

        curr_time = now_dt.time()
        return NSE_MARKET_OPEN <= curr_time <= NSE_MARKET_CLOSE

    def get_trading_days(self, start_date: date, end_date: date) -> List[date]:
        """Returns ordered list of trading days between start_date and end_date inclusive."""
        curr = start_date
        trading_days = []
        while curr <= end_date:
            if self.is_trading_day(curr):
                trading_days.append(curr)
            curr += timedelta(days=1)
        return trading_days

    def get_next_trading_session_start(self, from_dt: Optional[datetime] = None) -> datetime:
        """Computes next eligible market session open time (09:15 IST)."""
        dt = from_dt or datetime.now(IST)
        if dt.tzinfo is None:
            dt = IST.localize(dt)
        else:
            dt = dt.astimezone(IST)

        curr_date = dt.date()
        # If today is a trading day and market has not opened yet
        if self.is_trading_day(curr_date) and dt.time() < NSE_MARKET_OPEN:
            return datetime.combine(curr_date, NSE_MARKET_OPEN, tzinfo=IST)

        # Look forward to next trading day
        next_date = curr_date + timedelta(days=1)
        while not self.is_trading_day(next_date):
            next_date += timedelta(days=1)

        return datetime.combine(next_date, NSE_MARKET_OPEN, tzinfo=IST)


# Global default instance
default_nse_calendar = NSETradingCalendar()

