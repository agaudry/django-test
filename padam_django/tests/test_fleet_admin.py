from datetime import timedelta
from django.utils import timezone
from django.test import TestCase, RequestFactory
from django.contrib.admin.sites import AdminSite
from padam_django.apps.fleet.admin import (
    BusShiftAdmin,
)
from padam_django.apps.fleet.models import Bus, Driver, BusShift, BusStop
from padam_django.apps.geography.models import Place
from padam_django.apps.users.models import User


class BusStopFormSetTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin_user = User.objects.create_superuser(
            username="admin", password="password"
        )
        self.bus = Bus.objects.create(licence_plate="ABC123")
        self.user = User.objects.create_user(username="driver1", password="password")
        self.driver = Driver.objects.create(user=self.user)
        self.user2 = User.objects.create_user(username="driver2", password="password")
        self.driver2 = Driver.objects.create(user=self.user2)

        self.place1 = Place.objects.create(
            name="Place 1", latitude=48.8566, longitude=2.3522
        )
        self.place2 = Place.objects.create(
            name="Place 2", latitude=48.8606, longitude=2.3376
        )
        self.place3 = Place.objects.create(
            name="Place 3", latitude=48.8738, longitude=2.2950
        )

    def _get_formset(self, bus_shift):
        site = AdminSite()
        admin = BusShiftAdmin(BusShift, site)
        request = self.factory.get("/")
        request.user = self.admin_user
        inline_instance = admin.inlines[0](admin.model, site)
        return inline_instance.get_formset(request, obj=bus_shift)

    def _create_existing_shift(self, start_time, end_time):
        bus_shift = BusShift.objects.create(bus=self.bus, driver=self.driver)
        BusStop.objects.create(
            bus_shift=bus_shift,
            place=self.place1,
            time=start_time,
        )
        BusStop.objects.create(
            bus_shift=bus_shift,
            place=self.place2,
            time=end_time,
        )
        return bus_shift

    def _make_formset_data(self, bus_shift, stops):
        """Helper to create formset data

        Args:
            bus_shift: The BusShift instance
            stops: List of (place, time) tuples
        """
        data = {
            "stops-TOTAL_FORMS": str(len(stops)),
            "stops-INITIAL_FORMS": "0",
            "stops-MIN_NUM_FORMS": "0",
            "stops-MAX_NUM_FORMS": "1000",
        }

        for i, (place, time) in enumerate(stops):
            data.update(
                {
                    f"stops-{i}-place": place.pk,
                    f"stops-{i}-time_0": time.strftime("%Y-%m-%d"),
                    f"stops-{i}-time_1": time.strftime("%H:%M:%S"),
                    f"stops-{i}-id": "",
                    f"stops-{i}-bus_shift": bus_shift.pk,
                }
            )

        return data

    def test_bus_shift_creation_success(self):
        """Test creating a valid BusShift with 2 BusStops"""
        bus_shift = BusShift.objects.create(bus=self.bus, driver=self.driver)
        FormSet = self._get_formset(bus_shift)

        now = timezone.now()
        formset_data = self._make_formset_data(
            bus_shift, [(self.place1, now), (self.place2, now + timedelta(hours=2))]
        )

        formset = FormSet(data=formset_data, instance=bus_shift)
        self.assertTrue(
            formset.is_valid(),
            f"Errors: {formset.errors}, Non-form errors: {formset.non_form_errors()}",
        )
        formset.save()
        self.assertEqual(BusStop.objects.count(), 2)

    def test_bus_shift_creation_failure_because_only_one_stop(self):
        """Test creating a BusShift with only 1 BusStop fails"""
        bus_shift = BusShift.objects.create(bus=self.bus, driver=self.driver)
        FormSet = self._get_formset(bus_shift)

        now = timezone.now()
        formset_data = self._make_formset_data(bus_shift, [(self.place1, now)])

        formset = FormSet(data=formset_data, instance=bus_shift)
        self.assertFalse(formset.is_valid())
        self.assertIn(
            "A bus shift must have at least two valid stops.",
            formset.non_form_errors(),
        )

    def test_bus_shift_creation_failure_because_no_stops(self):
        """Test creating a BusShift with no BusStops fails"""
        bus_shift = BusShift.objects.create(bus=self.bus, driver=self.driver)
        FormSet = self._get_formset(bus_shift)

        formset_data = self._make_formset_data(bus_shift, [])

        formset = FormSet(data=formset_data, instance=bus_shift)
        self.assertFalse(formset.is_valid())
        self.assertIn(
            "A bus shift must have at least two valid stops.",
            formset.non_form_errors(),
        )

    def test_bus_shift_creation_failure_because_duplicate_stops(self):
        """Test creating a BusShift with duplicate BusStops fails"""
        bus_shift = BusShift.objects.create(bus=self.bus, driver=self.driver)
        FormSet = self._get_formset(bus_shift)

        now = timezone.now()
        formset_data = self._make_formset_data(
            bus_shift, [(self.place1, now), (self.place1, now)]
        )

        formset = FormSet(data=formset_data, instance=bus_shift)
        self.assertFalse(formset.is_valid())
        self.assertIn(
            "Please correct the duplicate data for place and time, which must be unique.",
            formset.non_form_errors(),
        )

    def test_bus_shift_creation_success_two_shifts_for_driver_and_bus_no_overlap(self):
        """Test creating two BusShifts for the same driver and bus with no overlapping times"""
        # Define the non-overlapping shift times
        existing_shift_start = timezone.now()
        existing_shift_end = existing_shift_start + timedelta(hours=1)

        new_shift_start = existing_shift_start + timedelta(hours=2)
        new_shift_end = new_shift_start + timedelta(hours=3)

        # Create the first bus shift
        self._create_existing_shift(existing_shift_start, existing_shift_end)

        # Create the second bus shift with non-overlapping times
        second_shift = BusShift.objects.create(bus=self.bus, driver=self.driver)
        FormSet = self._get_formset(second_shift)

        formset_data = self._make_formset_data(
            second_shift, [(self.place2, new_shift_start), (self.place3, new_shift_end)]
        )

        formset = FormSet(data=formset_data, instance=second_shift)
        self.assertTrue(
            formset.is_valid(),
            f"Errors: {formset.errors}, Non-form errors: {formset.non_form_errors()}",
        )
        formset.save()
        self.assertEqual(BusStop.objects.filter(bus_shift=second_shift).count(), 2)

    def test_bus_shift_creation_failure_because_overlapping_shift_both_bus_and_driver(
        self,
    ):
        """Test creating a BusShift that overlaps with an existing shift as follows:

        Existing shift: |==========|
        New shift:           |===============|
        """
        # Define the overlapping shift times
        existing_shift_start = timezone.now()
        existing_shift_end = existing_shift_start + timedelta(hours=2)

        new_shift_start = existing_shift_start + timedelta(hours=1)
        new_shift_end = new_shift_start + timedelta(days=2)

        # Create a pre-existing bus shift in DB
        self._create_existing_shift(existing_shift_start, existing_shift_end)

        # Create a new bus shift that will overlap
        new_shift = BusShift.objects.create(bus=self.bus, driver=self.driver)
        FormSet = self._get_formset(new_shift)

        formset_data = self._make_formset_data(
            new_shift, [(self.place2, new_shift_start), (self.place3, new_shift_end)]
        )

        formset = FormSet(data=formset_data, instance=new_shift)
        self.assertFalse(formset.is_valid())
        self.assertIn(
            "This bus already has a conflicting shift.",
            formset.non_form_errors(),
        )

    def test_bus_shift_creation_failure_because_overlapping_shift_driver_only(self):
        """Test creating a BusShift that overlaps with an existing shift for driver only

        Existing shift: |==================|
        New shift:          |=======|
        """
        # Define the overlapping shift times
        existing_shift_start = timezone.now()
        existing_shift_end = existing_shift_start + timedelta(days=4)

        new_shift_start = existing_shift_start + timedelta(hours=1)
        new_shift_end = existing_shift_start + timedelta(hours=3)

        # Create a pre-existing bus shift in DB
        self._create_existing_shift(existing_shift_start, existing_shift_end)

        # Create a new bus shift that will overlap
        new_bus = Bus.objects.create(licence_plate="DEF456")
        new_shift = BusShift.objects.create(bus=new_bus, driver=self.driver)
        FormSet = self._get_formset(new_shift)

        formset_data = self._make_formset_data(
            new_shift, [(self.place2, new_shift_start), (self.place3, new_shift_end)]
        )

        formset = FormSet(data=formset_data, instance=new_shift)
        self.assertFalse(formset.is_valid())
        self.assertIn(
            "This driver already has a conflicting shift.",
            formset.non_form_errors(),
        )

    def test_bus_shift_creation_failure_because_overlapping_shift_bus_only(self):
        """Test creating a BusShift that overlaps with an existing shift for bus only

        Existing shift:     |=======|
        New shift:      |==================|
        """
        # Define the overlapping shift times
        existing_shift_start = timezone.now() + timedelta(hours=1)
        existing_shift_end = existing_shift_start + timedelta(hours=2)

        new_shift_start = timezone.now()
        new_shift_end = new_shift_start + timedelta(hours=4)

        # Create a pre-existing bus shift in DB
        self._create_existing_shift(existing_shift_start, existing_shift_end)

        # Create a new bus shift that will overlap
        new_shift = BusShift.objects.create(bus=self.bus, driver=self.driver2)
        FormSet = self._get_formset(new_shift)

        formset_data = self._make_formset_data(
            new_shift, [(self.place2, new_shift_start), (self.place3, new_shift_end)]
        )

        formset = FormSet(data=formset_data, instance=new_shift)
        self.assertFalse(formset.is_valid())
        self.assertIn(
            "This bus already has a conflicting shift.",
            formset.non_form_errors(),
        )

    def test_bus_shift_creation_failure_because_back_to_back_shift(self):
        """Test creating a BusShift that overlaps with an existing shift with
        an end time identical to the new shift's start time

        Existing shift: |=======|
        New shift:              |=======|
        """
        # Define the overlapping shift times
        existing_shift_start = timezone.now()
        existing_shift_end = existing_shift_start + timedelta(hours=2)

        new_shift_start = existing_shift_end
        new_shift_end = existing_shift_end + timedelta(hours=2)

        # Create a pre-existing bus shift in DB
        self._create_existing_shift(existing_shift_start, existing_shift_end)

        # Create a new bus shift that will overlap
        new_shift = BusShift.objects.create(bus=self.bus, driver=self.driver2)
        FormSet = self._get_formset(new_shift)

        formset_data = self._make_formset_data(
            new_shift, [(self.place2, new_shift_start), (self.place3, new_shift_end)]
        )

        formset = FormSet(data=formset_data, instance=new_shift)
        self.assertFalse(formset.is_valid())
        self.assertIn(
            "This bus already has a conflicting shift.",
            formset.non_form_errors(),
        )

    def test_bus_shift_creation_failure_because_identical_start_and_end(self):
        """Test creating a BusShift that overlaps with an existing shift with
        exactly the same start and end times

        Existing shift: |=======|
        New shift:      |=======|
        """
        # Define the overlapping shift times
        existing_shift_start = timezone.now()
        existing_shift_end = existing_shift_start + timedelta(hours=2)

        new_shift_start = existing_shift_start
        new_shift_end = existing_shift_end

        # Create a pre-existing bus shift in DB
        self._create_existing_shift(existing_shift_start, existing_shift_end)

        # Create a new bus shift that will overlap
        new_shift = BusShift.objects.create(bus=self.bus, driver=self.driver2)
        FormSet = self._get_formset(new_shift)

        formset_data = self._make_formset_data(
            new_shift, [(self.place2, new_shift_start), (self.place3, new_shift_end)]
        )

        formset = FormSet(data=formset_data, instance=new_shift)
        self.assertFalse(formset.is_valid())
        self.assertIn(
            "This bus already has a conflicting shift.",
            formset.non_form_errors(),
        )
