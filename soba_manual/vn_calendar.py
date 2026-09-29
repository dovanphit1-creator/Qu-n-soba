"""Vietnam wall clock and local public-holiday calendar (offline)."""
from datetime import datetime, timedelta, timezone, date
from functools import lru_cache
from holidays.countries.vietnam import Vietnam

VIETNAM = timezone(timedelta(hours=7), 'Asia/Ho_Chi_Minh')
WEEKDAYS = ('Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy', 'Chủ nhật')


def vn_now():
    return datetime.now(VIETNAM)


@lru_cache(maxsize=8)
def calendar(year):
    days = Vietnam(years=year, observed=True, language='vi')
    # Resolution 28/2026/QH16, effective 2026-07-01.
    if year >= 2026:
        days[date(year, 11, 24)] = 'Ngày Văn hóa Việt Nam'
    # Official 2026 public-sector swapped holiday: 9441/TB-BNV.
    if year == 2026:
        days[date(2026, 1, 2)] = 'Nghỉ hoán đổi dịp Tết Dương lịch'
        days[date(2026, 8, 31)] = 'Nghỉ hoán đổi dịp Quốc khánh'
    return days


def holiday_name(day):
    return calendar(day.year).get(day, '')
