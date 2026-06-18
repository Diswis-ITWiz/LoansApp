from django.db import models
from django.core.validators import RegexValidator
from .constants import LoanItemStatus, TransactionStatus

# Create your models here.
class LoanItem(models.Model):
    itemCat = models.CharField(max_length=5, primary_key=True)
    lastClient = models.PositiveIntegerField(null=True, blank=True)

    INSTORAGE = LoanItemStatus.IN_STORAGE
    LOANEDOUT = LoanItemStatus.LOANED_OUT
    DAMAGED = LoanItemStatus.DAMAGED
    LOST = LoanItemStatus.LOST
    ITEM_STATUS = LoanItemStatus.CHOICES
    status = models.CharField(max_length=2, choices=ITEM_STATUS, default=INSTORAGE)
    
    description = models.CharField(null=True, blank=True, max_length=255)
    dateReg = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.itemCat
    

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

    def __str__(self):
        return f"{self.clientId} - {self.lastName}, {self.firstName}"



class Transaction(models.Model):
    clientId = models.ForeignKey(Client, null=True, on_delete=models.SET_NULL)
    itemCat = models.ForeignKey(LoanItem, on_delete=models.CASCADE)

    dswsMemLoanName = models.CharField(max_length=255)
    loanRemarks = models.CharField(null=True, blank=True, max_length=46)
    dateLoaned = models.DateTimeField(auto_now=False, auto_now_add=False)
    dueDate = models.DateTimeField(auto_now=False, auto_now_add=False)
   
    ONGOING = TransactionStatus.ONGOING
    COMPLETE = TransactionStatus.COMPLETE
    DAMAGED = TransactionStatus.DAMAGED
    LOST = TransactionStatus.LOST
    UNRETURNED = TransactionStatus.UNRETURNED
    TRANSACTION_STATUS = TransactionStatus.CHOICES
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

    def __str__(self):
        client_id = self.clientId.clientId if self.clientId else "No client"
        return f"Transaction {self.id}: {self.itemCat_id} / {client_id} ({self.status})"


class BlockOutDate(models.Model):
    dateBlocked = models.DateField(primary_key=True)
    description = models.CharField(null=True, blank=True, max_length=64)

    def __str__(self):
        return f"{self.dateBlocked} - {self.description or 'Blocked'}"

class BlockOutTime(models.Model):
    dateBlocked = models.DateField(auto_now=False, auto_now_add=False, blank=True, null=True)
    description = models.CharField(max_length=64)
    timeStart = models.DateTimeField(auto_now=False, auto_now_add=False)
    timeEnd = models.DateTimeField(auto_now=False, auto_now_add=False)

    def __str__(self):
        return f"{self.dateBlocked} {self.timeStart:%H:%M}-{self.timeEnd:%H:%M}"



    
