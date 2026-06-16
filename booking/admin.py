from django.contrib import admin, messages

from .models import (
    Appointment,
    Barber,
    BarberService,
    Service,
    Vacation,
    Visitor,
    WeeklySchedule,
)


class BarberServiceInline(admin.TabularInline):
    model = BarberService
    extra = 1


class WeeklyScheduleInline(admin.TabularInline):
    model = WeeklySchedule
    extra = 0
    max_num = 7


class VacationInline(admin.TabularInline):
    model = Vacation
    extra = 1


@admin.register(Barber)
class BarberAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "user__username", "user__first_name", "user__last_name")
    inlines = [BarberServiceInline, WeeklyScheduleInline, VacationInline]


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "duration_minutes", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "description")


@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "created_at")
    search_fields = ("name", "phone")
    readonly_fields = ("created_at", "updated_at")


@admin.register(WeeklySchedule)
class WeeklyScheduleAdmin(admin.ModelAdmin):
    list_display = ("barber", "weekday", "is_working", "start_time", "end_time")
    list_filter = ("barber", "weekday", "is_working")
    actions = ["apply_hours_to_working_weekdays"]

    @admin.action(description="Применить часы первой выбранной строки ко всем рабочим дням мастера")
    def apply_hours_to_working_weekdays(self, request, queryset):
        source = queryset.order_by("barber_id", "weekday").first()
        if not source:
            return
        updated = WeeklySchedule.objects.filter(
            barber=source.barber,
            is_working=True,
        ).update(start_time=source.start_time, end_time=source.end_time)
        self.message_user(
            request,
            f"Часы {source.start_time} - {source.end_time} применены к {updated} рабочим дням мастера {source.barber}.",
            messages.SUCCESS,
        )


@admin.register(Vacation)
class VacationAdmin(admin.ModelAdmin):
    list_display = ("barber", "start_date", "end_date")
    list_filter = ("barber",)
    date_hierarchy = "start_date"


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("starts_at", "visitor", "barber", "service", "price_snapshot", "is_active")
    list_filter = ("is_active", "barber", "service")
    search_fields = ("visitor__name", "visitor__phone", "barber__name", "service__name")
    date_hierarchy = "starts_at"
    readonly_fields = ("price_snapshot", "duration_minutes_snapshot", "created_at", "updated_at")
