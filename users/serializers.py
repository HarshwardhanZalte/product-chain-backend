from rest_framework import serializers

from organization.models import Organization

from .models import User


class RegistrationSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    password = serializers.CharField(min_length=8, write_only=True)
    role = serializers.ChoiceField(choices=User.Role.values)
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(),
        required=False,
        allow_null=True,
    )

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value.lower()

    def validate_role(self, value):
        if value == User.Role.ADMIN:
            raise serializers.ValidationError('Administrator accounts cannot be registered publicly.')
        return value


class OTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(min_length=6, max_length=6)


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(min_length=6, max_length=6)
    new_password = serializers.CharField(min_length=8, write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(min_length=8, write_only=True)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class UserSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = User
        fields = (
            'user_id',
            'email',
            'name',
            'phone_number',
            'role',
            'organization',
            'is_active',
            'is_email_verified',
            'date_joined',
        )
        read_only_fields = fields
