from django.forms import ModelForm
from django import forms
from .models import Client, Transaction, LoanItem, BlockOutDate, BlockOutTime
from .widgets import DatePickerInput, TimePickerInput, DateTimePickerInput
from django.contrib.auth.models import User
from datetime import datetime

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



class LoanItemForm(ModelForm):
    class Meta:
        model = LoanItem
        fields = '__all__'
        exclude = ['dateReg', 'lastClient', 'status']
        

class LoanItemEditForm(ModelForm):
    class Meta:
        model = LoanItem
        fields = '__all__'
        exclude = ['dateReg', 'lastClient']



class LoanItemTransactionForm(forms.Form):
    dateLoaned = forms.DateTimeField(widget=forms.HiddenInput())
    dateDue = forms.DateTimeField(widget=DateTimePickerInput(attrs={"class":"form-control form-control-sm", "label":"Date Due"}))
    itemCat = forms.CharField(widget=forms.HiddenInput())
    reciever = forms.CharField(widget=forms.TextInput(attrs={"class":"form-control form-control-sm", "label": "DSWS Member"}))
    remarks = forms.CharField(
        widget = forms.Textarea(attrs={'rows':'2', "class":"form-control form-control-sm", "label":"Remarks"}),
        required=False
    )
    


class ReturnItemATransactionForm(forms.Form):
    clientIDNo = forms.IntegerField(widget=forms.NumberInput(attrs={'readonly' : 'readonly'}))
    clientName = forms.CharField(widget=forms.TextInput(attrs={'readonly' : 'readonly'}))
    itemCat = forms.CharField(widget=forms.TextInput(attrs={'readonly' : 'readonly'}))
    itemType = forms.CharField(widget=forms.TextInput(attrs={'readonly' : 'readonly'}))
    dueDate = forms.DateTimeField(widget=DateTimePickerInput(attrs={"readonly":"readonly"}))
    overDueDays = forms.IntegerField(widget=forms.NumberInput(attrs={'readonly' : 'readonly'}))
    reciever = forms.CharField()
    remarks = forms.CharField(
        widget = forms.Textarea(attrs={'rows':'2'}),
        required=False
    )

class ReturnItemBTransactionForm(forms.Form):
    clientIDNo = forms.IntegerField(widget=forms.NumberInput(attrs={'readonly' : 'readonly'}))
    clientName = forms.CharField(widget=forms.TextInput(attrs={'readonly' : 'readonly'}))
    itemCat = forms.CharField(widget=forms.TextInput(attrs={'readonly' : 'readonly'}))
    itemType = forms.CharField(widget=forms.TextInput(attrs={'readonly' : 'readonly'}))
    dueDate = forms.DateTimeField(widget=DateTimePickerInput(attrs={"readonly":"readonly"}))
    overDueHours = forms.IntegerField(widget=forms.NumberInput(attrs={'readonly' : 'readonly'}))
    overDueMinutes = forms.IntegerField(widget=forms.NumberInput(attrs={'readonly' : 'readonly'}))
    reciever = forms.CharField()
    remarks = forms.CharField(
        widget = forms.Textarea(attrs={'rows':'2'}),
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
        widget=DatePickerInput()
    )
    description = forms.CharField(
        widget = forms.Textarea(attrs={'rows':'2'}),
        required=False
    )


class LoanItemSelectForm(forms.Form):
    def __init__ (self, item_choices, *args, **kwargs):
        super(LoanItemSelectForm, self).__init__(*args, **kwargs)
        self.fields['item'].choices = item_choices
    
    items = forms.ChoiceField(choices=(), required=True)
