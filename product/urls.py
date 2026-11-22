from django.urls import path

from .views import (
    ProductCreateView,
    ProductDetailView,
    ProductListView,
    ProductQRView,
    PublicProductAssetView,
    PublicProductVerificationView,
)

urlpatterns = [
    path('list/', ProductListView.as_view()),
    path('detail/<uuid:product_id>/', ProductDetailView.as_view()),
    path('create/', ProductCreateView.as_view()),
    path('qr/<uuid:product_id>/', ProductQRView.as_view()),
    path('<uuid:product_id>/assets/<str:asset>/', PublicProductAssetView.as_view(), name='product-asset'),
    path('verify/<str:qr_reference>/', PublicProductVerificationView.as_view()),
]
