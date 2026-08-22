import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .constants import HOLD_TTL_MINUTES
from .models import DiscoveryBooking

logger = logging.getLogger(__name__)


@shared_task
def expire_stale_discovery_bookings():
    """Cancel abandoned Discover payment holds (state=CREATED) so the slot frees up for other patients."""
    cutoff = timezone.now() - timedelta(minutes=HOLD_TTL_MINUTES)
    updated = DiscoveryBooking.objects.filter(
        state_id=DiscoveryBooking.STATE_CREATED, created_on__lt=cutoff,
    ).update(state_id=DiscoveryBooking.STATE_CANCELED, cancel_reason="Payment hold expired")
    if updated:
        logger.info("[Discover] expired %d stale discovery booking(s)", updated)
