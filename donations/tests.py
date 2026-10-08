# Unit tests for the payment logic. Run with:  python manage.py test donations
# (or, with no Django installed:  python -m unittest donations.tests)

import hashlib
import hmac
import importlib.util
import pathlib
import unittest

_spec = importlib.util.spec_from_file_location(
    "payments", pathlib.Path(__file__).with_name("payments.py"))
payments = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(payments)


def paid_session(kind="sale", **over):
    s = {
        "id": "cs_test_abc123", "created": 1790000000, "payment_status": "paid",
        "amount_total": 10500,
        "metadata": {"type": kind, "name": "Ann", "email": "ann@example.com",
                     "fulfilment": "delivery", "message": ""},
        "line_items": {"data": [
            {"description": "Noble Fir — 7 ft", "quantity": 1, "price": {"unit_amount": 8500}},
            {"description": payments.DELIVERY_LABEL, "quantity": 1, "price": {"unit_amount": 1500}},
        ]},
    }
    s.update(over)
    return s


class MoneyTests(unittest.TestCase):
    def test_to_cents(self):
        self.assertEqual(payments.to_cents("50"), 5000)
        self.assertEqual(payments.to_cents(19.99), 1999)
        self.assertEqual(payments.to_cents("0.005"), 1)

    def test_donation_line_items(self):
        lines = payments.build_line_items({"type": "donation", "amount": "25.00"})
        self.assertEqual(lines[0]["price_data"]["unit_amount"], 2500)
        self.assertEqual(lines[0]["quantity"], 1)

    def test_sale_line_items_with_delivery(self):
        pending = {"type": "sale", "fulfilment": "delivery",
                   "items": [{"product_name": "Tree", "unit_price": 55.0, "quantity": 2}]}
        lines = payments.build_line_items(pending)
        self.assertEqual([l["price_data"]["unit_amount"] for l in lines], [5500, 1500])
        self.assertEqual(lines[0]["quantity"], 2)

    def test_sale_line_items_pickup_has_no_delivery(self):
        pending = {"type": "sale", "fulfilment": "pickup",
                   "items": [{"product_name": "Tree", "unit_price": 55.0, "quantity": 1}]}
        self.assertEqual(len(payments.build_line_items(pending)), 1)

    def test_metadata_truncated(self):
        meta = payments.build_metadata({"type": "donation", "message": "x" * 900})
        self.assertEqual(len(meta["message"]), 450)


class FulfilmentTests(unittest.TestCase):
    def test_reference_is_deterministic(self):
        s = paid_session()
        self.assertEqual(payments.reference_for_session(s), payments.reference_for_session(s))
        self.assertRegex(payments.reference_for_session(s), r"^RCP-\d{4}-[0-9A-F]{10}$")

    def test_fields_exclude_delivery_and_use_total(self):
        f = payments.fields_from_session(paid_session())
        self.assertEqual(f["amount"], 105.0)
        self.assertEqual(len(f["items"]), 1)
        self.assertEqual(f["items"][0]["unit_price"], 85.0)

    def test_foreign_session_rejected(self):
        with self.assertRaises(ValueError):
            payments.fields_from_session(paid_session(metadata={}))

    def test_unpaid_session_does_nothing(self):
        calls = []
        r = payments.fulfil_checkout_session(
            paid_session(payment_status="unpaid"),
            lambda ref, **f: calls.append(ref) or True, calls.append)
        self.assertIsNone(r)
        self.assertEqual(calls, [])

    def test_idempotent_and_notifies_once(self):
        store, sent = set(), []

        def create_once(ref, **fields):
            if ref in store:
                return False
            store.add(ref)
            return True

        for _ in range(3):  # browser redirect + webhook + webhook retry
            ref = payments.fulfil_checkout_session(paid_session(), create_once, sent.append)
        self.assertEqual(len(store), 1)
        self.assertEqual(sent, [ref])


class SignatureTests(unittest.TestCase):
    SECRET = "whsec_test"
    BODY = b'{"id":"evt_1"}'

    def header(self, ts, secret=None, body=None):
        mac = hmac.new((secret or self.SECRET).encode(),
                       f"{ts}.".encode() + (body or self.BODY), hashlib.sha256).hexdigest()
        return f"t={ts},v1={mac}"

    def test_valid(self):
        self.assertTrue(payments.verify_webhook_signature(
            self.BODY, self.header(1000), self.SECRET, now=1100))

    def test_wrong_secret(self):
        self.assertFalse(payments.verify_webhook_signature(
            self.BODY, self.header(1000, secret="other"), self.SECRET, now=1100))

    def test_tampered_body(self):
        self.assertFalse(payments.verify_webhook_signature(
            b'{"id":"evt_2"}', self.header(1000), self.SECRET, now=1100))

    def test_stale_timestamp(self):
        self.assertFalse(payments.verify_webhook_signature(
            self.BODY, self.header(1000), self.SECRET, now=5000))

    def test_missing_pieces(self):
        for hdr, secret in [("", self.SECRET), ("garbage", self.SECRET), (self.header(1000), "")]:
            self.assertFalse(payments.verify_webhook_signature(self.BODY, hdr, secret, now=1100))


if __name__ == "__main__":
    unittest.main()
