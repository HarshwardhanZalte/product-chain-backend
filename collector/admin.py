from django.contrib import admin

from .models import CollectorProfile, TransferEvent


@admin.register(CollectorProfile)
class CollectorProfileAdmin(admin.ModelAdmin):
    exclude = ('organization',)
    list_display = ('collector_name', 'verification_status')
    list_filter = ('verification_status',)
    search_fields = ('collector_name', 'phone_number')


@admin.register(TransferEvent)
class TransferEventAdmin(admin.ModelAdmin):
    exclude = ('from_organization', 'to_organization')
    list_display = ('event_id', 'batch', 'from_party', 'to_party', 'quantity', 'status')
    list_filter = ('status', 'transfer_date')
