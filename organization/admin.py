from django.contrib import admin

from .models import BlockchainEvent, Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('organization_name', 'organization_type', 'registration_number', 'verification_status')
    list_filter = ('organization_type', 'verification_status')
    search_fields = ('organization_name', 'registration_number', 'email')


@admin.register(BlockchainEvent)
class BlockchainEventAdmin(admin.ModelAdmin):
    list_display = ('blockchain_event_id', 'entity_type', 'entity_id', 'event_type', 'transaction_status')
    list_filter = ('entity_type', 'event_type', 'transaction_status')
    search_fields = ('entity_id', 'data_hash', 'transaction_hash')
