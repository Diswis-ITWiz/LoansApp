from base.constants import (
    BLACKLIST_FINE_AMOUNT,
    LONG_OVERDUE_FINE_AMOUNT,
    PenaltyDescription,
    PenaltyLiftChoice,
    TYPE_A_BLACKLIST_WARNING_COUNT,
    TYPE_A_LONG_OVERDUE_MIN_DAYS,
    TYPE_A_TEMP_BLACKLIST_MAX_DAYS,
    TYPE_A_TEMP_BLACKLIST_MIN_DAYS,
    TYPE_A_WARNING_MAX_DAYS,
    TYPE_A_WARNING_MIN_DAYS,
    TYPE_B_BLACKLIST_WARNING_COUNT,
    TYPE_B_LONG_OVERDUE_MIN_HOURS,
    TYPE_B_TEMP_BLACKLIST_MAX_HOURS,
    TYPE_B_TEMP_BLACKLIST_MIN_HOURS,
    TYPE_B_WARNING_MAX_HOURS,
    TYPE_B_WARNING_MIN_HOURS,
)


def calculate_type_a_penalty(overdue_days, client):
    penalty = PenaltyDescription.NO_PENALTY
    if client.warningCount >= TYPE_A_BLACKLIST_WARNING_COUNT:
        penalty = PenaltyDescription.BLACKLIST
    elif TYPE_A_WARNING_MIN_DAYS <= overdue_days <= TYPE_A_WARNING_MAX_DAYS:
        penalty = PenaltyDescription.WARNING
    elif TYPE_A_TEMP_BLACKLIST_MIN_DAYS <= overdue_days <= TYPE_A_TEMP_BLACKLIST_MAX_DAYS:
        penalty = PenaltyDescription.TEMPORARY_BLACKLIST_EXCUSE_LETTER
    elif overdue_days >= TYPE_A_LONG_OVERDUE_MIN_DAYS:
        penalty = PenaltyDescription.LONG_OVERDUE
    return penalty


def apply_type_a_penalty(overdue_days, client):
    if client.warningCount >= TYPE_A_BLACKLIST_WARNING_COUNT:
        client.blackListed = True
        client.holdOrder = True
        client.fineAmount = BLACKLIST_FINE_AMOUNT
        client.excuseLetter = True
    elif TYPE_A_WARNING_MIN_DAYS <= overdue_days <= TYPE_A_WARNING_MAX_DAYS:
        client.warningCount = client.warningCount + 1
    elif TYPE_A_TEMP_BLACKLIST_MIN_DAYS <= overdue_days <= TYPE_A_TEMP_BLACKLIST_MAX_DAYS:
        client.temporaryBlackList = True
        client.excuseLetter = True
    elif overdue_days >= TYPE_A_LONG_OVERDUE_MIN_DAYS:
        client.temporaryBlackList = True
        client.holdOrder = True
        client.fineAmount = LONG_OVERDUE_FINE_AMOUNT
        client.excuseLetter = True
    client.save()


def calculate_type_b_penalty(overdue_hours, overdue_minutes, client):
    penalty = PenaltyDescription.NO_PENALTY
    if client.warningCount == TYPE_B_BLACKLIST_WARNING_COUNT:
        penalty = PenaltyDescription.BLACKLIST
    elif TYPE_B_WARNING_MIN_HOURS <= overdue_hours <= TYPE_B_WARNING_MAX_HOURS:
        penalty = PenaltyDescription.WARNING
    elif TYPE_B_TEMP_BLACKLIST_MIN_HOURS <= overdue_hours <= TYPE_B_TEMP_BLACKLIST_MAX_HOURS:
        penalty = PenaltyDescription.TEMPORARY_BLACKLIST_EXCUSE_LETTER
    elif overdue_hours >= TYPE_B_LONG_OVERDUE_MIN_HOURS:
        penalty = PenaltyDescription.LONG_OVERDUE
    return penalty


def apply_type_b_penalty(overdue_hours, overdue_minutes, client):
    if client.warningCount == TYPE_B_BLACKLIST_WARNING_COUNT:
        client.blackListed = True
        client.holdOrder = True
        client.fineAmount = BLACKLIST_FINE_AMOUNT
        client.excuseLetter = True
    elif TYPE_B_WARNING_MIN_HOURS <= overdue_hours <= TYPE_B_WARNING_MAX_HOURS:
        client.warningCount += 1
    elif TYPE_B_TEMP_BLACKLIST_MIN_HOURS <= overdue_hours <= TYPE_B_TEMP_BLACKLIST_MAX_HOURS:
        client.temporaryBlackList = True
        client.excuseLetter = True
    elif overdue_hours >= TYPE_B_LONG_OVERDUE_MIN_HOURS:
        client.temporaryBlackList = True
        client.holdOrder = True
        client.fineAmount = LONG_OVERDUE_FINE_AMOUNT
        client.excuseLetter = True
    client.save()


def lift_client_penalty(client, choice):
    if choice == PenaltyLiftChoice.ALL:
        client.blackListed = False
        client.holdOrder = False
        client.excuseLetter = False
        client.fineAmount = 0
        client.temporaryBlackList = False
    elif choice == PenaltyLiftChoice.BLACKLIST:
        client.blackListed = True
        client.holdOrder = False
        client.excuseLetter = False
        client.fineAmount = 0
        client.temporaryBlackList = False
    elif choice == PenaltyLiftChoice.TEMPORARY_BLACKLIST:
        client.temporaryBlackList = False
        client.excuseLetter = False
        client.holdOrder = False
        client.fineAmount = 0
    elif choice == PenaltyLiftChoice.FINE:
        client.fineAmount = 0
    elif choice == PenaltyLiftChoice.WARNING:
        client.warningCount = 0 if client.warningCount == 0 else client.warningCount - 1
    client.save()
    return client


calculateTypeAPenalty = calculate_type_a_penalty
applyTypeAPenalty = apply_type_a_penalty
calculateTypeBPenalty = calculate_type_b_penalty
applyTypeBPenalty = apply_type_b_penalty
