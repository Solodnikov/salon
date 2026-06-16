from django import forms

from .models import Barber, Service


class LoginForm(forms.Form):
    name = forms.CharField(label="Имя", max_length=120)
    phone = forms.CharField(label="Телефон", max_length=32)


class AppointmentForm(forms.Form):
    service = forms.ModelChoiceField(
        label="Услуга",
        queryset=Service.objects.filter(is_active=True).order_by("name"),
        empty_label="Выберите услугу",
    )
    barber = forms.ModelChoiceField(
        label="Парикмахер",
        queryset=Barber.objects.filter(is_active=True).order_by("name"),
        empty_label="Выберите парикмахера",
    )
    date = forms.DateField(widget=forms.HiddenInput)
    time = forms.TimeField(widget=forms.HiddenInput)
    comment = forms.CharField(label="Комментарий", required=False, widget=forms.Textarea(attrs={"rows": 3}))
