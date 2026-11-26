from django.contrib import admin

from .models import BlockchainEvent


@admin.register(BlockchainEvent)
class BlockchainEventAdmin(admin.ModelAdmin):
    list_display = ('blockchain_event_id', 'entity_type', 'entity_id', 'event_type', 'transaction_status')
    list_filter = ('entity_type', 'event_type', 'transaction_status')
    search_fields = ('entity_id', 'data_hash', 'transaction_hash')
