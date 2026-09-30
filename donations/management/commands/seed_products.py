from django.core.management.base import BaseCommand
from donations import firestore_data as data


class Command(BaseCommand):
    help = "Seed Firestore with demo Christmas tree products."

    def handle(self, *args, **options):
        demo_products = [
            {"name": "Noble Fir — 5 ft", "description": "Compact, great for apartments", "price": 55, "emoji": "🌲"},
            {"name": "Noble Fir — 7 ft", "description": "Our most popular family size", "price": 85, "emoji": "🎄"},
            {"name": "Grand Fir — 9 ft", "description": "Statement tree for larger rooms", "price": 120, "emoji": "🎄"},
        ]

        created = data.seed_products(demo_products)
        self.stdout.write(self.style.SUCCESS(f"Seeded {created} new product(s) into Firestore."))
