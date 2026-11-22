import mimetypes
from pathlib import Path

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from lab.models import LabTest
from organization.models import Organization


def _file_response(field_file):
    if not field_file:
        raise Http404
    response = FileResponse(
        field_file.open('rb'),
        as_attachment=True,
        filename=Path(field_file.name).name,
        content_type=mimetypes.guess_type(field_file.name)[0] or 'application/octet-stream',
    )
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, no-store'
    return response


class OrganizationVerificationDocumentView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(responses={200: OpenApiTypes.BINARY, 404: OpenApiTypes.OBJECT})
    def get(self, request, organization_id):
        organization = get_object_or_404(Organization, organization_id=organization_id)
        if not (
            request.user.is_staff
            or request.user.role == 'ADMIN'
            or request.user.organization_id == organization.pk
        ):
            raise Http404
        return _file_response(organization.verification_document)


class LabCertificateView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(responses={200: OpenApiTypes.BINARY, 404: OpenApiTypes.OBJECT})
    def get(self, request, test_id):
        test = get_object_or_404(
            LabTest.objects.select_related('batch__farmer', 'laboratory'),
            test_id=test_id,
        )
        user = request.user
        is_participant = (
            test.laboratory.user_id == user.pk
            or test.batch.current_owner_id == user.pk
            or test.batch.farmer.user_id == user.pk
            or test.batch.transfers.filter(from_party=user).exists()
            or test.batch.transfers.filter(to_party=user).exists()
        )
        if not (user.is_staff or user.role == 'ADMIN' or is_participant):
            raise Http404
        return _file_response(test.certificate_file)
