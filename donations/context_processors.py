from django.conf import settings


def site(request):
    """Lets base.html show a 'test mode' banner while Stripe is using test keys."""
    return {"stripe_test_mode": settings.STRIPE_SECRET_KEY.startswith("sk_test_")}
