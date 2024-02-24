from typing import Any
from django.shortcuts import render, redirect
from .forms import ClientForm, LoanItemForm, LoanItemEditForm
from .models import Client, LoanItem, Transaction, BlockOutDate, BlockOutTime
from datetime import datetime, timedelta
from django.db.models import Q
from django.utils import timezone
from django.utils.timezone import localtime
import numpy as np
import math
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib import messages


# Create your views here
def home(request):
    return render(request, 'base/home.html')

# Register Client
def newClient(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Client added.') # <- Needs Bootstrap
            return redirect('home')
        return render(request, 'base/Home-Client/new_client.html', {'form': form})
    else:
        form = ClientForm()
        context = {'form': form}
        return render(request, 'base/Home-Client/new_client.html', context)


# Loan Item
def loanItemClientFinder(request):
    context = {}
    if request.method == 'GET':
        q = request.GET.get('q', '')
        # Prevents Getting all clients
        if q == '':
            return render(request, 'base/Home-Item/find_client.html', context)
        #Client May Not Exist

        if Client.objects.filter(clientId__exact=q).exists():
            client = Client.objects.get(clientId__exact=q)
            # Check if Graduating senior or has currently borrowed an Item:
            if client.gradWaiting == True:
                context = {'client': client, 'borrowingStatus': False, 'gradWaiting': client.gradWaiting}
            elif client.borrowing == True:
                context = {'client': client, 'borrowingStatus': client.borrowing}
            elif client.blackListed:
                context = {'client': client, 'blackListed': True}
            elif client.temporaryBlackList:
                context = {'client': client, 'blackListed': True}
            else:
                context = {'client':client}
        else:
            context = {'input_validity': True}
        return render(request, 'base/Home-Item/find_client.html', context)


def loanItemTransaction(request, pk):
    client = Client.objects.get(clientId__exact=pk)
    items = LoanItem.objects.filter(status='IS')
    time = None
    closingtime = None
    dateDue = None

    def timeOverlap(challengertime):
        try:
            blockedtimedate = BlockOutTime.objects.get(dateBlocked=challengertime.date())
            startTime = localtime(blockedtimedate.timeStart)
            endTime = localtime(blockedtimedate.timeEnd)
            if startTime <= challengertime <= endTime:
                endTime += timedelta(hours=2)
                nonlocal dateDue 
                dateDue = endTime

                closingtime = challengertime
                tempclosingtime = closingtime.replace(hour=17)
                closingtime = tempclosingtime

                if dateDue >= closingtime:
                    return True
                else:
                    
                    return False
            else:
                return False
        except BlockOutTime.DoesNotExist:
            return False


    if request.method == 'GET':
        q = request.GET.get('selectedItem', '')
        if q == '':
            context = {'client': client, 'items': items}
            return render(request, 'base/Home-Item/loan_item_transaction.html', context)
        
        selectedItem = LoanItem.objects.get(itemCat__exact=q)

        time = timezone.localtime(timezone.now())
        closingtime = getClosingTime(time)
        dateDue = time
        itemCat = selectedItem.itemCat
        hasWednesdayClasses = client.hasWednesdayClasses
        itemType = ''
        # Item type A - borrow for a whole day
        if checkItemType(itemCat) == 'A':
            itemType = 'A'
            dateDue += timedelta(days=1)

            # Keep adding 1 day to dateDue until we find a valid date
            while ifNoClasses(dateDue, hasWednesdayClasses):
                dateDue += timedelta(days=1)
            
            # Set Closing Time of due date
            tempDateDue = getClosingTime(dateDue)
            dateDue = tempDateDue

        # Item type B - borrow for only 2 hours
        else:
            itemType = 'B'
            # Check if the client cannot return the item before closing time
            dateDue += timedelta(hours=2)
            if dateDue >= closingtime:
                dateDue += timedelta(days=1)
                tempDateDue = dateDue.replace(hour=11, minute=00)
                dateDue = tempDateDue
                while ifNoClasses(dateDue, hasWednesdayClasses) or timeOverlap(dateDue):
                    dateDue += timedelta(days=1)
                    tempDateDue = dateDue.replace(hour=11, minute=00, second=00, microsecond=00)
                    dateDue = tempDateDue                
            else:
                while ifNoClasses(dateDue, hasWednesdayClasses) or timeOverlap(dateDue):
                    dateDue += timedelta(days=1)
                    tempDateDue = dateDue.replace(hour=11, minute=00, second=00, microsecond=00)
                    dateDue = tempDateDue
        context = {'client': client, 'items': items, 
                   'time': time, 'itemType': itemType,
                   'dateDue': dateDue, 
                   'selectedItem': selectedItem}
        return render (request, 'base/Home-Item/loan_item_transaction.html', context)
    if request.method == 'POST':
        selectedItem = items.get(itemCat__exact=request.POST.get('itemCat'))
        time = request.POST.get('hiddendateloaned')
        dueDate = request.POST.get('hiddendatedue')
        Transaction.objects.create(
            clientId = client,
            itemCat = selectedItem,
            dateLoaned = time,
            dueDate = dueDate,
            dswsMemLoanName = request.POST.get('dswsMemLoan'),
            loanRemarks = request.POST.get('remarks'),
        )
        client.lastBorrowedDate = time
        client.lastBorrowedItem = selectedItem
        client.borrowing = True
        client.save()
        selectedItem.lastClient = client.clientId
        selectedItem.status = 'LO'
        selectedItem.save()


        formatted_borrow_date_datetime = datetime.strptime(time, '%Y-%m-%d %H:%M:%S:%f')
        formatted_dueDate_datetime = datetime.strptime(dueDate, '%Y-%m-%d %H:%M:%S:%f')
        email_borrow_date = formatted_borrow_date_datetime.strftime("%m/%d/%Y %I:%M %p")
        email_return_date = formatted_dueDate_datetime.strftime("%m/%d/%Y %I:%M %p")
        itemCatName = getItemTypeName(selectedItem.itemCat)
        subject_matter = f'{itemCatName} [{selectedItem.itemCat}] is due on {email_return_date}'


        email_context = {
            "itemCat": selectedItem.itemCat,
            "dateBorrowed": email_borrow_date,
            "dueDate": email_return_date
        }
        html_message = render_to_string("base/email.html", context=email_context)
        plain_message = "Plain Template"

        message = EmailMultiAlternatives(
            subject = subject_matter,
            body= plain_message,
            from_email=None,
            to=[client.email]
        )
        message.attach_alternative(html_message, "text/html")
        message.send()
        
        return redirect('home')
    
    # Standard Loading of Resources of View
    context = {'client': client, 'items': items}
    return render(request, 'base/Home-Item/loan_item_transaction.html', context)


#Return Item
def returnItem1(request):
    client = None
    # Client Finder similar to loan item 1
    context = {}
    if request.method == 'GET':
        q = request.GET.get('q', '')
        if q == '':
            return render(request, 'base/Home-Item/return_item.html', context)
        
        #Client May Not Exist
        try:
            client = Client.objects.get(clientId__exact=q)
        except Client.DoesNotExist:
            invalidInput = True
            context = {'input_validity': invalidInput}
            return render(request, 'base/Home-Item/return_item.html', context)
        
        # Find transaction of the client
        try:
            transaction = Transaction.objects.get(
                Q(clientId__exact=client.clientId) &
                Q(status__exact='OG')
            )
        except Transaction.DoesNotExist:
            transaction = False

        context = {'client': client, 'transaction': transaction}
        return render(request, 'base/Home-Item/return_item.html', context)
    
    return render(request, 'base/Home-Item/return_item.html')

def returnItem2(request, pk):
    transaction = Transaction.objects.get(id=pk)
    client = Client.objects.get(clientId=transaction.clientId.clientId)
    loanedItem = LoanItem.objects.get(itemCat = transaction.itemCat.itemCat)
    overdueDays = 0
    overdueHours = 0
    overdueMinutes = 0
    penalty = ''
    if checkItemType(loanedItem.itemCat) == 'A':
        overdueDays = getItemTypeAOverdueDays(localtime(transaction.dueDate), client)
        penalty = calculateTypeAPenalty(overdueDays, client)
    else:
        overdueHours, overdueMinutes = getItemTypeBOverdueTime(localtime(transaction.dueDate), client)
        penalty = calculateTypeBPenalty(overdueHours,overdueMinutes, client)
    



    if request.method == 'POST':
        if request.POST.get('itemType') == 'A':
            applyTypeAPenalty(int(request.POST.get('overDueDays')), client)
        else:
            applyTypeBPenalty(int(request.POST.get('overDueHours')), request.POST.get('overDueHours'), client)

        # Modify Transaction Instance in DB
        transaction.dateReturned = timezone.localtime(timezone.now())
        transaction.overdueDays = request.POST.get('overDueDays')
        transaction.overdueHours = request.POST.get('overDueHours')
        transaction.overdueMinutes = request.POST.get('overDueMinutes')
        transaction.dswsMemRetName = request.POST.get('dswsMemRet')
        transaction.returnRemarks = request.POST.get('remarks')
        transaction.status = 'C'
        transaction.save()
        # Modify the statuses of the respective client, transaction, and loanItem
        client.borrowing = False
        client.save()
        loanedItem.status = 'IS'
        loanedItem.save()

        return redirect('home')
    
    context = {'transaction':transaction, 'client':client, 
               'loanedItem': loanedItem, 'itemType': checkItemType(loanedItem.itemCat), 
               'penalty': penalty, 'overDueDays': overdueDays, 'overDueHours': overdueHours, 
               'overDueMinutes': overdueMinutes}


    return render(request, 'base/Home-Item/return_item2.html', context)






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
    print(formattedDueDate)
    print(returnDate)
    if returnDate <= formattedDueDate:
        print('Test1')
        return 0
    elif client.hasWednesdayClasses:
        print('Test2')
        currentDate = formattedDueDate + timedelta(days=1)
        totaldays = 1
        while currentDate != returnDate:
            if not ifNoClasses(currentDate, client.hasWednesdayClasses):
                totaldays += 1
            currentDate += timedelta(days=1)
        return totaldays
    else:
        print('Test3')
        busdays = np.busday_count(formattedDueDate, returnDate)
        totaldays = busdays + 1 - blockedDays
        return totaldays
   
def calculateTypeAPenalty(overDueDays, client):
    penalty = ""
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
    penalty = ""
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
        return 'Dictionary/Transalator'
    elif itemCat.startswith('LC'):
        return 'Laptop Charger'
    elif itemCat.startswith('PC'):
        return 'Phone Charger'
    elif itemCat.startswith('S'):
        return 'Speaker'
    elif itemCat.startswith('U'):
        return 'Umbrella'





# ADMIN PANELS

def adminDashboard(request):
    return render(request, 'base/admin_page.html')


# ITEMS
def itemPanel(request):
    if request.method == 'GET':
        if request.GET.get('getItemBtn'):
            search_param = request.GET.get('itemCatQuery')
            if search_param == '':
                pass
            else:
                search_item = LoanItem.objects.filter(itemCat=search_param)
                return render(request, 'base/Admin-Item/item_panel.html', {'items': search_item})
        
    items = LoanItem.objects.all()
    context = {"items": items}        
    return render(request, 'base/Admin-Item/item_panel.html', context)

def addItem(request):
    if request.method == 'POST':
        form = LoanItemForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('item-panel')
        return render(request, 'base/Admin-Item/add_item.html', {'form': form})
    else:
        form = LoanItemForm()
    context={'form': form}
    return render(request, 'base/Admin-Item/add_item.html',context)

def itemDetailView(request, pk):
    loanItem = LoanItem.objects.get(itemCat=pk)
    transactionHistory = Transaction.objects.filter(itemCat=loanItem)
    context = {"item": loanItem,"transactions":transactionHistory}
    return render(request, 'base/Admin-Item/loanitem_detail.html', context)

def editItem(request, pk):
    item = LoanItem.objects.get(itemCat=pk)
    if request.method == 'POST': 
        item.itemCat = request.POST.get('itemCat')
        item.description = request.POST.get('description')
        item.status = request.POST.get('status')
        item.save()
        return redirect('item-panel')
    else:
        form = LoanItemEditForm(instance=item)
    context = {'form': form}
    return render(request, 'base/Admin-Item/edit_item.html', context)

def deleteItem(request, pk):
    item = LoanItem.objects.get(itemCat=pk)

    if request.method == 'POST':
        item.delete()
        return redirect('item-panel')
    else:
        return render(request, 'base/Admin-Item/delete_item.html', {'item': item})


# CLIENTS
def clientPanel(request):
    
    if request.method == 'GET':
        if request.GET.get('getClientBtn'):
            search_param = request.GET.get('clientIdQuery')
            if search_param == '':
                pass
            else:
                search_client = Client.objects.filter(clientId=search_param)
                return render(request, 'base/Admin-Client/client_panel.html', {'clients': search_client})
        
    clients = Client.objects.all()
    context = {'clients': clients}
    return render(request, 'base/Admin-Client/client_panel.html', context)

def clientDetails(request, pk):
    client = Client.objects.get(clientId=pk)
    transactions = Transaction.objects.filter(clientId=client)
    context = {'client': client, 'transactions': transactions}
    return render(request, 'base/Admin-Client/client_details.html', context)

def editClient(request, pk):
    client = Client.objects.get(clientId=pk)
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('client-details', pk=client.clientId)
        return render(request, 'base/Admin-Client/edit_client.html', {'form': form, 'client':client.clientId})
    else:
        form = ClientForm(instance=client)
        return render(request, 'base/Admin-Client/edit_client.html', {'form': form, 'client':client.clientId})

def liftClientPenalty(request, pk):
    client = Client.objects.get(clientId=pk)
    if request.method == 'POST':
        if client.blackListed == True:
            timeStart = timezone.localtime(timezone.now())
            timeEnd = timeStart + timedelta(days=105)
            client.blackListed = True
            client.holdOrder = False
            client.excuseLetter = False
            client.fineAmount = 0
            client.HOcount = 0 if client.HOcount == 0 else client.HOcount - 1
            client.temporaryBlackList = False
            client.blacklistStart = timeStart
            client.blacklistEnd = timeEnd
        elif client.temporaryBlackList == True:
            client.temporaryBlackList = False
            client.excuseLetter = False
            client.holdOrder = False
            client.fineAmount = 0
            client.HOcount = 0 if client.HOcount == 0 else client.HOcount - 1
        else:
            client.warningCount = 0 if client.warningCount == 0 else client.warningCount - 1
            client.HOcount = 0 if client.HOcount == 0 else client.HOcount - 1
            client.BLcount = 0 if client.BLcount == 0 else client.BLcount - 1
        client.save()
        return redirect('client-details', pk=client.clientId)

                
    return render(request, 'base/Admin-Client/lift_client_penalty.html', {'client': client})


# Block Dates
def blockOutDate(request):
    if request.method == 'POST':
        date = datetime.strptime(request.POST.get('dateInput',), '%Y-%m-%d')
        blockOutDate = BlockOutDate.objects.create(
            dateBlocked = date,
            description = request.POST.get('descriptionInput')
        )
        return redirect('admin-dashboard')
    else:
        blockedDates = BlockOutDate.objects.all()
    return render(request, 'base/Admin-Blockout/block_date.html', {'blockedDates': blockedDates})

def blockOutTime(request):
    if request.method == 'POST':
        dateInput = datetime.strptime(request.POST.get('dateInput'), '%Y-%m-%d')
        startDateTime = datetime.strptime(request.POST.get('startTime'), '%H:%M')
        finalStartDateTime = startDateTime.replace(year=dateInput.year, month=dateInput.month, day=dateInput.day)
        endDateTime = datetime.strptime(request.POST.get('endTime'), '%H:%M')
        finalEndDateTime = endDateTime.replace(year=dateInput.year, month=dateInput.month, day=dateInput.day)
        blockOutTime = BlockOutTime.objects.create(
            dateBlocked = dateInput.date(),
            description = request.POST.get('descriptionInput'),
            timeStart = finalStartDateTime,
            timeEnd = finalEndDateTime
        )
        return redirect('admin-dashboard')
    else:
        blockedTimes = BlockOutTime.objects.all()
    return render(request, 'base/Admin-Blockout/block_time.html', {'blockedTimes':blockedTimes})

def finalsWeek(request):
    if request.method == 'POST':
        date = datetime.strptime(request.POST.get('firstDay'), '%Y-%m-%d')
        dateWeekDay =  date.weekday()
        weekday = True
        while weekday:
            try:
                blockedDate = BlockOutDate.objects.get(dateBlocked=date.date())
            except BlockOutDate.DoesNotExist:    
                blockOutDate = BlockOutDate.objects.create(
                    dateBlocked = date.date(),
                    description = 'FINALS'
                )
            date += timedelta(days=1)
            dateWeekDay +=1
            if dateWeekDay == 5:
                weekday=False
        return redirect('admin-dashboard')
    return render(request, 'base/Admin-Blockout/finals_week.html')

def blockGraduating(request):
    if request.method == 'POST':
        clients = Client.objects.filter(graduating=True).update(gradWaiting=True)
        return redirect('admin-dashboard')
    return render(request, 'base/Admin-Blockout/block_graduating.html')
    

def emailTemplate(request):
    return render(request, 'base/email.html')












