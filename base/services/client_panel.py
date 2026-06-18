from django.db.models import QuerySet
from django.http import HttpRequest

from base.models import Client


def get_client_panel_queryset(request: HttpRequest) -> tuple[QuerySet[Client], bool]:
    clients = Client.objects.select_related("lastBorrowedItem").all().order_by("lastName", "firstName")
    filtered = False

    if request.method != 'GET':
        return clients, filtered

    if request.GET.get('getClientBtn'):
        search_param = request.GET.get('clientIdQuery')
        if search_param:
            clients = (
                Client.objects
                .select_related("lastBorrowedItem")
                .filter(clientId=search_param)
                .order_by("lastName", "firstName")
            )
    elif request.GET.get('filterBorrowingClientsBtn') and request.GET.get('filter4BorrowingClients') == 'on':
        clients = (
            Client.objects
            .select_related("lastBorrowedItem")
            .filter(borrowing=True)
            .order_by("lastName", "firstName")
        )
        filtered = True

    return clients, filtered
