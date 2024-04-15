from django.core.management.base import BaseCommand
from base.models import *
from base.helpers import *
from django.db.models import Q
from datetime import date, datetime, timedelta
from django.utils import timezone
from django.utils.timezone import localtime

class Command(BaseCommand):
    help = "This command send emails at the beginning of the day to inform clients of their due items"

    def handle(self, *args, **kwargs):
        # Get all overdue items
        overdueItems = Transaction.objects.filter(  Q(status='OG') &
                                                    (   Q(itemCat__itemCat__startswith='B') |
                                                        Q(itemCat__itemCat__startswith='U') |
                                                        Q(itemCat__itemCat__startswith='TR') |
                                                        Q(itemCat__itemCat__startswith='D') |
                                                        Q(itemCat__itemCat__startswith='C')
                                                    )
                                                  )
        # Get current date
        today = timezone.localtime(timezone.now()).date()
        
        # Loop
        for x in overdueItems:
            # Check if their overdue by comparing the current date with their due date
            if x.dueDate < today:
                # If late calculate overdue
                overdueDays = getItemTypeAOverdueDays(x.dueDate, x.clientId)
                # call emailer method
        stuff = 'This command send emails at the beginning of the day to inform clients of their due items'
        self.stdout.write(stuff)