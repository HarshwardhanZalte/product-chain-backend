import os

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiTypes, extend_schema

from factory.models import ManufacturingRecord
from users.permissions import IsVerifiedActiveUser
from users.services import log_activity

from .models import Product, ProductBatch
from .serializers import ProductCreateSerializer, ProductSerializer


def generate_product_qr(product):
    try:
        import qrcode
    except ImportError:
        return
    base_url = getattr(settings, 'PRODUCT_VERIFICATION_BASE_URL', 'http://localhost:8000')
    verification_url = f"{base_url.rstrip('/')}/api/product/verify/{product.qr_reference}/"
    qr = qrcode.QRCode(version=1, box_size=8, border=4)
    qr.add_data(verification_url)
    qr.make(fit=True)
    image = qr.make_image(fill_color='black', back_color='white')
    from io import BytesIO
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    product.qr_code_image.save(
        f'{product.qr_reference}.png',
        ContentFile(buffer.getvalue()),
        save=True,
    )


class ProductCreateView(APIView):
    permission_classes = (IsVerifiedActiveUser,)

    @extend_schema(request=ProductCreateSerializer, responses={201: ProductSerializer})
    @transaction.atomic
    def post(self, request):
        if request.user.role != 'FACTORY':
            return Response({'detail': 'Only factory users can create products.'}, status=403)
        serializer = ProductCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        profile = getattr(request.user, 'factory_profile', None)
        if not profile:
            return Response({'detail': 'Factory profile is not configured.'}, status=404)
        record = ManufacturingRecord.objects.select_for_update().filter(
            manufacturing_id=data['manufacturing_id'],
            factory=profile,
            status=ManufacturingRecord.Status.COMPLETED,
        ).first()
        if not record:
            return Response({'detail': 'Completed manufacturing record not found.'}, status=404)
        product = Product.objects.create(
            product_name=data['product_name'],
            description=data.get('description', ''),
            product_type=data['product_type'],
            manufacturer=profile,
            manufacturing_record=record,
            manufacture_date=data['manufacture_date'],
            expiry_date=data.get('expiry_date'),
            batch_number=data['batch_number'],
            total_quantity=data['total_quantity'],
            unit=data['unit'],
            product_image=data.get('product_image'),
        )
        manufacturing_links = record.input_batches.select_related('herb_batch').all()
        if not manufacturing_links.exists():
            raise ValueError('Manufacturing record has no input batches.')
        for link in manufacturing_links:
            ProductBatch.objects.create(
                product=product,
                herb_batch=link.herb_batch,
                quantity_used=link.quantity_used,
                unit=link.unit,
            )
        generate_product_qr(product)
        log_activity(
            request.user,
            'PRODUCT_CREATED',
            'Product',
            product.product_id,
            f'Created product {product.product_name}',
        )
        return Response(ProductSerializer(product).data, status=201)


class ProductListView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = (IsVerifiedActiveUser,)

    def get_queryset(self):
        if getattr(self.request.user, 'is_staff', False):
            return Product.objects.all()
        profile = getattr(self.request.user, 'factory_profile', None)
        return Product.objects.filter(manufacturer=profile) if profile else Product.objects.none()


class ProductDetailView(generics.RetrieveAPIView):
    serializer_class = ProductSerializer
    permission_classes = (IsVerifiedActiveUser,)
    lookup_field = 'product_id'

    def get_queryset(self):
        if getattr(self.request.user, 'is_staff', False):
            return Product.objects.all()
        profile = getattr(self.request.user, 'factory_profile', None)
        return Product.objects.filter(manufacturer=profile) if profile else Product.objects.none()


class ProductQRView(APIView):
    permission_classes = (IsVerifiedActiveUser,)

    @extend_schema(request=None, responses={200: ProductSerializer})
    def post(self, request, product_id):
        product = Product.objects.filter(product_id=product_id).first()
        if not product:
            return Response({'detail': 'Product not found.'}, status=404)
        if not getattr(request.user, 'is_staff', False):
            profile = getattr(request.user, 'factory_profile', None)
            if not profile or product.manufacturer_id != profile.id:
                return Response({'detail': 'Access denied.'}, status=403)
        generate_product_qr(product)
        return Response(ProductSerializer(product).data)


class PublicProductVerificationView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    @extend_schema(responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT})
    def get(self, request, qr_reference):
        product = (
            Product.objects
            .select_related('manufacturer', 'manufacturing_record')
            .prefetch_related(
                'input_batches__herb_batch__laboratory_tests',
                'input_batches__herb_batch__transfers',
            )
            .filter(qr_reference=qr_reference)
            .first()
        )
        if not product:
            return Response({'detail': 'UNAVAILABLE'}, status=404)

        input_batches = []
        verification_status = 'VERIFIED'
        for link in product.input_batches.all():
            batch = link.herb_batch
            tests = batch.laboratory_tests.all()
            latest_test = tests.order_by('-created_at').first()
            if batch.status in ('REJECTED',):
                verification_status = 'REJECTED'
            if not tests.exists():
                verification_status = 'INCOMPLETE'
            input_batches.append({
                'batch_id': batch.batch_id,
                'herb_name': batch.herb_name,
                'botanical_name': batch.botanical_name,
                'quantity_used': str(link.quantity_used),
                'unit': link.unit,
                'origin': {
                    'village': batch.village,
                    'district': batch.district,
                    'state': batch.state,
                    'collection_date': batch.collection_date,
                },
                'laboratory_test_status': latest_test.status if latest_test else None,
                'certificate_available': bool(latest_test and latest_test.certificate_file),
                'transfer_history': [
                    {
                        'event_id': str(event.event_id),
                        'status': event.status,
                        'transfer_date': event.transfer_date,
                        'transfer_location': event.transfer_location,
                    }
                    for event in batch.transfers.all()
                ],
            })

        if product.status in ('REJECTED', 'HOLD'):
            verification_status = 'REJECTED'
        if not input_batches:
            verification_status = 'INCOMPLETE'

        return Response({
            'verification_status': verification_status,
            'product': {
                'product_name': product.product_name,
                'product_type': product.product_type,
                'manufacture_date': product.manufacture_date,
                'status': product.status,
                'manufacturer_name': product.manufacturer.factory_name,
                'batch_number': product.batch_number,
            },
            'manufacturing': {
                'process_date': product.manufacturing_record.process_date,
                'process_description': product.manufacturing_record.process_description,
                'output_quantity': str(product.manufacturing_record.output_quantity),
                'unit': product.manufacturing_record.unit,
            },
            'input_herb_batches': input_batches,
        })
