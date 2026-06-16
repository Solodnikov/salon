from dataclasses import dataclass
from datetime import date, datetime, timedelta

from django.db import transaction
from django.utils import timezone

from .models import Appointment, Barber, BarberService, Service, Vacation, Visitor, WeeklySchedule


SLOT_STEP_MINUTES = 15


@dataclass(frozen=True)
class Slot:
    value: str
    label: str


def _aware_datetime(day: date, value):
    return timezone.make_aware(datetime.combine(day, value), timezone.get_current_timezone())


def _service_for_barber_exists(barber: Barber, service: Service) -> bool:
    return (
        barber.is_active
        and service.is_active
        and BarberService.objects.filter(barber=barber, service=service).exists()
    )


def _work_window(barber: Barber, day: date):
    schedule = WeeklySchedule.objects.filter(
        barber=barber,
        weekday=day.weekday(),
        is_working=True,
    ).first()
    if not schedule:
        return None

    if Vacation.objects.filter(barber=barber, start_date__lte=day, end_date__gte=day).exists():
        return None

    return _aware_datetime(day, schedule.start_time), _aware_datetime(day, schedule.end_time)


def _overlaps(start, end, other_start, other_end) -> bool:
    return start < other_end and end > other_start


def get_available_slots(barber: Barber, service: Service, day: date, exclude_appointment_id=None):
    if not _service_for_barber_exists(barber, service):
        return []

    window = _work_window(barber, day)
    if not window:
        return []

    work_start, work_end = window
    now = timezone.now()
    duration = timedelta(minutes=service.duration_minutes)
    step = timedelta(minutes=SLOT_STEP_MINUTES)

    appointments = Appointment.objects.filter(
        barber=barber,
        is_active=True,
        starts_at__gte=work_start - timedelta(days=1),
        starts_at__lt=work_end,
    )
    if exclude_appointment_id:
        appointments = appointments.exclude(pk=exclude_appointment_id)

    booked_intervals = [
        (appointment.starts_at, appointment.ends_at)
        for appointment in appointments.select_related("service")
    ]

    slots = []
    current = work_start
    while current + duration <= work_end:
        slot_end = current + duration
        is_free = current >= now and all(
            not _overlaps(current, slot_end, booked_start, booked_end)
            for booked_start, booked_end in booked_intervals
        )
        if is_free:
            local_current = timezone.localtime(current)
            value = local_current.strftime("%H:%M")
            slots.append(Slot(value=value, label=value))
        current += step

    return slots


def get_available_dates(barber: Barber, service: Service, year: int, month: int, exclude_appointment_id=None):
    first_day = date(year, month, 1)
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)

    available = []
    current = first_day
    while current < next_month:
        if get_available_slots(barber, service, current, exclude_appointment_id):
            available.append(current.isoformat())
        current += timedelta(days=1)
    return available


def parse_slot(day_value: str, time_value: str):
    parsed_day = datetime.strptime(day_value, "%Y-%m-%d").date()
    parsed_time = datetime.strptime(time_value, "%H:%M").time()
    return _aware_datetime(parsed_day, parsed_time)


def visitor_active_future_appointment(visitor: Visitor):
    return (
        Appointment.objects.filter(
            visitor=visitor,
            is_active=True,
            starts_at__gte=timezone.now(),
        )
        .select_related("barber", "service")
        .order_by("starts_at")
        .first()
    )


def book_appointment(visitor: Visitor, barber_id, service_id, day_value, time_value, comment="", appointment_id=None):
    starts_at = parse_slot(day_value, time_value)
    day = timezone.localdate(starts_at)

    with transaction.atomic():
        barber = Barber.objects.select_for_update().get(pk=barber_id, is_active=True)
        service = Service.objects.get(pk=service_id, is_active=True)

        if appointment_id:
            appointment = Appointment.objects.select_for_update().get(
                pk=appointment_id,
                visitor=visitor,
                is_active=True,
            )
            exclude_id = appointment.pk
        else:
            existing = visitor_active_future_appointment(visitor)
            if existing:
                raise ValueError("У вас уже есть активная будущая запись.")
            appointment = Appointment(visitor=visitor)
            exclude_id = None

        available_values = {slot.value for slot in get_available_slots(barber, service, day, exclude_id)}
        selected_value = timezone.localtime(starts_at).strftime("%H:%M")
        if selected_value not in available_values:
            raise ValueError("Выбранное время уже недоступно.")

        appointment.barber = barber
        appointment.service = service
        appointment.starts_at = starts_at
        appointment.comment = comment.strip()
        appointment.is_active = True
        appointment.save()
        return appointment
