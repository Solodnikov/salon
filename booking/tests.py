from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Appointment, Barber, BarberService, Service, Vacation, Visitor, WeeklySchedule
from .services import book_appointment, get_available_slots


def next_weekday(weekday):
    today = timezone.localdate()
    days_ahead = (weekday - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return today + timedelta(days=days_ahead)


class BookingSetupMixin:
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="barber",
            password="password",
            is_staff=True,
        )
        self.barber = Barber.objects.create(user=user, name="Анна")
        self.service = Service.objects.create(
            name="Мужская стрижка",
            price=650,
            duration_minutes=45,
            description="",
        )
        BarberService.objects.create(barber=self.barber, service=self.service)
        self.work_day = next_weekday(0)
        WeeklySchedule.objects.create(
            barber=self.barber,
            weekday=self.work_day.weekday(),
            is_working=True,
            start_time=time(10, 0),
            end_time=time(12, 0),
        )
        self.visitor = Visitor.objects.create(name="Иван", phone="+79990000000")

    def starts_at(self, day, value):
        return timezone.make_aware(
            datetime.combine(day, value),
            timezone.get_current_timezone(),
        )


class AvailabilityServiceTests(BookingSetupMixin, TestCase):
    def test_slots_respect_working_window(self):
        slots = get_available_slots(self.barber, self.service, self.work_day)

        self.assertEqual(
            [slot.value for slot in slots],
            ["10:00", "10:15", "10:30", "10:45", "11:00", "11:15"],
        )

    def test_booked_time_is_excluded_but_later_time_is_available(self):
        Appointment.objects.create(
            visitor=self.visitor,
            barber=self.barber,
            service=self.service,
            starts_at=self.starts_at(self.work_day, time(10, 0)),
        )

        slots = get_available_slots(self.barber, self.service, self.work_day)

        self.assertNotIn("10:00", [slot.value for slot in slots])
        self.assertNotIn("10:30", [slot.value for slot in slots])
        self.assertIn("10:45", [slot.value for slot in slots])

    def test_vacation_excludes_day(self):
        Vacation.objects.create(
            barber=self.barber,
            start_date=self.work_day,
            end_date=self.work_day,
        )

        self.assertEqual(get_available_slots(self.barber, self.service, self.work_day), [])

    def test_service_must_fit_before_end_of_day(self):
        short_day = next_weekday(1)
        WeeklySchedule.objects.create(
            barber=self.barber,
            weekday=short_day.weekday(),
            is_working=True,
            start_time=time(10, 0),
            end_time=time(10, 30),
        )

        self.assertEqual(get_available_slots(self.barber, self.service, short_day), [])

    def test_booking_rejects_second_active_future_appointment(self):
        book_appointment(
            self.visitor,
            self.barber.pk,
            self.service.pk,
            self.work_day.isoformat(),
            "10:00",
        )

        with self.assertRaisesMessage(ValueError, "активная будущая запись"):
            book_appointment(
                self.visitor,
                self.barber.pk,
                self.service.pk,
                self.work_day.isoformat(),
                "10:45",
            )


class VisitorFlowTests(BookingSetupMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()

    def login(self):
        response = self.client.post(
            reverse("booking:login"),
            {"name": "Иван", "phone": "+79990000000"},
        )
        self.assertEqual(response.status_code, 302)

    def test_login_registers_visitor_by_phone(self):
        self.client.post(reverse("booking:login"), {"name": "Мария", "phone": "+79990000001"})

        visitor = Visitor.objects.get(phone="+79990000001")
        self.assertEqual(visitor.name, "Мария")

    def test_create_and_cancel_appointment(self):
        self.login()

        response = self.client.post(
            reverse("booking:appointment_new"),
            {
                "service": self.service.pk,
                "barber": self.barber.pk,
                "date": self.work_day.isoformat(),
                "time": "10:00",
                "comment": "Без машинки",
            },
        )

        self.assertEqual(response.status_code, 302)
        appointment = Appointment.objects.get(visitor=self.visitor)
        self.assertEqual(appointment.comment, "Без машинки")
        self.assertEqual(appointment.price_snapshot, self.service.price)

        response = self.client.post(reverse("booking:appointment_cancel", args=[appointment.pk]))
        self.assertEqual(response.status_code, 302)
        appointment.refresh_from_db()
        self.assertFalse(appointment.is_active)

    def test_appointment_form_renders(self):
        self.login()

        response = self.client.get(reverse("booking:appointment_new"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "booking/booking.js")

    def test_availability_api_returns_dates_and_slots(self):
        self.login()

        response = self.client.get(
            reverse("booking:availability_api"),
            {
                "service": self.service.pk,
                "barber": self.barber.pk,
                "year": self.work_day.year,
                "month": self.work_day.month,
                "date": self.work_day.isoformat(),
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn(self.work_day.isoformat(), payload["dates"])
        self.assertIn({"value": "10:00", "label": "10:00"}, payload["slots"])

    def test_edit_appointment_reuses_existing_record(self):
        self.login()
        appointment = book_appointment(
            self.visitor,
            self.barber.pk,
            self.service.pk,
            self.work_day.isoformat(),
            "10:00",
        )

        response = self.client.post(
            reverse("booking:appointment_edit", args=[appointment.pk]),
            {
                "service": self.service.pk,
                "barber": self.barber.pk,
                "date": self.work_day.isoformat(),
                "time": "10:45",
                "comment": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        appointment.refresh_from_db()
        self.assertEqual(timezone.localtime(appointment.starts_at).strftime("%H:%M"), "10:45")
        self.assertEqual(Appointment.objects.count(), 1)


class AdminSmokeTests(BookingSetupMixin, TestCase):
    def test_staff_can_open_admin_changelists(self):
        staff = get_user_model().objects.create_user(
            username="staff",
            password="password",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(staff)

        for route in [
            "admin:booking_barber_changelist",
            "admin:booking_service_changelist",
            "admin:booking_appointment_changelist",
        ]:
            response = self.client.get(reverse(route))
            self.assertEqual(response.status_code, 200)
