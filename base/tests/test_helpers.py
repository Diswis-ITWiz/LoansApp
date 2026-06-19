from datetime import date, datetime, timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from base.services.calendar_rules import get_closing_time, if_no_classes
from base.services.emailing import (
    TransactionEmailThread,
    send_deadline_email,
    send_overdue_item_a_email,
    send_overdue_item_b_email,
    send_transaction_email,
)
from base.services.item_types import check_item_type, get_item_type_name
from base.services.overdue import get_item_type_a_overdue_days, get_item_type_b_overdue_time
from base.services.penalties import (
    apply_type_a_penalty,
    apply_type_b_penalty,
    calculate_type_a_penalty,
    calculate_type_b_penalty,
)
from base.models import BlockOutDate, BlockOutTime, Client


def aware(year, month, day, hour=0, minute=0):
    return timezone.make_aware(datetime(year, month, day, hour, minute))


def make_client(client_id=100001, **overrides):
    values = {
        "clientId": client_id,
        "lastName": "Garcia",
        "firstName": "Ana",
        "middleInitial": "M",
        "contactNum": "09171234567",
        "email": "ana@example.com",
        "yearLevel": 2,
        "course": "BS CS",
        "hasWednesdayClasses": True,
        "dswsMemRegName": "Member Name",
    }
    values.update(overrides)
    return Client.objects.create(**values)


class CalendarHelperTests(TestCase):
    def test_if_no_classes_blocks_weekends(self):
        self.assertTrue(if_no_classes(date(2024, 6, 15), True))
        self.assertTrue(if_no_classes(date(2024, 6, 16), True))

    def test_if_no_classes_depends_on_wednesday_class_flag(self):
        wednesday = date(2024, 6, 12)

        self.assertFalse(if_no_classes(wednesday, True))
        self.assertTrue(if_no_classes(wednesday, False))

    def test_if_no_classes_blocks_configured_dates(self):
        blocked_date = date(2024, 6, 10)
        BlockOutDate.objects.create(dateBlocked=blocked_date, description="Holiday")

        self.assertTrue(if_no_classes(blocked_date, True))

    def test_get_closing_time_uses_early_wednesday_closing(self):
        self.assertEqual(get_closing_time(aware(2024, 6, 12, 10, 15)).hour, 14)
        self.assertEqual(get_closing_time(aware(2024, 6, 12, 10, 15)).minute, 0)

    def test_get_closing_time_uses_five_pm_for_other_weekdays(self):
        self.assertEqual(get_closing_time(aware(2024, 6, 10, 10, 15)).hour, 17)
        self.assertEqual(get_closing_time(aware(2024, 6, 10, 10, 15)).minute, 0)


class ItemHelperTests(TestCase):
    def test_check_item_type_classifies_type_a_prefixes(self):
        for item_cat in ["B-01", "C-01", "D-01", "TR-01", "U-01"]:
            with self.subTest(item_cat=item_cat):
                self.assertEqual(check_item_type(item_cat), "A")

    def test_check_item_type_classifies_other_prefixes_as_type_b(self):
        for item_cat in ["A-01", "LC-01", "PC-01", "S-01"]:
            with self.subTest(item_cat=item_cat):
                self.assertEqual(check_item_type(item_cat), "B")

    def test_get_item_type_name_maps_known_prefixes(self):
        expected_names = {
            "A-01": "Adapter",
            "B-01": "Bible",
            "C-01": "Calculator",
            "D-01": "Dictionary",
            "TR-01": "Transalor Dictionary",
            "LC-01": "Laptop Charger",
            "PC-01": "Phone Charger",
            "S-01": "Speaker",
            "U-01": "Umbrella",
        }

        for item_cat, expected_name in expected_names.items():
            with self.subTest(item_cat=item_cat):
                self.assertEqual(get_item_type_name(item_cat), expected_name)


