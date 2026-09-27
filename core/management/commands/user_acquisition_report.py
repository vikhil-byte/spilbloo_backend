from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta

from accounts.models import User
from core.models import ApiAccessToken
from plans.models import SubscribedPlan

class Command(BaseCommand):
    help = "Generates an acquisition and subscription source report broken down by device (iOS, Android, Web)."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== SPILBLOO USER ACQUISITION & SUBSCRIBER REPORT ==="))

        total_users = User.objects.count()
        total_patients = User.objects.filter(role_id=User.ROLE_PATIENT).count()
        total_tokens = ApiAccessToken.objects.count()
        total_subs = SubscribedPlan.objects.count()
        active_subs = SubscribedPlan.objects.filter(state_id=SubscribedPlan.STATE_ACTIVE).count()

        self.stdout.write(f"Total Users Registered: {total_users} (Patients: {total_patients})")
        self.stdout.write(f"Total Mobile API Tokens: {total_tokens}")
        self.stdout.write(f"Total Subscriptions Created: {total_subs} (Active Now: {active_subs})\n")

        # 1. Device Breakdown from ApiAccessToken
        self.stdout.write(self.style.SUCCESS("--- 1. Mobile App Signups/Logins by Platform ---"))
        token_breakdown = ApiAccessToken.objects.values('device_type').annotate(count=Count('id')).order_by('-count')

        ios_users = set()
        android_users = set()

        for row in token_breakdown:
            dtype = str(row['device_type']).strip()
            if dtype == '1':
                label = 'Android (App)'
                u_ids = ApiAccessToken.objects.filter(device_type='1').values_list('created_by_id', flat=True)
                android_users.update(filter(None, u_ids))
            elif dtype == '2':
                label = 'iOS (Apple App)'
                u_ids = ApiAccessToken.objects.filter(device_type='2').values_list('created_by_id', flat=True)
                ios_users.update(filter(None, u_ids))
            else:
                label = f'Other / Web ({dtype or "empty"})'

            self.stdout.write(f"  • {label.ljust(20)}: {row['count']} active tokens")

        all_mobile_user_ids = ios_users.union(android_users)
        web_only_count = total_patients - len(all_mobile_user_ids)

        self.stdout.write(self.style.SUCCESS("\n--- 2. Unique Patients by Primary Platform ---"))
        self.stdout.write(f"  • Android App Users   : {len(android_users)}")
        self.stdout.write(f"  • iOS App Users       : {len(ios_users)}")
        self.stdout.write(f"  • Web / Unlinked      : {max(0, web_only_count)}")

        # 2. Subscriptions Breakdown by Platform
        self.stdout.write(self.style.SUCCESS("\n--- 3. Subscriptions Breakdown by Platform ---"))
        subs_by_ios = SubscribedPlan.objects.filter(created_by_id__in=ios_users).count()
        subs_by_android = SubscribedPlan.objects.filter(created_by_id__in=android_users).count()
        subs_by_web = total_subs - (subs_by_ios + subs_by_android)

        active_ios = SubscribedPlan.objects.filter(created_by_id__in=ios_users, state_id=SubscribedPlan.STATE_ACTIVE).count()
        active_android = SubscribedPlan.objects.filter(created_by_id__in=android_users, state_id=SubscribedPlan.STATE_ACTIVE).count()
        active_web = active_subs - (active_ios + active_android)

        self.stdout.write(f"  • iOS Subscribers     : {subs_by_ios} total ({active_ios} active)")
        self.stdout.write(f"  • Android Subscribers : {subs_by_android} total ({active_android} active)")
        self.stdout.write(f"  • Web Subscribers     : {max(0, subs_by_web)} total ({max(0, active_web)} active)")

        # 3. Top Device Hardware Models
        self.stdout.write(self.style.SUCCESS("\n--- 4. Top Device Models Logged ---"))
        models_qs = ApiAccessToken.objects.exclude(device_name__isnull=True).exclude(device_name='').values('device_name').annotate(total=Count('id')).order_by('-total')[:8]
        for m in models_qs:
            self.stdout.write(f"  • {m['device_name'].ljust(30)}: {m['total']} devices")

        # 4. Recent 10 Subscriptions with Device Association
        self.stdout.write(self.style.SUCCESS("\n--- 5. Recent 10 Subscriptions & Source ---"))
        recent_subs = SubscribedPlan.objects.select_related('created_by', 'plan').order_by('-id')[:10]
        for s in recent_subs:
            u = s.created_by
            tokens = ApiAccessToken.objects.filter(created_by=u).order_by('-id')
            if tokens.exists():
                first_tok = tokens.first()
                dev_str = "Android" if str(first_tok.device_type) == "1" else ("iOS" if str(first_tok.device_type) == "2" else first_tok.device_type)
                dev_label = f"{dev_str} ({first_tok.device_name or 'device'})"
            else:
                dev_label = "Web / Portal"

            plan_name = s.plan.title if s.plan else "Custom/Direct"
            user_id_str = u.email or u.contact_no or f"User #{u.id}"
            status_str = "Active" if s.state_id == SubscribedPlan.STATE_ACTIVE else f"State {s.state_id}"
            self.stdout.write(f"  [Sub #{s.id}] {user_id_str.ljust(25)} | {plan_name.ljust(28)} | {dev_label.ljust(22)} | {status_str}")

        self.stdout.write("\n=======================================================\n")
