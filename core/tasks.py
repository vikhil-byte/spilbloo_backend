import os
import razorpay
import logging
from datetime import timedelta
from django.utils.timezone import now
from django.db import models
from celery import shared_task

# Django Models
from availability.models import SlotBooking, Notification
from accounts.models import User
from core.models import RefundLog, Notification, PushNotification, TherapistEarning, AssignedTherapist
from plans.models import SubscribedPlan, Coupon
from company.models import Company, CompanyCoupon, MonthlyInvoice, CouponInvoice
from calls.models import Call

logger = logging.getLogger(__name__)

# Initialize Razorpay Client
razorpay_client = None
if os.environ.get("RAZORPAY_KEY_ID") and os.environ.get("RAZORPAY_KEY_SECRET"):
    razorpay_client = razorpay.Client(
        auth=(os.environ.get("RAZORPAY_KEY_ID"), os.environ.get("RAZORPAY_KEY_SECRET"))
    )
else:
    logger.warning("Razorpay keys missing from .env. Payment-related tasks will be skipped or mocked.")

# ==========================================
# BATCH 1: Booking & Call Room Logic
# ==========================================

@shared_task
def send_booking_notification():
    """
    Finds accepted bookings happening in < 5 minutes.
    Activates the call room (is_active=1) and creates Notifications for Patient & Doctor.
    """
    logger.info("Running: send_booking_notification")
    cutoff_time = now() + timedelta(minutes=5)
    
    # STATE_ACCEPT = 3
    bookings = SlotBooking.objects.filter(
        state_id=3, 
        is_active=0, 
        start_time__lte=cutoff_time
    )

    for booking in bookings:
        booking.is_active = 1
        booking.save(update_fields=['is_active'])

        Notification.objects.create(
            to_user_id=booking.created_by_id,
            created_by_id=booking.doctor_id,
            title="Tap here to join",
            model_type="SlotBooking"
        )

        Notification.objects.create(
            to_user_id=booking.doctor_id,
            created_by_id=booking.created_by_id,
            title="Tap here to join",
            model_type="SlotBooking"
        )
        logger.info(f"Notification Sent & Room Opened for booking: {booking.id}")


@shared_task
def inactive_booking_call():
    """
    Finds active rooms where the end time passed 5 mins ago.
    Sets is_call_end = 1 and is_active = 0.
    """
    logger.info("Running: inactive_booking_call")
    cutoff_time = now() - timedelta(minutes=5)
    
    bookings = SlotBooking.objects.filter(
        is_active=1,
        end_time__lte=cutoff_time
    )

    for booking in bookings:
        booking.is_active = 0
        booking.is_call_end = 1
        booking.save()
        logger.info(f"Call room closed for booking: {booking.id}")


@shared_task
def auto_cancel_booking():
    """
    Legacy: SlotBooking::cancelBooking()
    Completes bookings that ended 5 minutes ago if users attended, 
    otherwise cancels them and issues automatic credit refunds.
    """
    logger.info("Running: auto_cancel_booking")
    cutoff_time = now() - timedelta(minutes=5)
    
    bookings = SlotBooking.objects.filter(
        state_id=3, # STATE_ACCEPT
        end_time__lte=cutoff_time
    )

    for booking in bookings:
        patient_call = Call.objects.filter(booking_id=booking.id, created_by_id=booking.created_by_id).first()
        
        if not patient_call:
            booking.state_id = 5 # STATE_COMPLETED
            booking.complete_reason = "User did not attend the video call"
            booking.save(update_fields=['state_id', 'complete_reason'])
        else:
            doctor_call = Call.objects.filter(booking_id=booking.id, created_by_id=booking.doctor_id).first()
            if not doctor_call:
                booking.state_id = 4 # CANCELED
                booking.cancel_reason = "Therapist did not attend the video call"
                booking.is_refunded = 1
                booking.save(update_fields=['state_id', 'cancel_reason', 'is_refunded'])
                
                user = booking.created_by
                if user:
                    user.video_credit = (user.video_credit or 0) + 1
                    user.save(update_fields=['video_credit'])
                
                RefundLog.objects.create(
                    reason="Therapist did not attend the video call",
                    booking_id=booking.id,
                    doctor_id=booking.doctor_id,
                    created_by_id=booking.created_by_id,
                    credit=1
                )
                logger.info(f"Booking {booking.id} Auto-Canceled and credit refunded to Patient {booking.created_by_id}")


