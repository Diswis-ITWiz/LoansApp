from django.core.management.base import BaseCommand
from base.constants import TYPE_A_ITEM_PREFIXES
from base.models import Transaction
from django.db.models import Q
from django.utils import timezone
from base.services.emailing import send_overdue_item_a_email
from base.services.item_types import get_item_type_name
from base.services.overdue import get_item_type_a_overdue_days

class Command(BaseCommand):
    help = "This command send emails at the beginning of the day to inform clients of their due items"

    def handle(self, *args: object, **kwargs: object) -> None:
        # Get all overdue items
        item_prefix_filter = Q()
        for prefix in TYPE_A_ITEM_PREFIXES:
            item_prefix_filter |= Q(itemCat__itemCat__startswith=prefix)
        overdueItems = Transaction.objects.select_related("clientId", "itemCat").filter(
            Q(status=Transaction.ONGOING) & item_prefix_filter
        )
        # Get current date
        today = timezone.localtime(timezone.now()).date()
        
        # Loop
        for x in overdueItems:
            # Check if their overdue by comparing the current date with their due date
            due_date = timezone.localtime(x.dueDate)
            loan_date = timezone.localtime(x.dateLoaned)
            if due_date.date() < today:
                # If late calculate overdue
                overdueDays = get_item_type_a_overdue_days(due_date, x.clientId)
                send_overdue_item_a_email(x.itemCat.itemCat, 
                                      get_item_type_name(x.itemCat.itemCat),
                                      loan_date,
                                      due_date,
                                      x.clientId,
                                      overdueDays
                                      )
                # call emailer method
        stuff = 'This command send emails at the beginning of the day to inform clients of their due items'
        self.stdout.write(stuff)
