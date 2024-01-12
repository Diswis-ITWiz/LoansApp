from django.contrib import admin
from .models import *
# Register your models here.

admin.site.register(LoanItem)
admin.site.register(Client)
admin.site.register(Transaction)
admin.site.register(ReturnItem)
admin.site.register(Student)
admin.site.register(BlockOutDate)
admin.site.register(BlockOutTime)
