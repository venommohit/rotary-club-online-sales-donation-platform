# donations/emails.py
from django.core.mail import send_mail
from django.conf import settings


def send_confirmation_email(transaction):
    """
    Fires after a transaction is created. Wrapped so a failed send
    (bad credentials, no internet, etc.) never breaks checkout —
    it just logs to the console instead.
    """
    if not transaction.get("email"):
        return

    subject = f"Rotary Padstow — receipt {transaction['reference']}"
    body = (
        f"Thank you, {transaction['name']}!\n\n"
        f"Reference: {transaction['reference']}\n"
        f"Type: {transaction['type_display']}\n"
        f"Amount: ${transaction['amount']}\n\n"
        f"This confirms your {transaction['type_display'].lower()} with "
        f"Rotary Club of Padstow. No further action is needed.\n"
    )

    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [transaction["email"]],
            fail_silently=False,
        )
    except Exception as exc:
        print(
            f"[email] failed to send confirmation for {transaction['reference']}: {exc}"
        )
