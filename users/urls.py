from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    ChangePasswordView,
    ForgotPasswordView,
    LoginView,
    LogoutView,
    OnboardingStatusView,
    ProfileView,
    RegisterView,
    ResendOTPView,
    ResetPasswordView,
    SendOTPView,
    VerifyOTPView,
)

urlpatterns = [
    path('register/', RegisterView.as_view()),
    path('send-otp/', SendOTPView.as_view()),
    path('resend-otp/', ResendOTPView.as_view()),
    path('verify-otp/', VerifyOTPView.as_view()),
    path('login/', LoginView.as_view()),
    path('logout/', LogoutView.as_view()),
    path('refresh/', TokenRefreshView.as_view()),
    path('forgot-password/', ForgotPasswordView.as_view()),
    path('reset-password/', ResetPasswordView.as_view()),
    path('profile/', ProfileView.as_view()),
    path('change-password/', ChangePasswordView.as_view()),
    path('onboarding/', OnboardingStatusView.as_view()),
]
