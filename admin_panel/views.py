from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from collector.models import TransferEvent
from factory.models import FactoryProfile, ManufacturingRecord
from farmer.models import HerbBatch
from lab.models import LabTest
from organization.models import Organization
from product.models import Product
from users.models import ActivityLog, User


staff_required = user_passes_test(
    lambda user: user.is_active and user.is_staff,
    login_url='admin_login',
)


def admin_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard')

    error = None
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('email', '').strip().lower(),
            password=request.POST.get('password', ''),
        )
        if user and user.is_active and user.is_staff:
            login(request, user)
            return redirect('admin_dashboard')
        error = 'Invalid administrator credentials.'

    return render(request, 'admin_panel/login.html', {'error': error})


@staff_required
def admin_logout(request):
    logout(request)
    return redirect('admin_login')


@staff_required
def dashboard(request):
    context = {
        'total_users': User.objects.count(),
        'total_organizations': Organization.objects.count(),
        'total_farmers': User.objects.filter(role='FARMER').count(),
        'total_collectors': User.objects.filter(role='COLLECTOR').count(),
        'total_laboratories': User.objects.filter(role='LAB').count(),
        'total_factories': User.objects.filter(role='FACTORY').count(),
        'total_batches': HerbBatch.objects.count(),
        'pending_lab_tests': LabTest.objects.filter(status='PENDING').count(),
        'approved_batches': HerbBatch.objects.filter(status='APPROVED').count(),
        'rejected_batches': HerbBatch.objects.filter(status='REJECTED').count(),
        'total_manufacturing_records': ManufacturingRecord.objects.count(),
        'total_products': Product.objects.count(),
        'recent_activities': ActivityLog.objects.select_related('user')[:10],
    }
    context['dashboard_stats'] = [
        ('Users', context['total_users']),
        ('Organizations', context['total_organizations']),
        ('Herb batches', context['total_batches']),
        ('Pending lab tests', context['pending_lab_tests']),
        ('Approved batches', context['approved_batches']),
        ('Rejected batches', context['rejected_batches']),
        ('Manufacturing records', context['total_manufacturing_records']),
        ('Products', context['total_products']),
    ]
    return render(request, 'admin_panel/dashboard.html', context)


def paginate(request, queryset, per_page=20):
    return Paginator(queryset, per_page).get_page(request.GET.get('page'))


@staff_required
def users(request):
    queryset = User.objects.all().select_related('organization')
    search = request.GET.get('q', '').strip()
    role = request.GET.get('role', '').strip()
    if search:
        queryset = queryset.filter(Q(email__icontains=search) | Q(name__icontains=search))
    if role:
        queryset = queryset.filter(role=role)

    if request.method == 'POST':
        user = get_object_or_404(User, pk=request.POST.get('user_id'))
        user.is_active = request.POST.get('is_active') == 'true'
        if 'role' in request.POST and request.POST['role'] in User.Role.values:
            if request.POST['role'] != 'ADMIN' or request.user.is_superuser:
                user.role = request.POST['role']
        user.save(update_fields=['is_active', 'role', 'updated_at'])

    return render(request, 'admin_panel/users.html', {
        'page_obj': paginate(request, queryset),
        'roles': User.Role.choices,
    })


@staff_required
def user_detail(request, user_id):
    user = get_object_or_404(User, user_id=user_id)
    return render(request, 'admin_panel/user_detail.html', {'detail_user': user})


@staff_required
def organizations(request):
    queryset = Organization.objects.all()
    search = request.GET.get('q', '').strip()
    status_value = request.GET.get('status', '').strip()
    if search:
        queryset = queryset.filter(
            Q(organization_name__icontains=search)
            | Q(registration_number__icontains=search)
        )
    if status_value:
        queryset = queryset.filter(verification_status=status_value)

    if request.method == 'POST':
        organization = get_object_or_404(
            Organization,
            organization_id=request.POST.get('organization_id'),
        )
        if request.POST.get('status') in Organization.VerificationStatus.values:
            organization.verification_status = request.POST['status']
            organization.save(update_fields=['verification_status', 'updated_at'])

    return render(request, 'admin_panel/organizations.html', {
        'page_obj': paginate(request, queryset),
        'statuses': Organization.VerificationStatus.choices,
    })


@staff_required
def organization_detail(request, organization_id):
    organization = get_object_or_404(Organization, organization_id=organization_id)
    return render(request, 'admin_panel/organization_detail.html', {'organization': organization})


@staff_required
def batches(request):
    queryset = HerbBatch.objects.select_related('farmer', 'organization', 'current_owner')
    search = request.GET.get('q', '').strip()
    status_value = request.GET.get('status', '').strip()
    if search:
        queryset = queryset.filter(
            Q(batch_id__icontains=search) | Q(herb_name__icontains=search)
        )
    if status_value:
        queryset = queryset.filter(status=status_value)

    return render(request, 'admin_panel/batches.html', {
        'page_obj': paginate(request, queryset),
        'statuses': HerbBatch.Status.choices,
    })


@staff_required
def batch_detail(request, batch_id):
    batch = get_object_or_404(HerbBatch, batch_id=batch_id)
    return render(request, 'admin_panel/batch_detail.html', {
        'batch': batch,
        'transfers': TransferEvent.objects.filter(batch=batch),
        'tests': LabTest.objects.filter(batch=batch),
    })


@staff_required
def lab_tests(request):
    queryset = LabTest.objects.select_related('batch', 'laboratory')
    return render(request, 'admin_panel/lab_tests.html', {
        'page_obj': paginate(request, queryset),
    })


@staff_required
def factories(request):
    return render(request, 'admin_panel/factories.html', {
        'page_obj': paginate(request, FactoryProfile.objects.select_related('organization')),
        'manufacturing_records': ManufacturingRecord.objects.select_related('factory')[:20],
        'products': Product.objects.select_related('manufacturer')[:20],
    })


@staff_required
def products(request):
    return render(request, 'admin_panel/products.html', {
        'page_obj': paginate(request, Product.objects.select_related('manufacturer')),
    })


@staff_required
def product_detail(request, product_id):
    product = get_object_or_404(Product, product_id=product_id)
    return render(request, 'admin_panel/product_detail.html', {'product': product})


@staff_required
def activity(request):
    return render(request, 'admin_panel/activity.html', {
        'page_obj': paginate(request, ActivityLog.objects.select_related('user')),
    })
