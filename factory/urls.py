from django.urls import path

from .views import (
    AvailableApprovedBatchesView,
    CancelManufacturingDraftView,
    CompleteManufacturingDraftView,
    FactoryDashboardView,
    FactoryProfileView,
    ManufacturingCreateView,
    ManufacturingDetailView,
    ManufacturingListView,
    ReceiveBatchView,
)

urlpatterns = [
    path('profile/', FactoryProfileView.as_view()),
    path('dashboard/', FactoryDashboardView.as_view()),
    path('available-batches/', AvailableApprovedBatchesView.as_view()),
    path('receive-batch/', ReceiveBatchView.as_view()),
    path('manufacturing/create/', ManufacturingCreateView.as_view()),
    path('manufacturing/complete/', CompleteManufacturingDraftView.as_view()),
    path('manufacturing/cancel/', CancelManufacturingDraftView.as_view()),
    path('manufacturing/list/', ManufacturingListView.as_view()),
    path('manufacturing/detail/<uuid:manufacturing_id>/', ManufacturingDetailView.as_view()),
]
