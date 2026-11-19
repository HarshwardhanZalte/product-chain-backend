from django.urls import path

from .views import (
    MyOrganizationView,
    OrganizationCreateView,
    OrganizationDetailView,
    OrganizationListView,
)

urlpatterns = [
    path('create/', OrganizationCreateView.as_view()),
    path('list/', OrganizationListView.as_view()),
    path('detail/<uuid:organization_id>/', OrganizationDetailView.as_view()),
    path('my-organization/', MyOrganizationView.as_view()),
]
