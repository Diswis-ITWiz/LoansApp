from django.db.models import Q

from base.models import Client, Transaction


def get_loan_client_lookup_context(client_id: str) -> dict[str, object]:
    if client_id == "":
        return {}

    if not Client.objects.filter(clientId__exact=client_id).exists():
        return {"input_validity": True}

    client = Client.objects.select_related("lastBorrowedItem").get(clientId__exact=client_id)
    transactions = Transaction.objects.select_related("clientId", "itemCat").filter(clientId__exact=client_id)
    context = {
        "client": client,
        "borrowCount": transactions.count(),
        "latest_transaction": transactions.first(),
    }

    if client.borrowing:
        context.update(
            {
                "dueDate": transactions[0].dueDate,
                "borrowing": True,
            }
        )
    elif client.gradWaiting:
        context.update({"gradWaiting": True})
    elif client.blackListed or client.temporaryBlackList:
        context.update({"blackListed": True})

    return context


def get_return_client_lookup_context(client_id: str) -> dict[str, object]:
    if client_id == "":
        return {}

    try:
        client = Client.objects.select_related("lastBorrowedItem").get(clientId__exact=client_id)
    except Client.DoesNotExist:
        return {"noClient": True}

    try:
        loan_transaction = Transaction.objects.select_related("clientId", "itemCat").get(
            Q(clientId__exact=client.clientId) & Q(status__exact=Transaction.ONGOING)
        )
        return {"client": client, "transaction": loan_transaction}
    except Transaction.DoesNotExist:
        return {"client": client, "noTransaction": True}
