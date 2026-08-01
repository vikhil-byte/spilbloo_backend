import datetime
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from availability.models import SlotBooking
from calls.models import Call

User = get_user_model()


class CallViewsTestCase(APITestCase):
    def setUp(self):
        self.patient = User.objects.create_user(
            email="patient@test.com",
            password="Password123!",
            role_id=User.ROLE_PATIENT,
            full_name="Patient User"
        )
        self.doctor = User.objects.create_user(
            email="doctor@test.com",
            password="Password123!",
            role_id=User.ROLE_DOCTER,
            full_name="Doctor User"
        )
        now = timezone.now()
        self.booking = SlotBooking.objects.create(
            slot_id=1,
            start_time=now,
            end_time=now + datetime.timedelta(hours=1),
            doctor_id=self.doctor.id,
            room_id="room_12345",
            state_id=SlotBooking.STATE_ACCEPT,
            created_by=self.patient
        )

    def test_complete_booking_post(self):
        self.client.force_authenticate(user=self.doctor)
        response = self.client.post(
            f"/api/call/complete-booking/?booking_id={self.booking.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.state_id, SlotBooking.STATE_COMPLETED)

    def test_complete_booking_get(self):
        self.client.force_authenticate(user=self.doctor)
        response = self.client.get(
            f"/api/call/complete-booking/?booking_id={self.booking.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.state_id, SlotBooking.STATE_COMPLETED)

    def test_join_call_get_and_post(self):
        self.client.force_authenticate(user=self.patient)

        # GET join call
        response_get = self.client.get(f"/api/call/join/?booking_id={self.booking.id}")
        self.assertEqual(response_get.status_code, status.HTTP_200_OK)

        # POST join call
        response_post = self.client.post(f"/api/call/join/", {"booking_id": self.booking.id})
        self.assertEqual(response_post.status_code, status.HTTP_200_OK)

    def test_leave_call_get_and_post(self):
        self.client.force_authenticate(user=self.patient)

        # GET leave call
        response_get = self.client.get(
            f"/api/call/leave/?booking_id={self.booking.id}&duration=120"
        )
        self.assertEqual(response_get.status_code, status.HTTP_200_OK)

        # POST leave call
        response_post = self.client.post(
            "/api/call/leave/",
            {"booking_id": self.booking.id, "duration": 180}
        )
        self.assertEqual(response_post.status_code, status.HTTP_200_OK)
