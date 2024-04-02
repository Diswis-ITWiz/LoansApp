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
        # Get date today
        today = timezone.localtime(timezone.now()).date()
        # Query database for all ongoing transactions
        ongoing = Transaction.objects.filter(status='OG')
        print(ongoing[0].dueDate)
        for x in ongoing:
            if x.dueDate.date() == today:
                sendDeadlineEmail(x.itemCat.itemCat, 
                                getItemTypeName(x.itemCat.itemCat), 
                                x.dateLoaned.strftime("%m/%d/%Y %I:%M %p"), 
                                x.dueDate.strftime("%m/%d/%Y %I:%M %p"), 
                                x.clientId.email)
        stuff = 'This command send emails at the beginning of the day to inform clients of their due items'
        self.stdout.write(stuff)