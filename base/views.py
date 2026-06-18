from base.constants import (
    BLOCK_TIME_INPUT_CONSTRAINTS,
    ItemType,
    LoanItemStatus,
    PenaltyLiftChoice,
)
from base.services.blockouts import (
    block_finals_weekdays,
    block_graduating_clients,
    create_blockout_date,
    create_blockout_time,
)
from base.services.clients import get_loan_client_lookup_context, get_return_client_lookup_context
from base.services.emailing import send_transaction_email
from base.services.item_types import get_item_type_name
from base.services.loaning import calculate_loan_due_date, create_loan_transaction
from base.services.pagination import paginate_queryset
from base.services.penalties import lift_client_penalty
from base.services.reporting import report_item as report_item_service
from base.services.returns import assess_return, complete_return, enable_overdue_override
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import (
    BlockDateForm,
    ClientForm,
    LoanItemEditForm,
    LoanItemForm,
    LoanItemTransactionForm,
    LoginForm,
    ReturnItemATransactionForm,
    ReturnItemBTransactionForm,
)
from .models import Client, LoanItem, Transaction, BlockOutDate, BlockOutTime
from django.db.models import Q
from django.utils import timezone
from django.contrib import messages



# Create your views here
def home(request):
    return render(request, 'base/home.html')

# Register Client
def newClient(request):
    error = False
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Client added.') # <- Needs Bootstrap
            return redirect('home')
        else:
            error=True
        return render(request, 'base/Home-Client/new_client.html', {'form': form, "duplicate": error})
    else:
        form = ClientForm()
        context = {'form': form, "duplicate": error}
        return render(request, 'base/Home-Client/new_client.html', context)


# Loan Item
def loanItemClientFinder(request):
    if request.method == 'GET':
        q = request.GET.get('q', '')
        context = get_loan_client_lookup_context(q)
        return render(request, 'base/Home-Item/find_client.html', context)


def loanItemTransaction(request, pk):
    client = Client.objects.select_related("lastBorrowedItem").get(clientId__exact=pk)
    items = LoanItem.objects.filter(status=LoanItem.INSTORAGE).order_by("itemCat")
    latestTransaction = Transaction.objects.select_related("clientId", "itemCat").filter(clientId__exact=pk).first()

    if request.method == 'GET':
        q = request.GET.get('selectedItem', '')
        if q == '':
            form = LoanItemTransactionForm()
            context = {'client': client, 'items': items, 'form': form, 'selectedItem': None, "latestTransaction": latestTransaction, "calculated": False}
            return render(request, 'base/Home-Item/loan_item_transaction.html', context)
        
        selectedItem = LoanItem.objects.get(itemCat__exact=q)
        due_date = calculate_loan_due_date(client, selectedItem)

        form = LoanItemTransactionForm(
            initial={"itemCat": selectedItem.itemCat,
                    "dateDue": due_date.due_date,
                    "dateLoaned": due_date.loaned_at
            }
        )
        context = {'client': client, 'items': items,  
                   'itemType': due_date.item_type, 'form':form, 
                   'selectedItem':selectedItem.itemCat, "latestTransaction": latestTransaction,
                   'calculated':True}
        return render(request, 'base/Home-Item/loan_item_transaction.html', context)
    
    
    if request.method == 'POST':
        form = LoanItemTransactionForm(request.POST)
        if form.is_valid():
            selectedItem = LoanItem.objects.get(itemCat=form.cleaned_data["itemCat"])
            create_loan_transaction(
                client=client,
                item=selectedItem,
                dsws_member_name=form.cleaned_data["reciever"],
                remarks=form.cleaned_data["remarks"],
                date_loaned=form.cleaned_data["dateLoaned"],
                due_date=form.cleaned_data["dateDue"],
            )
            messages.success(request, 'Transaction added.')

            # Email Functionality
            email_borrow_date = form.cleaned_data["dateLoaned"].strftime("%m/%d/%Y %I:%M %p")
            email_due_date = form.cleaned_data["dateDue"].strftime("%m/%d/%Y %I:%M %p")
            itemCatName = get_item_type_name(selectedItem.itemCat)
            send_transaction_email(selectedItem.itemCat, itemCatName, email_borrow_date, email_due_date, client)
            
            return redirect('home')
        
        context = {'client': client, 'items': items, 'form':form, 'selectedItem': None}
        return render(request, 'base/Home-Item/loan_item_transaction.html', context)



#Return Item
def returnItem1(request):
    if request.method == 'GET':
        q = request.GET.get('q', '')
        context = get_return_client_lookup_context(q)
        return render(request, 'base/Home-Item/return_item.html', context)
    return render(request, 'base/Home-Item/return_item.html')

