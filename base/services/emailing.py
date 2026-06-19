import threading
from datetime import datetime

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from base.models import Client
from base.services.penalties import calculate_type_a_penalty, calculate_type_b_penalty


class TransactionEmailThread(threading.Thread):
    def __init__(self, subject: str, message: str, email: str, template: str) -> None:
        self.subject = subject
        self.message = message
        self.email_to = email
        self.template = template
        threading.Thread.__init__(self)

    def run(self) -> None:
        email_from = settings.EMAIL_HOST_USER
        send_mail(
            self.subject,
            self.message,
            email_from,
            recipient_list=[self.email_to],
            html_message=self.template,
            fail_silently=True,
        )


def send_transaction_email(
    item_cat: str,
    item_cat_name: str | None,
    loan_date: str | datetime,
    due_date: str | datetime,
    client: Client,
) -> None:
    subject_matter = f"{item_cat_name} [{item_cat}] is due on {due_date}"
    message = f"""
                LOANS RECEIPT

                The Department of Student Welfare and Servicesâ€™ Loans Committee would like to thank you for availing our services.
                Please be aware of the details of our transaction.
                --------------------
                Item Number: {item_cat}
                Time Borrowed: {loan_date}
                Due Date: {due_date}
                --------------------
                If you have any concerns or inquiries, contact us at:
                Email: dsws.loans@gmail.com

                Thank you and have a great day!
                """
    template = render_to_string(
        template_name="base/Email-Templates/transaction_email.html",
        context={
            "itemCat": item_cat,
            "loanDate": loan_date,
            "dueDate": due_date,
        },
    )

    msg = TransactionEmailThread(subject_matter, message, client.email, template)
    msg.start()


def send_deadline_email(
    item_cat: str,
    item_cat_name: str | None,
    loan_date: str | datetime,
    due_date: str | datetime,
    client: Client,
) -> None:
    subject_matter = f"Reminder: Your borrowed item {item_cat_name} [{item_cat}] is due today!! {due_date}"
    message = f"""
                Good Day {client.firstName} {client.lastName},

                The Department of Student Welfare and Servicesâ€™ Loans Committee would like to remind
                you that you have an item loaned out under your name. The item is due to be returned
                during the day.

                Kindly refer to the list below for more information
                --------------------
                Item Number: {item_cat_name}
                Time Borrowed: {loan_date}
                Due Date: {due_date}
                --------------------
                As stated in the contract you submitted prior to borrowing an item, overdue returns are subject to certain penalties.

                If you have any concerns or inquiries,
                please feel free to reply to this email or contact us at:
                Email: dsws.loans@gmail.com

                Thank you and have a great day!
                """
    template = render_to_string(
        template_name="base/Email-Templates/deadline_email.html",
        context={
            "itemCat": item_cat,
            "loanDate": loan_date,
            "dueDate": due_date,
        },
    )
    msg = TransactionEmailThread(subject_matter, message, client.email, template)
    msg.start()


def send_overdue_item_a_email(
    item_cat: str,
    item_cat_name: str | None,
    loan_date: str | datetime,
    due_date: str | datetime,
    client: Client,
    overdue_days: int,
) -> None:
    subject_matter = f"Notice: Loaned item {item_cat_name} [{item_cat}] is {overdue_days} day/s overdue!"
    penalty = calculate_type_a_penalty(overdue_days, client)
    message = f"""
                Good day {client.firstName} {client.lastName} ,

                The Department of Student Welfare and Servicesâ€™ Loans Committee would like to remind you
                that you have/had an overdue item loaned out under your name.
                As stated in the contract you submitted prior to borrowing an item,
                overdue returns are subject to certain penalties.

                Kindly refer to the list below for more information.
                --------------------
                Item Number: {item_cat_name}
                Estimated Number of Days Overdue: {overdue_days}
                Penalty: {penalty}
                --------------------
                If you have any concerns or inquiries, contact us at:
                Email: dsws.loans@gmail.com
                """
    template = render_to_string(
        template_name="base/Email-Templates/overdue_item_a_email.html",
        context={
            "client": client,
            "itemCat": item_cat,
            "overdueDays": overdue_days,
            "penalty": penalty,
        },
    )
    msg = TransactionEmailThread(subject_matter, message, client.email, template)
    msg.start()


def send_overdue_item_b_email(
    item_cat: str,
    item_cat_name: str | None,
    loan_date: str | datetime,
    due_date: str | datetime,
    client: Client,
    overdue_hours: int,
    overdue_minutes: int,
) -> None:
    subject_matter = (
        f"Notice: Loaned item {item_cat_name} [{item_cat}] is "
        f"{overdue_hours} hr/s {overdue_minutes} min/s overdue!"
    )
    penalty = calculate_type_b_penalty(overdue_hours, overdue_minutes, client)
    message = f"""
                Good day {client.firstName} {client.lastName},

                The Department of Student Welfare and Servicesâ€™ Loans Committee would like to remind you
                that you have/had an overdue item loaned out under your name.
                As stated in the contract you submitted prior to borrowing an item,
                overdue returns are subject to certain penalties.

                Kindly refer to the list below for more information.
                --------------------
                Item Number: {item_cat_name}
                Estimated Time Overdue: {overdue_hours} hr/s {overdue_minutes} min/s
                Penalty: {penalty}
                --------------------
                If you have any concerns or inquiries, contact us at:
                Email: dsws.loans@gmail.com
                """
    template = render_to_string(
        template_name="base/Email-Templates/overdue_item_b_email.html",
        context={
            "client": client,
            "itemCat": item_cat,
            "overdueHours": overdue_hours,
            "overdueMinutes": overdue_minutes,
            "penalty": penalty,
        },
    )
    msg = TransactionEmailThread(subject_matter, message, client.email, template)
    msg.start()
