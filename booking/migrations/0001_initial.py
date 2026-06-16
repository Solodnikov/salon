import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Service",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True, verbose_name="Название")),
                ("price", models.DecimalField(decimal_places=2, max_digits=10, verbose_name="Стоимость")),
                ("duration_minutes", models.PositiveIntegerField(verbose_name="Время выполнения, минут")),
                ("description", models.TextField(blank=True, verbose_name="Описание")),
                ("is_active", models.BooleanField(default=True, verbose_name="Активна")),
            ],
            options={
                "verbose_name": "Услуга",
                "verbose_name_plural": "Услуги",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Visitor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, verbose_name="Имя")),
                ("phone", models.CharField(max_length=32, unique=True, verbose_name="Телефон")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создан")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Обновлен")),
            ],
            options={
                "verbose_name": "Посетитель",
                "verbose_name_plural": "Посетители",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Barber",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, verbose_name="Имя мастера")),
                ("is_active", models.BooleanField(default=True, verbose_name="Активен")),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="barber_profile",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Пользователь админки",
                    ),
                ),
            ],
            options={
                "verbose_name": "Парикмахер",
                "verbose_name_plural": "Парикмахеры",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="BarberService",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "barber",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="booking.barber", verbose_name="Парикмахер"),
                ),
                (
                    "service",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="booking.service", verbose_name="Услуга"),
                ),
            ],
            options={
                "verbose_name": "Услуга парикмахера",
                "verbose_name_plural": "Услуги парикмахеров",
                "constraints": [
                    models.UniqueConstraint(fields=("barber", "service"), name="unique_barber_service")
                ],
            },
        ),
        migrations.CreateModel(
            name="Vacation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("start_date", models.DateField(verbose_name="Дата начала")),
                ("end_date", models.DateField(verbose_name="Дата окончания")),
                (
                    "barber",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="booking.barber", verbose_name="Парикмахер"),
                ),
            ],
            options={
                "verbose_name": "Отпуск",
                "verbose_name_plural": "Отпуска",
                "ordering": ["barber", "start_date"],
            },
        ),
        migrations.CreateModel(
            name="WeeklySchedule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "weekday",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (0, "Понедельник"),
                            (1, "Вторник"),
                            (2, "Среда"),
                            (3, "Четверг"),
                            (4, "Пятница"),
                            (5, "Суббота"),
                            (6, "Воскресенье"),
                        ],
                        verbose_name="День недели",
                    ),
                ),
                ("is_working", models.BooleanField(default=True, verbose_name="Рабочий день")),
                ("start_time", models.TimeField(verbose_name="Начало рабочего дня")),
                ("end_time", models.TimeField(verbose_name="Конец рабочего дня")),
                (
                    "barber",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="booking.barber", verbose_name="Парикмахер"),
                ),
            ],
            options={
                "verbose_name": "Рабочий день",
                "verbose_name_plural": "Рабочие дни",
                "ordering": ["barber", "weekday"],
                "constraints": [
                    models.UniqueConstraint(fields=("barber", "weekday"), name="unique_barber_weekday")
                ],
            },
        ),
        migrations.CreateModel(
            name="Appointment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("starts_at", models.DateTimeField(verbose_name="Дата и время")),
                ("comment", models.TextField(blank=True, verbose_name="Комментарий")),
                ("is_active", models.BooleanField(default=True, verbose_name="Активна")),
                ("price_snapshot", models.DecimalField(decimal_places=2, max_digits=10, verbose_name="Стоимость на момент записи")),
                ("duration_minutes_snapshot", models.PositiveIntegerField(verbose_name="Длительность на момент записи")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создана")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Обновлена")),
                (
                    "barber",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="booking.barber", verbose_name="Парикмахер"),
                ),
                (
                    "service",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="booking.service", verbose_name="Услуга"),
                ),
                (
                    "visitor",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="booking.visitor", verbose_name="Посетитель"),
                ),
            ],
            options={
                "verbose_name": "Запись",
                "verbose_name_plural": "Записи",
                "ordering": ["starts_at"],
                "indexes": [
                    models.Index(fields=["barber", "starts_at"], name="appointment_barber_starts_idx"),
                    models.Index(fields=["visitor", "is_active"], name="appointment_visitor_active_idx"),
                ],
            },
        ),
    ]
