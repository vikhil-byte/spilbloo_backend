import logging

import razorpay
from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

razorpay_client = razorpay.Client(auth=(
    getattr(settings, 'RAZORPAY_KEY_ID', ''),
    getattr(settings, 'RAZORPAY_KEY_SECRET', ''),
))


def try_refund_discovery_credit(user):
    """
    If `user` has a paid, unrefunded Discover booking whose 90-day refund
    window hasn't expired, refund the 199 via Razorpay.

    Call this whenever a plan purchase (recurring subscription, one-time
    plan, or video-credit top-up) becomes active. Safe to call on every such
    event — a booking is only ever refunded once, since the lookup filters
    on refunded_at being unset and a successful refund sets it.

    Eligibility is intentionally independent of the booking's own state_id:
    whether the discovery call was completed, no-showed, or is still
    scheduled doesn't matter — this is a purchase-triggered incentive, not a
    service-quality refund. It only requires that a payment actually
    happened and the 90-day window hasn't lapsed.
    """
    from .models import DiscoveryBooking

    if not user or not getattr(user, "id", None):
        return

    with transaction.atomic():
        booking = (
            DiscoveryBooking.objects.select_for_update()
            .filter(
                created_by=user,
                refunded_at__isnull=True,
                refund_eligible_until__gte=timezone.now(),
            )
            .exclude(razorpay_payment_id="")
            .order_by("-id")
            .first()
        )
        if not booking:
            return

        try:
            refund = razorpay_client.payment.refund(
                booking.razorpay_payment_id,
                {"amount": int(booking.amount * 100)},
            )
            booking.state_id = DiscoveryBooking.STATE_REFUNDED
            booking.refund_id = refund.get("id", "") if isinstance(refund, dict) else ""
            booking.refunded_amount = booking.amount
            booking.refunded_at = timezone.now()
            booking.save(update_fields=["state_id", "refund_id", "refunded_amount", "refunded_at"])
            logger.info(
                "[Discover] refunded booking_id=%s user_id=%s refund_id=%s",
                booking.id, user.id, booking.refund_id,
            )
        except Exception:
            logger.exception(
                "[Discover] refund failed booking_id=%s user_id=%s",
                booking.id, user.id,
            )
            booking.state_id = DiscoveryBooking.STATE_REFUND_FAILED
            booking.save(update_fields=["state_id"])
