"""
Verification script — checks all PHP↔Django parity changes are reflected in code + DB.

Usage:
    docker compose exec web python manage.py check_parity
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Verify all PHP parity changes are reflected in models, serializers, views, and DB schema."

    def handle(self, *args, **options):
        passed = 0
        failed = 0

        def check(label, condition):
            nonlocal passed, failed
            if condition:
                self.stdout.write(self.style.SUCCESS(f"  ✅ {label}"))
                passed += 1
            else:
                self.stdout.write(self.style.ERROR(f"  ❌ {label}"))
                failed += 1

        self.stdout.write(self.style.WARNING("\n═══ 1. PLANS.MODEL — Plan ═══"))
        from plans.models import Plan
        plan_fields = {f.name for f in Plan._meta.get_fields()}
        for f in ["weekly_price", "image_file", "tax_percentage"]:
            check(f"Plan.{f} exists", f in plan_fields)

        self.stdout.write(self.style.WARNING("\n═══ 2. PLANS.MODEL — SubscribedPlan ═══"))
        from plans.models import SubscribedPlan
        sp_fields = {f.name for f in SubscribedPlan._meta.get_fields()}
        for f in [
            "no_of_video_session", "is_doctor_changed", "doctor_price",
            "company_coupon_type", "upcoming_plan_video_credit", "incentive_days",
            "value", "rezorpay_start_time", "start_at", "end_at",
            "trail_end_time", "signature", "zipcode",
        ]:
            check(f"SubscribedPlan.{f} exists", f in sp_fields)

        self.stdout.write(self.style.WARNING("\n═══ 3. PLANS.MODEL — Coupon ═══"))
        from plans.models import Coupon
        coupon_fields = {f.name for f in Coupon._meta.get_fields()}
        for f in ["description", "created_on", "created_by"]:
            check(f"Coupon.{f} exists", f in coupon_fields)

        self.stdout.write(self.style.WARNING("\n═══ 4. PLANS.MODEL — WebhookLog ═══"))
        from plans.models import WebhookLog
        check("WebhookLog db_table = tbl_subscription_event_log",
              WebhookLog._meta.db_table == "tbl_subscription_event_log")
        wl_fields = {f.name for f in WebhookLog._meta.get_fields()}
        check("WebhookLog.type_id exists", "type_id" in wl_fields)

        self.stdout.write(self.style.WARNING("\n═══ 5. AVAILABILITY.MODEL — SlotBooking ═══"))
        from availability.models import SlotBooking
        sb_fields = {f.name for f in SlotBooking._meta.get_fields()}
        for f in ["date", "description", "call_duration", "duration_millisec", "old_date"]:
            check(f"SlotBooking.{f} exists", f in sb_fields)

        self.stdout.write(self.style.WARNING("\n═══ 6. AVAILABILITY.MODEL — Slot ═══"))
        from availability.models import Slot
        slot_fields = {f.name for f in Slot._meta.get_fields()}
        for f in ["slot_gap_time", "type_id", "created_on", "created_by"]:
            check(f"Slot.{f} exists", f in slot_fields)

        self.stdout.write(self.style.WARNING("\n═══ 7. AVAILABILITY.MODEL — DoctorSlot ═══"))
        from availability.models import DoctorSlot
        ds_fields = {f.name for f in DoctorSlot._meta.get_fields()}
        for f in ["availability_doctor_id", "type_id"]:
            check(f"DoctorSlot.{f} exists", f in ds_fields)

        self.stdout.write(self.style.WARNING("\n═══ 8. AVAILABILITY.MODEL — Notification ═══"))
        from availability.models import Notification
        notif_fields = {f.name for f in Notification._meta.get_fields()}
        for f in ["description", "model_id", "state_id", "type_id"]:
            check(f"Notification.{f} exists", f in notif_fields)
        check("Notification.html removed (legacy field gone)", "html" not in notif_fields)

        self.stdout.write(self.style.WARNING("\n═══ 9. CALLS.MODEL — Call ═══"))
        from calls.models import Call
        call_fields = {f.name for f in Call._meta.get_fields()}
        for f in ["call_end_id", "token", "type_id"]:
            check(f"Call.{f} exists", f in call_fields)

        self.stdout.write(self.style.WARNING("\n═══ 10. CORE.MODEL — NodeSubscriptionPlan conflict ═══"))
        from core.models import NodeSubscriptionPlan
        check("NodeSubscriptionPlan.managed = False",
              NodeSubscriptionPlan._meta.managed is False)

        self.stdout.write(self.style.WARNING("\n═══ 11. SERIALIZER — SlotBookingSerializer hardcodes fixed ═══"))
        import inspect
        from availability.serializers import SlotBookingSerializer
        src = inspect.getsource(SlotBookingSerializer)

        is_call_end_src = inspect.getsource(SlotBookingSerializer.get_is_call_end)
        check("get_is_call_end reads DB (not 'return False')",
              "return False" not in is_call_end_src and "getattr" in is_call_end_src)

        dur_ms_src = inspect.getsource(SlotBookingSerializer.get_duration_millisec)
        check("get_duration_millisec reads DB (not 'return \"\"')",
              'return ""' not in dur_ms_src and "getattr" in dur_ms_src)

        self.stdout.write(self.style.WARNING("\n═══ 12. CALLS.VIEWS — CompleteBookingView fixes ═══"))
        from calls.views import CompleteBookingView, IsDoctor
        view_src = inspect.getsource(CompleteBookingView)

        check("IsDoctor permission class exists", IsDoctor is not None)
        check("CompleteBookingView uses IsDoctor",
              "IsDoctor" in str(CompleteBookingView.permission_classes))
        check("Response serializes SlotBookingSerializer (not CallSerializer)",
              "SlotBookingSerializer" in view_src and "CallSerializer(call).data" not in view_src)
        check("Notification includes doctor name",
              "doctor_name" in view_src and "Your booking with" in view_src)
        check("send_push_notification called",
              "send_push_notification" in view_src)
        check("Does NOT set is_call_end on booking",
              "booking.is_call_end = 1" not in view_src)
        check("Does NOT set call_duration on booking",
              "booking.call_duration = duration" not in view_src)
        check("Success message has no trailing period",
              '"Booking completed successfully."' not in view_src and
              '"Booking completed successfully"' in view_src)

        self.stdout.write(self.style.WARNING("\n═══ 13. SETTINGS — float default fix ═══"))
        from django.conf import settings as dj_settings
        check("ANDROID_APP_VERSION is a float (not crashing)",
              isinstance(dj_settings.ANDROID_APP_VERSION, float))
        check("IOS_APP_VERSION is a float (not crashing)",
              isinstance(dj_settings.IOS_APP_VERSION, float))

        self.stdout.write(self.style.WARNING("\n═══ 14. DATABASE — columns exist in live Postgres ═══"))
        db_checks = [
            ("tbl_plan", "weekly_price"),
            ("tbl_plan", "image_file"),
            ("tbl_plan", "tax_percentage"),
            ("tbl_subscribed_plan", "no_of_video_session"),
            ("tbl_subscribed_plan", "is_doctor_changed"),
            ("tbl_subscribed_plan", "doctor_price"),
            ("tbl_subscribed_plan", "upcoming_plan_video_credit"),
            ("tbl_subscribed_plan", "incentive_days"),
            ("tbl_subscribed_plan", "value"),
            ("tbl_subscribed_plan", "start_at"),
            ("tbl_subscribed_plan", "end_at"),
            ("tbl_subscribed_plan", "trail_end_time"),
            ("tbl_subscribed_plan", "signature"),
            ("tbl_subscribed_plan", "zipcode"),
            ("tbl_slot_booking", "date"),
            ("tbl_slot_booking", "description"),
            ("tbl_slot_booking", "call_duration"),
            ("tbl_slot_booking", "duration_millisec"),
            ("tbl_slot_booking", "old_date"),
            ("tbl_notification", "description"),
            ("tbl_notification", "model_id"),
            ("tbl_notification", "state_id"),
            ("tbl_notification", "type_id"),
            ("tbl_call", "call_end_id"),
            ("tbl_call", "token"),
            ("tbl_call", "type_id"),
        ]
        with connection.cursor() as cursor:
            for table, column in db_checks:
                try:
                    cursor.execute(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = %s AND column_name = %s",
                        [table, column],
                    )
                    row = cursor.fetchone()
                    check(f"DB: {table}.{column}", row is not None)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ❌ DB query failed for {table}.{column}: {e}"))
                    failed += 1

            # Check tbl_subscription_event_log table exists (WebhookLog target)
            cursor.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_name = %s",
                ["tbl_subscription_event_log"],
            )
            check("DB: tbl_subscription_event_log table exists", cursor.fetchone() is not None)

            # Check tbl_notification no longer has 'html' (shouldn't — we removed it from model)
            cursor.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = %s AND column_name = %s",
                ["tbl_notification", "html"],
            )
            check("DB: tbl_notification.html removed", cursor.fetchone() is None)

        self.stdout.write(self.style.WARNING("\n═══ 15. MIGRATIONS — applied ═══"))
        from django.db.migrations.recorder import MigrationRecorder
        recorder = MigrationRecorder(connection)
        applied = recorder.applied_migrations()
        for mig in [
            ("plans", "0008_add_missing_plan_fields"),
            ("availability", "0007_add_missing_fields"),
            ("calls", "0002_add_missing_fields"),
            ("core", "0021_nodesubscriptionplan_unmanaged"),
        ]:
            check(f"Migration {mig[0]}.{mig[1]} applied", mig in applied)

        # ── Summary ──
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("═" * 60))
        if failed == 0:
            self.stdout.write(self.style.SUCCESS(
                f"  ALL {passed} CHECKS PASSED — parity is fully reflected ✅"
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f"  {passed} passed, {failed} FAILED — review failures above ❌"
            ))
        self.stdout.write(self.style.WARNING("═" * 60))