@shared_task
def cancel_pending_booking():
    """
    Legacy: SlotBooking::autoCancelBooking()
    Cancels 'Requested' bookings 5 minutes PAST their scheduled start time.
    """
    logger.info("Running: cancel_pending_booking")
    cutoff_time = now() - timedelta(minutes=5)
    
    bookings = SlotBooking.objects.filter(
        state_id=2, # STATE_REQUEST
        start_time__lte=cutoff_time
    )

    for booking in bookings:
        booking.state_id = 4 # CANCELED
        booking.cancel_reason = "Therapist did not respond to the booking request"
        booking.is_refunded = 1
        booking.save(update_fields=['state_id', 'cancel_reason', 'is_refunded'])

        user = booking.created_by
        if user:
            user.video_credit = (user.video_credit or 0) + 1
            user.save(update_fields=['video_credit'])

        RefundLog.objects.create(
            reason="Therapist did not respond to the booking request",
            booking_id=booking.id,
            doctor_id=booking.doctor_id,
            created_by_id=booking.created_by_id,
            credit=1
        )
        logger.info(f"Unanswered Request {booking.id} Auto-Canceled.")


@shared_task
def auto_complete_booking():
    """
    Legacy: SlotBooking::completeBooking()
    Closes bookings exactly 45 minutes past the start/end time safely.
    """
    logger.info("Running: auto_complete_booking")
    cutoff_time = now() - timedelta(minutes=45)
    
    bookings = SlotBooking.objects.filter(
        state_id=3, # ACCEPTED
        end_time__lte=cutoff_time
    )

    for booking in bookings:
        booking.state_id = 5 # STATE_COMPLETED
        booking.complete_reason = "Auto completed after 45 minutes of booking end time."
        booking.save(update_fields=['state_id', 'complete_reason'])
        
        Notification.objects.create(
            to_user_id=booking.created_by_id,
            created_by_id=booking.doctor_id,
            title=f"Your booking completed successfully",
            model_type="SlotBooking"
        )
        logger.info(f"Booking {booking.id} Auto-Completed.")


@shared_task
def booking_reminder():
    """
    Legacy: SlotBooking::bookingReminder()
    Finds bookings exactly 24 hours away and prints console logs instead of email queue.
    """
    logger.info("Running: booking_reminder")
    target_start = now() + timedelta(hours=23, minutes=45)
    target_end = now() + timedelta(hours=24, minutes=15)
    
    bookings = SlotBooking.objects.filter(
        state_id__in=[2, 3], # REQUEST, ACCEPTED
        start_time__gte=target_start,
        start_time__lte=target_end
    )

    for booking in bookings:
        logger.info(f"[EMAIL QUEUE MOCK] Reminder sent to Patient ID {booking.created_by_id} and Doctor ID {booking.doctor_id} for Booking {booking.id}")


# ==========================================
# BATCH 2: Subscription Logic
# ==========================================

@shared_task
def cancel_plans():
    """
    Legacy: User::cancelPlans()
    Cancels subscriptions that reached their end_date and were marked for cancellation.
    """
    logger.info("Running: cancel_plans")
    cutoff_time = now() + timedelta(minutes=5)
    
    plans = SubscribedPlan.objects.filter(
        state_id=1,
        end_date__lte=cutoff_time,
        upcoming_state__in=[4, 5]
    )
    
    for plan in plans:
        plan.state_id = 4
        plan.save(update_fields=['state_id'])
        logger.info(f"Plan {plan.id} cancelled as scheduled.")


@shared_task
def cancel_trial_plans():
    """
    Legacy: User::cancelTrialPlans()
    Cancels trial plans that ended without conversion.
    """
    logger.info("Running: cancel_trial_plans")
    cutoff_time = now() + timedelta(minutes=5)
    
    plans = SubscribedPlan.objects.filter(
        state_id=1,
        upcoming_state=5,
        end_date__lte=cutoff_time
    )
    
    for plan in plans:
        plan.state_id = 4
        plan.cancel_reason = "User free plan period is over"
        plan.save(update_fields=['state_id', 'cancel_reason'])
        logger.info(f"Trial Plan {plan.id} expired and cancelled.")


