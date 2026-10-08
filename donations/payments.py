# donations/payments.py
#
# Pure helpers for the Stripe Checkout integration. This module
# deliberately imports neither Django nor the Stripe SDK so the logic that
# matters (amounts, line items, webhook signature check, mapping a paid
# session onto a Firestore transaction) can be unit-tested in isolation —
# see donations/tests.py.
#
# Flow:
#   1. payment view  -> build_line_items() + build_metadata() -> Stripe creates a
#                       hosted Checkout page; the browser is redirected there.
#   2. Stripe        -> customer pays on Stripe's page (card data never touches us)
#   3. Stripe        -> redirects the browser to /payment/success/?session_id=...
#                    -> AND (independently) calls our webhook.
#   4. Either one calls fulfil_checkout_session(), which is idempotent: the
#      Firestore document id is derived from the Stripe session id, so whichever
#      arrives second finds the record already there and does nothing (no
#      duplicate transaction, no duplicate email).

import hashlib
import hmac
import time
from decimal import Decimal, ROUND_HALF_UP

CURRENCY = "aud"
DONATION_LABEL = "Donation to Rotary Club of Padstow"
DELIVERY_LABEL = "Local delivery (Padstow / Panania)"
DELIVERY_FEE = Decimal("15.00")

VALID_TYPES = ("donation", "sale")


def to_cents(amount):
    """Dollars (int/float/str/Decimal) -> whole cents, rounded half-up."""
    return int((Decimal(str(amount)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _line(name, unit_amount, quantity):
    return {
        "price_data": {
            "currency": CURRENCY,
            "product_data": {"name": name},
            "unit_amount": to_cents(unit_amount),
        },
        "quantity": int(quantity),
    }


def build_line_items(pending):
    """Turn the pending donation/order held in the session into Stripe line items."""
    if pending["type"] == "donation":
        return [_line(DONATION_LABEL, pending["amount"], 1)]

    lines = [_line(i["product_name"], i["unit_price"], i["quantity"]) for i in pending["items"]]
    if pending.get("fulfilment") == "delivery":
        lines.append(_line(DELIVERY_LABEL, DELIVERY_FEE, 1))
    return lines


def build_metadata(pending):
    """
    Small facts stored on the Stripe session so the webhook can rebuild the
    record without needing the customer's browser session. Stripe limits metadata
    values to 500 characters.
    """
    return {
        "type": pending["type"],
        "name": (pending.get("name") or "")[:200],
        "email": (pending.get("email") or "")[:200],
        "fulfilment": pending.get("fulfilment") or "",
        "message": (pending.get("message") or "")[:450],
    }


def reference_for_session(session):
    """
    Deterministic receipt reference derived from the Stripe session id. Same
    session -> same reference, which is what makes fulfilment idempotent.
    """
    year = time.gmtime(session.get("created") or time.time()).tm_year
    digest = hashlib.sha256(session["id"].encode("utf-8")).hexdigest()[:10].upper()
    return f"RCP-{year}-{digest}"


def fields_from_session(session):
    """Map a (dict-like) Stripe Checkout Session onto our transaction fields."""
    meta = session.get("metadata") or {}
    details = session.get("customer_details") or {}

    kind = meta.get("type")
    if kind not in VALID_TYPES:
        raise ValueError("Not a Rotary checkout session")

    items = []
    if kind == "sale":
        # Note: Stripe returns the first 10 line items when expanded, plenty here;
        # amount_total below is authoritative either way.
        for li in (session.get("line_items") or {}).get("data", []):
            if li.get("description") == DELIVERY_LABEL:
                continue
            items.append({
                "product_name": li.get("description") or "Item",
                "quantity": li.get("quantity") or 1,
                "unit_price": float(Decimal(li["price"]["unit_amount"]) / 100),
            })

    return {
        "type": kind,
        "name": meta.get("name") or details.get("name") or "Guest",
        "email": meta.get("email") or details.get("email") or "",
        "amount": float(Decimal(session["amount_total"]) / 100),
        "message": meta.get("message", ""),
        "fulfilment": meta.get("fulfilment", ""),
        "items": items or None,
        "stripe_session_id": session["id"],
    }


def fulfil_checkout_session(session, create_once, notify):
    """
    If the session is paid, record it (once) and notify (once).

    create_once(reference, **fields) -> True if it created the record, False if it
    already existed. notify(reference) is called only when we created it.
    Returns the reference, or None if the session isn't paid.
    """
    if session.get("payment_status") != "paid":
        return None
    reference = reference_for_session(session)
    fields = fields_from_session(session)
    if create_once(reference, **fields):
        notify(reference)
    return reference


def verify_webhook_signature(payload, header, secret, tolerance=300, now=None):
    """
    Verify a Stripe webhook per Stripe's documented scheme: the Stripe-Signature
    header is "t=<unix ts>,v1=<hex hmac>[,v1=...]" where the HMAC-SHA256 is over
    "<ts>.<raw body>" keyed with the endpoint's signing secret (whsec_...).
    Rejects stale timestamps to stop replays.
    """
    if payload is None or not header or not secret:
        return False

    timestamp = None
    signatures = []
    for part in header.split(","):
        key, _, value = part.strip().partition("=")
        if key == "t":
            timestamp = value
        elif key == "v1":
            signatures.append(value)
    if not timestamp or not signatures:
        return False

    try:
        ts = int(timestamp)
    except ValueError:
        return False
    if abs((now if now is not None else time.time()) - ts) > tolerance:
        return False

    signed = f"{timestamp}.".encode("utf-8") + payload
    expected = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, sig) for sig in signatures)
