from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django import forms
from django.db import transaction as db_transaction
from django.utils import timezone
from django.utils.timezone import localtime

from base.constants import ItemType
from base.models import Client, LoanItem, Transaction
from base.services.item_types import check_item_type
from base.services.overdue import get_item_type_a_overdue_days, get_item_type_b_overdue_time
from base.services.penalties import (
    apply_type_a_penalty,
    apply_type_b_penalty,
    calculate_type_a_penalty,
    calculate_type_b_penalty,
)


@dataclass(frozen=True)
class ReturnAssessment:
    item_type: str
    penalty: str
    initial_data: dict[str, object]
    overdue_days: int = 0
    overdue_hours: int = 0
    overdue_minutes: int = 0


def _client_display_name(client: Client) -> str:
    middle_initial = client.middleInitial or ""
    return f"{client.lastName}, {client.firstName}, {middle_initial}"


def assess_return(loan_transaction: Transaction) -> ReturnAssessment:
    client = loan_transaction.clientId
    loaned_item = loan_transaction.itemCat
    item_type = check_item_type(loaned_item.itemCat)

    initial_data = {
        "clientIDNo": client.clientId,
        "clientName": _client_display_name(client),
        "itemCat": loaned_item.itemCat,
        "itemType": item_type,
        "dueDate": localtime(loan_transaction.dueDate),
    }

    if item_type == ItemType.A:
        overdue_days = get_item_type_a_overdue_days(localtime(loan_transaction.dueDate), client)
        penalty = calculate_type_a_penalty(overdue_days, client)
        initial_data["overDueDays"] = overdue_days
        return ReturnAssessment(
            item_type=item_type,
            penalty=penalty,
            initial_data=initial_data,
            overdue_days=overdue_days,
        )

    overdue_hours, overdue_minutes = get_item_type_b_overdue_time(localtime(loan_transaction.dueDate), client)
    penalty = calculate_type_b_penalty(overdue_hours, overdue_minutes, client)
    initial_data.update(
        {
            "overDueHours": overdue_hours,
            "overDueMinutes": overdue_minutes,
        }
    )
    return ReturnAssessment(
        item_type=item_type,
        penalty=penalty,
        initial_data=initial_data,
        overdue_hours=overdue_hours,
        overdue_minutes=overdue_minutes,
    )


def enable_overdue_override(form: forms.Form, item_type: str) -> None:
    if item_type == ItemType.A:
        form.fields["overDueDays"].widget.attrs.pop("readonly", None)
    else:
        form.fields["overDueHours"].widget.attrs.pop("readonly", None)
        form.fields["overDueMinutes"].widget.attrs.pop("readonly", None)


@db_transaction.atomic
def complete_return(
    loan_transaction: Transaction,
    item_type: str,
    cleaned_data: dict[str, Any],
    returned_at: datetime | None = None,
) -> Transaction:
    loan_transaction = (
        Transaction.objects.select_for_update()
        .select_related("clientId", "itemCat")
        .get(id=loan_transaction.id)
    )
    client = loan_transaction.clientId
    loaned_item = loan_transaction.itemCat
    returned_at = returned_at or timezone.localtime(timezone.now())

    if item_type == ItemType.A:
        apply_type_a_penalty(cleaned_data["overDueDays"], client)
        loan_transaction.overdueDays = cleaned_data["overDueDays"]
    else:
        apply_type_b_penalty(cleaned_data["overDueHours"], cleaned_data["overDueMinutes"], client)
        loan_transaction.overdueHours = cleaned_data["overDueHours"]
        loan_transaction.overdueMinutes = cleaned_data["overDueMinutes"]

    loan_transaction.dateReturned = returned_at
    loan_transaction.dswsMemRetName = cleaned_data["reciever"]
    loan_transaction.returnRemarks = cleaned_data["remarks"]
    loan_transaction.status = Transaction.COMPLETE
    loan_transaction.save()

    client.borrowing = False
    client.lastBorrowedDate = returned_at
    client.save(update_fields=["borrowing", "lastBorrowedDate"])

    loaned_item.status = LoanItem.INSTORAGE
    loaned_item.save(update_fields=["status"])

    return loan_transaction