@shared_task
def cancel_halted_plans():
    """
    Legacy: User::cancelHaltedPlans()
    Communicates with Razorpay to cancel subscriptions where payment is halted.
    """
    logger.info("Running: cancel_halted_plans")
    
    plans = SubscribedPlan.objects.filter(upcoming_state=6)
    
    for plan in plans:
        if razorpay_client and plan.subscription_id:
            try:
                razorpay_client.subscription.cancel(plan.subscription_id, {'cancel_at_cycle_end': 0})
                logger.info(f"Razorpay subscription {plan.subscription_id} cancelled.")
            except Exception as e:
                logger.error(f"Error cancelling Razorpay subscription {plan.subscription_id}: {str(e)}")
        
        plan.state_id = 4
        plan.upcoming_state = 4
        plan.cancel_reason = "Subscription recurring Payment not received in all attempts."
        plan.save(update_fields=['state_id', 'upcoming_state', 'cancel_reason'])
        logger.info(f"Halted Plan {plan.id} marked as cancelled.")


@shared_task
def subscription_reminder():
    """
    Legacy: User::subscriptionReminder()
    Reminds users who registered 48 hours ago to purchase a plan.
    """
    logger.info("Running: subscription_reminder")
    target_time_start = now() - timedelta(hours=48, minutes=15)
    target_time_end = now() - timedelta(hours=47, minutes=45)
    
    users = User.objects.filter(
        is_active=True,
        role_id=3,
        date_joined__gte=target_time_start,
        date_joined__lte=target_time_end
    )
    
    for user in users:
        if not SubscribedPlan.objects.filter(created_by=user).exists():
            logger.info(f"[EMAIL MOCK] Reminder: Purchase a plan sent to {user.email}")


@shared_task
def admin_notifications():
    """
    Legacy: User::sendAdminNotifications()
    Processes pending push notifications sent by Admin.
    """
    logger.info("Running: admin_notifications")
    pending_pushes = PushNotification.objects.filter(state_id=1)
    
    for push in pending_pushes:
        target_user_ids = []
        if push.role_type == 2:
            target_user_ids = User.objects.filter(is_active=True, role_id=2).values_list('id', flat=True)
        elif push.role_type == 1:
            if push.type_id == 1:
                target_user_ids = SubscribedPlan.objects.filter(state_id=1).values_list('created_by_id', flat=True).distinct()
            elif push.type_id == 2:
                all_patients = User.objects.filter(is_active=True, role_id=3).values_list('id', flat=True)
                subscribed = SubscribedPlan.objects.all().values_list('created_by_id', flat=True)
                target_user_ids = list(set(all_patients) - set(subscribed))
            else:
                target_user_ids = User.objects.filter(is_active=True, role_id=3).values_list('id', flat=True)
        elif push.role_type == 3:
            target_user_ids = User.objects.filter(is_active=True).values_list('id', flat=True)

        for uid in target_user_ids:
            Notification.objects.create(
                to_user_id=uid,
                created_by_id=push.created_by_id,
                title=push.title,
                description=push.description,
                model_type="PushNotification"
            )
        
        push.state_id = 2
        push.save(update_fields=['state_id'])
        logger.info(f"Admin Push '{push.title}' sent to {len(set(target_user_ids))} users.")


@shared_task
def cancel_free_plans():
    """
    Legacy: User::cancelFreePlans()
    Cancels free plans that reached their end_date.
    """
    logger.info("Running: cancel_free_plans")
    plans = SubscribedPlan.objects.filter(
        state_id=1,
        plan_type=0,
        end_date__lte=now()
    )
    
    for plan in plans:
        plan.state_id = 4
        plan.cancel_reason = "User free plan period is over"
        plan.save(update_fields=['state_id', 'cancel_reason'])
        logger.info(f"Free Plan {plan.id} expired.")


@shared_task
def expire_one_time_plans():
    """
    Legacy: User::expireOneTimePaymentSubscriptions()
    Cancels one-time payment plans that reached their end_date.
    """
    logger.info("Running: expire_one_time_plans")
    plans = SubscribedPlan.objects.filter(
        state_id=1,
        plan_type=1,
        end_date__lte=now() + timedelta(minutes=5)
    )
    
    for plan in plans:
        plan.state_id = 4
        plan.cancel_reason = "User one time payment subscription period is over"
        plan.save(update_fields=['state_id', 'cancel_reason'])
        logger.info(f"One-Time Plan {plan.id} expired.")


@shared_task
def active_upcoming_plans():
    """
    Legacy: User::activeOneTimePaymentSubscriptions()
    Activates upcoming one-time payment plans that reached their start_date.
    """
    logger.info("Running: active_upcoming_plans")
    plans = SubscribedPlan.objects.filter(
        state_id=2,
        plan_type=1,
        start_date__lte=now() + timedelta(minutes=5)
    )
    
    for plan in plans:
        plan.state_id = 1
        plan.save(update_fields=['state_id'])
        logger.info(f"Upcoming Plan {plan.id} activated.")


