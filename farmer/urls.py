from django.urls import path

from .views import (
    BatchDetailView,
    BatchEvidenceView,
    BatchHistoryView,
    BatchListView,
    BatchRegisterView,
    FarmerDashboardView,
    FarmerProfileView,
)

urlpatterns = [
    path('profile/', FarmerProfileView.as_view()),
    path('dashboard/', FarmerDashboardView.as_view()),
    path('batches/', BatchListView.as_view()),
    path('batches/register/', BatchRegisterView.as_view()),
    path('batches/detail/<str:batch_id>/', BatchDetailView.as_view()),
    path('batches/detail/<str:batch_id>/evidence/', BatchEvidenceView.as_view()),
    path('batches/history/<str:batch_id>/', BatchHistoryView.as_view()),
]
