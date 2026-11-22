from django.contrib.auth import authenticate
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import OpenApiTypes, extend_schema
import logging

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import ActivityLog, EmailOTP, User
from .serializers import (
    ChangePasswordSerializer,
    LogoutSerializer,
    EmailSerializer,
    LoginSerializer,
    OTPSerializer,
    RegistrationSerializer,
    ResetPasswordSerializer,
    UserSerializer,
)
from .services import EmailDeliveryError, create_otp, verify_otp

logger = logging.getLogger(__name__)

def client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    return (forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR'))


def log_activity(request, action, entity_type, entity_id, description=''):
    ActivityLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        description=description,
        ip_address=client_ip(request),
    )


def get_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {'access': str(refresh.access_token), 'refresh': str(refresh)}


class RegisterView(APIView):
    permission_classes = (permissions.AllowAny,)

    @extend_schema(request=RegistrationSerializer, responses={201: UserSerializer})
    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = User.objects.create_user( 
            email=data['email'],
            password=data['password'],
            name=data['name'],
            phone_number=data.get('phone_number', ''),
            role=data['role'],
            is_email_verified=False,
        )
        try:
            create_otp(user, EmailOTP.Purpose.VERIFY_EMAIL)
        except EmailDeliveryError:
            user.delete()
            logger.exception('Unable to send registration OTP for user %s', user.user_id)
            return Response(
                {'detail': 'Unable to send verification email.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        log_activity(request, 'USER_REGISTERED', 'User', user.user_id)
        return Response(
            {'detail': 'Registration successful. Verify your email with the OTP.'},
            status=status.HTTP_201_CREATED,
        )


class SendOTPView(APIView):
    permission_classes = (permissions.AllowAny,)

    @extend_schema(request=EmailSerializer, responses={200: None})
    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=serializer.validated_data.get('email', '')).first()
        if not user:
            return Response({'detail': 'If the account exists, an OTP will be sent.'})
        try:
            _, created = create_otp(user, EmailOTP.Purpose.VERIFY_EMAIL)
        except EmailDeliveryError:
            logger.exception('Unable to resend verification OTP for user %s', user.user_id)
            return Response(
                {'detail': 'Unable to send verification email.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if not created:
            return Response(
                {'detail': 'OTP resend cooldown is active.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        return Response({'detail': 'OTP sent.'})


class ResendOTPView(APIView):
    permission_classes = (permissions.AllowAny,)

    @extend_schema(
        request=EmailSerializer,
        responses={
            200: None,
            400: None,
            429: None,
        },
    )
    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email'].strip().lower()
        user = User.objects.filter(email__iexact=email).first()

        if not user:
            return Response(
                {'detail': 'If the account exists, an OTP will be sent.'},
                status=status.HTTP_200_OK,
            )

        if user.is_email_verified:
            return Response(
                {'detail': 'Email is already verified.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            _, created = create_otp(user, EmailOTP.Purpose.VERIFY_EMAIL)
        except EmailDeliveryError:
            logger.exception('Unable to resend verification OTP for user %s', user.user_id)
            return Response(
                {'detail': 'Unable to send verification email.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if not created:
            return Response(
                {'detail': 'OTP resend cooldown is active.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        log_activity(
            request,
            'OTP_RESENT',
            'User',
            user.user_id,
            'Email verification OTP resent',
        )
        return Response(
            {'detail': 'A new OTP has been sent.'},
            status=status.HTTP_200_OK,
        )


class VerifyOTPView(APIView):
    permission_classes = (permissions.AllowAny,)

    @extend_schema(request=OTPSerializer, responses={200: None})
    def post(self, request):
        serializer = OTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=serializer.validated_data['email']).first()
        if not user:
            return Response({'detail': 'Invalid verification request.'}, status=400)
        ok, message = verify_otp(
            user,
            EmailOTP.Purpose.VERIFY_EMAIL,
            serializer.validated_data['otp'],
        )
        if not ok:
            return Response({'detail': message}, status=400)
        user.is_email_verified = True
        user.save(update_fields=['is_email_verified', 'updated_at'])
        log_activity(request, 'EMAIL_VERIFIED', 'User', user.user_id)
        return Response({'detail': 'Email verified successfully.'})


class LoginView(APIView):
    permission_classes = (permissions.AllowAny,)

    @extend_schema(request=LoginSerializer, responses={200: None})
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email'].lower()
        user = authenticate(
            request,
            username=email,
            password=serializer.validated_data['password'],
        )
        if not user:
            return Response({'detail': 'Invalid credentials.'}, status=401)
        if not user.is_active:
            return Response({'detail': 'Account is inactive.'}, status=403)
        if not user.is_email_verified:
            return Response({'detail': 'Email verification is required.'}, status=403)
        if user.role == User.Role.ADMIN or user.is_staff:
            return Response({'detail': 'Administrators must use the session admin login.'}, status=403)
        log_activity(request, 'USER_LOGIN', 'User', user.user_id)
        return Response({'user': UserSerializer(user).data, 'tokens': get_tokens(user)})


class LogoutView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(request=LogoutSerializer, responses={200: None})
    def post(self, request):
        refresh = request.data.get('refresh')
        if not refresh:
            return Response({'detail': 'Refresh token is required.'}, status=400)
        try:
            RefreshToken(refresh).blacklist()
        except Exception:
            return Response({'detail': 'Invalid refresh token.'}, status=400)
        log_activity(request, 'USER_LOGOUT', 'User', request.user.user_id)
        return Response({'detail': 'Logout successful.'})


class ForgotPasswordView(APIView):
    permission_classes = (permissions.AllowAny,)

    @extend_schema(request=EmailSerializer, responses={200: None})
    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=serializer.validated_data['email']).first()
        if user:
            try:
                create_otp(user, EmailOTP.Purpose.RESET_PASSWORD)
            except EmailDeliveryError:
                logger.exception('Unable to send password reset OTP for user %s', user.user_id)
        return Response({'detail': 'If the account exists, a password reset OTP will be sent.'})


class ResetPasswordView(APIView):
    permission_classes = (permissions.AllowAny,)

    @extend_schema(request=ResetPasswordSerializer, responses={200: None})
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = User.objects.filter(email__iexact=data['email']).first()
        if not user:
            return Response({'detail': 'Invalid reset request.'}, status=400)
        try:
            validate_password(data['new_password'], user=user)
        except DjangoValidationError as exc:
            return Response({'new_password': exc.messages}, status=400)
        ok, message = verify_otp(
            user,
            EmailOTP.Purpose.RESET_PASSWORD,
            data['otp'],
        )
        if not ok:
            return Response({'detail': message}, status=400)
        user.set_password(data['new_password'])
        user.save(update_fields=['password', 'updated_at'])
        log_activity(request, 'PASSWORD_RESET', 'User', user.user_id)
        return Response({'detail': 'Password reset successful.'})


class ProfileView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(responses={200: UserSerializer})
    def get(self, request):
        if not request.user.is_email_verified:
            return Response({'detail': 'Email verification is required.'}, status=403)
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(request=ChangePasswordSerializer, responses={200: None})
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if not request.user.check_password(data['current_password']):
            return Response({'detail': 'Current password is incorrect.'}, status=400)
        try:
            validate_password(data['new_password'], user=request.user)
        except DjangoValidationError as exc:
            return Response({'new_password': exc.messages}, status=400)
        request.user.set_password(data['new_password'])
        request.user.save(update_fields=['password', 'updated_at'])
        log_activity(request, 'PASSWORD_CHANGED', 'User', request.user.user_id)
        return Response({'detail': 'Password changed successfully.'})
