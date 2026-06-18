from django.core.management.base import BaseCommand
from base.constants import TYPE_B_ITEM_PREFIXES
from base.models import Transaction
from django.db.models import Q
from django.utils import timezone
from base.services.emailing import send_overdue_item_b_email as sendOverdueItemBEmail
from base.services.item_types import get_item_type_name
from base.services.overdue import get_item_type_b_overdue_time

class Command(BaseCommand):
    help = "This command send emails at the beginning of the day to inform clients of their due items"

    def handle(self, *args: object, **kwargs: object) -> None:
        # Get all ongoing items
        item_prefix_filter = Q()
        for prefix in TYPE_B_ITEM_PREFIXES:
            item_prefix_filter |= Q(itemCat__itemCat__startswith=prefix)
        overdueItems = Transaction.objects.select_related("clientId", "itemCat").filter(
            Q(status__exact=Transaction.ONGOING) & item_prefix_filter
        )
        # Get current date
        today = timezone.localtime(timezone.now())
        # Loop
        for x in overdueItems:
            # Check if their overdue by comparing the current date with their due date
            # If late calculate overdue
            if x.dueDate < today:
                overdueHours, overdueMinutes = get_item_type_b_overdue_time(x.dueDate, x.clientId)
                sendOverdueItemBEmail(x.itemCat.itemCat, 
                                      get_item_type_name(x.itemCat.itemCat),
                                      x.dateLoaned,
                                      x.dueDate,
                                      x.clientId,
                                      overdueHours,
                                      overdueMinutes
                )
           
            # call emailer method
        stuff = 'This command send emails at the beginning of the day to inform clients of their due items'
        self.stdout.write(stuff)
