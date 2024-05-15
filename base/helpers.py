from .models import Client, LoanItem, Transaction, BlockOutDate, BlockOutTime
from datetime import datetime, timedelta
from django.utils import timezone
from django.utils.timezone import localtime
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import math
import numpy as np
import threading
from threading import Thread


# FRONT PAGE VIEW HELPER METHODS
def ifNoClasses(duedate, hasWednesdayClasses):
    if hasWednesdayClasses:
        if duedate.weekday() == 5 or duedate.weekday() == 6:
            return True 
    else:
        if duedate.weekday() == 5 or duedate.weekday() == 6 or duedate.weekday() == 2:
            return True
    try:
        blockedDate = BlockOutDate.objects.get(dateBlocked=duedate)
        return True
    except BlockOutDate.DoesNotExist:
        return False
    
def getClosingTime(time):
    dayofweek = time.weekday()
    closingtime = time
    if dayofweek == 2:
        return closingtime.replace(hour=14, minute=00, second=00, microsecond=00)
    else:
        return closingtime.replace(hour=17, minute=00, second=00, microsecond=00)

def checkItemType(itemCat):
    if (itemCat.startswith('B') or itemCat.startswith('C') or itemCat.startswith('D') 
            or itemCat.startswith('TR') or itemCat.startswith('U')):
        return 'A'
    return 'B'

# PENALTY HELPER METHODS
def getItemTypeAOverdueDays(dueDate, client):
    formattedDueDate = dueDate.date()
    returnDate = timezone.localtime(timezone.now()).date()
    blockedDays = BlockOutDate.objects.filter(dateBlocked__range=[formattedDueDate, returnDate]).count()
    if returnDate <= formattedDueDate:
        return 0
    elif client.hasWednesdayClasses:
        currentDate = formattedDueDate + timedelta(days=1)
        totaldays = 1
        while currentDate != returnDate:
            if not ifNoClasses(currentDate, client.hasWednesdayClasses):
                totaldays += 1
            currentDate += timedelta(days=1)
        return totaldays
    else:
        busdays = np.busday_count(formattedDueDate, returnDate)
        totaldays = busdays + 1 - blockedDays
        return totaldays
   
def calculateTypeAPenalty(overDueDays, client):
    penalty = "No Penalty"
    if client.warningCount > 3:
        penalty = "Black Listed\n Hold Order\n PHP 1000 Fine, EL"
    elif 1 <= overDueDays <= 3:
        penalty = "Warning"
    elif 4 <= overDueDays <= 10:
        penalty = "TBL, EL"
    elif overDueDays > 10:
        penalty = 'TBL, HO, PHP 500 Fine, EL'
    return penalty

def applyTypeAPenalty(overDueDays, client):
    if client.warningCount > 3:
        client.blackListed = True
        client.BLcount += 1
        client.holdOrder = True
        client.HOcount += 1
        client.fineAmount = 1000
        client.excuseLetter = True
    elif 1 <= overDueDays <= 3:
        client.warningCount = client.warningCount + 1
    elif 4 <= overDueDays <= 10:
        client.temporaryBlackList = True
        client.excuseLetter = True
    elif overDueDays > 10:
        client.temporaryBlackList = True
        client.holdOrder = True
        client.HOcount += 1
        client.fineAmount = 500
        client.excuseLetter = True
    client.save()

