from django.contrib import admin

from .models import LabProfile, LabTest


@admin.register(LabProfile)
class LabProfileAdmin(admin.ModelAdmin):
    list_display = ('laboratory_name', 'registration_number', 'organization', 'verification_status')
    list_filter = ('verification_status',)
    search_fields = ('laboratory_name', 'registration_number')


@admin.register(LabTest)
class LabTestAdmin(admin.ModelAdmin):
    list_display = ('test_id', 'batch', 'laboratory', 'test_type', 'status', 'test_date')
    list_filter = ('status', 'test_date')
    search_fields = ('test_id', 'batch__batch_id')