@shared_task
def notify_subscribed_user():
    """
    Legacy: User::notifySubscribedUser()
    Notifies subscribed users if they haven't used the app in 72 hours.
    """
    logger.info("Running: notify_subscribed_user")
    cutoff_time = now() - timedelta(hours=72)
    subscribed_ids = SubscribedPlan.objects.filter(state_id=1).values_list('created_by_id', flat=True).distinct()
    
    users = User.objects.filter(
        id__in=subscribed_ids,
        role_id=3,
        last_login__lte=cutoff_time
    )
    
    for user in users:
        latest_booking = SlotBooking.objects.filter(created_by=user).order_by('-start_time').first()
        if latest_booking and latest_booking.doctor:
            doctor_name = latest_booking.doctor.first_name or "Therapist"
            msg = f"{user.first_name or 'User'}, {doctor_name} would like to know how you're doing! Tap here to send them a message."
            
            Notification.objects.create(
                to_user_id=user.id,
                created_by_id=latest_booking.doctor_id,
                title=msg,
                model_type="User"
            )
            logger.info(f"Inactive notification sent to User {user.id}")


# ==========================================
# BATCH 3: Earnings & Invoicing
# ==========================================

@shared_task
def calculate_earning():
    """
    Legacy: User::manageTherapistEarning()
    Calculates daily earnings for therapists based on active patient plans 
    and completed video bookings.
    """
    logger.info("Running: calculate_earning")
    today = now().date()
    
    # ROLE_DOCTER = 2
    therapists = User.objects.filter(is_active=True, role_id=2)
    
    for therapist in therapists:
        assignments = AssignedTherapist.objects.filter(
            therapist=therapist, 
            state_id=1
        )
        
        for assignment in assignments:
            patient = assignment.patient
            if not patient:
                continue
                
            active_plan = SubscribedPlan.objects.filter(
                created_by=patient,
                state_id=1
            ).order_by('-created_on').first()
            
            if active_plan and active_plan.plan:
                doctor_total = float(active_plan.plan.doctor_price or 0)
                duration = active_plan.plan.duration or 30
                daily_payout = doctor_total / duration
                
                TherapistEarning.objects.update_or_create(
                    therapist=therapist,
                    patient=patient,
                    date__date=today,
                    type_id=1,
                    defaults={
                        'amount': str(round(daily_payout, 2)),
                        'date': now(),
                        'state_id': 1
                    }
                )

            bookings = SlotBooking.objects.filter(
                state_id=5,
                doctor_id=therapist.id,
                created_by=patient,
                type_id=2,
                start_time__date=today
            )
            
            booking_count = bookings.count()
            video_payout = booking_count * 700
            
            if booking_count > 0:
                TherapistEarning.objects.update_or_create(
                    therapist=therapist,
                    patient=patient,
                    date__date=today,
                    type_id=2,
                    defaults={
                        'amount': str(video_payout),
                        'date': now(),
                        'completed_booking': booking_count,
                        'state_id': 1
                    }
                )
    logger.info("Daily earnings calculation complete.")


@shared_task
def inactive_company_coupon():
    """
    Legacy: User::inactiveCompanyCoupon()
    Deactivates coupons that reached their valid_till date.
    """
    logger.info("Running: inactive_company_coupon")
    expired_coupons = Coupon.objects.filter(
        state_id=1,
        valid_till__lte=now()
    )
    
    count = expired_coupons.update(state_id=0)
    logger.info(f"{count} coupons deactivated.")

@shared_task
def add_company_invoice():
    """
    Legacy: User::addCompanyInvoice()
    Runs on the 1st of every month to initiate invoice cycles for active corporate coupons.
    """
    logger.info("Running: add_company_invoice")
    if now().day != 1:
        logger.info("Skipping add_company_invoice: Today is not the 1st of the month.")
        return

    # STATE_ACTIVE = 1
    companies = Company.objects.filter(state_id=1)
    
    for company in companies:
        # Coupons that are still valid or ended last month (for final billing)
        today = now()
        last_month = today - timedelta(days=28) # Approximation to get previous month's Y-m
        
        active_coupons = CompanyCoupon.objects.filter(
            company=company,
            state_id=1
        ).filter(
            models.Q(end_date__gt=today) | 
            models.Q(end_date__year=last_month.year, end_date__month=last_month.month)
        )
        
        for coupon in active_coupons:
            year_month = today.strftime('%Y-%m')
            
            # Check if invoice already exists for this month
            if not MonthlyInvoice.objects.filter(
                company=company,
                coupon=coupon,
                date__year=today.year,
                date__month=today.month
            ).exists():
                MonthlyInvoice.objects.create(
                    company=company,
                    coupon=coupon,
                    coupon_code=coupon.code,
                    type_id=coupon.coupon_type,
                    date=today.date(),
                    state_id=0 # STATE_PENDING / INACTIVE
                )
                logger.info(f"Initiated invoice for {company.title} - Coupon: {coupon.code}")

