from django.db.models import QuerySet
from django.http import HttpRequest

from base.forms import LoanItemForm
from base.models import LoanItem


def get_empty_item_form() -> LoanItemForm:
    return LoanItemForm()


def handle_item_create(request: HttpRequest) -> tuple[LoanItemForm | None, bool]:
    form = LoanItemForm(request.POST)
    if form.is_valid():
        form.save()
        return None, False

    return LoanItemForm(), True


def get_item_panel_queryset(request: HttpRequest) -> tuple[QuerySet[LoanItem], bool]:
    items = LoanItem.objects.all().order_by("itemCat")
    filtered = False

    if request.method != 'GET':
        return items, filtered

    if request.GET.get('getItemBtn'):
        search_param = request.GET.get('itemCatQuery')
        if search_param:
            items = LoanItem.objects.filter(itemCat=search_param).order_by("itemCat")
    elif request.GET.get('filterLoanedItemsBtn') and request.GET.get('filter4LoanedItems') == 'on':
        items = LoanItem.objects.filter(status=LoanItem.LOANEDOUT).order_by("itemCat")
        filtered = True

    return items, filtered
