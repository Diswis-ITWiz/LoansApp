from django.forms import ModelForm
from django import forms
from .models import Client, Transaction, LoanItem, BlockOutDate, BlockOutTime

class ClientForm(ModelForm):
    class Meta:
        model = Client
        fields = '__all__'
        exclude = ['borrowing', 'warningCount', 'status', 'dateReg', 
                   'lastBorrowed', 'lastItem', 'HOcount', 'BLcount',
                   'excuseLetter', 'holdOrder', 'blackListed', 'fine', 
                    'temporaryBlackList', 'tblStart','tblEnd',] 

class LoanItemForm(ModelForm):
    class Meta:
        model = LoanItem
        fields = '__all__'
        exclude = ['dateReg', 'lastClient']

        