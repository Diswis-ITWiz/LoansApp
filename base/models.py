from django.db import models
from django.core.validators import RegexValidator

# Create your models here.
class LoanItem(models.Model):
    itemCat = models.CharField(max_length=5, primary_key=True)
    lastClient = models.PositiveIntegerField(null=True, blank=True)

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
    

class Client(models.Model):
    clientId = models.PositiveIntegerField(primary_key=True)
    lastName = models.CharField(max_length=50, null=False)
    firstName = models.CharField(max_length=50, null=False)
    middleInitial = models.CharField(max_length=3, null=True)
    suffix = models.CharField(null = True, blank=True, max_length=2)

    contactNum = models.CharField(max_length=11, validators=[RegexValidator(r'^\d{1,11}$')])
    email = models.EmailField(null=False)
    yearLevel = models.SmallIntegerField(default=1)

    course = models.CharField(max_length=50, null=False)
    hasWednesdayClasses = models.BooleanField(default=True)
    graduating = models.BooleanField(default=False)
    gradWaiting = models.BooleanField(default=False) #Boolean Value for graduating seniors
    dswsMemRegName = models.CharField(max_length=50, null=False)
    regDate = models.DateTimeField(auto_now_add=True) # registrationDate
    borrowing = models.BooleanField(default=False)
    excuseLetter = models.BooleanField(default=False)
    holdOrder = models.BooleanField(default=False)
    blackListed = models.BooleanField(default=False)
    fineAmount = models.PositiveSmallIntegerField(default=0)
    temporaryBlackList = models.BooleanField(default=False)
    warningCount = models.SmallIntegerField(default=0, null = True, blank=True,)
    lastBorrowedDate = models.DateTimeField(default=None, null = True, blank=True)
    lastBorrowedItem = models.ForeignKey(LoanItem, null=True, blank=True, on_delete=models.SET_NULL)



class Transaction(models.Model):
    clientId = models.ForeignKey(Client, null=True, on_delete=models.SET_NULL)
    itemCat = models.ForeignKey(LoanItem, on_delete=models.CASCADE)

    dswsMemLoanName = models.CharField(max_length=15)
    loanRemarks = models.CharField(null=True, blank=True, max_length=46)
    dateLoaned = models.DateTimeField(auto_now=False, auto_now_add=False)
    dueDate = models.DateTimeField(auto_now=False, auto_now_add=False)
   
    ONGOING = 'OG'
    COMPLETE = 'C'
    DAMAGED = 'DM'
    LOST = 'L'
    UNRETURNED = "UR"
    TRANSACTION_STATUS = {
        ONGOING: 'On-going',
        COMPLETE: 'Complete',
        DAMAGED:'Damaged',
        LOST: 'Lost',
        UNRETURNED: 'Unreturned',
    }
    status = models.CharField(max_length=2, choices=TRANSACTION_STATUS, default=ONGOING)

    class Meta:
        ordering = ["-dateLoaned"]

    # Return Item
    
    dateReturned = models.DateTimeField(null=True, blank=True)
    overdueDays = models.PositiveSmallIntegerField(default=0)
    overdueHours = models.PositiveSmallIntegerField(default=0)
    overdueMinutes = models.PositiveSmallIntegerField(default=0)
    dswsMemRetName = models.CharField(max_length=50, null=True, blank=True)
    returnRemarks = models.CharField(null=True, blank=True, max_length=96)


class BlockOutDate(models.Model):
    dateBlocked = models.DateField(primary_key=True)
    description = models.CharField(null=True, blank=True, max_length=64)

class BlockOutTime(models.Model):
    dateBlocked = models.DateField(auto_now=False, auto_now_add=False, blank=True, null=True)
    description = models.CharField(max_length=64)
    timeStart = models.DateTimeField(auto_now=False, auto_now_add=False)
    timeEnd = models.DateTimeField(auto_now=False, auto_now_add=False)



    