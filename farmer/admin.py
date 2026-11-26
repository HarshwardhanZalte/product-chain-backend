from django.contrib import admin

from .models import FarmerProfile, HerbBatch


@admin.register(FarmerProfile)
class FarmerProfileAdmin(admin.ModelAdmin):
    exclude = ('organization',)
    list_display = ('farmer_name', 'district', 'verification_status')
    list_filter = ('verification_status', 'district', 'state')
    search_fields = ('farmer_name', 'phone_number')


@admin.register(HerbBatch)
class HerbBatchAdmin(admin.ModelAdmin):
    exclude = ('organization',)
    list_display = ('batch_id', 'herb_name', 'farmer', 'quantity', 'available_quantity', 'status')
    list_filter = ('status', 'source_type', 'district', 'state')
    search_fields = ('batch_id', 'herb_name', 'botanical_name')
