from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Visitor(models.Model):
    name = models.CharField("Имя", max_length=120)
    phone = models.CharField("Телефон", max_length=32, unique=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлен", auto_now=True)

    class Meta:
        verbose_name = "Посетитель"
        verbose_name_plural = "Посетители"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.phone})"


class Barber(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="Пользователь админки",
        on_delete=models.CASCADE,
        related_name="barber_profile",
    )
    name = models.CharField("Имя мастера", max_length=120)
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        verbose_name = "Парикмахер"
        verbose_name_plural = "Парикмахеры"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Service(models.Model):
    name = models.CharField("Название", max_length=120, unique=True)
    price = models.DecimalField("Стоимость", max_digits=10, decimal_places=2)
    duration_minutes = models.PositiveIntegerField("Время выполнения, минут")
    description = models.TextField("Описание", blank=True)
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        verbose_name = "Услуга"
        verbose_name_plural = "Услуги"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.duration_minutes} мин.)"


class BarberService(models.Model):
    barber = models.ForeignKey(Barber, verbose_name="Парикмахер", on_delete=models.CASCADE)
    service = models.ForeignKey(Service, verbose_name="Услуга", on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Услуга парикмахера"
        verbose_name_plural = "Услуги парикмахеров"
        constraints = [
            models.UniqueConstraint(fields=["barber", "service"], name="unique_barber_service")
        ]

    def __str__(self):
        return f"{self.barber}: {self.service}"


class Weekday(models.IntegerChoices):
    MONDAY = 0, "Понедельник"
    TUESDAY = 1, "Вторник"
    WEDNESDAY = 2, "Среда"
    THURSDAY = 3, "Четверг"
    FRIDAY = 4, "Пятница"
    SATURDAY = 5, "Суббота"
    SUNDAY = 6, "Воскресенье"


class WeeklySchedule(models.Model):
    barber = models.ForeignKey(Barber, verbose_name="Парикмахер", on_delete=models.CASCADE)
    weekday = models.PositiveSmallIntegerField("День недели", choices=Weekday.choices)
    is_working = models.BooleanField("Рабочий день", default=True)
    start_time = models.TimeField("Начало рабочего дня")
    end_time = models.TimeField("Конец рабочего дня")

    class Meta:
        verbose_name = "Рабочий день"
        verbose_name_plural = "Рабочие дни"
        ordering = ["barber", "weekday"]
        constraints = [
            models.UniqueConstraint(fields=["barber", "weekday"], name="unique_barber_weekday")
        ]

    def clean(self):
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("Начало рабочего дня должно быть раньше конца.")

    def __str__(self):
        return f"{self.barber}: {self.get_weekday_display()}"


class Vacation(models.Model):
    barber = models.ForeignKey(Barber, verbose_name="Парикмахер", on_delete=models.CASCADE)
    start_date = models.DateField("Дата начала")
    end_date = models.DateField("Дата окончания")

    class Meta:
        verbose_name = "Отпуск"
        verbose_name_plural = "Отпуска"
        ordering = ["barber", "start_date"]

    def clean(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError("Дата начала отпуска должна быть не позже даты окончания.")

    def __str__(self):
        return f"{self.barber}: {self.start_date} - {self.end_date}"


class Appointment(models.Model):
    starts_at = models.DateTimeField("Дата и время")
    visitor = models.ForeignKey(Visitor, verbose_name="Посетитель", on_delete=models.PROTECT)
    barber = models.ForeignKey(Barber, verbose_name="Парикмахер", on_delete=models.PROTECT)
    service = models.ForeignKey(Service, verbose_name="Услуга", on_delete=models.PROTECT)
    comment = models.TextField("Комментарий", blank=True)
    is_active = models.BooleanField("Активна", default=True)
    price_snapshot = models.DecimalField("Стоимость на момент записи", max_digits=10, decimal_places=2)
    duration_minutes_snapshot = models.PositiveIntegerField("Длительность на момент записи")
    created_at = models.DateTimeField("Создана", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлена", auto_now=True)

    class Meta:
        verbose_name = "Запись"
        verbose_name_plural = "Записи"
        ordering = ["starts_at"]
        indexes = [
            models.Index(fields=["barber", "starts_at"], name="appointment_barber_starts_idx"),
            models.Index(fields=["visitor", "is_active"], name="appointment_visitor_active_idx"),
        ]

    @property
    def ends_at(self):
        return self.starts_at + timedelta(minutes=self.duration_minutes_snapshot)

    @property
    def is_future(self):
        return self.starts_at >= timezone.now()

    def clean(self):
        if not BarberService.objects.filter(barber=self.barber, service=self.service).exists():
            raise ValidationError("Выбранный парикмахер не оказывает эту услугу.")

    def save(self, *args, **kwargs):
        if self.service_id:
            self.price_snapshot = self.service.price
            self.duration_minutes_snapshot = self.service.duration_minutes
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.starts_at:%d.%m.%Y %H:%M} - {self.visitor} - {self.service}"
