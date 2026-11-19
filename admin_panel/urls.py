from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.admin_login, name='admin_login'),
    path('logout/', views.admin_logout, name='admin_logout'),
    path('', views.dashboard, name='admin_dashboard'),
    path('users/', views.users, name='admin_users'),
    path('users/<uuid:user_id>/', views.user_detail, name='admin_user_detail'),
    path('organizations/', views.organizations, name='admin_organizations'),
    path(
        'organizations/<uuid:organization_id>/',
        views.organization_detail,
        name='admin_organization_detail',
    ),
    path('batches/', views.batches, name='admin_batches'),
    path(
        'batches/<str:batch_id>/',
        views.batch_detail,
        name='admin_batch_detail',
    ),
    path('lab-tests/', views.lab_tests, name='admin_lab_tests'),
    path('factories/', views.factories, name='admin_factories'),
    path('products/', views.products, name='admin_products'),
    path(
        'products/<uuid:product_id>/',
        views.product_detail,
        name='admin_product_detail',
    ),
    path('activity/', views.activity, name='admin_activity'),
]