@shared_task
def generate_limited_coupon_invoice():
    """
    Legacy: User::generateLimitedCouponInvoice()
    Processes pending invoices for LIMITED coupons (free trial based).
    Final Price = (sub_count) * (one_day_price * trial_days) + 18% GST.
    """
    logger.info("Running: generate_limited_coupon_invoice")
    
    # type_id: 2 = LIMITED, state_id: 0 = PENDING
    pending_invoices = MonthlyInvoice.objects.filter(type_id=2, state_id=0)
    
    for invoice in pending_invoices:
        coupon = invoice.coupon
        if not coupon:
            continue
            
        # Target last month's subscriptions
        last_month = (invoice.created_on - timedelta(days=28))
        
        # SubscribedPlan search for this coupon in previous month
        sub_count = SubscribedPlan.objects.filter(
            company_coupon=coupon,
            start_date__year=last_month.year,
            start_date__month=last_month.month
        ).count()
        
        one_sub_price = float(coupon.one_day_price) * coupon.no_of_free_trial_days
        total_price = sub_count * one_sub_price
        gst_price = total_price * 0.18
        final_price = total_price + gst_price
        
        CouponInvoice.objects.create(
            company=invoice.company,
            coupon=coupon,
            coupon_code=invoice.coupon_code,
            date=invoice.date,
            type_id=invoice.type_id,
            monthly_invoice=invoice,
            subscription_count=sub_count,
            one_subscription_price=round(one_sub_price, 2),
            total_price=round(total_price, 2),
            gst_price=round(gst_price, 2),
            final_price=round(final_price, 2),
            state_id=1 # ACTIVE
        )
        
        invoice.state_id = 1 # INITIATED
        invoice.save(update_fields=['state_id'])
        logger.info(f"Generated Limited Invoice for {invoice.coupon_code}")

@shared_task
def generate_un_limited_coupon_invoice():
    """
    Legacy: User::generateUnLimitedCouponInvoice()
    Processes pending invoices for UNLIMITED coupons (consumption based).
    Final Price = (total_active_days) * (one_day_price) + 18% GST.
    """
    logger.info("Running: generate_un_limited_coupon_invoice")
    
    # type_id: 1 = UNLIMITED, state_id: 0 = PENDING
    pending_invoices = MonthlyInvoice.objects.filter(type_id=1, state_id=0)
    
    for invoice in pending_invoices:
        coupon = invoice.coupon
        if not coupon:
            continue
            
        last_month = (invoice.created_on - timedelta(days=28))
        
        # Find all subscriptions for this coupon started last month
        subscriptions = SubscribedPlan.objects.filter(
            company_coupon=coupon,
            start_date__year=last_month.year,
            start_date__month=last_month.month
        )
        
        sub_count = subscriptions.count()
        total_days = 0
        
        for sub in subscriptions:
            if sub.start_date and sub.end_date:
                delta = (sub.end_date - sub.start_date).days + 1
                total_days += delta
        
        one_day_price = float(coupon.one_day_price)
        total_price = total_days * one_day_price
        gst_price = total_price * 0.18
        final_price = total_price + gst_price
        
        CouponInvoice.objects.create(
            company=invoice.company,
            coupon=coupon,
            coupon_code=invoice.coupon_code,
            date=invoice.date,
            type_id=invoice.type_id,
            monthly_invoice=invoice,
            subscription_count=sub_count,
            subscription_days=total_days,
            one_subscription_price=round(one_day_price, 2),
            total_price=round(total_price, 2),
            gst_price=round(gst_price, 2),
            final_price=round(final_price, 2),
            state_id=1 # ACTIVE
        )
        
        invoice.state_id = 1 # INITIATED
        invoice.save(update_fields=['state_id'])
        logger.info(f"Generated Unlimited Invoice for {invoice.coupon_code}")
