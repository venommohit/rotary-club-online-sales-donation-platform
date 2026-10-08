# urls.py
# Include this in your project's urls.py, e.g.:
#   path("", include("donations.urls")),

from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("donate/", views.donate, name="donate"),
    path("shop/", views.shop, name="shop"),
    path("payment/", views.payment, name="payment"),
    path("payment/success/", views.payment_success, name="payment_success"),
    path("stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),
    path("confirmation/", views.confirmation, name="confirmation"),

    path("dashboard/login/", views.dashboard_login, name="dashboard_login"),
    path("dashboard/logout/", views.dashboard_logout, name="dashboard_logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/transactions/", views.dashboard_transactions, name="dashboard_transactions"),
    path("dashboard/reports/", views.dashboard_reports, name="dashboard_reports"),
]
