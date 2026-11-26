from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from .models import User


class RegistrationSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    password = serializers.CharField(min_length=8, write_only=True)
    role = serializers.ChoiceField(choices=User.Role.values)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value.lower()

    def validate_role(self, value):
        if value == User.Role.ADMIN:
            raise serializers.ValidationError('Administrator accounts cannot be registered publicly.')
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return value

    def validate(self, attrs):
        if 'organization' in self.initial_data:
            raise serializers.ValidationError({
                'organization': 'Organization membership is not supported.'
            })
        return attrs


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

    def validate_new_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return value


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(min_length=8, write_only=True)

    def validate_new_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return value


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'user_id',
            'email',
            'name',
            'phone_number',
            'role',
            'is_active',
            'is_email_verified',
            'date_joined',
        )
        read_only_fields = fields


class DetailResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class LoginResponseSerializer(serializers.Serializer):
    user = UserSerializer()
    tokens = serializers.DictField(child=serializers.CharField())


class OnboardingStatusSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=User.Role.choices)
    email_verified = serializers.BooleanField()
    role_profile = serializers.DictField(allow_null=True)
    role_profile_status = serializers.CharField(allow_null=True)
    business_identity_approved = serializers.BooleanField()
    next_step = serializers.ChoiceField(choices=(
        'VERIFY_EMAIL',
        'CREATE_PROFILE',
        'WAIT_FOR_APPROVAL',
        'READY',
    ))
