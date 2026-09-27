from django.core.management.base import BaseCommand
from donations.models import Product


class Command(BaseCommand):
    help = "Seed the database with demo Christmas tree products."

    def handle(self, *args, **options):
        demo_products = [
            {"name": "Noble Fir — 5 ft", "description": "Compact, great for apartments", "price": 55, "emoji": "🌲"},
            {"name": "Noble Fir — 7 ft", "description": "Our most popular family size", "price": 85, "emoji": "🎄"},
            {"name": "Grand Fir — 9 ft", "description": "Statement tree for larger rooms", "price": 120, "emoji": "🎄"},
        ]

        created = 0
        for data in demo_products:
            _, was_created = Product.objects.get_or_create(name=data["name"], defaults=data)
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {created} new product(s)."))
