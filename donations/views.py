# views.py
#
# Same page flow as before, but the data layer is now Firestore
# (donations/firestore_data.py) instead of the Django ORM. Pending
# donations/orders still travel through the Django session between
# donate/shop -> payment -> confirmation, exactly like a real hosted
# checkout redirect flow.

from django.contrib import messages
from django.shortcuts import render, redirect

from .forms import DonationForm, StaffLoginForm
from . import firestore_data as data


def home(request):
    last_ref = request.session.get("last_reference")
    return render(request, "donations/home.html", {"last_reference": last_ref})


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


def shop(request):
    products = data.list_active_products()

    if request.method == "POST":
        items = []
        subtotal = 0.0
        for product in products:
            qty = int(request.POST.get(f"qty_{product['id']}", 0) or 0)
            if qty > 0:
                items.append(
                    {
                        "product_id": product["id"],
                        "product_name": product["name"],
                        "quantity": qty,
                        "unit_price": float(product["price"]),
                    }
                )
                subtotal += qty * float(product["price"])

        if not items:
            messages.error(
                request, "Add at least one tree to your cart before continuing."
            )
            return render(request, "donations/shop.html", {"products": products})

        fulfilment = request.POST.get("fulfilment", "pickup")
        delivery_fee = 15 if fulfilment == "delivery" else 0
        total = subtotal + delivery_fee

        request.session["pending_transaction"] = {
            "type": "sale",
            "type_display": "Tree order",
            "name": request.POST.get("buyer_name", "Guest customer"),
            "email": request.POST.get("buyer_email", ""),
            "amount": str(total),
            "fulfilment": fulfilment,
            "items": items,
        }
        return redirect("payment")

    return render(request, "donations/shop.html", {"products": products})


def payment(request):
    pending = request.session.get("pending_transaction")
    if not pending:
        messages.error(request, "Your session expired — please start again.")
        return redirect("home")

    if request.method == "POST":
        # ---- Placeholder only. ----
        # In production you would NOT collect raw card fields yourself:
        # redirect to your payment provider (Stripe Checkout / PayPal /
        # Square), then handle their webhook or return_url here to
        # confirm payment before writing the transaction to Firestore.

        reference = data.create_transaction(
            type=pending["type"],
            name=pending["name"],
            email=pending.get("email", ""),
            amount=pending["amount"],
            message=pending.get("message", ""),
            fulfilment=pending.get("fulfilment", ""),
            items=pending.get("items"),
            status="paid",
        )
        reference = data.create_transaction(
            type=pending["type"],
            name=pending["name"],
            email=pending.get("email", ""),
            amount=pending["amount"],
            message=pending.get("message", ""),
            fulfilment=pending.get("fulfilment", ""),
            items=pending.get("items"),
            status="paid",
        )

        from .emails import send_confirmation_email

        transaction = data.get_transaction(reference)
        send_confirmation_email(transaction)

        request.session["last_reference"] = reference

        request.session["last_reference"] = reference
        del request.session["pending_transaction"]
        return redirect(f"/confirmation/?ref={reference}")

    return render(request, "donations/payment.html", {"pending": pending})


def confirmation(request):
    ref = request.GET.get("ref")
    transaction = data.get_transaction(ref) if ref else None
    if ref and not transaction:
        messages.error(request, "We couldn't find that receipt.")
    return render(request, "donations/confirmation.html", {"transaction": transaction})


# ---------------------------------------------------------------------------
# Staff dashboard
# NOTE: this uses a toy session flag for demo purposes, same as before —
# swapping the database doesn't change that. See README for swapping
# this to Firebase Authentication for real deployment.
# ---------------------------------------------------------------------------


def dashboard_login(request):
    if request.method == "POST":
        form = StaffLoginForm(request.POST)
        if form.is_valid():
            # TODO: replace with real Firebase Authentication sign-in.
            request.session["staff_user"] = form.cleaned_data["username"]
            return redirect("dashboard")
    else:
        form = StaffLoginForm()
    return render(request, "donations/dashboard_login.html", {"form": form})


def _require_staff(request):
    return bool(request.session.get("staff_user"))


def dashboard(request):
    if not _require_staff(request):
        return redirect("dashboard_login")

    stats = data.get_summary_stats()
    return render(
        request,
        "donations/dashboard.html",
        {
            "total_raised": stats["total_raised"],
            "donation_count": stats["donation_count"],
            "order_count": stats["order_count"],
            "avg_donation": stats["avg_donation"],
        },
    )


def dashboard_transactions(request):
    if not _require_staff(request):
        return redirect("dashboard_login")
    transactions = data.list_transactions()
    return render(
        request, "donations/dashboard_transactions.html", {"transactions": transactions}
    )


def dashboard_reports(request):
    if not _require_staff(request):
        return redirect("dashboard_login")
    stats = data.get_summary_stats()
    return render(
        request,
        "donations/dashboard_reports.html",
        {
            "donation_total": stats["donation_total"],
            "sales_total": stats["sales_total"],
            "pending_count": stats["pending_count"],
        },
    )
