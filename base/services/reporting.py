from django.db import transaction as db_transaction

from base.models import Client, LoanItem, Transaction


@db_transaction.atomic
def report_item(client: Client, fine_amount, report_type):
    client = Client.objects.select_for_update().get(clientId=client.clientId)
    reported_item = client.lastBorrowedItem

    loan_transaction = Transaction.objects.select_for_update().filter(
        clientId=client,
        itemCat=reported_item,
    ).first()

    client.fineAmount = fine_amount
    client.borrowing = False
    client.save(update_fields=["fineAmount", "borrowing"])

    if reported_item:
        reported_item = LoanItem.objects.select_for_update().get(itemCat=reported_item.itemCat)
        reported_item.status = report_type
        reported_item.save(update_fields=["status"])

    if loan_transaction:
        loan_transaction.status = report_type
        loan_transaction.save(update_fields=["status"])

    return loan_transaction
