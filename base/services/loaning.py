from dataclasses import dataclass
from datetime import datetime, timedelta

from django.db import transaction as db_transaction
from django.utils import timezone
from django.utils.timezone import localtime

from base.constants import (
    ItemType,
    REGULAR_CLOSING_HOUR,
    TYPE_B_LOAN_DURATION,
    TYPE_B_NEXT_DAY_DUE_HOUR,
    TYPE_B_NEXT_DAY_DUE_MINUTE,
)
from base.models import BlockOutTime, Client, LoanItem, Transaction
from base.services.calendar_rules import get_closing_time, if_no_classes
from base.services.item_types import check_item_type


@dataclass(frozen=True)
class LoanDueDate:
    item_type: str
    loaned_at: datetime
    due_date: datetime


def _apply_blockout_time_overlap(challenger_time):
    try:
        blocked_time = BlockOutTime.objects.get(dateBlocked=challenger_time.date())
    except BlockOutTime.DoesNotExist:
        return challenger_time, False

    start_time = localtime(blocked_time.timeStart)
    end_time = localtime(blocked_time.timeEnd)
    if not start_time <= challenger_time <= end_time:
        return challenger_time, False

    adjusted_due_date = end_time + TYPE_B_LOAN_DURATION
    closing_time = challenger_time.replace(hour=REGULAR_CLOSING_HOUR)
    return adjusted_due_date, adjusted_due_date >= closing_time


def _advance_to_next_11am(candidate_due_date):
    return (candidate_due_date + timedelta(days=1)).replace(
        hour=TYPE_B_NEXT_DAY_DUE_HOUR,
        minute=TYPE_B_NEXT_DAY_DUE_MINUTE,
        second=0,
        microsecond=0,
    )


def _normalize_type_b_due_date(candidate_due_date, has_wednesday_classes):
    while True:
        if if_no_classes(candidate_due_date, has_wednesday_classes):
            candidate_due_date = _advance_to_next_11am(candidate_due_date)
            continue

        candidate_due_date, overlaps_past_closing = _apply_blockout_time_overlap(candidate_due_date)
        if overlaps_past_closing:
            candidate_due_date = _advance_to_next_11am(candidate_due_date)
            continue

        return candidate_due_date


def calculate_loan_due_date(client: Client, item: LoanItem, loaned_at=None) -> LoanDueDate:
    loaned_at = loaned_at or timezone.localtime(timezone.now())
    closing_time = get_closing_time(loaned_at)
    due_date = loaned_at
    item_type = check_item_type(item.itemCat)

    if item_type == ItemType.A:
        due_date += timedelta(days=1)
        while if_no_classes(due_date, client.hasWednesdayClasses):
            due_date += timedelta(days=1)
        due_date = get_closing_time(due_date)
    else:
        due_date += TYPE_B_LOAN_DURATION
        if due_date >= closing_time:
            due_date = _advance_to_next_11am(due_date)
        due_date = _normalize_type_b_due_date(due_date, client.hasWednesdayClasses)

    return LoanDueDate(item_type=item_type, loaned_at=loaned_at, due_date=due_date)


@db_transaction.atomic
def create_loan_transaction(
    *,
    client: Client,
    item: LoanItem,
    dsws_member_name: str,
    remarks: str,
    date_loaned,
    due_date,
) -> Transaction:
    item = LoanItem.objects.select_for_update().get(itemCat=item.itemCat)
    client = Client.objects.select_for_update().get(clientId=client.clientId)

    loan_transaction = Transaction.objects.create(
        clientId=client,
        itemCat=item,
        dswsMemLoanName=dsws_member_name,
        loanRemarks=remarks,
        dateLoaned=date_loaned,
        dueDate=due_date,
    )

    client.lastBorrowedDate = date_loaned
    client.lastBorrowedItem = item
    client.borrowing = True
    client.save(update_fields=["lastBorrowedDate", "lastBorrowedItem", "borrowing"])

    item.lastClient = client.clientId
    item.status = LoanItem.LOANEDOUT
    item.save(update_fields=["lastClient", "status"])

    return loan_transaction
