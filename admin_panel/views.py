from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Case, CharField, F, Q, Value, When
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from collector.models import TransferEvent
from factory.models import FactoryProfile, ManufacturingRecord
from farmer.models import HerbBatch
from lab.models import LabTest
from product.models import Product
from users.models import ActivityLog, User


staff_required = user_passes_test(
    lambda user: user.is_active and user.is_staff,
    login_url='admin_login',
)

PROFILE_RELATIONS = {
    User.Role.FARMER: 'farmer_profile',
    User.Role.COLLECTOR: 'collector_profile',
    User.Role.LAB: 'lab_profile',
    User.Role.FACTORY: 'factory_profile',
}


def _user_queryset():
    return (
        User.objects.select_related(
            'farmer_profile',
            'collector_profile',
            'lab_profile',
            'factory_profile',
        )
        .annotate(
            verification_status=Case(
                When(role=User.Role.FARMER, farmer_profile__isnull=True, then=Value('MISSING')),
                When(role=User.Role.FARMER, then=F('farmer_profile__verification_status')),
                When(role=User.Role.COLLECTOR, collector_profile__isnull=True, then=Value('MISSING')),
                When(role=User.Role.COLLECTOR, then=F('collector_profile__verification_status')),
                When(role=User.Role.LAB, lab_profile__isnull=True, then=Value('MISSING')),
                When(role=User.Role.LAB, then=F('lab_profile__verification_status')),
                When(role=User.Role.FACTORY, factory_profile__isnull=True, then=Value('MISSING')),
                When(role=User.Role.FACTORY, then=F('factory_profile__verification_status')),
                default=Value('NOT_REQUIRED'),
                output_field=CharField(),
            )
        )
        .order_by('-date_joined')
    )


def _get_profile(user):
    relation = PROFILE_RELATIONS.get(user.role)
    if relation is None:
        return None
    try:
        return getattr(user, relation)
    except ObjectDoesNotExist:
        return None


def admin_login(request):
    if request.user.is_authenticated and request.user.is_active and request.user.is_staff:
        return redirect('admin_dashboard')

    error = None
    next_url = request.POST.get('next') or request.GET.get('next', '')
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('email', '').strip().lower(),
            password=request.POST.get('password', ''),
        )
        if user and user.is_active and user.is_staff:
            login(request, user)
            if url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect('admin_dashboard')
        error = 'Invalid administrator credentials.'

    return render(request, 'admin_panel/login.html', {'error': error, 'next': next_url})


@staff_required
@require_POST
def admin_logout(request):
    logout(request)
    return redirect('admin_login')


@staff_required
def dashboard(request):
    total_users = User.objects.count()
    pending_role_reviews = _user_queryset().filter(verification_status='PENDING').count()
    email_verification_pending = User.objects.filter(is_email_verified=False).count()
    total_batches = HerbBatch.objects.count()
    pending_lab_tests = LabTest.objects.filter(status='PENDING').count()

    context = {
        'dashboard_stats': [
            {
                'label': 'Registered users',
                'value': total_users,
                'url': reverse('admin_users'),
                'tone': 'green',
            },
            {
                'label': 'Pending profile reviews',
                'value': pending_role_reviews,
                'url': f"{reverse('admin_users')}?status=PENDING",
                'tone': 'amber',
            },
            {
                'label': 'Email verification pending',
                'value': email_verification_pending,
                'url': f"{reverse('admin_users')}?email=unverified",
                'tone': 'blue',
            },
            {
                'label': 'Herb batches',
                'value': total_batches,
                'url': reverse('admin_batches'),
                'tone': 'green',
            },
            {
                'label': 'Lab tests awaiting review',
                'value': pending_lab_tests,
                'url': reverse('admin_lab_tests'),
                'tone': 'amber',
            },
            {
                'label': 'Products',
                'value': Product.objects.count(),
                'url': reverse('admin_products'),
                'tone': 'blue',
            },
        ],
        'recent_activities': ActivityLog.objects.select_related('user')[:10],
    }
    return render(request, 'admin_panel/dashboard.html', context)


def paginate(request, queryset, per_page=20):
    return Paginator(queryset, per_page).get_page(request.GET.get('page'))


