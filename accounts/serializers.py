from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    profile_file = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    affirmation_for_the_day = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'first_name', 'last_name', 'role_id', 'contact_no', 'address', 'city', 'country', 'profile_file', 'language', 'is_superuser', 'is_staff', 'permissions', 'affirmation_for_the_day')

    def get_permissions(self, obj):
        if obj.is_superuser:
            return ["*"]
        return list(obj.get_all_permissions())

    def get_profile_file(self, obj):
        if not obj.profile_file:
            return ""
        from urllib.parse import quote
        return f"/user/image/{obj.id}?file={quote(str(obj.profile_file))}"

    def get_first_name(self, obj):
        return getattr(obj, "first_name", "") or ""

    def get_last_name(self, obj):
        return getattr(obj, "last_name", "") or ""

    def get_affirmation_for_the_day(self, obj):
        return obj.get_affirmation_for_the_day()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Prevent iOS/Swift force-unwrap crashes by turning null string values into empty strings
        for key in ('email', 'full_name', 'first_name', 'last_name', 'contact_no', 'address', 'city', 'country', 'profile_file', 'language', 'affirmation_for_the_day'):
            if key in data and data[key] is None:
                data[key] = ""
        return data


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'password', 'full_name', 'first_name', 'last_name', 'role_id')
        extra_kwargs = {
            'email': {'required': True},
            'full_name': {'required': False, 'allow_blank': True},
            'first_name': {'required': False, 'allow_blank': True},
            'last_name': {'required': False, 'allow_blank': True}
        }

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data.get('password') or None,
            full_name=validated_data.get('full_name', ''),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            role_id=validated_data.get('role_id', User.ROLE_USER)
        )
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['email'] = user.email
        token['name'] = user.full_name
        token['role_id'] = user.role_id

        return token
