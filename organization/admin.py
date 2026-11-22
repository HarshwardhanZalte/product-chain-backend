from django.contrib import admin
from django import forms
from django.db import models
from django.utils.html import format_html
from django.urls import reverse

from .models import BlockchainEvent, Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('organization_name', 'organization_type', 'registration_number', 'verification_status')
    list_filter = ('organization_type', 'verification_status')
    search_fields = ('organization_name', 'registration_number', 'email')
    readonly_fields = ('verification_document_download',)
    formfield_overrides = {
        models.FileField: {'widget': forms.FileInput},
    }

    @admin.display(description='Verification document')
    def verification_document_download(self, obj):
        if not obj or not obj.verification_document:
            return 'No document uploaded.'
        url = reverse(
            'organization-verification-document',
            kwargs={'organization_id': obj.organization_id},
        )
        return format_html('<a href="{}">Download document</a>', url)


@admin.register(BlockchainEvent)
class BlockchainEventAdmin(admin.ModelAdmin):
    list_display = ('blockchain_event_id', 'entity_type', 'entity_id', 'event_type', 'transaction_status')
    list_filter = ('entity_type', 'event_type', 'transaction_status')
    search_fields = ('entity_id', 'data_hash', 'transaction_hash')
