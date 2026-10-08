# donations/views.py
#
# Page flow:
#   donate / shop  -> payment (review)  -> Stripe's hosted Checkout page
#                  -> payment_success   (browser comes back from Stripe)
#                  -> stripe_webhook    (Stripe calls us server-to-server)
#
# Card details are entered on Stripe's page only; they never reach this server.
# The pending donation/order lives in the signed session cookie until Stripe
# confirms payment; only then is a transaction written to Firestore.

import hmac
import json
import logging

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from . import firestore_data as data
from . import payments
from .emails import send_confirmation_email
from .forms import DonationForm, StaffLoginForm

logger = logging.getLogger(__name__)

MAX_QTY = 50


def _stripe_client():
    """Created lazily so the site still runs (and says so clearly) with no key set."""
    if not settings.STRIPE_SECRET_KEY:
        raise RuntimeError("STRIPE_SECRET_KEY is not set")
    import stripe
    return stripe.StripeClient(settings.STRIPE_SECRET_KEY)


def _site_base(request):
    return (settings.SITE_URL or request.build_absolute_uri("/")).rstrip("/")


def _as_dict(obj):
    return obj.to_dict() if hasattr(obj, "to_dict") else dict(obj)


def _notify(reference):
    send_confirmation_email(data.get_transaction(reference))


# ---------------------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------------------


def home(request):
    # The receipt page is only for the person who has just paid. Once they come
    # back to the home page we forget it, so the next person to use a shared
    # device can't see someone else's order. The emailed receipt is the record.
    request.session.pop("last_reference", None)
    return render(request, "donations/home.html")


def donate(request):
    if request.method == "POST":
        form = DonationForm(request.POST)
        if form.is_valid():
            request.session["pending_transaction"] = {
                "type": "donation",
                "type_display": "Donation",
                "name": form.cleaned_data["donor_name"],
                "email": form.cleaned_data["donor_email"],
                "amount": str(form.cleaned_data["amount"]),
                "message": form.cleaned_data.get("donor_message", ""),
            }
            return redirect("payment")
    else:
        form = DonationForm(initial={"amount": 50})
    return render(request, "donations/donate.html", {"form": form})


def _safe_qty(raw):
    try:
        return max(0, min(MAX_QTY, int(raw)))
    except (TypeError, ValueError):
        return 0


def shop(request):
    products = data.list_active_products()

    if request.method == "POST":
        items = []
        subtotal = 0.0
        for product in products:
            qty = _safe_qty(request.POST.get(f"qty_{product['id']}", 0))
            if qty > 0:
                items.append({
                    "product_id": product["id"],
                    "product_name": product["name"],
                    "quantity": qty,
                    "unit_price": float(product["price"]),
                })
                subtotal += qty * float(product["price"])

        name = request.POST.get("buyer_name", "").strip()[:150]
        email = request.POST.get("buyer_email", "").strip()
        fulfilment = "delivery" if request.POST.get("fulfilment") == "delivery" else "pickup"

        error = None
        if not items:
            error = "Add at least one tree to your cart before continuing."
        elif not name:
            error = "Please enter your name."
        else:
            try:
                validate_email(email)
            except ValidationError:
                error = "Please enter a valid email address so we can send your receipt."

        if error:
            messages.error(request, error)
            return render(request, "donations/shop.html", {"products": products})

        total = subtotal + (float(payments.DELIVERY_FEE) if fulfilment == "delivery" else 0)
        request.session["pending_transaction"] = {
            "type": "sale",
            "type_display": "Tree order",
            "name": name,
            "email": email,
            "amount": f"{total:.2f}",
            "fulfilment": fulfilment,
            "items": items,
        }
        return redirect("payment")

    return render(request, "donations/shop.html", {"products": products})


# ---------------------------------------------------------------------------
# Payment (Stripe Checkout)
# ---------------------------------------------------------------------------

def payment(request):
    pending = request.session.get("pending_transaction")
    if not pending:
        messages.error(request, "Your session expired — please start again.")
        return redirect("home")

    if request.method == "POST":
        base = _site_base(request)
        params = {
            "mode": "payment",
            "line_items": payments.build_line_items(pending),
            "metadata": payments.build_metadata(pending),
            "success_url": base + reverse("payment_success") + "?session_id={CHECKOUT_SESSION_ID}",
            "cancel_url": base + reverse("payment"),
        }
        if pending.get("email"):
            params["customer_email"] = pending["email"]
        if pending["type"] == "donation":
            params["submit_type"] = "donate"

        try:
            session = _stripe_client().v1.checkout.sessions.create(params)
        except Exception:
            logger.exception("Could not create Stripe Checkout session")
            messages.error(request, "We couldn't reach the payment provider. "
                                    "You have not been charged — please try again shortly.")
            return render(request, "donations/payment.html", {"pending": pending})

        return _see_other(session.url)

    return render(request, "donations/payment.html", {"pending": pending})


