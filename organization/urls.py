from django.urls import path

from .views import BusinessParticipantListView

urlpatterns = [
    path('participants/', BusinessParticipantListView.as_view()),
]
