from django.contrib import admin

from .models import FactoryProfile, ManufacturingBatch, ManufacturingRecord


@admin.register(FactoryProfile)
class FactoryProfileAdmin(admin.ModelAdmin):
    exclude = ('organization',)
    list_display = ('factory_name', 'registration_number', 'verification_status')
    list_filter = ('verification_status',)
    search_fields = ('factory_name', 'registration_number')


@admin.register(ManufacturingRecord)
class ManufacturingRecordAdmin(admin.ModelAdmin):
    list_display = ('manufacturing_id', 'factory', 'product_name', 'status', 'process_date')
    list_filter = ('status', 'process_date')
    search_fields = ('manufacturing_id', 'product_name')


@admin.register(ManufacturingBatch)
class ManufacturingBatchAdmin(admin.ModelAdmin):
    list_display = ('manufacturing_record', 'herb_batch', 'quantity_used', 'unit')
