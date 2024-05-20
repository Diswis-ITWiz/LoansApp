import base.helpers as helpers
from base.helpers import *
from typing import Any
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import *
from .models import Client, LoanItem, Transaction, BlockOutDate, BlockOutTime
from datetime import datetime, timedelta
from django.db.models import Q
from django.utils import timezone
from django.utils.timezone import localtime
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
    if request.method == 'GET':
        q = request.GET.get('q', '')
        # Prevents Getting all clients
        if q == '':
            return render(request, 'base/Home-Item/find_client.html', {})
        #Client May Not Exist
        if Client.objects.filter(clientId__exact=q).exists():
            client = Client.objects.get(clientId__exact=q)
            transactions = Transaction.objects.filter(clientId__exact=q)
            context = {'client':client, 'borrowCount': transactions.count(), 'latest_transaction':transactions.first()}
            if client.borrowing == True:
                context.update({
                    'dueDate': transactions[0].dueDate,
                    'borrowing': True,
                })
            elif client.gradWaiting:
                context.update({
                    'gradWaiting': True
                })
            elif client.blackListed or client.temporaryBlackList:
                context.update(
                    {
                        'blackListed': True
                    }
                )
            else:
                return render(request, 'base/Home-Item/find_client.html', context)
            return render(request, 'base/Home-Item/find_client.html', context)
        else:
            return redirect('new-client')


def loanItemTransaction(request, pk):
    client = Client.objects.get(clientId__exact=pk)
    items = LoanItem.objects.filter(status='IS')
    latestTransaction = Transaction.objects.filter(clientId__exact=pk).first()
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
            form = LoanItemTransactionForm()
            context = {'client': client, 'items': items, 'form': form, 'selectedItem': None, "latestTransaction": latestTransaction, "calculated": False}
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


        form = LoanItemTransactionForm(
            initial={"itemCat": itemCat,
                    "dateDue": dateDue,
                    "dateLoaned": time
            }
        )
        context = {'client': client, 'items': items,  
                   'itemType': itemType, 'form':form, 
                   'selectedItem':itemCat, "latestTransaction": latestTransaction,
                   'calculated':True}
        return render(request, 'base/Home-Item/loan_item_transaction.html', context)
    
    
    if request.method == 'POST':
        form = LoanItemTransactionForm(request.POST)
        if form.is_valid():
            selectedItem = LoanItem.objects.get(itemCat=form.cleaned_data["itemCat"])
            transaction = Transaction.objects.create(
                clientId = client,
                itemCat = selectedItem,
                dswsMemLoanName = form.cleaned_data["reciever"],
                loanRemarks = form.cleaned_data["remarks"],
                dateLoaned = form.cleaned_data["dateLoaned"],
                dueDate = form.cleaned_data["dateDue"]
            )
            client.lastBorrowedDate = time
            client.lastBorrowedItem = selectedItem
            client.borrowing = True
            client.save()
            selectedItem.lastClient = client.clientId
            selectedItem.status = 'LO'
            selectedItem.save()
            messages.success(request, 'Transaction added.')

            # Email Functionality
            email_borrow_date = form.cleaned_data["dateLoaned"].strftime("%m/%d/%Y %I:%M %p")
            email_due_date = form.cleaned_data["dateDue"].strftime("%m/%d/%Y %I:%M %p")
            itemCatName = getItemTypeName(selectedItem.itemCat)
            sendTransactionEmail(selectedItem.itemCat, itemCatName, email_borrow_date, email_due_date, client)
            
            return redirect('home')
        
        context = {'client': client, 'items': items, 'form':form, 'selectedItem': None}
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
            try:
                transaction = Transaction.objects.get(
                    Q(clientId__exact=client.clientId) & Q(status__exact='OG')
                )
            except Transaction.DoesNotExist:
                transaction = False
            context = {'client': client, 'transaction': transaction}
            return render(request, 'base/Home-Item/return_item.html', context)
        except Client.DoesNotExist:
            invalidInput = True
            context = {'input_validity': invalidInput}
            return render(request, 'base/Home-Item/return_item.html', context)
    return render(request, 'base/Home-Item/return_item.html')

