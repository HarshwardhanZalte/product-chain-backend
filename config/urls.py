"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView
)
from users.file_views import LabCertificateView
from organization.views import BusinessParticipantListView

def health_check(request):
    from django.http import JsonResponse
    return JsonResponse({'status': 'ok'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('panel/', include('admin_panel.urls')),

    # Application APIs
    path('api/auth/', include('users.urls')),
    path('api/participants/', BusinessParticipantListView.as_view()),
    path('api/farmers/', include('farmer.urls')),
    path('api/batches/', include('farmer.urls')),
    path('api/collectors/', include('collector.urls')),
    path('api/labs/', include('lab.urls')),
    path('api/factories/', include('factory.urls')),
    path('api/products/', include('product.urls')),
    path(
        'api/private/lab-tests/<uuid:test_id>/certificate/',
        LabCertificateView.as_view(),
        name='lab-certificate',
    ),

    # OpenAPI Schema
    path(
        'api/schema/',
        SpectacularAPIView.as_view(),
        name='schema'
    ),

    # Swagger UI
    path(
        'api/docs/',
        SpectacularSwaggerView.as_view(
            url_name='schema'
        ),
        name='swagger-ui'
    ),

    # ReDoc
    path(
        'api/redoc/',
        SpectacularRedocView.as_view(
            url_name='schema'
        ),
        name='redoc'
    ),
    
    #health
    path('health/', health_check, name='health_check'),
]