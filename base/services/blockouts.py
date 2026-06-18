from datetime import date, datetime, timedelta

from base.constants import FINALS_BLOCKOUT_DESCRIPTION
from base.models import BlockOutDate, BlockOutTime, Client


def block_finals_weekdays(first_day: str) -> int:
    current_date = datetime.strptime(first_day, "%Y-%m-%d")
    current_weekday = current_date.weekday()
    created_count = 0

    while True:
        _, created = BlockOutDate.objects.get_or_create(
            dateBlocked=current_date.date(),
            defaults={"description": FINALS_BLOCKOUT_DESCRIPTION},
        )
        if created:
            created_count += 1

        current_date += timedelta(days=1)
        current_weekday += 1
        if current_weekday == 5:
            break

    return created_count


def block_graduating_clients(client_model: type[Client]) -> int:
    return client_model.objects.filter(graduating=True).update(gradWaiting=True)


def create_blockout_date(block_date: date, description: str) -> bool:
    if BlockOutDate.objects.filter(dateBlocked=block_date).exists():
        return False

    BlockOutDate.objects.create(
        dateBlocked=block_date,
        description=description,
    )
    return True


def create_blockout_time(date_input: str, start_time: str, end_time: str, description: str) -> bool:
    blocked_date = datetime.strptime(date_input, "%Y-%m-%d")
    parsed_start_time = datetime.strptime(start_time, "%H:%M")
    parsed_end_time = datetime.strptime(end_time, "%H:%M")
    final_start_time = parsed_start_time.replace(
        year=blocked_date.year,
        month=blocked_date.month,
        day=blocked_date.day,
    )
    final_end_time = parsed_end_time.replace(
        year=blocked_date.year,
        month=blocked_date.month,
        day=blocked_date.day,
    )

    if BlockOutTime.objects.filter(dateBlocked=blocked_date.date()).exists():
        return False

    BlockOutTime.objects.create(
        dateBlocked=blocked_date.date(),
        description=description,
        timeStart=final_start_time,
        timeEnd=final_end_time,
    )
    return True
