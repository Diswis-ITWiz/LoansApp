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
        # Get current date
        # Loop
            # Check if their overdue by comparing the current date with their due date
            # If late calculate overdue
            # call emailer method
        stuff = 'This command send emails at the beginning of the day to inform clients of their due items'
        self.stdout.write(stuff)