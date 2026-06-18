from django.contrib import admin

from .models import BlockOutDate, BlockOutTime, Client, LoanItem, Transaction


@admin.register(LoanItem)
class LoanItemAdmin(admin.ModelAdmin):
    list_display = ("itemCat", "status", "description", "lastClient", "dateReg")
    list_filter = ("status", "dateReg")
    search_fields = ("itemCat", "description", "lastClient")
    readonly_fields = ("dateReg",)
    ordering = ("itemCat",)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = (
        "clientId",
        "lastName",
        "firstName",
        "course",
        "yearLevel",
        "borrowing",
        "blackListed",
        "temporaryBlackList",
        "fineAmount",
        "warningCount",
    )
    list_filter = (
        "borrowing",
        "blackListed",
        "temporaryBlackList",
        "holdOrder",
        "excuseLetter",
        "graduating",
        "gradWaiting",
        "hasWednesdayClasses",
        "yearLevel",
    )
    search_fields = ("clientId", "lastName", "firstName", "email", "course", "contactNum")
    readonly_fields = ("regDate", "lastBorrowedDate", "lastBorrowedItem")
    ordering = ("lastName", "firstName")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "clientId",
        "itemCat",
        "status",
        "dateLoaned",
        "dueDate",
        "dateReturned",
        "overdueDays",
        "overdueHours",
        "overdueMinutes",
    )
    list_filter = ("status", "dateLoaned", "dueDate", "dateReturned")
    search_fields = (
        "id",
        "clientId__clientId",
        "clientId__lastName",
        "clientId__firstName",
        "itemCat__itemCat",
        "dswsMemLoanName",
        "dswsMemRetName",
    )
    autocomplete_fields = ("clientId", "itemCat")
    date_hierarchy = "dateLoaned"
    ordering = ("-dateLoaned",)


@admin.register(BlockOutDate)
class BlockOutDateAdmin(admin.ModelAdmin):
    list_display = ("dateBlocked", "description")
    search_fields = ("description",)
    ordering = ("-dateBlocked",)


@admin.register(BlockOutTime)
class BlockOutTimeAdmin(admin.ModelAdmin):
    list_display = ("dateBlocked", "timeStart", "timeEnd", "description")
    list_filter = ("dateBlocked",)
    search_fields = ("description",)
    ordering = ("-dateBlocked", "timeStart")
