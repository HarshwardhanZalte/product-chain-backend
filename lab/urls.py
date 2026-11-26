from django.urls import path

from .views import (
    ApproveTestView,
    LabDashboardView,
    LabProfileView,
    LabRequestsView,
    LabTestDetailView,
    LabTestHistoryView,
    RecordTestResultView,
    RejectTestView,
    SubmitForTestingView,
)

urlpatterns = [
    path('profile/', LabProfileView.as_view()),
    path('dashboard/', LabDashboardView.as_view()),
    path('requests/', LabRequestsView.as_view()),
    path('tests/<uuid:test_id>/', LabTestDetailView.as_view()),
    path('submit-batch/', SubmitForTestingView.as_view()),
    path('submit-result/', RecordTestResultView.as_view()),
    path('approve-test/', ApproveTestView.as_view()),
    path('reject-test/', RejectTestView.as_view()),
    path('test-history/', LabTestHistoryView.as_view()),
]