def returnItem2(request, pk):
    transaction = Transaction.objects.select_related("clientId", "itemCat").get(id=pk)
    assessment = assess_return(transaction)
    form_class = ReturnItemATransactionForm if assessment.item_type == ItemType.A else ReturnItemBTransactionForm
    form = form_class(initial=assessment.initial_data)
    loginform = LoginForm()

    if request.method == 'POST':
        if 'override' in request.POST:
            loginform = LoginForm(request.POST)
            if loginform.is_valid():
                username = loginform.cleaned_data['username']
                password = loginform.cleaned_data['password']
                user = authenticate(request, username=username, password=password)
                if user:
                    enable_overdue_override(form, assessment.item_type)
        else:
            if ItemType.A in request.POST:
                form = ReturnItemATransactionForm(request.POST)
                item_type = ItemType.A
            else:
                form = ReturnItemBTransactionForm(request.POST)
                item_type = ItemType.B

            if form.is_valid():
                complete_return(transaction, item_type, form.cleaned_data)
                return redirect('home')
    
    context = {'form':form, 'penalty': assessment.penalty, 'itemType': assessment.item_type, "loginform": loginform}


    return render(request, 'base/Home-Item/return_item2.html', context)

def report(request, pk):
    offendingClient = Client.objects.get(clientId=pk)
    reportedItem = offendingClient.lastBorrowedItem
    if request.method == "POST":
        report_item_service(
            offendingClient,
            fine_amount=request.POST.get('fineAmount'),
            report_type=request.POST.get("reportType"),
        )
        return redirect('home')
    context={
        "offendingClient": offendingClient,
        "reportedItem": reportedItem,
        "reportStatusChoices": LoanItemStatus.REPORT_CHOICES,
    }
    return render(request, 'base/Home-Item/report_item.html', context)

# Overdue Transactions
def lateTransactions(request):
    currentTime = timezone.localtime(timezone.now())
    transactions = Transaction.objects.select_related("clientId", "itemCat").filter(
        Q(status__exact=Transaction.ONGOING) & Q(dueDate__lt=currentTime))
    page_obj, page_querystring = paginate_queryset(request, transactions)
    context = {
        'currentTime': currentTime,
        'transactions': page_obj,
        "page_obj": page_obj,
        "page_querystring": page_querystring,
    }
    return render(request, 'base/Home-Item/late_transactions.html', context)

def lateTranscactionDetails(request, pk):
    transaction = Transaction.objects.select_related("clientId", "itemCat").get(id=pk)
    assessment = assess_return(transaction)
    context = {'transaction':transaction, 'client':transaction.clientId, 
               'loanedItem': transaction.itemCat, 'itemType': assessment.item_type, 
               'penalty': assessment.penalty, 'overDueDays': assessment.overdue_days, 'overDueHours': assessment.overdue_hours, 
               'overDueMinutes': assessment.overdue_minutes}
    return render(request, 'base/Home-Item/late_transactions_detail.html', context)

# ADMIN PANELS
@login_required(login_url='login')
def adminDashboard(request):
    if "toggleFinalsWeek" in request.POST:
        block_finals_weekdays(request.POST.get('firstDay'))
        return redirect('admin-dashboard')
    elif 'blockGradWaiting' in request.POST:
        block_graduating_clients(Client)
        return redirect('admin-dashboard')
    return render(request, 'base/admin_page.html')


# ITEMS
@login_required(login_url='login')
def itemPanel(request):
    form = LoanItemForm()
    duplicateItem = False
    items = LoanItem.objects.all().order_by("itemCat")
    filtered = False

    if request.method == 'GET':
        if request.GET.get('getItemBtn'):
            search_param = request.GET.get('itemCatQuery')
            if search_param == '':
                pass
            else:
                items = LoanItem.objects.filter(itemCat=search_param).order_by("itemCat")
        elif request.GET.get('filterLoanedItemsBtn'):
            if request.GET.get('filter4LoanedItems') == 'on':
                items = LoanItem.objects.filter(status=LoanItem.LOANEDOUT).order_by("itemCat")
                filtered = True

    if request.method == 'POST':
        form = LoanItemForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('item-panel')
        else:
            duplicateItem = True
            form = LoanItemForm()

    page_obj, page_querystring = paginate_queryset(request, items)
    context = {
        "items": page_obj,
        "page_obj": page_obj,
        "page_querystring": page_querystring,
        'filtered': filtered,
        "form": form,
        "duplicate": duplicateItem,
    }        
    return render(request, 'base/Admin-Item/item_panel.html', context)

