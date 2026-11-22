import os

from django.core.exceptions import ValidationError


DOCUMENT_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png'}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024


def validate_document_upload(upload):
    extension = os.path.splitext(upload.name)[1].lower()
    if extension not in DOCUMENT_EXTENSIONS:
        raise ValidationError('Only PDF, JPG, JPEG, and PNG files are allowed.')
    if getattr(upload, 'size', 0) > MAX_FILE_SIZE:
        raise ValidationError('File size must not exceed 10 MB.')
    upload.seek(0)
    header = upload.read(8)
    upload.seek(0)
    valid_signatures = {
        '.pdf': header.startswith(b'%PDF-'),
        '.jpg': header.startswith(b'\xff\xd8\xff'),
        '.jpeg': header.startswith(b'\xff\xd8\xff'),
        '.png': header.startswith(b'\x89PNG\r\n\x1a\n'),
    }
    if not valid_signatures[extension]:
        raise ValidationError('The uploaded file content does not match its extension.')


def validate_image_upload(upload):
    extension = os.path.splitext(upload.name)[1].lower()
    if extension not in IMAGE_EXTENSIONS:
        raise ValidationError('Only JPG, JPEG, PNG, and WebP images are allowed.')
    if getattr(upload, 'size', 0) > MAX_FILE_SIZE:
        raise ValidationError('Image size must not exceed 10 MB.')