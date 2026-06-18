from datetime import timedelta


class LoanItemStatus:
    IN_STORAGE = "IS"
    LOANED_OUT = "LO"
    DAMAGED = "DM"
    LOST = "L"

    CHOICES = [
        (IN_STORAGE, "In-Storage"),
        (LOANED_OUT, "Loaned-Out"),
        (DAMAGED, "Damaged"),
        (LOST, "Lost"),
    ]

    REPORT_CHOICES = [
        (LOST, "Lost"),
        (DAMAGED, "Damaged"),
    ]


class TransactionStatus:
    ONGOING = "OG"
    COMPLETE = "C"
    DAMAGED = "DM"
    LOST = "L"
    UNRETURNED = "UR"

    CHOICES = [
        (ONGOING, "On-going"),
        (COMPLETE, "Complete"),
        (DAMAGED, "Damaged"),
        (LOST, "Lost"),
        (UNRETURNED, "Unreturned"),
    ]


class ItemType:
    A = "A"
    B = "B"


TYPE_A_ITEM_PREFIXES = ("B", "C", "D", "TR", "U")
TYPE_B_ITEM_PREFIXES = ("PC", "LC", "A", "S")

ITEM_TYPE_NAMES = (
    ("TR", "Transalor Dictionary"),
    ("LC", "Laptop Charger"),
    ("PC", "Phone Charger"),
    ("A", "Adapter"),
    ("B", "Bible"),
    ("C", "Calculator"),
    ("D", "Dictionary"),
    ("S", "Speaker"),
    ("U", "Umbrella"),
)

WEEKDAY_WEDNESDAY = 2
WEEKEND_DAYS = frozenset((5, 6))
NO_CLASS_DAYS_WITHOUT_WEDNESDAY = frozenset((WEEKDAY_WEDNESDAY, 5, 6))

OFFICE_OPEN_HOUR = 9
OFFICE_OPEN_MINUTE = 30
REGULAR_CLOSING_HOUR = 17
WEDNESDAY_CLOSING_HOUR = 14
TYPE_B_NEXT_DAY_DUE_HOUR = 11
TYPE_B_NEXT_DAY_DUE_MINUTE = 0

TYPE_B_LOAN_DURATION = timedelta(hours=2)
REGULAR_OFFICE_DAY_DURATION = timedelta(hours=7, minutes=30)
WEDNESDAY_OFFICE_DAY_DURATION = timedelta(hours=4, minutes=30)

BLOCK_TIME_START_MIN = "09:30"
BLOCK_TIME_START_MAX = "17:00"
BLOCK_TIME_END_MIN = "09:30"
BLOCK_TIME_END_MAX = "17:00"
BLOCK_TIME_INPUT_CONSTRAINTS = {
    "start_min": BLOCK_TIME_START_MIN,
    "start_max": BLOCK_TIME_START_MAX,
    "end_min": BLOCK_TIME_END_MIN,
    "end_max": BLOCK_TIME_END_MAX,
}


class PenaltyDescription:
    NO_PENALTY = "No Penalty"
    WARNING = "Warning"
    TEMPORARY_BLACKLIST_EXCUSE_LETTER = "TBL, EL"
    LONG_OVERDUE = "TBL, HO, PHP 500 Fine, EL"
    BLACKLIST = "Black Listed\n Hold Order\n PHP 1000 Fine, EL"


TYPE_A_BLACKLIST_WARNING_COUNT = 4
TYPE_A_WARNING_MIN_DAYS = 1
TYPE_A_WARNING_MAX_DAYS = 3
TYPE_A_TEMP_BLACKLIST_MIN_DAYS = 4
TYPE_A_TEMP_BLACKLIST_MAX_DAYS = 10
TYPE_A_LONG_OVERDUE_MIN_DAYS = 11

TYPE_B_BLACKLIST_WARNING_COUNT = 3
TYPE_B_WARNING_MIN_HOURS = 3
TYPE_B_WARNING_MAX_HOURS = 5
TYPE_B_TEMP_BLACKLIST_MIN_HOURS = 6
TYPE_B_TEMP_BLACKLIST_MAX_HOURS = 10
TYPE_B_LONG_OVERDUE_MIN_HOURS = 11

BLACKLIST_FINE_AMOUNT = 1000
LONG_OVERDUE_FINE_AMOUNT = 500


class PenaltyLiftChoice:
    ALL = "All"
    BLACKLIST = "BL"
    TEMPORARY_BLACKLIST = "TBL"
    FINE = "RF"
    WARNING = "W"

    CHOICES = [
        (ALL, "Blacklist -- Lift ALL penalties"),
        (BLACKLIST, "Blacklist -- Lift penalties except Blacklist"),
        (TEMPORARY_BLACKLIST, "Temporary Blacklist -- Lift penalties"),
        (FINE, "Fine -- Reduce Fine to 0"),
        (WARNING, "Warning -- Reduce Warning Count"),
    ]


FINALS_BLOCKOUT_DESCRIPTION = "FINALS"
