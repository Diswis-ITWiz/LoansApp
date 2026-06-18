from __future__ import annotations

from django.contrib import messages
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from base.forms import LoanItemTransactionForm
from base.models import Client, LoanItem, Transaction
from base.services.emailing import send_transaction_email
from base.services.item_types import get_item_type_name
from base.services.loaning import LoanDueDate, calculate_loan_due_date, create_loan_transaction


def build_loan_item_context(
    client: Client,
    items: QuerySet[LoanItem],
    form: LoanItemTransactionForm,
    latest_transaction: Transaction | None,
    selected_item: LoanItem | None = None,
    due_date: LoanDueDate | None = None,
) -> dict[str, object]:
    context = {
        "client": client,
        "items": items,
        "form": form,
        "selectedItem": selected_item.itemCat if selected_item else None,
        "latestTransaction": latest_transaction,
        "calculated": due_date is not None,
    }
    if due_date is not None:
        context["itemType"] = due_date.item_type
    return context


def handle_loan_transaction_get(
    request: HttpRequest,
    client: Client,
    items: QuerySet[LoanItem],
    latest_transaction: Transaction | None,
) -> HttpResponse:
    selected_item_code = request.GET.get('selectedItem', '')
    if selected_item_code == '':
        form = LoanItemTransactionForm()
        context = build_loan_item_context(client, items, form, latest_transaction)
        return render(request, 'base/Home-Item/loan_item_transaction.html', context)

    selected_item = LoanItem.objects.get(itemCat__exact=selected_item_code)
    due_date = calculate_loan_due_date(client, selected_item)
    form = LoanItemTransactionForm(
        initial={
            "itemCat": selected_item.itemCat,
            "dateDue": due_date.due_date,
            "dateLoaned": due_date.loaned_at,
        }
    )
    context = build_loan_item_context(client, items, form, latest_transaction, selected_item, due_date)
    return render(request, 'base/Home-Item/loan_item_transaction.html', context)


def handle_loan_transaction_post(
    request: HttpRequest,
    client: Client,
    items: QuerySet[LoanItem],
    latest_transaction: Transaction | None,
) -> HttpResponse:
    form = LoanItemTransactionForm(request.POST)
    if form.is_valid():
        selected_item = LoanItem.objects.get(itemCat=form.cleaned_data["itemCat"])
        create_loan_transaction(
            client=client,
            item=selected_item,
            dsws_member_name=form.cleaned_data["reciever"],
            remarks=form.cleaned_data["remarks"],
            date_loaned=form.cleaned_data["dateLoaned"],
            due_date=form.cleaned_data["dateDue"],
        )
        messages.success(request, 'Transaction added.')

        email_borrow_date = form.cleaned_data["dateLoaned"].strftime("%m/%d/%Y %I:%M %p")
        email_due_date = form.cleaned_data["dateDue"].strftime("%m/%d/%Y %I:%M %p")
        item_cat_name = get_item_type_name(selected_item.itemCat)
        send_transaction_email(selected_item.itemCat, item_cat_name, email_borrow_date, email_due_date, client)

        return redirect('home')

    context = build_loan_item_context(client, items, form, latest_transaction)
    return render(request, 'base/Home-Item/loan_item_transaction.html', context)