def returnItem2(request, pk):
    transaction = Transaction.objects.get(id=pk)
    client = Client.objects.get(clientId=transaction.clientId.clientId)
    name = client.lastName + ', ' + client.firstName + ', ' + client.middleInitial
    loanedItem = LoanItem.objects.get(itemCat = transaction.itemCat.itemCat)
    overdueDays = 0
    overdueHours = 0
    overdueMinutes = 0
    penalty = ''
    form = ''
    loginform = LoginForm()
    if checkItemType(loanedItem.itemCat) == 'A':
        overdueDays = getItemTypeAOverdueDays(localtime(transaction.dueDate), client)
        penalty = calculateTypeAPenalty(overdueDays, client)
        form = ReturnItemATransactionForm(
            initial={
                "clientIDNo": client.clientId,
                "clientName": name,
                "itemCat": loanedItem.itemCat,
                "itemType": "A",
                "dueDate": localtime(transaction.dueDate),
                "overDueDays": overdueDays,
            }
        )
    else:
        overdueHours, overdueMinutes = getItemTypeBOverdueTime(localtime(transaction.dueDate), client)
        penalty = calculateTypeBPenalty(overdueHours,overdueMinutes, client)
        form = ReturnItemBTransactionForm(
            initial={
                "clientIDNo": client.clientId,
                "clientName": name,
                "itemCat": loanedItem.itemCat,
                "itemType": "B",
                "dueDate": localtime(transaction.dueDate),
                "overDueHours": overdueHours,
                "overDueMinutes": overdueMinutes
            }
        )
    if request.method == 'POST':
        if 'override' in request.POST:
            loginform = LoginForm(request.POST)
            if loginform.is_valid():
                username = loginform.cleaned_data['username']
                password = loginform.cleaned_data['password']
                user = authenticate(request, username=username, password=password)
                if user:
                    if checkItemType(loanedItem.itemCat) == 'A':
                        form.fields['overDueDays'].widget.attrs.pop('readonly')
                    else:
                        form.fields['overDueHours'].widget.attrs.pop('readonly', None)
                        form.fields['overDueMinutes'].widget.attrs.pop('readonly', None)
        else:
            form = None
            dateofReturn = timezone.localtime(timezone.now())
            if "A" in request.POST:
                form = ReturnItemATransactionForm(request.POST)
                if form.is_valid():
                    applyTypeAPenalty(form.cleaned_data["overDueDays"], client)
                    transaction.overdueDays = form.cleaned_data["overDueDays"]
            else:
                form = ReturnItemBTransactionForm(request.POST)
                if form.is_valid():
                    applyTypeBPenalty(form.cleaned_data["overDueHours"], form.cleaned_data["overDueMinutes"] , client)
                    transaction.overdueHours = form.cleaned_data["overDueHours"]
                    transaction.overdueMinutes = form.cleaned_data["overDueMinutes"]

            # Modify Transaction Instance in DB
            transaction.dateReturned = timezone.localtime(timezone.now())
            transaction.dswsMemRetName = form.cleaned_data["reciever"]
            transaction.returnRemarks = form.cleaned_data["remarks"]
            transaction.status = 'C'
            transaction.save()
            # Modify the statuses of the respective client, transaction, and loanItem
            client.borrowing = False
            client.lastBorrowedDate = dateofReturn
            client.save()
            loanedItem.status = 'IS'
            loanedItem.save()

            return redirect('home')
    
    context = {'form':form, 'penalty': penalty, 'itemType': checkItemType(loanedItem.itemCat), "loginform": loginform}


    return render(request, 'base/Home-Item/return_item2.html', context)


# Overdue Transactions
def lateTransactions(request):
    currentTime = timezone.localtime(timezone.now())
    transactions = Transaction.objects.filter(
        Q(status__exact='OG') & Q(dueDate__lt=currentTime))
    context = {'currentTime':currentTime, 'transactions':transactions}
    return render(request, 'base/Home-item/late_transactions.html', context)

def lateTranscactionDetails(request, pk):
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
    context = {'transaction':transaction, 'client':client, 
               'loanedItem': loanedItem, 'itemType': checkItemType(loanedItem.itemCat), 
               'penalty': penalty, 'overDueDays': overdueDays, 'overDueHours': overdueHours, 
               'overDueMinutes': overdueMinutes}
    return render(request, 'base/Home-item/late_transactions_detail.html', context)

# ADMIN PANELS
@login_required(login_url='login')
def adminDashboard(request):
    if "toggleFinalsWeek" in request.POST:
        date = datetime.strptime(request.POST.get('firstDay'), '%Y-%m-%d')
        dateWeekDay =  date.weekday()
        weekday = True
        while weekday:
            try:
                blockedDate = BlockOutDate.objects.get(dateBlocked=date.date())
            except BlockOutDate.DoesNotExist:    
                print(date.date())
                blockOutDate = BlockOutDate.objects.create(
                    dateBlocked = date.date(),
                    description = 'FINALS'
                )
            date += timedelta(days=1)
            dateWeekDay +=1
            print(date)
            print(dateWeekDay)
            if dateWeekDay == 5:
                weekday=False
        return redirect('admin-dashboard')
    elif 'blockGradWaiting' in request.POST:
        clients = Client.objects.filter(graduating=True).update(gradWaiting=True)
        return redirect('admin-dashboard')
    return render(request, 'base/admin_page.html')