@staff_required
def users(request):
    queryset = _user_queryset()
    search = request.GET.get('q', '').strip()
    role = request.GET.get('role', '').strip()
    status_value = request.GET.get('status', '').strip().upper()
    email_status = request.GET.get('email', '').strip().lower()

    if search:
        queryset = queryset.filter(
            Q(email__icontains=search)
            | Q(name__icontains=search)
            | Q(phone_number__icontains=search)
            | Q(farmer_profile__farmer_name__icontains=search)
            | Q(collector_profile__collector_name__icontains=search)
            | Q(lab_profile__laboratory_name__icontains=search)
            | Q(factory_profile__factory_name__icontains=search)
        )
    if role in User.Role.values:
        queryset = queryset.filter(role=role)
    if status_value in {'PENDING', 'VERIFIED', 'REJECTED', 'SUSPENDED', 'MISSING', 'NOT_REQUIRED'}:
        queryset = queryset.filter(verification_status=status_value)
    if email_status == 'verified':
        queryset = queryset.filter(is_email_verified=True)
    elif email_status == 'unverified':
        queryset = queryset.filter(is_email_verified=False)

    query_params = request.GET.copy()
    query_params.pop('page', None)
    return render(
        request,
        'admin_panel/users.html',
        {
            'page_obj': paginate(request, queryset),
            'roles': User.Role.choices,
            'status_options': (
                ('PENDING', 'Pending review'),
                ('VERIFIED', 'Approved'),
                ('REJECTED', 'Rejected'),
                ('SUSPENDED', 'Suspended'),
                ('MISSING', 'Profile missing'),
                ('NOT_REQUIRED', 'Not applicable'),
            ),
            'total_users': User.objects.count(),
            'pending_role_reviews': _user_queryset().filter(
                verification_status='PENDING'
            ).count(),
            'email_verification_pending': User.objects.filter(
                is_email_verified=False
            ).count(),
            'querystring': query_params.urlencode(),
        },
    )


@staff_required
def user_detail(request, user_id):
    detail_user = get_object_or_404(
        User.objects.select_related(
            'farmer_profile',
            'collector_profile',
            'lab_profile',
            'factory_profile',
        ),
        user_id=user_id,
    )
    profile = _get_profile(detail_user)

    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action in {'approve_profile', 'reject_profile'}:
            if profile is None:
                messages.error(request, 'This account has no role profile to review.')
            elif not detail_user.is_active or not detail_user.is_email_verified:
                messages.error(
                    request,
                    'Activate the account and verify its email before reviewing the role profile.',
                )
            else:
                new_status = (
                    'VERIFIED' if action == 'approve_profile' else 'REJECTED'
                )
                previous_status = profile.verification_status
                note = request.POST.get('note', '').strip()[:2000]
                action_label = (
                    'BUSINESS_PROFILE_APPROVED'
                    if new_status == 'VERIFIED'
                    else 'BUSINESS_PROFILE_REJECTED'
                )
                description = (
                    f'{detail_user.role} profile for {detail_user.email}: '
                    f'{previous_status} -> {new_status}.'
                )
                if note:
                    description += f' Review note: {note}'
                with transaction.atomic():
                    profile.verification_status = new_status
                    profile.save(update_fields=['verification_status', 'updated_at'])
                    ActivityLog.objects.create(
                        user=request.user,
                        action=action_label,
                        entity_type=profile.__class__.__name__,
                        entity_id=str(detail_user.user_id),
                        description=description,
                        ip_address=request.META.get('REMOTE_ADDR'),
                    )
                messages.success(
                    request,
                    f'{detail_user.get_role_display()} profile {new_status.lower()}.',
                )
        elif action == 'toggle_active':
            should_activate = not detail_user.is_active
            if detail_user.user_id == request.user.user_id and not should_activate:
                messages.error(request, 'You cannot deactivate your own administrator account.')
            elif detail_user.is_staff and not request.user.is_superuser:
                messages.error(request, 'Only a superuser can change an administrator account.')
            else:
                detail_user.is_active = should_activate
                detail_user.save(update_fields=['is_active', 'updated_at'])
                ActivityLog.objects.create(
                    user=request.user,
                    action='ADMIN_USER_ACTIVATED' if should_activate else 'ADMIN_USER_DEACTIVATED',
                    entity_type='User',
                    entity_id=str(detail_user.user_id),
                    description=f'Account for {detail_user.email} was {"activated" if should_activate else "deactivated"}.',
                    ip_address=request.META.get('REMOTE_ADDR'),
                )
                messages.success(
                    request,
                    f'Account {"activated" if should_activate else "deactivated"}.',
                )
        else:
            messages.error(request, 'Choose a valid user-management action.')
        return redirect('admin_user_detail', user_id=detail_user.user_id)

    excluded_fields = {
        'id',
        'user',
        'organization',
        'verification_status',
        'created_at',
        'updated_at',
        'farmer_id',
        'collector_id',
        'lab_id',
        'factory_id',
    }
    profile_fields = []
    if profile is not None:
        profile_fields = [
            (field.verbose_name, getattr(profile, field.name))
            for field in profile._meta.concrete_fields
            if field.name not in excluded_fields and not field.is_relation
        ]

    return render(
        request,
        'admin_panel/user_detail.html',
        {
            'detail_user': detail_user,
            'profile': profile,
            'profile_fields': profile_fields,
        },
    )


@staff_required
def batches(request):
    queryset = HerbBatch.objects.select_related('farmer', 'current_owner')
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
        'page_obj': paginate(request, FactoryProfile.objects.all()),
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
