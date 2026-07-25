from django.contrib import admin
from django import forms
from .models import User, HaLogins

from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

class CustomUserCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    password_2 = forms.CharField(widget=forms.PasswordInput, label="Password confirmation", help_text="Enter the same password as above, for verification.")

    class Meta:
        model = User
        fields = ('email',)

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
        fields = '__all__'

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    
    list_display = ('id', 'email', 'full_name', 'role_id', 'current_subscription', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'role_id', 'state_id')
    search_fields = ('email', 'full_name', 'contact_no')
    ordering = ('-date_joined',)
    readonly_fields = ('date_joined', 'last_login', 'current_subscription')

    # Exposes fields in clean sections, including groups/permissions and superuser checkbox
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'date_of_birth', 'gender', 'contact_no', 'address', 'city', 'country', 'zipcode')}),
        ('Subscription Info', {'fields': ('current_subscription',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions', 'role_id', 'state_id')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password', 'password_2'),
        }),
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


@admin.register(HaLogins)
class HaLoginsAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'user_id_str', 'login_provider', 'login_provider_identifier', 'created_by_id')
    list_filter = ('login_provider',)
    search_fields = ('user_id_str', 'login_provider', 'login_provider_identifier')
    ordering = ('-id',)
    
    list_select_related = ('user',)
    raw_id_fields = ('user',)