# ITEMS
@login_required(login_url='login')
def itemPanel(request):
    form = LoanItemForm()
    if request.method == 'GET':
        if request.GET.get('getItemBtn'):
            search_param = request.GET.get('itemCatQuery')
            if search_param == '':
                pass
            else:
                search_item = LoanItem.objects.filter(itemCat=search_param)
                return render(request, 'base/Admin-Item/item_panel.html', {'items': search_item})
        elif request.GET.get('filterLoanedItemsBtn'):
            if request.GET.get('filter4LoanedItems') == 'on':
                loaned_items = LoanItem.objects.filter(status='LO')
                return render(request, 'base/Admin-Item/item_panel.html', {"items": loaned_items, 'filtered': True})
    if request.method == 'POST':
        form = LoanItemForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('item-panel')
    items = LoanItem.objects.all()
    context = {"items": items, 'filtered': False, "form":form}        
    return render(request, 'base/Admin-Item/item_panel.html', context)

@login_required(login_url='login')
def itemDetailView(request, pk):
    loanItem = LoanItem.objects.get(itemCat=pk)
    transactionHistory = Transaction.objects.filter(itemCat=loanItem)
    context = {"item": loanItem,"transactions":transactionHistory}
    return render(request, 'base/Admin-Item/loanitem_detail.html', context)

@login_required(login_url='login')
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

@login_required(login_url='login')
def deleteItem(request, pk):
    item = LoanItem.objects.get(itemCat=pk)

    if request.method == 'POST':
        item.delete()
        return redirect('item-panel')
    else:
        return render(request, 'base/Admin-Item/delete_item.html', {'item': item})


# CLIENTS
@login_required(login_url='login')
def clientPanel(request):
    if request.method == 'GET':
        if request.GET.get('getClientBtn'):
            search_param = request.GET.get('clientIdQuery')
            if search_param == '':
                pass
            else:
                search_client = Client.objects.filter(clientId=search_param)
                return render(request, 'base/Admin-Client/client_panel.html', {'clients': search_client})
        elif request.GET.get('filterBorrowingClientsBtn'):
            if request.GET.get('filter4BorrowingClients') == 'on':
                borrowing_clients = Client.objects.filter(borrowing=True)
                return render(request, 'base/Admin-Client/client_panel.html', {"clients": borrowing_clients, 'filtered': True})
    clients = Client.objects.all()
    context = {'clients': clients, 'filtered': False}
    return render(request, 'base/Admin-Client/client_panel.html', context)

@login_required(login_url='login')
def clientDetails(request, pk):
    client = Client.objects.get(clientId=pk)
    transactions = Transaction.objects.filter(clientId=client)
    context = {'client': client, 'transactions': transactions}
    return render(request, 'base/Admin-Client/client_details.html', context)

@login_required(login_url='login')
def editClient(request, pk):
    client = Client.objects.get(clientId=pk)
    if request.method == 'POST':
        form = ClientForm(request.POST or None, instance=client)
        form.fields["clientId"].disabled = "disabled"
        if form.is_valid():
            form.save()
            return redirect('client-details', pk=client.clientId)
        return render(request, 'base/Admin-Client/edit_client.html', {'form': form, 'client':client.clientId})
    else:
        form = ClientForm(instance=client)
        form.fields["clientId"].disabled = "disabled"
        return render(request, 'base/Admin-Client/edit_client.html', {'form': form, 'client':client.clientId})

@login_required(login_url='login')  
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
            client.temporaryBlackList = False
        elif client.temporaryBlackList == True:
            client.temporaryBlackList = False
            client.excuseLetter = False
            client.holdOrder = False
            client.fineAmount = 0
        elif client.fineAmount > 0:
            client.fineAmount = 0
        else:
            client.warningCount = 0 if client.warningCount == 0 else client.warningCount - 1
        client.save()
        return redirect('client-details', pk=client.clientId)

                
    return render(request, 'base/Admin-Client/lift_client_penalty.html', {'client': client})

@login_required(login_url='login')  
def blacklistedClients(request):
    print("Stuff")
    clients = Client.objects.filter(Q(blackListed=True) | 
                                    Q(temporaryBlackList=True) | 
                                    Q(fineAmount__gt=0, blackListed=False, temporaryBlackList=False))
    context={"clients":clients}
    return render(request, 'base/Admin-Client/blacklist.html', context)

# Block Dates
@login_required(login_url='login')
def blockOutDate(request):
    form = BlockDateForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            blockOutDate = BlockOutDate.objects.create(
                dateBlocked = form.cleaned_data["blockDate"],
                description = form.cleaned_data["description"]
            )
            return redirect('admin-dashboard')
    blockedDates = BlockOutDate.objects.all()
    return render(request, 'base/Admin-Blockout/block_date.html', {'blockedDates': blockedDates, "form": form})

@login_required(login_url='login')
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

    

def emailTemplate(request):
    return render(request, 'base/email.html')


def adminLogin(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)    
                return redirect('admin-dashboard')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})

def adminLogout(request):
    logout(request)
    return redirect('home')









