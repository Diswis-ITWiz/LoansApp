import math
from datetime import datetime, timedelta

import numpy as np
from django.utils import timezone
from django.utils.timezone import localtime

from base.constants import (
    OFFICE_OPEN_HOUR,
    OFFICE_OPEN_MINUTE,
    REGULAR_OFFICE_DAY_DURATION,
    WEEKDAY_WEDNESDAY,
    WEDNESDAY_OFFICE_DAY_DURATION,
)
from base.models import BlockOutDate, BlockOutTime, Client
from base.services.calendar_rules import get_closing_time, if_no_classes


def get_item_type_a_overdue_days(due_date: datetime, client: Client) -> int:
    formatted_due_date = due_date.date()
    return_date = timezone.localtime(timezone.now()).date()
    blocked_days = BlockOutDate.objects.filter(dateBlocked__range=[formatted_due_date, return_date]).count()

    if return_date <= formatted_due_date:
        return 0
    elif client.hasWednesdayClasses:
        current_date = formatted_due_date + timedelta(days=1)
        total_days = 1
        while current_date != return_date:
            if not if_no_classes(current_date, client.hasWednesdayClasses):
                total_days += 1
            current_date += timedelta(days=1)
        return total_days
    else:
        business_days = np.busday_count(formatted_due_date, return_date)
        return business_days + 1 - blocked_days


def get_item_type_b_overdue_time(due_date: datetime, client: Client) -> tuple[int, int]:
    return_date = timezone.localtime(timezone.now())

    if return_date <= localtime(due_date):
        return 0, 0

    if return_date > localtime(due_date) and return_date.date() == due_date.date():
        difference = return_date - localtime(due_date)
        blocked_time_on_return_date = BlockOutTime.objects.filter(dateBlocked=return_date.date())

        if blocked_time_on_return_date.exists() and (
            localtime(due_date) <= blocked_time_on_return_date[0].timeStart
            and blocked_time_on_return_date[0].timeEnd <= return_date
        ):
            blocked_time_span = blocked_time_on_return_date[0].timeEnd - blocked_time_on_return_date[0].timeStart
            difference -= blocked_time_span

        overdue_hours = math.floor(difference.total_seconds() // 3600)
        overdue_minutes = math.floor((difference.seconds // 60) % 60)
        return overdue_hours, overdue_minutes

    due_date_closing_time = get_closing_time(localtime(due_date))
    overdue_time = due_date_closing_time - due_date

    due_date_blocked_time = BlockOutTime.objects.filter(dateBlocked=due_date.date())
    if due_date_blocked_time.exists() and (
        localtime(due_date) <= due_date_blocked_time[0].timeStart
        and due_date_blocked_time[0].timeEnd <= due_date_closing_time
    ):
        blocked_time_span = due_date_blocked_time[0].timeEnd - due_date_blocked_time[0].timeStart
        overdue_time -= blocked_time_span

    day_between = localtime(due_date) + timedelta(days=1)
    while return_date.date() > day_between.date():
        if not if_no_classes(day_between, client.hasWednesdayClasses):
            office_hours = (
                REGULAR_OFFICE_DAY_DURATION
                if day_between.weekday() != WEEKDAY_WEDNESDAY
                else WEDNESDAY_OFFICE_DAY_DURATION
            )
            day_between_blocked_time = BlockOutTime.objects.filter(dateBlocked=day_between.date())
            if day_between_blocked_time.exists():
                day_between_time_span = day_between_blocked_time[0].timeEnd - day_between_blocked_time[0].timeStart
                office_hours -= day_between_time_span
            overdue_time += office_hours
        day_between += timedelta(days=1)

    return_date_opening_time = return_date.replace(
        hour=OFFICE_OPEN_HOUR,
        minute=OFFICE_OPEN_MINUTE,
        second=0,
        microsecond=0,
    )
    return_date_difference = return_date - return_date_opening_time
    return_date_blocked_time = BlockOutTime.objects.filter(dateBlocked=return_date.date())
    if return_date_blocked_time.exists() and (
        return_date_opening_time <= return_date_blocked_time[0].timeStart
        and return_date_blocked_time[0].timeEnd <= return_date
    ):
        return_date_blocked_time_difference = (
            return_date_blocked_time[0].timeEnd - return_date_blocked_time[0].timeStart
        )
        return_date_difference -= return_date_blocked_time_difference

    overdue_time += return_date_difference
    overdue_hours = math.floor(overdue_time.total_seconds() // 3600)
    overdue_minutes = math.floor((overdue_time.seconds // 60) % 60)
    return overdue_hours, overdue_minutes


getItemTypeAOverdueDays = get_item_type_a_overdue_days
getItemTypeBOverdueTime = get_item_type_b_overdue_time
