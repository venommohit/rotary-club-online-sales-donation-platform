# views.py
# This wires up every template in /templates to a working Django view.
# It uses the session to carry the "pending transaction" between
# donate/shop -> payment -> confirmation, which mirrors a normal
# hosted-checkout flow (Stripe/PayPal/Square) where you redirect out,
# then come back and mark the transaction paid.

from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404

from .forms import DonationForm, StaffLoginForm
from .models import Product, Transaction, OrderItem


def home(request):
    last_ref = request.session.get("last_reference")
    return render(request, "donations/home.html", {"last_reference": last_ref})


def donate(request):
    if request.method == "POST":
        form = DonationForm(request.POST)
        if form.is_valid():
            request.session["pending_transaction"] = {
                "type": "donation",
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
    products = Product.objects.filter(active=True)

    if request.method == "POST":
        items = []
        subtotal = 0
        for product in products:
            qty = int(request.POST.get(f"qty_{product.id}", 0) or 0)
            if qty > 0:
                items.append({"product_id": product.id, "quantity": qty, "unit_price": str(product.price)})
                subtotal += qty * float(product.price)

        if not items:
            messages.error(request, "Add at least one tree to your cart before continuing.")
            return render(request, "donations/shop.html", {"products": products})

        fulfilment = request.POST.get("fulfilment", "pickup")
        delivery_fee = 15 if fulfilment == "delivery" else 0
        total = subtotal + delivery_fee

        request.session["pending_transaction"] = {
            "type": "sale",
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
        # confirm payment before creating/marking the Transaction as paid.

        transaction = Transaction.objects.create(
            type=pending["type"],
            name=pending["name"],
            email=pending.get("email", ""),
            amount=pending["amount"],
            message=pending.get("message", ""),
            fulfilment=pending.get("fulfilment", ""),
            status="paid",
        )

        if pending["type"] == "sale":
            for item in pending.get("items", []):
                OrderItem.objects.create(
                    transaction=transaction,
                    product_id=item["product_id"],
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                )

        request.session["last_reference"] = transaction.reference
        del request.session["pending_transaction"]
        return redirect(f"/confirmation/?ref={transaction.reference}")

    return render(request, "donations/payment.html", {"pending": pending})


def confirmation(request):
    ref = request.GET.get("ref")
    transaction = get_object_or_404(Transaction, reference=ref) if ref else None
    return render(request, "donations/confirmation.html", {"transaction": transaction})


# ---------------------------------------------------------------------------
# Staff dashboard
# NOTE: this uses a toy session flag for demo purposes. For a real deployment,
# swap this for Django's built-in auth (@login_required, django.contrib.auth)
# so passwords are hashed and access is properly protected.
# ---------------------------------------------------------------------------

def dashboard_login(request):
    if request.method == "POST":
        form = StaffLoginForm(request.POST)
        if form.is_valid():
            # TODO: replace with django.contrib.auth.authenticate(...)
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

    transactions = Transaction.objects.all()
    total_raised = transactions.aggregate(Sum("amount"))["amount__sum"] or 0
    donations = transactions.filter(type="donation")
    orders = transactions.filter(type="sale")
    donation_total = donations.aggregate(Sum("amount"))["amount__sum"] or 0
    avg_donation = round(donation_total / donations.count()) if donations.count() else 0

    return render(request, "donations/dashboard.html", {
        "total_raised": total_raised,
        "donation_count": donations.count(),
        "order_count": orders.count(),
        "avg_donation": avg_donation,
    })


def dashboard_transactions(request):
    if not _require_staff(request):
        return redirect("dashboard_login")
    transactions = Transaction.objects.order_by("-created_at")
    return render(request, "donations/dashboard_transactions.html", {"transactions": transactions})


def dashboard_reports(request):
    if not _require_staff(request):
        return redirect("dashboard_login")
    transactions = Transaction.objects.all()
    donation_total = transactions.filter(type="donation").aggregate(Sum("amount"))["amount__sum"] or 0
    sales_total = transactions.filter(type="sale").aggregate(Sum("amount"))["amount__sum"] or 0
    pending_count = transactions.filter(status="pending").count()
    return render(request, "donations/dashboard_reports.html", {
        "donation_total": donation_total,
        "sales_total": sales_total,
        "pending_count": pending_count,
    })
