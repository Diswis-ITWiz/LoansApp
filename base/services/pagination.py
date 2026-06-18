from typing import Any

from django.core.paginator import Paginator
from django.core.paginator import Page
from django.db.models import QuerySet
from django.http import HttpRequest


def paginate_queryset(request: HttpRequest, queryset: QuerySet[Any], per_page: int = 25) -> tuple[Page, str]:
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(request.GET.get("page"))
    query_params = request.GET.copy()
    query_params.pop("page", None)
    return page_obj, query_params.urlencode()
