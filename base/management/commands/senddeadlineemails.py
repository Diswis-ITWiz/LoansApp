from django.core.management.base import BaseCommand
from base.models import Transaction
from django.utils import timezone
from base.services.emailing import send_deadline_email
from base.services.item_types import get_item_type_name

class Command(BaseCommand):
    help = "This command send emails at the beginning of the day to inform clients of their due items"

    def handle(self, *args: object, **kwargs: object) -> None:
        # Get date today
        today = timezone.localtime(timezone.now()).date()
        # Query database for all ongoing transactions
        ongoing = Transaction.objects.select_related("clientId", "itemCat").filter(status=Transaction.ONGOING)
        for x in ongoing:
            if x.dueDate.date() == today:
                send_deadline_email(x.itemCat.itemCat, 
                                get_item_type_name(x.itemCat.itemCat), 
                                x.dateLoaned.strftime("%m/%d/%Y %I:%M %p"), 
                                x.dueDate.strftime("%m/%d/%Y %I:%M %p"), 
                                x.clientId)
        stuff = 'This command send emails at the beginning of the day to inform clients of their due items'
        self.stdout.write(stuff)