def getItemTypeBOverdueTime(dueDate, client):
    returnDate = timezone.localtime(timezone.now())
    # RETURN DATE < DUEDATE
    if returnDate <= localtime(dueDate):
        overdueHours = 0
        overdueMinutes = 0
        return overdueHours, overdueMinutes
    # SAME DAY: RETURN DATE > DUEDATE
    elif (returnDate > localtime(dueDate)) and returnDate.date() == dueDate.date():
        difference = returnDate - localtime(dueDate) #difference is timedelta
        blockedTimeOnReturnDate = BlockOutTime.objects.filter(dateBlocked=returnDate.date())
        
        if blockedTimeOnReturnDate.exists() and (localtime(dueDate) <= blockedTimeOnReturnDate[0].timeStart 
                                                 and blockedTimeOnReturnDate[0].timeEnd <= returnDate):
            blockedTimeSpan = blockedTimeOnReturnDate[0].timeEnd - blockedTimeOnReturnDate[0].timeStart
            difference -= blockedTimeSpan
            
        overdueHours = math.floor(difference.total_seconds()//3600)
        overdueMinutes = math.floor((difference.seconds//60)%60)
        return overdueHours, overdueMinutes
    # Overdue by multiple days
    else:
        # Due Date Closing time - Due Date time
        dueDateClosingTime = getClosingTime(localtime(dueDate)) 
        overDueTime = dueDateClosingTime - dueDate


        # Date of Borrowing
        dueDateBlockedTime = BlockOutTime.objects.filter(dateBlocked=dueDate.date())
        if dueDateBlockedTime.exists() and (localtime(dueDate) <= dueDateBlockedTime[0].timeStart and dueDateBlockedTime[0].timeEnd <= dueDateClosingTime):
            blockedTimeSpan = dueDateBlockedTime[0].timeEnd - dueDateBlockedTime[0].timeStart
            overDueTime -= blockedTimeSpan


        # Days in Between
        dayBetween = localtime(dueDate) + timedelta(days=1)
        while returnDate.date() > dayBetween.date():
            if not ifNoClasses(dayBetween, client.hasWednesdayClasses):
                officeHours = timedelta(hours=7, minutes=30) if dayBetween.weekday() != 2 else timedelta(hours=4, minutes=30)
                dayBetweenBlockedTime = BlockOutTime.objects.filter(dateBlocked=dayBetween.date())
                if dayBetweenBlockedTime.exists():
                    dayBetweenTimeSpan = dayBetweenBlockedTime[0].timeEnd - dayBetweenBlockedTime[0].timeStart
                    officeHours -= dayBetweenTimeSpan
                overDueTime += officeHours
            dayBetween += timedelta(days=1)


        returnDateOpeningTime = returnDate.replace(hour=9, minute=30, second=0, microsecond=0)
        returnDateDifference = returnDate - returnDateOpeningTime
        returnDateBlockedTime = BlockOutTime.objects.filter(dateBlocked=returnDate.date())
        if (returnDateBlockedTime.exists() and 
            (returnDateOpeningTime <= returnDateBlockedTime[0].timeStart and returnDateBlockedTime[0].timeEnd <= returnDate)):
            returnDateBlockedTimeDifference = returnDateBlockedTime[0].timeEnd - returnDateBlockedTime[0].timeStart
            returnDateDifference -= returnDateBlockedTimeDifference
        overDueTime += returnDateDifference
        overdueHours = math.floor(overDueTime.total_seconds()//3600)
        overdueMinutes = math.floor((overDueTime.seconds//60)%60)
        return overdueHours, overdueMinutes

def calculateTypeBPenalty(overdueHours, overdueMinutes, client):
    penalty = "No Penalty"
    if client.warningCount == 3:
        penalty = "Black Listed\n Hold Order\n PHP 1000 Fine, EL"
    elif 3 <= overdueHours <= 5:
        penalty = 'Warning'
    elif 6 <= overdueHours <= 10:
        penalty = "TBL, EL"
    elif overdueHours > 10:
        penalty = 'TBL, HO, PHP 500 Fine, EL'
    return penalty 

def applyTypeBPenalty(overdueHours, overDueMinutes, client):
    if client.warningCount == 3:
        client.blackListed = True
        client.BLcount += 1
        client.holdOrder = True
        client.HOcount += 1
        client.fineAmount = 1000
        client.excuseLetter = True
    elif 3 <= overdueHours <= 5:
        client.warningCount +=1
    elif 6 <= overdueHours <= 10:
        client.temporaryBlackList = True
        client.excuseLetter = True
    elif overdueHours > 10:
        client.temporaryBlackList = True
        client.holdOrder = True
        client.HOcount += 1
        client.fineAmount = 500
        client.excuseLetter = True
    client.save()

# EMAILER METHODS
def getItemTypeName(itemCat):
    if itemCat.startswith('A'):
        return 'Adapter'
    elif itemCat.startswith('B'):
        return 'Bible'
    elif itemCat.startswith('C'):
        return 'Calculator'
    elif itemCat.startswith('D'):
        return 'Dictionary'
    elif itemCat.startswith('TR'):
        return 'Transalor Dictionary'
    elif itemCat.startswith('LC'):
        return 'Laptop Charger'
    elif itemCat.startswith('PC'):
        return 'Phone Charger'
    elif itemCat.startswith('S'):
        return 'Speaker'
    elif itemCat.startswith('U'):
        return 'Umbrella'


class TransactionEmailThread(threading.Thread):
    def __init__(self, subject, message, email, template):
        self.subject = subject
        self.message = message
        self.email_to = email
        self.template = template
        threading.Thread.__init__(self)
    def run(self):
        email_from = settings.EMAIL_HOST_USER
        send_mail(
                    self.subject, 
                    self.message, 
                    email_from, 
                    recipient_list = [self.email_to, ], 
                    html_message= self.template,
                    fail_silently=True
                )


def sendTransactionEmail(itemCat, itemCatName, loanDate, dueDate, client):
    subject_matter = f'{itemCatName} [{itemCat}] is due on {dueDate}'
    message = f"""
                LOANS RECEIPT

                The Department of Student Welfare and Services’ Loans Committee would like to thank you for availing our services. 
                Please be aware of the details of our transaction. 
                --------------------
                Item Number: {itemCat}
                Time Borrowed: {loanDate}
                Due Date: {dueDate}
                --------------------
                If you have any concerns or inquiries, contact us at:
                Email: dsws.loans@gmail.com

                Thank you and have a great day!
                """
    template_name = "base/Email-Templates/transaction_email.html"
    convert_to_html_content = render_to_string(
        template_name= template_name,
        context = {
                    "itemCat": itemCat,
                    "loanDate": loanDate,
                    "dueDate": dueDate}
    )

    msg = TransactionEmailThread(subject_matter, message, client.email, convert_to_html_content)
    msg.start()

def sendDeadlineEmail(itemCat, itemCatName, loanDate, dueDate, client):
    subject_matter = f'Reminder: Your borrowed item {itemCatName} [{itemCat}] is due today!! {dueDate}'
    message = f"""
                Good Day {client.firstName} {client.lastName},

                The Department of Student Welfare and Services’ Loans Committee would like to remind 
                you that you have an item loaned out under your name. The item is due to be returned 
                during the day. 
                
                Kindly refer to the list below for more information
                --------------------
                Item Number: {itemCatName}
                Time Borrowed: {loanDate}
                Due Date: {dueDate}
                --------------------
                As stated in the contract you submitted prior to borrowing an item, overdue returns are subject to certain penalties. 

                If you have any concerns or inquiries, 
                please feel free to reply to this email or contact us at:
                Email: dsws.loans@gmail.com

                Thank you and have a great day!
                """
    template_name = "base/Email-Templates/deadline_email.html"
    convert_to_html_content = render_to_string(
        template_name= template_name,
        context = {
                    "itemCat": itemCat,
                    "loanDate": loanDate,
                    "dueDate": dueDate}
    )
    msg = TransactionEmailThread(subject_matter, message, client.email, convert_to_html_content)
    msg.start()

def sendOverdueItemAEmail(itemCat, itemCatName, loanDate, dueDate, client, overdueDays):
    subject_matter = f'Notice: Loaned item {itemCatName} [{itemCat}] is {overdueDays} day/s overdue!'
    penalty = calculateTypeAPenalty(overdueDays, client)
    message = f"""
                Good day {client.firstName} {client.lastName} ,

                The Department of Student Welfare and Services’ Loans Committee would like to remind you 
                that you have/had an overdue item loaned out under your name. 
                As stated in the contract you submitted prior to borrowing an item, 
                overdue returns are subject to certain penalties. 
                
                Kindly refer to the list below for more information.
                --------------------
                Item Number: {itemCatName}
                Estimated Number of Days Overdue: {overdueDays}
                Penalty: {penalty}
                --------------------
                If you have any concerns or inquiries, contact us at:
                Email: dsws.loans@gmail.com
                """
    template_name = "base/Email-Templates/overdue_item_a_email.html"
    convert_to_html_content = render_to_string(
        template_name= template_name,
        context = {
                    "client": client,
                    "itemCat": itemCat,
                    "overdueDays": overdueDays,
                    "penalty": penalty}
    )
    msg = TransactionEmailThread(subject_matter, message, client.email, convert_to_html_content)
    msg.start()

def sendOverdueItemBEmail(itemCat, itemCatName, loanDate, dueDate, client, overdueHours, overdueMinutes):
    subject_matter = f'Notice: Loaned item {itemCatName} [{itemCat}] is {overdueHours} hr/s {overdueMinutes} min/s overdue!'
    penalty = calculateTypeBPenalty(overdueHours, overdueMinutes, client)
    message = f"""
                Good day {client.firstName} {client.lastName},

                The Department of Student Welfare and Services’ Loans Committee would like to remind you 
                that you have/had an overdue item loaned out under your name. 
                As stated in the contract you submitted prior to borrowing an item, 
                overdue returns are subject to certain penalties. 
                
                Kindly refer to the list below for more information.
                --------------------
                Item Number: {itemCatName}
                Estimated Time Overdue: {overdueHours} hr/s {overdueMinutes} min/s
                Penalty: {penalty}
                --------------------
                If you have any concerns or inquiries, contact us at:
                Email: dsws.loans@gmail.com
                """
    template_name = "base/Email-Templates/overdue_item_b_email.html"
    convert_to_html_content = render_to_string(
        template_name= template_name,
        context = {
                    "client": client,
                    "itemCat": itemCat,
                    "overdueHours": overdueHours,
                    "overdueMinutes": overdueMinutes,
                    "penalty": penalty}
    )
    msg = TransactionEmailThread(subject_matter, message, client.email, convert_to_html_content)
    msg.start()