class TypeAOverdueAndPenaltyTests(TestCase):
    def test_type_a_overdue_days_returns_zero_until_after_due_date(self):
        client = make_client()

        with mock.patch("base.services.overdue.timezone.now", return_value=aware(2024, 6, 10, 12, 0)):
            self.assertEqual(get_item_type_a_overdue_days(aware(2024, 6, 10, 17, 0), client), 0)

    def test_type_a_overdue_days_counts_valid_days_for_clients_with_wednesday_classes(self):
        client = make_client(hasWednesdayClasses=True)

        with mock.patch("base.services.overdue.timezone.now", return_value=aware(2024, 6, 13, 10, 0)):
            self.assertEqual(get_item_type_a_overdue_days(aware(2024, 6, 10, 17, 0), client), 3)

    def test_type_a_overdue_days_excludes_blocked_business_days_without_wednesday_classes(self):
        client = make_client(hasWednesdayClasses=False)
        BlockOutDate.objects.create(dateBlocked=date(2024, 6, 11), description="Suspension")

        with mock.patch("base.services.overdue.timezone.now", return_value=aware(2024, 6, 14, 10, 0)):
            self.assertEqual(get_item_type_a_overdue_days(aware(2024, 6, 10, 17, 0), client), 4)

    def test_calculate_type_a_penalty_thresholds(self):
        client = make_client()

        self.assertEqual(calculate_type_a_penalty(0, client), "No Penalty")
        self.assertEqual(calculate_type_a_penalty(1, client), "Warning")
        self.assertEqual(calculate_type_a_penalty(4, client), "TBL, EL")
        self.assertEqual(calculate_type_a_penalty(11, client), "TBL, HO, PHP 500 Fine, EL")

    def test_calculate_type_a_penalty_blacklists_after_more_than_three_warnings(self):
        client = make_client(warningCount=4)

        self.assertEqual(calculate_type_a_penalty(0, client), "Black Listed\n Hold Order\n PHP 1000 Fine, EL")

    def test_apply_type_a_penalty_increments_warning_count(self):
        client = make_client(warningCount=0)

        apply_type_a_penalty(2, client)
        client.refresh_from_db()

        self.assertEqual(client.warningCount, 1)

    def test_apply_type_a_penalty_applies_temporary_blacklist(self):
        client = make_client()

        apply_type_a_penalty(5, client)
        client.refresh_from_db()

        self.assertTrue(client.temporaryBlackList)
        self.assertTrue(client.excuseLetter)

    def test_apply_type_a_penalty_applies_hold_order_and_fine_for_long_overdue(self):
        client = make_client()

        apply_type_a_penalty(11, client)
        client.refresh_from_db()

        self.assertTrue(client.temporaryBlackList)
        self.assertTrue(client.holdOrder)
        self.assertTrue(client.excuseLetter)
        self.assertEqual(client.fineAmount, 500)


class TypeBOverdueAndPenaltyTests(TestCase):
    def test_type_b_overdue_time_returns_zero_until_after_due_date(self):
        client = make_client()

        with mock.patch("base.services.overdue.timezone.now", return_value=aware(2024, 6, 10, 10, 0)):
            self.assertEqual(get_item_type_b_overdue_time(aware(2024, 6, 10, 12, 0), client), (0, 0))

    def test_type_b_overdue_time_counts_same_day_difference(self):
        client = make_client()

        with mock.patch("base.services.overdue.timezone.now", return_value=aware(2024, 6, 10, 12, 45)):
            self.assertEqual(get_item_type_b_overdue_time(aware(2024, 6, 10, 10, 0), client), (2, 45))

    def test_type_b_overdue_time_subtracts_same_day_blocked_time(self):
        client = make_client()
        BlockOutTime.objects.create(
            dateBlocked=date(2024, 6, 10),
            description="Blocked",
            timeStart=aware(2024, 6, 10, 11, 0),
            timeEnd=aware(2024, 6, 10, 12, 0),
        )

        with mock.patch("base.services.overdue.timezone.now", return_value=aware(2024, 6, 10, 13, 0)):
            self.assertEqual(get_item_type_b_overdue_time(aware(2024, 6, 10, 10, 0), client), (2, 0))

    def test_type_b_overdue_time_counts_office_hours_across_days(self):
        client = make_client(hasWednesdayClasses=True)

        with mock.patch("base.services.overdue.timezone.now", return_value=aware(2024, 6, 11, 10, 30)):
            self.assertEqual(get_item_type_b_overdue_time(aware(2024, 6, 10, 15, 0), client), (3, 0))

    def test_calculate_type_b_penalty_thresholds(self):
        client = make_client()

        self.assertEqual(calculate_type_b_penalty(2, 59, client), "No Penalty")
        self.assertEqual(calculate_type_b_penalty(3, 0, client), "Warning")
        self.assertEqual(calculate_type_b_penalty(6, 0, client), "TBL, EL")
        self.assertEqual(calculate_type_b_penalty(11, 0, client), "TBL, HO, PHP 500 Fine, EL")

    def test_calculate_type_b_penalty_blacklists_at_three_warnings(self):
        client = make_client(warningCount=3)

        self.assertEqual(calculate_type_b_penalty(0, 0, client), "Black Listed\n Hold Order\n PHP 1000 Fine, EL")

    def test_apply_type_b_penalty_increments_warning_count(self):
        client = make_client(warningCount=0)

        apply_type_b_penalty(4, 0, client)
        client.refresh_from_db()

        self.assertEqual(client.warningCount, 1)

    def test_apply_type_b_penalty_applies_temporary_blacklist(self):
        client = make_client()

        apply_type_b_penalty(7, 0, client)
        client.refresh_from_db()

        self.assertTrue(client.temporaryBlackList)
        self.assertTrue(client.excuseLetter)

    def test_apply_type_b_penalty_applies_hold_order_and_fine_for_long_overdue(self):
        client = make_client()

        apply_type_b_penalty(11, 0, client)
        client.refresh_from_db()

        self.assertTrue(client.temporaryBlackList)
        self.assertTrue(client.holdOrder)
        self.assertTrue(client.excuseLetter)
        self.assertEqual(client.fineAmount, 500)


