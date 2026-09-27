# models.py
# Drop into your Django app (e.g. `donations/models.py`), then:
#   python manage.py makemigrations
#   python manage.py migrate

import uuid
from django.db import models


class Product(models.Model):
    """A sellable item, e.g. a Christmas tree size."""
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=255, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    emoji = models.CharField(max_length=8, blank=True, default="🎄")
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Transaction(models.Model):
    """A single donation or product order."""

    TYPE_CHOICES = [
        ("donation", "Donation"),
        ("sale", "Tree order"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
    ]

    reference = models.CharField(max_length=20, unique=True, editable=False)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    name = models.CharField(max_length=150)
    email = models.EmailField()
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    message = models.TextField(blank=True)          # donor's optional note
    fulfilment = models.CharField(max_length=20, blank=True)  # pickup / delivery
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = "RCP-2026-" + uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} — {self.get_type_display()} — ${self.amount}"


class OrderItem(models.Model):
    """Line item linking a Transaction (type='sale') to Products bought."""
    transaction = models.ForeignKey(Transaction, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} × {self.product.name}"
