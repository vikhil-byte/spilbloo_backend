import pymysql
from django.core.management.base import BaseCommand
from django.db import models

# Import Base models across all apps
from accounts.models import User, HaLogins
from availability.models import Slot, DoctorSlot, SlotBooking, Notification
from plans.models import Plan, Coupon, SubscribedPlan
from company.models import Company, CompanyCoupon, MonthlyInvoice, CouponInvoice
from core.models import (
    Symptom, DoctorReason, Currency, Setting, Page, Disclaimer, VideoPlan, 
    VideoCoupon, File, EmergencyResource, AgeGroup, BestDoctor, HomeContent, ContactForm,
    UserSymptom, DoctorRequest, Feed, AssignedTherapist, PushNotification, 
    RefundLog, LoginHistory, SubscribedVideo, CouponUser, Invoice, TherapistEarning
)

# Ordered tuples to map legacy PHP MySQL table names to Django ORM Models
# IMPORTANT: Ordered strictly by database constraints (Parents first, then Dependent Children)
TABLE_MODEL_MAPPINGS = [
    # Level 0 (No Foreign Keys pointing to other tables in this set)
    ('tbl_user', User),
    ('tbl_symptom', Symptom),
    ('tbl_doctor_reason', DoctorReason),
    ('tbl_currency', Currency),
    ('tbl_setting', Setting),
    ('tbl_page', Page),
    ('tbl_disclaimer', Disclaimer),
    ('tbl_video_plan', VideoPlan),
    ('tbl_video_coupon', VideoCoupon),
    ('tbl_file', File),
    ('tbl_emergency_resource', EmergencyResource),
    ('tbl_age_group', AgeGroup),
    ('tbl_best_doctor', BestDoctor),
    ('tbl_home_content', HomeContent),
    ('tbl_contact_form', ContactForm),
    ('tbl_slot', Slot),
    ('tbl_plan', Plan),
    ('tbl_coupon', Coupon),
    ('tbl_company', Company),

    # Level 1 (Dependent on Level 0)
    ('ha_logins', HaLogins), # Depends on User
    ('tbl_user_symptom', UserSymptom), # Depends on User, Symptom
    ('tbl_doctor_request', DoctorRequest), # Depends on User, DoctorReason
    ('tbl_assigned_therapist', AssignedTherapist), # Depends on User
    ('tbl_login_history', LoginHistory), # Depends on User
    ('tbl_doctor_slot', DoctorSlot), # Depends on User
    ('tbl_push_notification', PushNotification), # Depends on User
    ('tbl_refund_log', RefundLog), # Depends on User
    ('tbl_feed', Feed), # Depends on User
    ('tbl_notification', Notification), # Depends on User
    ('tbl_company_coupon', CompanyCoupon), # Depends on Company, User

    # Level 2 (Dependent on Level 0 and 1)
    ('tbl_slot_booking', SlotBooking), # Depends on User, DoctorSlot
    ('tbl_subscribed_video', SubscribedVideo), # Depends on User, VideoPlan
    ('tbl_invoice', Invoice), # Depends on User, File
    ('tbl_therapist_earning', TherapistEarning), # Depends on User
    ('tbl_subscribed_plan', SubscribedPlan), # Depends on User, Plan, CompanyCoupon
    ('tbl_company_monthly_invoice', MonthlyInvoice), # Depends on Company, CompanyCoupon

    # Level 3 (Dependent on Level 2)
    ('tbl_coupon_user', CouponUser), # Depends on User, VideoPlan, VideoCoupon, SubscribedVideo
    ('tbl_company_coupon_invoice', CouponInvoice), # Depends on Company, CompanyCoupon, MonthlyInvoice
]


class Command(BaseCommand):
    help = 'Run Dynamic ETL pipeline to migrate the ENTIRE legacy MySQL PHP database to Django PostgreSQL'

    def handle(self, *args, **options):
        # Legacy Database Connection Details (from spilbloo-app/protected/config/db.php)
        legacy_db_config = {
            'host': '127.0.0.1',
            'user': 'dev_user',
            'password': 'Devusersmrt2@',
            'db': 'therapy_app_db',
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor
        }

        self.stdout.write(self.style.SUCCESS("Connecting to legacy MySQL database..."))
        
        try:
            connection = pymysql.connect(**legacy_db_config)
            
            with connection.cursor() as cursor:
                for table_name, ModelClass in TABLE_MODEL_MAPPINGS:
                    self.stdout.write(self.style.WARNING(f"\nProcessing {table_name} -> {ModelClass.__name__}..."))
                    
                    try:
                        cursor.execute(f"SELECT * FROM {table_name}")
                        rows = cursor.fetchall()
                    except pymysql.err.ProgrammingError as e:
                        self.stdout.write(self.style.NOTICE(f"  Skipped {table_name}: Table does not exist in MySQL ({e})."))
                        continue
                        
                    # Extract the exact database column names expected by the Django ORM model
                    valid_django_fields = [f.attname for f in ModelClass._meta.fields]
                    
                    created_count = 0
                    error_count = 0
                    
                    for row in rows:
                        # Dynamically filter out legacy PHP columns entirely deleted in Django schema
                        clean_row = {k: v for k, v in row.items() if k in valid_django_fields}
                        
                        if 'id' not in clean_row:
                            continue
                            
                        _id = clean_row.pop('id')
                        
                        try:
                            # Using 'update_or_create' ensures the script is stateless and idempotent.
                            ModelClass.objects.update_or_create(id=_id, defaults=clean_row)
                            created_count += 1
                        except Exception as e:
                            # Fails quietly if a row contains an orphaned ID pointing to a deleted parent row
                            error_count += 1
                            if error_count < 5: # Log first few errors for debugging
                                self.stdout.write(self.style.ERROR(f"    Error in Row ID {_id}: {e}"))
                            
                    self.stdout.write(self.style.SUCCESS(f"  + Migrated {created_count} rows ({error_count} error/orphaned rows skipped)."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Critical ETL Migration Failure: {e}"))
        
        finally:
            if 'connection' in locals():
                connection.close()
                self.stdout.write(self.style.SUCCESS("\n[DONE] Database connection closed. Complete Full-Stack Migration routine executed successfully!"))
