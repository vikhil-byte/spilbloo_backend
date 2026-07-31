from django.contrib import admin
from django import forms
from .models import User, HaLogins

from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm


class CustomUserCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    password_2 = forms.CharField(
        widget=forms.PasswordInput,
        label="Password confirmation",
        help_text="Enter the same password as above, for verification.",
    )

    class Meta:
        model = User
        fields = ("email",)

    def clean_password_2(self):
        password = self.cleaned_data.get("password")
        password_2 = self.cleaned_data.get("password_2")
        if password and password_2 and password != password_2:
            raise forms.ValidationError("Passwords don't match")
        return password_2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    actions = ["reset_user_state"]

    list_display = (
        "id",
        "email",
        "full_name",
        "role_id",
        "state_id",
        "current_subscription",
        "doctor_id",
        "video_credit",
        "is_active",
        "is_staff",
        "otp_verified",
        "date_joined",
    )
    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
        "role_id",
        "state_id",
        "type_id",
        "otp_verified",
        "email_verified",
        "is_available",
        "push_enabled",
        "email_enabled",
    )
    search_fields = (
        "email",
        "full_name",
        "first_name",
        "last_name",
        "contact_no",
        "city",
        "country",
        "activation_key",
        "token",
    )
    ordering = ("-date_joined",)
    readonly_fields = (
        "id",
        "date_joined",
        "last_login",
        "created_on",
        "updated_on",
        "current_subscription",
    )
    filter_horizontal = ("groups", "user_permissions")
    raw_id_fields = ()

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "id",
                    "email",
                    "password",
                )
            },
        ),
        (
            "Personal Info",
            {
                "fields": (
                    "full_name",
                    "first_name",
                    "last_name",
                    "date_of_birth",
                    "gender",
                    "age_group",
                    "about_me",
                    "profile_file",
                    "language",
                    "timezone",
                )
            },
        ),
        (
            "Contact & Location",
            {
                "fields": (
                    "contact_no",
                    "address",
                    "city",
                    "country",
                    "zipcode",
                    "latitude",
                    "longitude",
                )
            },
        ),
        (
            "Role & Status",
            {
                "fields": (
                    "role_id",
                    "state_id",
                    "type_id",
                    "designation",
                    "tos",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Therapist / Doctor",
            {
                "fields": (
                    "qualification",
                    "experience",
                    "sessions_completed",
                    "online",
                    "is_available",
                    "therapist_gender",
                    "doctor_id",
                    "doctor_assigned_time",
                )
            },
        ),
        (
            "Subscription & Credits",
            {
                "fields": (
                    "current_subscription",
                    "video_credit",
                )
            },
        ),
        (
            "Notifications & Consent",
            {
                "fields": (
                    "push_enabled",
                    "email_enabled",
                    "is_consent_accept",
                    "consent_accepted_on",
                )
            },
        ),
        (
            "OTP & Verification",
            {
                "fields": (
                    "otp",
                    "otp_verified",
                    "email_verified",
                )
            },
        ),
        (
            "Auth Tokens",
            {
                "fields": (
                    "token",
                    "activation_key",
                    "login_error_count",
                    "last_password_change",
                )
            },
        ),
        (
            "Activity Dates",
            {
                "fields": (
                    "last_login",
                    "last_visit_time",
                    "last_action_time",
                    "date_joined",
                    "created_on",
                    "updated_on",
                    "created_by_id",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password", "password_2", "full_name", "role_id", "state_id"),
            },
        ),
    )

    @admin.display(description="Subscription Plan")
    def current_subscription(self, obj):
        from plans.models import SubscribedPlan

        sub = SubscribedPlan.objects.filter(created_by=obj).order_by("-id").first()
        if not sub:
            return "No Subscription"
        state_map = {0: "Created", 1: "Active", 2: "Canceled", 3: "Payment Pending"}
        state_str = state_map.get(sub.state_id, f"State {sub.state_id}")
        upcoming_str = " (Auto-Renewal Stopped)" if sub.upcoming_state in [4, 5] else ""
        return f"{sub.plan.title if sub.plan else 'Plan'} - {state_str}{upcoming_str}"

    @admin.action(description="Reset selected user(s) state to fresh (unassign therapist & clear payments)")
    def reset_user_state(self, request, queryset):
        from plans.models import SubscribedPlan
        from core.models import AssignedTherapist, SubscribedVideo, UserSymptom, DoctorRequest

        count = 0
        for user in queryset:
            # 1. Reset user therapist and credit fields
            user.doctor_id = None
            user.doctor_assigned_time = None
            user.video_credit = "0"
            user.save()

            # 2. Clear assigned therapist records
            AssignedTherapist.objects.filter(created_by=user).delete()

            # 3. Clear plan subscriptions & video credits
            SubscribedPlan.objects.filter(created_by=user).delete()
            SubscribedVideo.objects.filter(created_by=user).delete()

            # 4. Clear onboarding symptoms and doctor requests
            UserSymptom.objects.filter(created_by=user).delete()
            DoctorRequest.objects.filter(created_by=user).delete()

            count += 1

        self.message_user(
            request,
            f"Successfully reset state for {count} user(s). Unassigned therapist, cleared plan subscriptions, video credits, and intake requests."
        )


@admin.register(HaLogins)
class HaLoginsAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "user_id_str", "login_provider", "login_provider_identifier", "created_by_id")
    list_filter = ("login_provider",)
    search_fields = ("user_id_str", "login_provider", "login_provider_identifier")
    ordering = ("-id",)

    list_select_related = ("user",)
    raw_id_fields = ("user",)