@login_required(login_url='login')
def itemDetailView(request, pk):
    loanItem = LoanItem.objects.get(itemCat=pk)
    transactionHistory = Transaction.objects.select_related("clientId", "itemCat").filter(itemCat=loanItem)
    page_obj, page_querystring = paginate_queryset(request, transactionHistory)
    context = {
        "item": loanItem,
        "transactions": page_obj,
        "page_obj": page_obj,
        "page_querystring": page_querystring,
    }
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
    clients = Client.objects.select_related("lastBorrowedItem").all().order_by("lastName", "firstName")
    filtered = False

    if request.method == 'GET':
        if request.GET.get('getClientBtn'):
            search_param = request.GET.get('clientIdQuery')
            if search_param == '':
                pass
            else:
                clients = Client.objects.select_related("lastBorrowedItem").filter(clientId=search_param).order_by("lastName", "firstName")
        elif request.GET.get('filterBorrowingClientsBtn'):
            if request.GET.get('filter4BorrowingClients') == 'on':
                clients = Client.objects.select_related("lastBorrowedItem").filter(borrowing=True).order_by("lastName", "firstName")
                filtered = True

    page_obj, page_querystring = paginate_queryset(request, clients)
    context = {
        'clients': page_obj,
        "page_obj": page_obj,
        "page_querystring": page_querystring,
        'filtered': filtered,
    }
    return render(request, 'base/Admin-Client/client_panel.html', context)

@login_required(login_url='login')
def clientDetails(request, pk):
    client = Client.objects.select_related("lastBorrowedItem").get(clientId=pk)
    transactions = Transaction.objects.select_related("clientId", "itemCat").filter(clientId=client)
    page_obj, page_querystring = paginate_queryset(request, transactions)
    context = {
        'client': client,
        'transactions': page_obj,
        "page_obj": page_obj,
        "page_querystring": page_querystring,
    }
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
        choice = request.POST.get("liftType", "")
        lift_client_penalty(client, choice)
        return redirect('client-details', pk=client.clientId)

                
    return render(
        request,
        'base/Admin-Client/lift_client_penalty.html',
        {'client': client, 'penaltyLiftChoices': PenaltyLiftChoice.CHOICES},
    )

@login_required(login_url='login')  
def penalizedClients(request):
    clients = (
        Client.objects
        .select_related("lastBorrowedItem")
        .filter(
            Q(blackListed=True) |
            Q(temporaryBlackList=True) |
            Q(fineAmount__gt=0, blackListed=False, temporaryBlackList=False)
        )
        .order_by("lastName", "firstName")
    )
    page_obj, page_querystring = paginate_queryset(request, clients)
    context = {
        "clients": page_obj,
        "page_obj": page_obj,
        "page_querystring": page_querystring,
    }
    return render(request, 'base/Admin-Client/penalized_clients.html', context)

# Block Dates
@login_required(login_url='login')
def blockOutDate(request):
    form = BlockDateForm(request.POST or None)
    context = {}
    isBlockedAlready = False
    if request.method == 'POST':
        if form.is_valid():
            isBlockedAlready = not create_blockout_date(
                form.cleaned_data["blockDate"],
                form.cleaned_data["description"],
            )
            form = BlockDateForm()
    blockedDates = BlockOutDate.objects.all()
    context = {'blockedDates': blockedDates, "form": form, "alreadyBlocked": isBlockedAlready}
    return render(request, 'base/Admin-Blockout/block_date.html', context)

@login_required(login_url='login')
def blockOutTime(request):
    context = {}
    isBlockedAlready = False
    if request.method == 'POST':
        isBlockedAlready = not create_blockout_time(
            request.POST.get('dateInput'),
            request.POST.get('startTime'),
            request.POST.get('endTime'),
            request.POST.get('descriptionInput'),
        )
    blockedTimes = BlockOutTime.objects.all()
    context = {
        "blockedTimes": blockedTimes,
        "alreadyBlocked": isBlockedAlready,
        "timeConstraints": BLOCK_TIME_INPUT_CONSTRAINTS,
    }
    return render(request, 'base/Admin-Blockout/block_time.html', context)

    

def emailTemplate(request):
    return render(request, 'base/email.html')


def adminLogin(request):
    form = LoginForm()
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
                return render(request, 'login.html', {'form': form, "invalidCredentials": True})
        
    return render(request, 'login.html', {'form': form})

def adminLogout(request):
    logout(request)
    return redirect('home')









