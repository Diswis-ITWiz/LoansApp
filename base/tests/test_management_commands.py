from datetime import datetime
from unittest import mock

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from base.models import Client, LoanItem, Transaction


def aware(year, month, day, hour=0, minute=0):
    return timezone.make_aware(datetime(year, month, day, hour, minute))


class SendOverdueItemBEmailsCommandTests(TestCase):
    def test_command_emails_overdue_type_b_transactions_using_client_object(self):
        client = Client.objects.create(
            clientId=100001,
            lastName="Garcia",
            firstName="Ana",
            middleInitial="M",
            contactNum="09171234567",
            email="ana@example.com",
            yearLevel=2,
            course="BS CS",
            hasWednesdayClasses=True,
            dswsMemRegName="Member Name",
        )
        item = LoanItem.objects.create(itemCat="A-01", status=LoanItem.LOANEDOUT, description="Adapter")
        transaction = Transaction.objects.create(
            clientId=client,
            itemCat=item,
            dswsMemLoanName="Loan Member",
            dateLoaned=aware(2024, 6, 10, 13, 0),
            dueDate=aware(2024, 6, 10, 15, 0),
            status=Transaction.ONGOING,
        )

        with mock.patch(
            "base.management.commands.sendoverdueitembemails.timezone.now",
            return_value=aware(2024, 6, 11, 10, 30),
        ), mock.patch(
            "base.services.overdue.timezone.now",
            return_value=aware(2024, 6, 11, 10, 30),
        ), mock.patch(
            "base.management.commands.sendoverdueitembemails.sendOverdueItemBEmail"
        ) as send_overdue_email:
            call_command("sendoverdueitembemails")

        send_overdue_email.assert_called_once_with(
            item.itemCat,
            "Adapter",
            transaction.dateLoaned,
            transaction.dueDate,
            client,
            3,
            0,
        )
