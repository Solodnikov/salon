from django.urls import path

from . import views


app_name = "booking"

urlpatterns = [
    path("", views.login_view, name="login"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("appointments/", views.appointments_view, name="appointments"),
    path("appointments/new/", views.appointment_form_view, name="appointment_new"),
    path("appointments/<int:pk>/edit/", views.appointment_form_view, name="appointment_edit"),
    path("appointments/<int:pk>/cancel/", views.cancel_appointment_view, name="appointment_cancel"),
    path("api/availability/", views.availability_api_view, name="availability_api"),
]
