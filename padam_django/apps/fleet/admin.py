from django.contrib import admin
from django.db.models import Min, Max
from django.forms import BaseInlineFormSet
from django.core.exceptions import ValidationError

from . import models


@admin.register(models.Bus)
class BusAdmin(admin.ModelAdmin):
    pass


@admin.register(models.Driver)
class DriverAdmin(admin.ModelAdmin):
    pass


class BusStopFormSet(BaseInlineFormSet):
    def _shift_has_overlap(self, shifts, departure_time, arrival_time):
        if self.instance.pk:
            shifts = shifts.exclude(pk=self.instance.pk)
        return (
            shifts.annotate(
                departure=Min("stops__time"),
                arrival=Max("stops__time"),
            )
            .filter(
                departure__lte=arrival_time,
                arrival__gte=departure_time,
            )
            .exists()
        )

    def clean(self):
        super().clean()

        # BusStops are not saved yet, so we have to get times from the forms
        bus_stop_times = [
            form.cleaned_data.get("time")
            for form in self.forms
            if form.cleaned_data.get("time") and not form.cleaned_data.get("DELETE")
        ]

        if len(bus_stop_times) < 2:
            raise ValidationError("A bus shift must have at least two valid stops.")

        departure_time = min(bus_stop_times)
        arrival_time = max(bus_stop_times)

        if self._shift_has_overlap(
            self.instance.bus.shifts, departure_time, arrival_time
        ):
            raise ValidationError("This bus already has a conflicting shift.")
        if self._shift_has_overlap(
            self.instance.driver.shifts, departure_time, arrival_time
        ):
            raise ValidationError("This driver already has a conflicting shift.")


class BusStopInline(admin.TabularInline):
    model = models.BusStop
    formset = BusStopFormSet
    min_num = 2
    extra = 0


@admin.register(models.BusShift)
class BusShiftAdmin(admin.ModelAdmin):
    fields = ["driver", "bus"]
    list_display = ["__str__", "departure", "arrival", "duration"]
    inlines = [BusStopInline]

    @admin.display(description="Departure")
    def departure(self, obj):
        return obj.departure_time

    @admin.display(description="Arrival")
    def arrival(self, obj):
        return obj.arrival_time

    @admin.display(description="Duration")
    def duration(self, obj):
        return obj.duration
