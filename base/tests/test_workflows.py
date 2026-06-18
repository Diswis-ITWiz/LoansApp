from datetime import datetime

from django.test import TestCase
from django.utils import timezone

from base.constants import ItemType
from base.models import Client, LoanItem, Transaction
from base.services.loaning import create_loan_transaction
from base.services.reporting import report_item
from base.services.returns import complete_return


def aware(year, month, day, hour=0, minute=0):
    return timezone.make_aware(datetime(year, month, day, hour, minute))


def make_client(client_id=100001, **overrides):
    values = {
        "clientId": client_id,
        "lastName": "Garcia",
        "firstName": "Ana",
        "middleInitial": "M",
        "contactNum": "09171234567",
        "email": "ana@example.com",
        "yearLevel": 2,
        "course": "BS CS",
        "hasWednesdayClasses": True,
        "dswsMemRegName": "Member Name",
    }
    values.update(overrides)
    return Client.objects.create(**values)


class LoanWorkflowTests(TestCase):
    def test_create_loan_transaction_updates_transaction_client_and_item(self):
        client = make_client()
        item = LoanItem.objects.create(itemCat="A-01", status=LoanItem.INSTORAGE, description="Adapter")
        date_loaned = aware(2024, 6, 10, 9, 30)
        due_date = aware(2024, 6, 10, 11, 30)

        loan_transaction = create_loan_transaction(
            client=client,
            item=item,
            dsws_member_name="Loan Member",
            remarks="",
            date_loaned=date_loaned,
            due_date=due_date,
        )

        client.refresh_from_db()
        item.refresh_from_db()
        loan_transaction.refresh_from_db()

        self.assertEqual(loan_transaction.clientId, client)
        self.assertEqual(loan_transaction.itemCat, item)
        self.assertEqual(loan_transaction.status, Transaction.ONGOING)
        self.assertTrue(client.borrowing)
        self.assertEqual(client.lastBorrowedDate, date_loaned)
        self.assertEqual(client.lastBorrowedItem, item)
        self.assertEqual(item.status, LoanItem.LOANEDOUT)
        self.assertEqual(item.lastClient, client.clientId)


class ReturnWorkflowTests(TestCase):
    def test_complete_return_updates_transaction_client_item_and_penalty(self):
        client = make_client(borrowing=True)
        item = LoanItem.objects.create(itemCat="B-01", status=LoanItem.LOANEDOUT, description="Bible")
        client.lastBorrowedItem = item
        client.save(update_fields=["lastBorrowedItem"])
        loan_transaction = Transaction.objects.create(
            clientId=client,
            itemCat=item,
            dswsMemLoanName="Loan Member",
            dateLoaned=aware(2024, 6, 10, 9, 30),
            dueDate=aware(2024, 6, 11, 17, 0),
            status=Transaction.ONGOING,
        )
        returned_at = aware(2024, 6, 12, 10, 0)

        complete_return(
            loan_transaction,
            ItemType.A,
            {
                "overDueDays": 2,
                "reciever": "Return Member",
                "remarks": "Returned",
            },
            returned_at=returned_at,
        )

        client.refresh_from_db()
        item.refresh_from_db()
        loan_transaction.refresh_from_db()

        self.assertEqual(loan_transaction.status, Transaction.COMPLETE)
        self.assertEqual(loan_transaction.dateReturned, returned_at)
        self.assertEqual(loan_transaction.overdueDays, 2)
        self.assertEqual(loan_transaction.dswsMemRetName, "Return Member")
        self.assertEqual(loan_transaction.returnRemarks, "Returned")
        self.assertFalse(client.borrowing)
        self.assertEqual(client.lastBorrowedDate, returned_at)
        self.assertEqual(client.warningCount, 1)
        self.assertEqual(item.status, LoanItem.INSTORAGE)


class ReportWorkflowTests(TestCase):
    def test_report_item_updates_client_item_and_transaction(self):
        item = LoanItem.objects.create(itemCat="A-01", status=LoanItem.LOANEDOUT, description="Adapter")
        client = make_client(borrowing=True, lastBorrowedItem=item)
        loan_transaction = Transaction.objects.create(
            clientId=client,
            itemCat=item,
            dswsMemLoanName="Loan Member",
            dateLoaned=aware(2024, 6, 10, 9, 30),
            dueDate=aware(2024, 6, 10, 11, 30),
            status=Transaction.ONGOING,
        )

        report_item(client, fine_amount=500, report_type=LoanItem.DAMAGED)

        client.refresh_from_db()
        item.refresh_from_db()
        loan_transaction.refresh_from_db()

        self.assertFalse(client.borrowing)
        self.assertEqual(client.fineAmount, 500)
        self.assertEqual(item.status, LoanItem.DAMAGED)
        self.assertEqual(loan_transaction.status, LoanItem.DAMAGED)
