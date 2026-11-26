from django.contrib import admin
from django import forms
from django.db import models
from django.urls import reverse
from django.utils.html import format_html

from .models import LabProfile, LabTest


@admin.register(LabProfile)
class LabProfileAdmin(admin.ModelAdmin):
    exclude = ('organization',)
    list_display = ('laboratory_name', 'registration_number', 'verification_status')
    list_filter = ('verification_status',)
    search_fields = ('laboratory_name', 'registration_number')


@admin.register(LabTest)
class LabTestAdmin(admin.ModelAdmin):
    list_display = ('test_id', 'batch', 'laboratory', 'test_type', 'status', 'test_date')
    list_filter = ('status', 'test_date')
    search_fields = ('test_id', 'batch__batch_id')
    readonly_fields = ('certificate_download',)
    formfield_overrides = {
        models.FileField: {'widget': forms.FileInput},
    }

    @admin.display(description='Certificate')
    def certificate_download(self, obj):
        if not obj or not obj.certificate_file:
            return 'No certificate uploaded.'
        url = reverse('lab-certificate', kwargs={'test_id': obj.test_id})
        return format_html('<a href="{}">Download certificate</a>', url)
