from django.db import models
from django.core.validators import RegexValidator

# Create your models here.
class LoanItem(models.Model):
    # itemId = models.AutoField() idk if I should include this
    itemCat = models.CharField(max_length=5, primary_key=True)

    INSTORAGE = "IS"
    LOANEDOUT = "LO"
    DAMAGED = "DM"
    LOST = "L"
    ITEM_STATUS = {
        INSTORAGE: 'In-Storage',
        LOANEDOUT: 'Loaned-Out', 
        DAMAGED: 'Damaged',
        LOST: 'Lost',
    }
    status = models.CharField(max_length=2, choices=ITEM_STATUS, default=INSTORAGE)

    description = models.CharField(null=True, blank=True, max_length=255)
    dateReg = models.DateTimeField(auto_now_add=True)
    lastClient = models.PositiveIntegerField(null=True, blank=True)

class Client(models.Model):
    clientId = models.PositiveIntegerField(primary_key=True)
    lastName = models.CharField(max_length=50, null=False)
    firstName = models.CharField(max_length=50, null=False)
    middleInitial = models.CharField(max_length=3, null=True)
    suffix = models.CharField(null = True, blank=True, max_length=2)

    contactNum = models.CharField(max_length=11, validators=[RegexValidator(r'^\d{1,11}$')])
    email = models.EmailField(null=False)
    yearLvl = models.SmallIntegerField(default=1)

    course = models.CharField(max_length=50, null=False)
    graduating = models.BooleanField(default=False)
    gradwaiting = models.BooleanField(default=False) #Boolean Value for graduating seniors
    dswsMemReg = models.CharField(max_length=50, null=False)
    dateReg = models.DateTimeField(auto_now_add=True)

    borrowing = models.BooleanField(default=False)
    excuseLetter = models.BooleanField(default=False)
    holdOrder = models.BooleanField(default=False)
    blackListed = models.BooleanField(default=False)
    fine = models.PositiveSmallIntegerField(default=0)

    temporaryBlackList = models.BooleanField(default=False)
    tblStart = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    tblEnd = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    
    warningCount = models.SmallIntegerField(default=0, null = True, blank=True,)
    lastBorrowed = models.DateTimeField(default=None, null = True, blank=True)
    lastItem = models.ForeignKey(LoanItem, null=True, blank=True, on_delete=models.SET_NULL)
    HOcount = models.SmallIntegerField(default=0, null = True, blank=True,)
    BLcount = models.SmallIntegerField(default=0, null = True, blank=True,)



class Transaction(models.Model):
    clientId = models.ForeignKey(Client, null=True, on_delete=models.SET_NULL)
    itemCat = models.ForeignKey(LoanItem, on_delete=models.CASCADE)
    dateDue = models.DateTimeField(auto_now=False, auto_now_add=False)
    dswsMemLoan = models.CharField(max_length=15)
    remarks = models.CharField(null=True, blank=True, max_length=46)
    dateLoaned = models.DateTimeField(auto_now=False, auto_now_add=False)
    
    ONGOING = 'OG'
    COMPLETE = 'C'
    DAMAGED = 'DM'
    LOST = 'L'
    TRANSACTION_STATUS = {
        ONGOING: 'On-going',
        COMPLETE: 'Complete',
        DAMAGED:'Unreturned',
        LOST: 'Lost'
    }
    status = models.CharField(max_length=2, choices=TRANSACTION_STATUS, default=ONGOING)

    class Meta:
        ordering = ["-dateLoaned"]


class ReturnItem(models.Model):
    dateReturned = models.DateTimeField()
    overdueDays = models.PositiveSmallIntegerField(default=0)
    overdueHours = models.PositiveSmallIntegerField(default=0)
    overdueMinutes = models.PositiveSmallIntegerField(default=0)

    dswsMemRet = models.CharField(max_length=50)
    remarks = models.CharField(null=True, blank=True, max_length=96)

    transactionId = models.OneToOneField(Transaction, on_delete=models.CASCADE)
    clientId = models.ForeignKey(Client, null=True, on_delete=models.SET_NULL)
    itemCat = models.ForeignKey(LoanItem, on_delete=models.CASCADE)



class Student(models.Model):
    studentId = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    course = models.CharField(max_length=50, null=False)
    yearLvl = models.SmallIntegerField(default=1)

class BlockOutDate(models.Model):
    dateblocked = models.DateField(primary_key=True)
    description = models.CharField(null=True, blank=True, max_length=64)

class BlockOutTime(models.Model):
    dateBlocked = models.DateField(auto_now=False, auto_now_add=False, blank=True, null=True)
    description = models.CharField(max_length=64)
    timeStart = models.DateTimeField(auto_now=False, auto_now_add=False)
    timeEnd = models.DateTimeField(auto_now=False, auto_now_add=False)



    