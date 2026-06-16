from django.core.management.base import BaseCommand

from booking.models import Service


class Command(BaseCommand):
    help = "Create or update default salon services."

    def handle(self, *args, **options):
        defaults = [
            {
                "name": "Женская стрижка",
                "price": 1000,
                "duration_minutes": 60,
                "description": "Базовая женская стрижка.",
            },
            {
                "name": "Мужская стрижка",
                "price": 650,
                "duration_minutes": 45,
                "description": "Базовая мужская стрижка.",
            },
        ]

        for item in defaults:
            service, created = Service.objects.update_or_create(
                name=item["name"],
                defaults={
                    "price": item["price"],
                    "duration_minutes": item["duration_minutes"],
                    "description": item["description"],
                    "is_active": True,
                },
            )
            action = "created" if created else "updated"
            self.stdout.write(self.style.SUCCESS(f"{service.name}: {action}"))
