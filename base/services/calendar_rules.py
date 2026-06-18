from base.constants import (
    NO_CLASS_DAYS_WITHOUT_WEDNESDAY,
    REGULAR_CLOSING_HOUR,
    WEEKDAY_WEDNESDAY,
    WEEKEND_DAYS,
    WEDNESDAY_CLOSING_HOUR,
)
from base.models import BlockOutDate


def if_no_classes(due_date, has_wednesday_classes):
    if has_wednesday_classes:
        if due_date.weekday() in WEEKEND_DAYS:
            return True
    else:
        if due_date.weekday() in NO_CLASS_DAYS_WITHOUT_WEDNESDAY:
            return True

    try:
        BlockOutDate.objects.get(dateBlocked=due_date)
        return True
    except BlockOutDate.DoesNotExist:
        return False


def get_closing_time(value):
    if value.weekday() == WEEKDAY_WEDNESDAY:
        return value.replace(hour=WEDNESDAY_CLOSING_HOUR, minute=0, second=0, microsecond=0)
    return value.replace(hour=REGULAR_CLOSING_HOUR, minute=0, second=0, microsecond=0)


ifNoClasses = if_no_classes
getClosingTime = get_closing_time
