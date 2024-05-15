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
        # Get all ongoing items
        overdueItems = Transaction.objects.filter(  Q(status__exact='OG') &
                                                    (   Q(itemCat__itemCat__startswith='PC') |
                                                        Q(itemCat__itemCat__startswith='LC') |
                                                        Q(itemCat__itemCat__startswith='A') |
                                                        Q(itemCat__itemCat__startswith='S')
                                                    )        
                                                )        
        # Get current date
        today = timezone.localtime(timezone.now())
        # Loop
        for x in overdueItems:
            # Check if their overdue by comparing the current date with their due date
            # If late calculate overdue
            if x.dueDate < today:
                overdueHours, overdueMinutes = getItemTypeBOverdueTime(x.dueDate, x.clientId.clientId)
                sendOverdueItemBEmail(x.itemCat.itemCat, 
                                      getItemTypeName(x.itemCat.itemCat),
                                      x.dateLoaned,
                                      x.dueDate,
                                      x.clientId,
                                      overdueHours,
                                      overdueMinutes
                )
           
            # call emailer method
        stuff = 'This command send emails at the beginning of the day to inform clients of their due items'
        self.stdout.write(stuff)