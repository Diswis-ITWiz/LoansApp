from django.forms import ModelForm
from django import forms
from .models import Client, Transaction, LoanItem, BlockOutDate, BlockOutTime
from .widgets import DatePickerInput, TimePickerInput, DateTimePickerInput
from django.contrib.auth.models import User
from datetime import datetime
from django.utils.translation import gettext_lazy as _

class LoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={'class':'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control'}))

class ClientForm(ModelForm):
    class Meta:
        model = Client
        fields = '__all__'
        exclude = ['borrowing', 'warningCount', 'status', 'dateReg',
                   'gradWaiting', 'lastBorrowedDate', 'lastBorrowedItem', 'HOcount', 
                   'BLcount','excuseLetter', 'holdOrder', 'blackListed', 
                    'fineAmount', 'temporaryBlackList', 'blacklistStart','blacklistEnd',
                    ] 
        labels = {
            "clientId": _("Client ID No"),
            "lastName": _("Last Name"),
            "firstName": _("First Name"),
            "middleInitial": _("Middle Initial"),
            "suffix": _("Suffix"),
            "contactNum": _("Contact No"),
            "email": _("Email"),
            "yearLevel": _("Yr Lvl"),
            "course": _("Course"),
            "hasWednesdayClasses": _("Wednesday Class"),
            "graduating": _("Graduating"),
            "dswsMemRegName": _("DSWS Member Name"),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Form Class
        self.fields['clientId'].widget.attrs['class'] = 'form-control form-control-sm'
        self.fields['lastName'].widget.attrs['class'] = 'form-control form-control-sm'
        self.fields['firstName'].widget.attrs['class'] = 'form-control form-control-sm'
        self.fields['middleInitial'].widget.attrs['class'] = 'form-control form-control-sm'
        self.fields['suffix'].widget.attrs['class'] = 'form-control form-control-sm'
        self.fields['contactNum'].widget.attrs['class'] = 'form-control form-control-sm'
        self.fields['email'].widget.attrs['class'] = 'form-control form-control-sm'
        self.fields['yearLevel'].widget.attrs['class'] = 'form-control form-control-sm'
        self.fields['course'].widget.attrs['class'] = 'form-control form-control-sm'
        self.fields['hasWednesdayClasses'].widget.attrs['class'] = 'form-check-input'
        self.fields['graduating'].widget.attrs['class'] = 'form-check-input'
        self.fields['dswsMemRegName'].widget.attrs['class'] = 'form-control form-control-sm'

        #Form Placeholders
        self.fields['clientId'].widget.attrs['placeholder'] = 'form-control form-control-sm'
        self.fields['lastName'].widget.attrs['placeholder'] = 'form-control form-control-sm'
        self.fields['firstName'].widget.attrs['placeholder'] = 'form-control form-control-sm'
        self.fields['middleInitial'].widget.attrs['placeholder'] = 'form-control form-control-sm'
        self.fields['suffix'].widget.attrs['placeholder'] = 'form-control form-control-sm'
        self.fields['contactNum'].widget.attrs['placeholder'] = 'form-control form-control-sm'
        self.fields['email'].widget.attrs['placeholder'] = 'form-control form-control-sm'
        self.fields['yearLevel'].widget.attrs['placeholder'] = 'form-control form-control-sm'
        self.fields['course'].widget.attrs['placeholder'] = 'form-control form-control-sm'
        self.fields['dswsMemRegName'].widget.attrs['placeholder'] = 'form-control form-control-sm'

class LoanItemForm(ModelForm):
    class Meta:
        model = LoanItem
        fields = '__all__'
        exclude = ['dateReg', 'lastClient', 'status']
        widgets = {
            "itemCat": forms.TextInput(attrs={"class":"form-control", "placeholder":"XY-99"}),
            "description": forms.Textarea(attrs={"class":"form-control", "rows":"2", "placeholder":"loanitem"})
        }
        

class LoanItemEditForm(ModelForm):
    class Meta:
        model = LoanItem
        fields = '__all__'
        exclude = ['dateReg', 'lastClient']
        widgets={
            "itemCat": forms.TextInput(attrs={"class":"form-control"}),
            "description": forms.Textarea(attrs={"class":"form-control", "rows":"2"}),
            "status": forms.Select(attrs={"class":"form-select"})
        }



class LoanItemTransactionForm(forms.Form):
    dateLoaned = forms.DateTimeField(widget=forms.HiddenInput())
    dateDue = forms.DateTimeField(widget=DateTimePickerInput(attrs={"class":"form-control form-control-sm", "label":"Date Due", "placeholder":"placeholder"}))
    itemCat = forms.CharField(widget=forms.HiddenInput())
    reciever = forms.CharField(widget=forms.TextInput(attrs={"class":"form-control form-control-sm", "label": "DSWS Member", "placeholder":"placeholder"}))
    remarks = forms.CharField(
        widget = forms.Textarea(attrs={'rows':'2', "class":"form-control form-control-sm", "label":"Remarks", "placeholder":"placeholder"}),
        required=False
    )
    


class ReturnItemATransactionForm(forms.Form):
    clientIDNo = forms.IntegerField(widget=forms.NumberInput(attrs={'readonly' : 'readonly', "class":"form-control form-control-sm"}))
    clientName = forms.CharField(widget=forms.TextInput(attrs={'readonly' : 'readonly', "class":"form-control form-control-sm"}))
    itemCat = forms.CharField(widget=forms.TextInput(attrs={'readonly' : 'readonly', "class":"form-control form-control-sm"}))
    itemType = forms.CharField(widget=forms.TextInput(attrs={'readonly' : 'readonly', "class":"form-control form-control-sm"}))
    dueDate = forms.DateTimeField(widget=DateTimePickerInput(attrs={"readonly":"readonly", "class":"form-control form-control-sm"}))
    overDueDays = forms.IntegerField(widget=forms.NumberInput(attrs={"class":"form-control form-control-sm"}))
    reciever = forms.CharField(widget=forms.TextInput(attrs={"class":"form-control form-control-sm"}))
    remarks = forms.CharField(
        widget = forms.Textarea(attrs={'rows':'2', "class":"form-control form-control-sm"}),
        required=False
    )

class ReturnItemBTransactionForm(forms.Form):
    clientIDNo = forms.IntegerField(widget=forms.NumberInput(attrs={'readonly' : 'readonly', "class":"form-control form-control-sm", "placeholder":"a"}))
    clientName = forms.CharField(widget=forms.TextInput(attrs={'readonly' : 'readonly', "class":"form-control form-control-sm", "placeholder":"a"}))
    itemCat = forms.CharField(widget=forms.TextInput(attrs={'readonly' : 'readonly', "class":"form-control form-control-sm", "placeholder":"a"}))
    itemType = forms.CharField(widget=forms.TextInput(attrs={'readonly' : 'readonly', "class":"form-control form-control-sm", "placeholder":"a"}))
    dueDate = forms.DateTimeField(widget=DateTimePickerInput(attrs={"readonly":"readonly", "class":"form-control form-control-sm", "placeholder":"a"}))
    overDueHours = forms.IntegerField(widget=forms.NumberInput(attrs={"class":"form-control form-control-sm", "placeholder":"a"}))
    overDueMinutes = forms.IntegerField(widget=forms.NumberInput(attrs={"class":"form-control form-control-sm", "placeholder":"a"}))
    reciever = forms.CharField(widget=forms.TextInput(attrs={"class":"form-control form-control-sm"}))
    remarks = forms.CharField(
        widget = forms.Textarea(attrs={'rows':'2', "class":"form-control form-control-sm", "placeholder":"a"}),
        required=False
    )


class BlockTimeForm(forms.Form):
    blockDate = forms.DateField(
        widget = DatePickerInput()
    )
    blockTimeStart = forms.TimeField(widget=TimePickerInput(attrs={"min":"09:00", "max":"16:30"}))
    blockTimeEnd = forms.TimeField(widget=TimePickerInput(attrs={"min":"09:30", "max":"17:00"}))
    description = forms.CharField(
        widget = forms.Textarea(attrs={'rows':'2'}),
        required=False
    )
class BlockDateForm(forms.Form):
    blockDate = forms.DateField(
        widget=DatePickerInput(attrs={"class":"form-control"})
    )
    description = forms.CharField(
        widget = forms.Textarea(attrs={'rows':'2', "class":"form-control", "placeholder":"class suspension"}),
        required=False
    )


class LoanItemSelectForm(forms.Form):
    def __init__ (self, item_choices, *args, **kwargs):
        super(LoanItemSelectForm, self).__init__(*args, **kwargs)
        self.fields['item'].choices = item_choices
    
    items = forms.ChoiceField(choices=(), required=True)
