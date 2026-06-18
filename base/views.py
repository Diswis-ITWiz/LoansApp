from base.constants import BLOCK_TIME_INPUT_CONSTRAINTS, LoanItemStatus, PenaltyLiftChoice
from base.services.blockouts import (
    block_finals_weekdays,
    block_graduating_clients,
    create_blockout_date,
    create_blockout_time,
)
from base.services.client_panel import get_client_panel_queryset
from base.services.clients import get_loan_client_lookup_context, get_return_client_lookup_context
from base.services.item_panel import get_empty_item_form, get_item_panel_queryset, handle_item_create
from base.services.loan_transaction_views import handle_loan_transaction_get, handle_loan_transaction_post
from base.services.pagination import paginate_queryset
from base.services.penalties import lift_client_penalty
from base.services.reporting import report_item as report_item_service
from base.services.return_views import build_return_item_context, get_return_form, handle_return_item_post
from base.services.returns import assess_return
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from .forms import (
    BlockDateForm,
    ClientForm,
    LoanItemEditForm,
    LoginForm,
)
from .models import Client, LoanItem, Transaction, BlockOutDate, BlockOutTime
from django.db.models import Q
from django.utils import timezone
from django.contrib import messages



# Create your views here
def home(request: HttpRequest) -> HttpResponse:
    return render(request, 'base/home.html')

# Register Client
def newClient(request: HttpRequest) -> HttpResponse:
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
def loanItemClientFinder(request: HttpRequest) -> HttpResponse | None:
    if request.method == 'GET':
        q = request.GET.get('q', '')
        context = get_loan_client_lookup_context(q)
        return render(request, 'base/Home-Item/find_client.html', context)


def loanItemTransaction(request: HttpRequest, pk: str) -> HttpResponse | None:
    client = Client.objects.select_related("lastBorrowedItem").get(clientId__exact=pk)
    items = LoanItem.objects.filter(status=LoanItem.INSTORAGE).order_by("itemCat")
    latestTransaction = Transaction.objects.select_related("clientId", "itemCat").filter(clientId__exact=pk).first()

    if request.method == 'POST':
        return handle_loan_transaction_post(request, client, items, latestTransaction)

    return handle_loan_transaction_get(request, client, items, latestTransaction)


#Return Item
def returnItem1(request: HttpRequest) -> HttpResponse:
    if request.method == 'GET':
        q = request.GET.get('q', '')
        context = get_return_client_lookup_context(q)
        return render(request, 'base/Home-Item/return_item.html', context)
    return render(request, 'base/Home-Item/return_item.html')

def returnItem2(request: HttpRequest, pk: str) -> HttpResponse:
    transaction = Transaction.objects.select_related("clientId", "itemCat").get(id=pk)
    assessment = assess_return(transaction)
    form = get_return_form(assessment)
    loginform = LoginForm()

    if request.method == 'POST':
        form, loginform, response = handle_return_item_post(request, transaction, assessment, form)
        if response:
            return response

    context = build_return_item_context(form, assessment, loginform)
    return render(request, 'base/Home-Item/return_item2.html', context)

def report(request: HttpRequest, pk: str) -> HttpResponse:
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
def lateTransactions(request: HttpRequest) -> HttpResponse:
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

def lateTranscactionDetails(request: HttpRequest, pk: str) -> HttpResponse:
    transaction = Transaction.objects.select_related("clientId", "itemCat").get(id=pk)
    assessment = assess_return(transaction)
    context = {'transaction':transaction, 'client':transaction.clientId,
               'loanedItem': transaction.itemCat, 'itemType': assessment.item_type,
               'penalty': assessment.penalty, 'overDueDays': assessment.overdue_days, 'overDueHours': assessment.overdue_hours,
               'overDueMinutes': assessment.overdue_minutes}
    return render(request, 'base/Home-Item/late_transactions_detail.html', context)

# ADMIN PANELS
@login_required(login_url='login')
def adminDashboard(request: HttpRequest) -> HttpResponse:
    if "toggleFinalsWeek" in request.POST:
        block_finals_weekdays(request.POST.get('firstDay'))
        return redirect('admin-dashboard')
    elif 'blockGradWaiting' in request.POST:
        block_graduating_clients(Client)
        return redirect('admin-dashboard')
    return render(request, 'base/admin_page.html')


# ITEMS
@login_required(login_url='login')
def itemPanel(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form, duplicateItem = handle_item_create(request)
        if form is None:
            return redirect('item-panel')
    else:
        form = get_empty_item_form()
        duplicateItem = False

    items, filtered = get_item_panel_queryset(request)
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
def itemDetailView(request: HttpRequest, pk: str) -> HttpResponse:
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
def editItem(request: HttpRequest, pk: str) -> HttpResponse:
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
def deleteItem(request: HttpRequest, pk: str) -> HttpResponse:
    item = LoanItem.objects.get(itemCat=pk)

    if request.method == 'POST':
        item.delete()
        return redirect('item-panel')
    else:
        return render(request, 'base/Admin-Item/delete_item.html', {'item': item})


# CLIENTS
@login_required(login_url='login')
def clientPanel(request: HttpRequest) -> HttpResponse:
    clients, filtered = get_client_panel_queryset(request)
    page_obj, page_querystring = paginate_queryset(request, clients)
    context = {
        'clients': page_obj,
        "page_obj": page_obj,
        "page_querystring": page_querystring,
        'filtered': filtered,
    }
    return render(request, 'base/Admin-Client/client_panel.html', context)

@login_required(login_url='login')
def clientDetails(request: HttpRequest, pk: str) -> HttpResponse:
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
def editClient(request: HttpRequest, pk: str) -> HttpResponse:
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
def liftClientPenalty(request: HttpRequest, pk: str) -> HttpResponse:
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
def penalizedClients(request: HttpRequest) -> HttpResponse:
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
def blockOutDate(request: HttpRequest) -> HttpResponse:
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
def blockOutTime(request: HttpRequest) -> HttpResponse:
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



def emailTemplate(request: HttpRequest) -> HttpResponse:
    return render(request, 'base/email.html')


def adminLogin(request: HttpRequest) -> HttpResponse:
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

def adminLogout(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect('home')



