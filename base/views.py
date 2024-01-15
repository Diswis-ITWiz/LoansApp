from typing import Any
from django.shortcuts import render, redirect
from .forms import ClientForm, LoanItemForm
from .models import Client, LoanItem, Transaction, ReturnItem, BlockOutDate, BlockOutTime
from datetime import datetime, timedelta
from django.db.models import Q
from django.utils import timezone
from django.utils.timezone import localtime
# Create your views here.

def home(request):
    return render(request, 'base/home.html')

# Register Client
def newClient(request):
    form = ClientForm()
    
    if request.method == 'POST':
        graduatingStatus = True if request.POST.get('graduating') == 'on' else False
        # if request.POST.get('graduating') == 'on':
        #         graduatingStatus = True
        try:
            client= Client.objects.get(clientId = request.POST.get('clientId'))
            context = {'form': form, 'duplicate': True}
            return render(request, 'base/new_client.html', context)
        except Client.DoesNotExist:
            Client.objects.create(
                clientId = request.POST.get('clientId'),
                lastName = request.POST.get('lastName'),
                firstName = request.POST.get('firstName'),
                middleInitial = request.POST.get('middleInitial'),
                suffix = request.POST.get('suffix'),
                contactNum = request.POST.get('contactNum'),
                email = request.POST.get('email'),
                yearLvl = request.POST.get('yearLvl'),
                course = request.POST.get('course'),
                graduating = graduatingStatus,
                dswsMemReg = request.POST.get('dswsMemReg')
            )
            return redirect('home')
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
        try:
            client = Client.objects.get(clientId__exact=q)
        except Client.DoesNotExist:
            invalidInput = True
            context = {'input_validity': invalidInput}
            return render(request, 'base/Home-Item/find_client.html', context)
        

        # Check if Graduating senior:
        if client.gradwaiting == True:
            context = {'gradwaiting': True}
            return render(request, 'base/Home-Item/find_client.html', context)

        if client.borrowing == True:
            context = {'client': client, 'borrowingStatus': True}
        else:
            context = {'client':client}

        return render(request, 'base/Home-Item/find_client.html', context)
    return render(request, 'base/Home-Item/find_client.html', context)

def loanItemTransaction(request, pk):
    client = Client.objects.get(clientId__exact=pk)
    items = LoanItem.objects.all()
    time = None
    closingtime = None
    dateDue = None
    checkedWedBox = None

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
        checkedWedBox = request.GET.get('hasWednesdayClasses')
        hasWednesdayClasses = True if checkedWedBox == 'on' else False

        # Item type A - borrow for a whole day
        if (itemCat.startswith('B') or itemCat.startswith('C') or itemCat.startswith('D') 
            or itemCat.startswith('TR') or itemCat.startswith('U')):
            dateDue += timedelta(days=1)

            # Keep adding 1 day to dateDue until we find a valid date
            while ifNoClasses(dateDue, hasWednesdayClasses):
                dateDue += timedelta(days=1)
            
            # Set Closing Time of due date
            tempDateDue = None
            if dateDue.weekday() == 2:
                tempDateDue = dateDue.replace(hour=14, minute=00)
            else:
                tempDateDue = dateDue.replace(hour=17, minute=00)
            dateDue = tempDateDue
        # Item type B - borrow for only 2 hours
        else:
            # Check if the client cannot return the item before closing time
            if dateDue >= closingtime:
                dateDue += timedelta(days=1)
                tempDateDue = dateDue.replace(hour=11, minute=00)
                dateDue = tempDateDue
                
                while ifNoClasses(dateDue, hasWednesdayClasses) or timeOverlap(dateDue):
                    dateDue += timedelta(days=1)
                    tempDateDue = dateDue.replace(hour=11, minute=00, second=00, microsecond=00)
                    dateDue = tempDateDue
                    
            else:
                dateDue += timedelta(hours=2)
                while ifNoClasses(dateDue, hasWednesdayClasses) or timeOverlap(dateDue):
                    dateDue += timedelta(days=1)
                    tempDateDue = dateDue.replace(hour=11, minute=00, second=00, microsecond=00)
                    dateDue = tempDateDue

        
        context = {'client': client, 'items': items, 
                   'time': time,
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
            dateDue = dueDate,
            dswsMemLoan = request.POST.get('dswsMemLoan'),
            remarks = request.POST.get('remarks'),
        )

        client.lastBorrowed = time
        client.lastItem = selectedItem
        client.borrowing = True
        client.save()

        selectedItem.lastClient = client.clientId
        selectedItem.status = 'LO'
        selectedItem.save()

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
    if request.method == 'POST':
        # Create ReturnItem Instance in DB
        returnItem = ReturnItem.objects.create(
            dateReturned = datetime.now(),
            overdueDays = 0,
            overdueHours = 0,
            overdueMinutes = 0 ,
            dswsMemRet = request.POST.get('dswsMemRet'),
            remarks = request.POST.get('remarks'),
            transactionId = transaction,
            clientId = client,
            itemCat = loanedItem,
        )
        returnItem.save()

        # Modify the statuses of the respective client, transaction, and loanItem
        client.borrowing = False
        client.save()
        transaction.status = 'C'
        transaction.save()
        loanedItem.status = 'IS'
        loanedItem.save()

        return redirect('home')
    
    context = {'transaction':transaction, 'client':client, 'loanedItem':loanedItem}
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
        blockedDate = BlockOutDate.objects.get(dateblocked=duedate.date())
        return True
    except BlockOutDate.DoesNotExist:
        return False
    
