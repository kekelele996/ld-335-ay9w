from datetime import datetime
from zoneinfo import ZoneInfo

BUSINESS_TIMEZONE = ZoneInfo("Asia/Shanghai")


def business_now() -> datetime:
    return datetime.now(BUSINESS_TIMEZONE).replace(tzinfo=None)
