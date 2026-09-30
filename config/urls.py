from django.urls import path, include

urlpatterns = [
    path("", include("donations.urls")),
]
