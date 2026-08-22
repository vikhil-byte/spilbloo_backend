from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL


class DiscoveryBooking(models.Model):
    """
    A discounted (299 -> 199), 15-minute, one-time-per-patient discovery video
    call, paid via Razorpay and assigned to whichever eligible therapist is
    free at the chosen time. Separate from the normal SlotBooking flow so it
    never appears in the regular therapist-booking UI; on payment it also
    creates a real availability.SlotBooking (type_id=TYPE_DISCOVERY) so the
    existing calls app (join/leave/Agora token/complete) works unmodified.
    """

    STATE_CREATED = 0
    STATE_PAID = 1
    STATE_CANCELED = 2
    STATE_COMPLETED = 3
    STATE_REFUNDED = 4
    STATE_REFUND_FAILED = 5

    STATE_CHOICES = (
        (STATE_CREATED, "Created"),
        (STATE_PAID, "Paid"),
        (STATE_CANCELED, "Canceled"),
        (STATE_COMPLETED, "Completed"),
        (STATE_REFUNDED, "Refunded"),
        (STATE_REFUND_FAILED, "Refund Failed"),
    )

    assigned_doctor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='discovery_bookings_as_doctor',
    )
    slot_booking_id = models.IntegerField(null=True, blank=True)

    date = models.DateField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    original_price = models.DecimalField(max_digits=8, decimal_places=2, default=299)
    amount = models.DecimalField(max_digits=8, decimal_places=2, default=199)

    razorpay_order_id = models.CharField(max_length=64, blank=True, default="")
    razorpay_payment_id = models.CharField(max_length=64, blank=True, default="")
    razorpay_signature = models.CharField(max_length=128, blank=True, default="")

    # 90-day window during which this payment is refundable if the patient buys any plan.
    refund_eligible_until = models.DateTimeField(null=True, blank=True)
    refund_id = models.CharField(max_length=64, blank=True, default="")
    refunded_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)

    cancel_reason = models.CharField(max_length=255, blank=True, default="")

    # A no-show still counts as a completed call (no refund) but is flagged
    # separately so support/ops can tell it apart from a call that actually happened.
    is_no_show = models.BooleanField(default=False)

    state_id = models.SmallIntegerField(choices=STATE_CHOICES, default=STATE_CREATED)

    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discovery_bookings')

    class Meta:
        db_table = 'tbl_discovery_booking'

    def __str__(self):
        return f"DiscoveryBooking {self.id} - patient {self.created_by_id}"