class EmailHelperTests(TestCase):
    def test_transaction_email_thread_sends_mail(self):
        email_thread = TransactionEmailThread("Subject", "Text body", "borrower@example.com", "<p>HTML</p>")

        with mock.patch("base.services.emailing.send_mail") as send_mail:
            email_thread.run()

        send_mail.assert_called_once_with(
            "Subject",
            "Text body",
            "tests@example.com",
            recipient_list=["borrower@example.com"],
            html_message="<p>HTML</p>",
            fail_silently=True,
        )

    def test_send_transaction_email_starts_thread(self):
        client = make_client()

        with mock.patch("base.services.emailing.render_to_string", return_value="<p>Receipt</p>"), mock.patch(
            "base.services.emailing.TransactionEmailThread"
        ) as thread_class:
            send_transaction_email("A-01", "Adapter", "06/10/2024 09:30 AM", "06/10/2024 11:30 AM", client)

        subject, message, email, template = thread_class.call_args.args
        self.assertEqual(subject, "Adapter [A-01] is due on 06/10/2024 11:30 AM")
        self.assertIn("LOANS RECEIPT", message)
        self.assertEqual(email, client.email)
        self.assertEqual(template, "<p>Receipt</p>")
        thread_class.return_value.start.assert_called_once()

    def test_send_deadline_email_starts_thread(self):
        client = make_client()

        with mock.patch("base.services.emailing.render_to_string", return_value="<p>Deadline</p>"), mock.patch(
            "base.services.emailing.TransactionEmailThread"
        ) as thread_class:
            send_deadline_email("A-01", "Adapter", "06/10/2024 09:30 AM", "06/10/2024 11:30 AM", client)

        subject = thread_class.call_args.args[0]
        self.assertIn("Reminder: Your borrowed item Adapter [A-01] is due today!!", subject)
        thread_class.return_value.start.assert_called_once()

    def test_send_overdue_item_a_email_starts_thread_with_penalty(self):
        client = make_client()

        with mock.patch("base.services.emailing.render_to_string", return_value="<p>Overdue A</p>"), mock.patch(
            "base.services.emailing.TransactionEmailThread"
        ) as thread_class:
            send_overdue_item_a_email("B-01", "Bible", "loan date", "due date", client, 4)

        subject, message, email, template = thread_class.call_args.args
        self.assertIn("Bible [B-01] is 4 day/s overdue", subject)
        self.assertIn("Penalty: TBL, EL", message)
        self.assertEqual(email, client.email)
        self.assertEqual(template, "<p>Overdue A</p>")
        thread_class.return_value.start.assert_called_once()

    def test_send_overdue_item_b_email_starts_thread_with_penalty(self):
        client = make_client()

        with mock.patch("base.services.emailing.render_to_string", return_value="<p>Overdue B</p>"), mock.patch(
            "base.services.emailing.TransactionEmailThread"
        ) as thread_class:
            send_overdue_item_b_email("A-01", "Adapter", "loan date", "due date", client, 6, 30)

        subject, message, email, template = thread_class.call_args.args
        self.assertIn("Adapter [A-01] is 6 hr/s 30 min/s overdue", subject)
        self.assertIn("Penalty: TBL, EL", message)
        self.assertEqual(email, client.email)
        self.assertEqual(template, "<p>Overdue B</p>")
        thread_class.return_value.start.assert_called_once()
