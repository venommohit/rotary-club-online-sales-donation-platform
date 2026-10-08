# donations/emails.py
#
# Confirmation email after a successful payment.
#
# Two transports:
#   * BREVO_API_KEY set  -> Brevo's HTTPS API. Use this on a hosted server: Render's
#                           free tier blocks outbound SMTP (ports 25/465/587), so
#                           Gmail SMTP would silently fail there.
#   * otherwise          -> Django's SMTP backend (Gmail app password) — fine locally.
#
# A failed send never breaks checkout: it's logged and swallowed, because by the
# time we get here the customer has already paid.

import json
import logging
import urllib.request

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def _compose(transaction):
    subject = f"Rotary Padstow — receipt {transaction['reference']}"
    kind = transaction["type_display"].lower()
    lines = [
        f"Thank you, {transaction['name']}!",
        "",
        f"Reference: {transaction['reference']}",
        f"Type: {transaction['type_display']}",
        f"Amount: ${transaction['amount']:.2f} AUD",
    ]
    for item in transaction.get("items") or []:
        lines.append(f"  - {item['product_name']} x {item['quantity']}")
    if transaction.get("fulfilment"):
        lines.append(f"Fulfilment: {transaction['fulfilment']}")
    lines += [
        "",
        f"This confirms your {kind} with Rotary Club of Padstow. No further action is needed.",
    ]
    return subject, "\n".join(lines) + "\n"


def _send_via_brevo(to_email, to_name, subject, body):
    payload = {
        "sender": {"name": "Rotary Club of Padstow", "email": settings.EMAIL_FROM_ADDRESS},
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
        "textContent": body,
    }
    request = urllib.request.Request(
        BREVO_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "api-key": settings.BREVO_API_KEY,
            "content-type": "application/json",
            "accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        response.read()


def send_confirmation_email(transaction):
    if not transaction or not transaction.get("email"):
        return

    subject, body = _compose(transaction)
    try:
        if settings.BREVO_API_KEY:
            _send_via_brevo(transaction["email"], transaction["name"], subject, body)
        else:
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL,
                      [transaction["email"]], fail_silently=False)
    except Exception:
        logger.exception("Failed to send confirmation email for %s", transaction.get("reference"))
