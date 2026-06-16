from datetime import date

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import AppointmentForm, LoginForm
from .models import Appointment, Barber, Service, Visitor
from .services import (
    book_appointment,
    get_available_dates,
    get_available_slots,
    visitor_active_future_appointment,
)


def _visitor_from_session(request):
    visitor_id = request.session.get("visitor_id")
    if not visitor_id:
        return None
    return Visitor.objects.filter(pk=visitor_id).first()


def _require_visitor(request):
    visitor = _visitor_from_session(request)
    if visitor is None:
        return None, redirect("booking:login")
    return visitor, None


def login_view(request):
    if _visitor_from_session(request):
        return redirect("booking:appointments")

    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        name = form.cleaned_data["name"].strip()
        phone = form.cleaned_data["phone"].strip()
        visitor, created = Visitor.objects.get_or_create(phone=phone, defaults={"name": name})
        if not created and visitor.name != name:
            visitor.name = name
            visitor.save(update_fields=["name", "updated_at"])
        request.session["visitor_id"] = visitor.pk
        return redirect("booking:appointments")

    return render(request, "booking/login.html", {"form": form})


def logout_view(request):
    request.session.flush()
    return redirect("booking:login")


def appointments_view(request):
    visitor, response = _require_visitor(request)
    if response:
        return response

    appointment = visitor_active_future_appointment(visitor)
    return render(
        request,
        "booking/appointments.html",
        {
            "visitor": visitor,
            "appointment": appointment,
        },
    )


def appointment_form_view(request, pk=None):
    visitor, response = _require_visitor(request)
    if response:
        return response

    appointment = None
    if pk is not None:
        appointment = get_object_or_404(
            Appointment.objects.select_related("service", "barber"),
            pk=pk,
            visitor=visitor,
            is_active=True,
        )
    else:
        existing = visitor_active_future_appointment(visitor)
        if existing:
            messages.info(request, "У вас уже есть активная запись. Ее можно изменить.")
            return redirect("booking:appointment_edit", pk=existing.pk)

    initial = {}
    if appointment:
        initial = {
            "service": appointment.service,
            "barber": appointment.barber,
            "date": timezone.localdate(appointment.starts_at),
            "time": timezone.localtime(appointment.starts_at).time().strftime("%H:%M"),
            "comment": appointment.comment,
        }

    form = AppointmentForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            saved = book_appointment(
                visitor=visitor,
                barber_id=form.cleaned_data["barber"].pk,
                service_id=form.cleaned_data["service"].pk,
                day_value=form.cleaned_data["date"].isoformat(),
                time_value=form.cleaned_data["time"].strftime("%H:%M"),
                comment=form.cleaned_data["comment"],
                appointment_id=appointment.pk if appointment else None,
            )
        except ValueError as exc:
            form.add_error(None, str(exc))
        else:
            return redirect(f"{reverse('booking:appointments')}?created={saved.pk}")

    return render(
        request,
        "booking/appointment_form.html",
        {
            "form": form,
            "appointment": appointment,
            "today": date.today().isoformat(),
            "service_data": {
                str(service.pk): {
                    "name": service.name,
                    "price": f"{service.price:.0f} ₽",
                }
                for service in Service.objects.filter(is_active=True)
            },
        },
    )


@require_POST
def cancel_appointment_view(request, pk):
    visitor, response = _require_visitor(request)
    if response:
        return response

    appointment = get_object_or_404(Appointment, pk=pk, visitor=visitor, is_active=True)
    appointment.is_active = False
    appointment.save(update_fields=["is_active", "updated_at"])
    messages.success(request, "Запись отменена.")
    return redirect("booking:appointments")


def availability_api_view(request):
    visitor, response = _require_visitor(request)
    if response:
        return JsonResponse({"error": "auth_required"}, status=403)

    service_id = request.GET.get("service")
    barber_id = request.GET.get("barber")
    if not service_id or not barber_id:
        return JsonResponse({"dates": [], "slots": []})

    service = get_object_or_404(Service, pk=service_id, is_active=True)
    barber = get_object_or_404(Barber, pk=barber_id, is_active=True)
    exclude_id = request.GET.get("exclude") or None

    today = timezone.localdate()
    year = int(request.GET.get("year") or today.year)
    month = int(request.GET.get("month") or today.month)
    selected_date = request.GET.get("date")

    dates = get_available_dates(barber, service, year, month, exclude_id)
    slots = []
    if selected_date:
        day = date.fromisoformat(selected_date)
        slots = [slot.__dict__ for slot in get_available_slots(barber, service, day, exclude_id)]

    return JsonResponse({"dates": dates, "slots": slots})
