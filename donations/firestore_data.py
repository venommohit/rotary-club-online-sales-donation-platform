# donations/firestore_data.py
#
# All Firestore reads/writes for the app live here, so views.py never
# touches the Firestore SDK directly. Two collections:
#
#   products      — doc id auto-generated, fields: name, description,
#                    price (float), emoji, active (bool)
#   transactions  — doc id IS the reference (e.g. "RCP-2026-A1B2C3D4"),
#                    fields: type, name, email, amount (float), message,
#                    fulfilment, status, created_at (server timestamp),
#                    items (list of maps, only for type="sale")
#
# Using the reference as the document id means looking up a transaction
# by reference (the confirmation page, ?ref=...) is a single direct
# document read rather than a query — the cheap, scalable way to do it
# in Firestore.

import uuid
from datetime import datetime

from firebase_admin import firestore

from .firestore_client import get_db

SERVER_TIMESTAMP = firestore.SERVER_TIMESTAMP

TYPE_LABELS = {"donation": "Donation", "sale": "Tree order"}
STATUS_LABELS = {"pending": "Pending", "paid": "Paid", "failed": "Failed"}

PRODUCTS_COLLECTION = "products"
TRANSACTIONS_COLLECTION = "transactions"


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

def list_active_products():
    """Returns active products as a list of dicts, each with its doc id as 'id'."""
    db = get_db()
    docs = db.collection(PRODUCTS_COLLECTION).where("active", "==", True).stream()
    products = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        products.append(data)
    return products


def get_product(product_id):
    db = get_db()
    doc = db.collection(PRODUCTS_COLLECTION).document(product_id).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    data["id"] = doc.id
    return data


def seed_products(products):
    """
    products: list of dicts with name/description/price/emoji.
    Skips any product whose name already exists, so it's safe to re-run.
    """
    db = get_db()
    collection = db.collection(PRODUCTS_COLLECTION)
    existing_names = {doc.to_dict().get("name") for doc in collection.stream()}

    created = 0
    for product in products:
        if product["name"] in existing_names:
            continue
        collection.add({
            "name": product["name"],
            "description": product.get("description", ""),
            "price": float(product["price"]),
            "emoji": product.get("emoji", "🎄"),
            "active": True,
        })
        created += 1
    return created


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

def _generate_reference():
    return "RCP-2026-" + uuid.uuid4().hex[:8].upper()


def _decorate(data):
    """Adds human-readable display labels, same job Django's
    get_FOO_display() would do on a model instance."""
    data["type_display"] = TYPE_LABELS.get(data.get("type"), data.get("type"))
    data["status_display"] = STATUS_LABELS.get(data.get("status"), data.get("status"))
    return data


def create_transaction(*, type, name, email, amount, message="", fulfilment="", items=None, status="paid"):
    """
    Creates a transaction document with the reference as its id, and
    (for a sale) writes matching OrderItem-style entries into the
    `items` array field on the same document — Firestore has no joins,
    so a small list of line items is embedded directly rather than put
    in a separate collection.
    """
    db = get_db()
    reference = _generate_reference()

    payload = {
        "reference": reference,
        "type": type,
        "name": name,
        "email": email,
        "amount": float(amount),
        "message": message,
        "fulfilment": fulfilment,
        "status": status,
        "created_at": SERVER_TIMESTAMP,
    }
    if items:
        payload["items"] = items

    db.collection(TRANSACTIONS_COLLECTION).document(reference).set(payload)
    return reference


def get_transaction(reference):
    db = get_db()
    doc = db.collection(TRANSACTIONS_COLLECTION).document(reference).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    data["created_at"] = data.get("created_at") or datetime.utcnow()
    return _decorate(data)


def list_transactions(limit=200):
    """Newest first. `limit` keeps this bounded as the collection grows —
    add pagination (start_after) once you outgrow a single page."""
    db = get_db()
    docs = (
        db.collection(TRANSACTIONS_COLLECTION)
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    results = []
    for doc in docs:
        data = doc.to_dict()
        results.append(_decorate(data))
    return results


def get_summary_stats():
    """
    Computed by reading transactions and summing in Python — fine at
    club scale. If this collection grows large, replace with Firestore
    aggregation queries (collection.count(), collection.sum('amount'))
    or a maintained counters document updated by a Cloud Function on
    each write, so this stops needing to read every row.
    """
    db = get_db()
    docs = db.collection(TRANSACTIONS_COLLECTION).stream()

    total_raised = 0.0
    donation_total = 0.0
    sales_total = 0.0
    donation_count = 0
    order_count = 0
    pending_count = 0

    for doc in docs:
        data = doc.to_dict()
        amount = float(data.get("amount", 0))
        total_raised += amount
        if data.get("type") == "donation":
            donation_count += 1
            donation_total += amount
        elif data.get("type") == "sale":
            order_count += 1
            sales_total += amount
        if data.get("status") == "pending":
            pending_count += 1

    avg_donation = round(donation_total / donation_count) if donation_count else 0

    return {
        "total_raised": round(total_raised),
        "donation_total": round(donation_total),
        "sales_total": round(sales_total),
        "donation_count": donation_count,
        "order_count": order_count,
        "pending_count": pending_count,
        "avg_donation": avg_donation,
    }
