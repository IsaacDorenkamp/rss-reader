import datetime
from typing import Optional

import config

WEEKDAYS = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6
}


def now(timezone: Optional[datetime.tzinfo] = None) -> datetime.datetime:
    if not timezone:
        timezone = config.TIMEZONE

    return datetime.datetime.now(timezone)


def parse(datetime_str: str) -> datetime.datetime:
    for dateformat in config.DATETIME_FORMATS:
        try:
            return datetime.datetime.strptime(datetime_str, dateformat)
        except ValueError:
            try:
                return datetime.datetime.fromisoformat(datetime_str)
            except ValueError:
                pass

    raise ValueError("Could not parse datetime string '%s'" % datetime_str)
