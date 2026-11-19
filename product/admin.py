from django.contrib import admin

from .models import Product, ProductBatch


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'batch_number', 'manufacturer', 'status', 'qr_reference')
    list_filter = ('status', 'manufacture_date')
    search_fields = ('product_name', 'batch_number', 'qr_reference')


@admin.register(ProductBatch)
class ProductBatchAdmin(admin.ModelAdmin):
    list_display = ('product', 'herb_batch', 'quantity_used', 'unit')
