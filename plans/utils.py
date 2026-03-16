import razorpay
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class RazorpayService:
    def __init__(self):
        self.client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    def verify_payment_signature(self, params):
        """
        Verifies the signature of a Razorpay payment/subscription.
        params dict should contain:
        - razorpay_payment_id
        - razorpay_subscription_id (or razorpay_order_id)
        - razorpay_signature
        """
        try:
            return self.client.utility.verify_payment_signature(params)
        except Exception as e:
            logger.error(f"Razorpay signature verification failed: {str(e)}")
            return False

    def create_subscription(self, plan_id, total_count, quantity=1, customer_notify=1, start_at=None, expire_by=None, addons=None, offer_id=None):
        """
        Creates a subscription in Razorpay.
        """
        data = {
            "plan_id": plan_id,
            "total_count": total_count,
            "quantity": quantity,
            "customer_notify": customer_notify,
        }
        if start_at:
            data["start_at"] = start_at
        if expire_by:
            data["expire_by"] = expire_by
        if addons:
            data["addons"] = addons
        if offer_id:
            data["offer_id"] = offer_id

        try:
            return self.client.subscription.create(data)
        except Exception as e:
            logger.error(f"Razorpay subscription creation failed: {str(e)}")
            raise e

    def create_order(self, amount, currency="INR", receipt=None, notes=None):
        """
        Creates an order for one-time payments (Video Plans).
        """
        data = {
            "amount": int(amount * 100), # Amount in paise
            "currency": currency,
        }
        if receipt:
            data["receipt"] = receipt
        if notes:
            data["notes"] = notes

        try:
            return self.client.order.create(data=data)
        except Exception as e:
            logger.error(f"Razorpay order creation failed: {str(e)}")
            raise e

    def cancel_subscription(self, subscription_id, cancel_at_cycle_end=True):
        """
        Cancels a subscription.
        """
        try:
            return self.client.subscription.cancel(subscription_id, {"cancel_at_cycle_end": 1 if cancel_at_cycle_end else 0})
        except Exception as e:
            logger.error(f"Razorpay subscription cancellation failed: {str(e)}")
            raise e

razorpay_service = RazorpayService()
