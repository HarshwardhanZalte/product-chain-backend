from django.urls import path

from .views import (
    AcceptTransferView,
    AvailableBatchesView,
    CollectorDashboardView,
    CollectorProfileView,
    InitiateTransferView,
    PendingTransferView,
    RejectTransferView,
    TransferHistoryView,
)

urlpatterns = [
    path('profile/', CollectorProfileView.as_view()),
    path('dashboard/', CollectorDashboardView.as_view()),
    path('available-batches/', AvailableBatchesView.as_view()),
    path('transfer/initiate/', InitiateTransferView.as_view()),
    path('transfer/pending/', PendingTransferView.as_view()),
    path('transfer/accept/', AcceptTransferView.as_view()),
    path('transfer/reject/', RejectTransferView.as_view()),
    path('transfer/history/', TransferHistoryView.as_view()),
]
