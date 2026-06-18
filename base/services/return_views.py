from django import forms
from django.contrib.auth import authenticate
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect

from base.constants import ItemType
from base.forms import LoginForm, ReturnItemATransactionForm, ReturnItemBTransactionForm
from base.models import Transaction
from base.services.returns import ReturnAssessment, complete_return, enable_overdue_override


def get_return_form_class(item_type: str) -> type[forms.Form]:
    return ReturnItemATransactionForm if item_type == ItemType.A else ReturnItemBTransactionForm


def get_return_form(assessment: ReturnAssessment) -> forms.Form:
    form_class = get_return_form_class(assessment.item_type)
    return form_class(initial=assessment.initial_data)


def build_return_item_context(
    form: forms.Form,
    assessment: ReturnAssessment,
    loginform: LoginForm,
) -> dict[str, object]:
    return {
        "form": form,
        "penalty": assessment.penalty,
        "itemType": assessment.item_type,
        "loginform": loginform,
    }


def handle_return_override(request: HttpRequest, form: forms.Form, item_type: str) -> LoginForm:
    loginform = LoginForm(request.POST)
    if loginform.is_valid():
        username = loginform.cleaned_data['username']
        password = loginform.cleaned_data['password']
        user = authenticate(request, username=username, password=password)
        if user:
            enable_overdue_override(form, item_type)
    return loginform


def handle_return_submission(request: HttpRequest, transaction: Transaction) -> tuple[forms.Form, HttpResponse | None]:
    if ItemType.A in request.POST:
        form = ReturnItemATransactionForm(request.POST)
        item_type = ItemType.A
    else:
        form = ReturnItemBTransactionForm(request.POST)
        item_type = ItemType.B

    if form.is_valid():
        complete_return(transaction, item_type, form.cleaned_data)
        return form, redirect('home')

    return form, None


def handle_return_item_post(
    request: HttpRequest,
    transaction: Transaction,
    assessment: ReturnAssessment,
    form: forms.Form,
) -> tuple[forms.Form, LoginForm, HttpResponse | None]:
    loginform = LoginForm()
    if 'override' in request.POST:
        loginform = handle_return_override(request, form, assessment.item_type)
        return form, loginform, None

    submitted_form, response = handle_return_submission(request, transaction)
    return submitted_form, loginform, response
