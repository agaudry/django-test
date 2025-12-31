from django.db import models
from padam_django.apps.geography.models import Place

class Driver(models.Model):
    user = models.OneToOneField(
        "users.User", on_delete=models.CASCADE, related_name="driver"
    )

    def __str__(self):
        return f"Driver: {self.user.username} (id: {self.pk})"


class Bus(models.Model):
    licence_plate = models.CharField("Name of the bus", max_length=10)

    class Meta:
        verbose_name_plural = "Buses"

    def __str__(self):
        return f"Bus: {self.licence_plate} (id: {self.pk})"


class BusShift(models.Model):
    driver = models.ForeignKey(Driver, on_delete=models.RESTRICT, related_name="shifts")
    bus = models.ForeignKey(Bus, on_delete=models.RESTRICT, related_name="shifts")

    def __str__(self):
        return f"BusShift: Driver {self.driver.user.username} with bus {self.bus.licence_plate} (id: {self.pk})"

    @property
    def departure_time(self):
        first_stop = self.stops.order_by("time").first()
        return first_stop.time if first_stop else None

    @property
    def arrival_time(self):
        last_stop = self.stops.order_by("time").last()
        return last_stop.time if last_stop else None

    @property
    def duration(self):
        arrival = self.arrival_time
        departure = self.departure_time
        if arrival and departure:
            return arrival - departure
        return None


class BusStop(models.Model):
    place = models.ForeignKey(Place, on_delete=models.RESTRICT, related_name="stops")
    bus_shift = models.ForeignKey(
        BusShift, on_delete=models.CASCADE, related_name="stops"
    )
    time = models.DateTimeField(
        "Scheduled time of arrival at the stop"
    )

    class Meta:
            constraints = [
                models.UniqueConstraint(
                    fields=['place', 'time', 'bus_shift'],
                    name='unique_bus_stop_combination'
                )
            ]

    def __str__(self):
        return f"BusStop: {self.place.name} (id: {self.pk})"