def _see_other(url):
    response = HttpResponse(status=303)
    response["Location"] = url
    return response


def payment_success(request):
    """The customer's browser lands here after paying on Stripe."""
    session_id = request.GET.get("session_id", "")
    if not session_id.startswith("cs_"):
        messages.error(request, "We couldn't find your payment. If you were charged, "
                                "your receipt will arrive by email.")
        return redirect("home")

    try:
        session = _as_dict(_stripe_client().v1.checkout.sessions.retrieve(
            session_id, {"expand": ["line_items"]}))
        reference = payments.fulfil_checkout_session(
            session, create_once=data.create_transaction_once, notify=_notify)
    except Exception:
        logger.exception("Could not confirm Stripe session %s", session_id)
        messages.error(request, "We couldn't confirm your payment just yet. If you were "
                                "charged, your receipt will arrive by email shortly.")
        return redirect("home")

    if not reference:
        messages.error(request, "Your payment hasn't completed. You have not been charged.")
        return redirect("payment")

    request.session["last_reference"] = reference
    request.session.pop("pending_transaction", None)
    return redirect(f"{reverse('confirmation')}?ref={reference}")


@csrf_exempt
def stripe_webhook(request):
    """
    Stripe -> us. Authenticated by signature, not CSRF. Guarantees the order is
    recorded even if the customer closes the tab before returning to the site.
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    if not payments.verify_webhook_signature(
            request.body, request.META.get("HTTP_STRIPE_SIGNATURE", ""),
            settings.STRIPE_WEBHOOK_SECRET):
        return HttpResponse(status=400)

    try:
        event = json.loads(request.body)
    except ValueError:
        return HttpResponse(status=400)

    if event.get("type") in ("checkout.session.completed",
                             "checkout.session.async_payment_succeeded"):
        session_id = event["data"]["object"]["id"]
        try:
            session = _as_dict(_stripe_client().v1.checkout.sessions.retrieve(
                session_id, {"expand": ["line_items"]}))
            payments.fulfil_checkout_session(
                session, create_once=data.create_transaction_once, notify=_notify)
        except ValueError:
            pass  # a Stripe session that isn't ours — acknowledge and ignore
        except Exception:
            logger.exception("Webhook fulfilment failed for %s", session_id)
            return HttpResponse(status=500)  # Stripe will retry

    return HttpResponse(status=200)


def confirmation(request):
    """Only the browser that just paid can view its receipt page."""
    ref = request.GET.get("ref")
    transaction = None
    if ref and hmac.compare_digest(ref, request.session.get("last_reference") or ""):
        transaction = data.get_transaction(ref)
    if not transaction:
        messages.error(request, "We couldn't find that receipt. Your receipt was also sent by email.")
        return redirect("home")
    return render(request, "donations/confirmation.html", {"transaction": transaction})


# ---------------------------------------------------------------------------
# Staff dashboard (credentials come from STAFF_USERNAME / STAFF_PASSWORD env vars)
# ---------------------------------------------------------------------------

def _credentials_ok(username, password):
    expected_user, expected_pass = settings.STAFF_USERNAME, settings.STAFF_PASSWORD
    if not expected_user or not expected_pass:
        return False  # fail closed when not configured
    user_ok = hmac.compare_digest(username.encode(), expected_user.encode())
    pass_ok = hmac.compare_digest(password.encode(), expected_pass.encode())
    return user_ok and pass_ok


def dashboard_login(request):
    if request.method == "POST":
        form = StaffLoginForm(request.POST)
        if form.is_valid():
            if _credentials_ok(form.cleaned_data["username"], form.cleaned_data["password"]):
                request.session.cycle_key()
                request.session["staff_user"] = form.cleaned_data["username"]
                return redirect("dashboard")
            messages.error(request, "Incorrect username or password.")
    else:
        form = StaffLoginForm()
    return render(request, "donations/dashboard_login.html", {"form": form})


def dashboard_logout(request):
    if request.method == "POST":
        request.session.pop("staff_user", None)
    return redirect("home")


def _is_staff(request):
    return bool(request.session.get("staff_user"))


def dashboard(request):
    if not _is_staff(request):
        return redirect("dashboard_login")
    stats = data.get_summary_stats()
    return render(request, "donations/dashboard.html", {
        "total_raised": stats["total_raised"],
        "donation_count": stats["donation_count"],
        "order_count": stats["order_count"],
        "avg_donation": stats["avg_donation"],
    })


def dashboard_transactions(request):
    if not _is_staff(request):
        return redirect("dashboard_login")
    return render(request, "donations/dashboard_transactions.html",
                  {"transactions": data.list_transactions()})


def dashboard_reports(request):
    if not _is_staff(request):
        return redirect("dashboard_login")
    stats = data.get_summary_stats()
    return render(request, "donations/dashboard_reports.html", {
        "donation_total": stats["donation_total"],
        "sales_total": stats["sales_total"],
        "pending_count": stats["pending_count"],
    })