def getClosingTime(time):
    dayofweek = time.weekday()
    closingtime = time
    if dayofweek == 2:
        closingtime.replace(hour=14, minute=00)
    else:
        closingtime.replace(hour=17, minute=00)
    return closingtime





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
        return redirect('item-details', pk=item.itemCat)
    else:
        form = LoanItemForm(instance=item)
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
        client.clientId = request.POST.get('clientId')
        client.firstName = request.POST.get('firstName')
        client.middleInitial = request.POST.get('middleInitial')
        client.lastName = request.POST.get('lastName')
        client.suffix = request.POST.get('suffix')
        client.yearLvl = request.POST.get('yearLvl')
        client.course = request.POST.get('course')
        if request.POST.get('graduating') == 'on':
                graduatingStatus = True
        client.graduating = graduatingStatus
        client.email = request.POST.get('email')
        client.contactNum = request.POST.get('contactNum')
        client.save()
        return redirect('client-details', pk=client.clientId)
    else:
        form = ClientForm(instance=client)
        context = {'form': form}
        return render(request, 'base/Admin-Client/edit_client.html', context)

def liftClientPenalty(request, pk):
    client = Client.objects.get(clientId=pk)
    if request.method == 'POST':
        client.excuseLetter = False
        client.temporaryBlackList = False
        client.blackListed = False
        client.holdOrder = False
        client.fine = 0
        client.tblStart = None
        client.tblEnd = None 
        client.HOcount = 0 if client.HOcount == 0 else client.HOcount - 1
        client.BLcount = 0 if client.BLcount == 0 else client.BLcount - 1
        client.warningCount = 0 if client.warningCount ==0 else client.warningCount - 1
        client.save()
        return redirect('client-details', pk=client.clientId)

                
    return render(request, 'base/Admin-Client/lift_client_penalty.html', {'client': client})


# Block Dates
def blockOutDate(request):
    if request.method == 'POST':
        date = datetime.strptime(request.POST.get('dateInput',), '%Y-%m-%d')
        blockOutDate = BlockOutDate.objects.create(
            dateblocked = date,
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
            print(dateWeekDay)
            try:
                blockedDate = BlockOutDate.objects.get(dateblocked=date.date())
            except BlockOutDate.DoesNotExist:    
                blockOutDate = BlockOutDate.objects.create(
                    dateblocked = date.date(),
                    description = 'FINALS'
                )
            date += timedelta(days=1)
            dateWeekDay +=1
            if dateWeekDay == 5:
                weekday=False
        return redirect('admin-dashboard')
    return render(request, 'base/Admin-Blockout/finals_week.html')
















