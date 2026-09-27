from django.contrib import admin
from .models import Product, Transaction, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("reference", "type", "name", "amount", "status", "created_at")
    list_filter = ("type", "status")
    search_fields = ("reference", "name", "email")
    inlines = [OrderItemInline]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "active")
    list_filter = ("active",)
