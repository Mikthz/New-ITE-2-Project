from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.db.models import Q, F
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models.deletion import ProtectedError
from django.core.files.storage import default_storage
from urllib.parse import quote

import uuid

from django.db.models import Sum, Avg
from django.utils import timezone
from django.utils.dateparse import parse_date
from .models import Admin, Category, Product, Supplier, SupplierProduct, SupplierPurchase, SupplierDelivery, Delivery, Sale, Expense, Invoice, ContactSupport
from .forms import AdminForm, AdminUpdateForm, AccountOverviewForm, ContactSupportForm, CategoryForm, ProductForm, SaleForm, SupplierForm, SupplierProductForm, SupplierPurchaseForm, SupplierDeliveryForm, DeliveryForm, ExpenseForm, InvoiceForm, ChangePINForm, ChangePasswordForm

CREATE_EXPENSE_PAGE_DISABLED = True
CREATE_INVOICE_PAGE_DISABLED = True

def get_current_admin(request):
    admin_pk = request.session.get('admin_id')

    if not admin_pk:
        return None

    try:
        return Admin.objects.get(pk=admin_pk)
    except Admin.DoesNotExist:
        request.session.flush()
        return None

def clean_missing_profile_picture(user):
    if user.profile_picture and not default_storage.exists(user.profile_picture.name):
        user.profile_picture = None
        user.save(update_fields=['profile_picture'])


def generate_delivery_group_code():
    next_number = (Delivery.objects.order_by('-pk').values_list('pk', flat=True).first() or 0) + 1

    while True:
        code = f"D{next_number:04d}"
        if not Delivery.objects.filter(Q(delivery_group=code) | Q(delivery_code=code)).exists():
            return code
        next_number += 1


def generate_supplier_batch_code():
    next_number = (SupplierDelivery.objects.order_by('-pk').values_list('pk', flat=True).first() or 0) + 1

    while True:
        code = f"SD{next_number:04d}"
        if (
            not Expense.objects.filter(remarks__icontains=f"SUPPLIER_BATCH={code}").exists() and
            not SupplierDelivery.objects.filter(delivery_code=code).exists()
        ):
            return code
        next_number += 1


def get_supplier_batch_code_from_expense(expense):
    if not expense or not expense.remarks:
        return ''

    for part in expense.remarks.split():
        if part.startswith('SUPPLIER_BATCH='):
            return part.split('=', 1)[1].strip()

    return ''


def strip_supplier_batch_marker(remarks):
    if not remarks:
        return ''

    cleaned_parts = [
        part for part in str(remarks).split()
        if not part.startswith('SUPPLIER_BATCH=')
    ]

    return ' '.join(cleaned_parts).strip()


def get_invoice_group_queryset(invoice):
    if not invoice or not invoice.sale_id:
        return Invoice.objects.filter(pk=invoice.pk)

    delivery_group = get_delivery_group_for_sale_map([invoice.sale_id]).get(invoice.sale_id)

    if not delivery_group:
        return Invoice.objects.filter(pk=invoice.pk)

    sale_ids = Delivery.objects.filter(
        Q(delivery_group=delivery_group) |
        Q(delivery_code=delivery_group)
    ).exclude(
        sale_id__isnull=True
    ).values_list('sale_id', flat=True)

    return Invoice.objects.filter(sale_id__in=sale_ids)


def get_expense_group_queryset(expense):
    if not expense:
        return Expense.objects.none()

    supplier_batch_code = get_supplier_batch_code_from_expense(expense)

    if not supplier_batch_code:
        return Expense.objects.filter(pk=expense.pk)

    return Expense.objects.filter(
        remarks__icontains=f'SUPPLIER_BATCH={supplier_batch_code}'
    )


def get_supplier_delivery_group_code(delivery):
    try:
        expense = delivery.supplier_purchase.expense
    except Expense.DoesNotExist:
        expense = None
    except AttributeError:
        expense = None

    return get_supplier_batch_code_from_expense(expense) or delivery.display_id


def summarize_customer_delivery_items(deliveries):
    item_labels = []

    for item in deliveries:
        if item.sale and item.sale.product:
            item_labels.append(f"{item.sale.product.product_name} - {item.sale.quantity_sold}")

    if not item_labels:
        return 'N/A'

    return ', '.join(item_labels)


def summarize_supplier_delivery_items(deliveries):
    item_labels = []

    for item in deliveries:
        purchase = item.supplier_purchase
        supplier_product = purchase.supplier_product
        product = supplier_product.product
        product_name = product.product_name if product else str(supplier_product)
        item_labels.append(f"{product_name} - {purchase.quantity}")

    if not item_labels:
        return 'N/A'

    return ', '.join(item_labels)



def summarize_invoice_items(invoices):
    item_labels = []

    for invoice in invoices:
        sale = invoice.sale
        if sale and sale.product:
            item_labels.append(f"{sale.product.product_name} - {sale.quantity_sold}")

    if not item_labels:
        return 'N/A'

    return ', '.join(item_labels)


def summarize_expense_items(expenses):
    item_labels = []

    for expense in expenses:
        product = expense.display_product
        product_name = product.product_name if product else 'N/A'
        item_labels.append(f"{product_name} - {expense.quantity}")

    if not item_labels:
        return 'N/A'

    return ', '.join(item_labels)



def build_invoice_receipt_items(invoices):
    receipt_items = []

    for invoice in invoices:
        sale = invoice.sale

        if not sale or not sale.product:
            continue

        receipt_items.append({
            'name': sale.product.product_name,
            'quantity': sale.quantity_sold,
            'unit_price': sale.product.price,
            'line_total': invoice.amount or sale.total_price or 0,
        })

    return receipt_items


def build_expense_receipt_items(expenses):
    receipt_items = []

    for expense in expenses:
        product = expense.display_product
        product_name = product.product_name if product else 'N/A'

        receipt_items.append({
            'name': product_name,
            'quantity': expense.quantity,
            'unit_price': expense.unit_price,
            'line_total': expense.total_price or 0,
        })

    return receipt_items


def summarize_statuses(records):
    statuses = []

    for record in records:
        status = getattr(record, 'status', None)
        if status and status not in statuses:
            statuses.append(status)

    if not statuses:
        return 'N/A'

    if len(statuses) == 1:
        return statuses[0]

    return 'Mixed'


def get_delivery_group_for_sale_map(sale_ids):
    delivery_group_map = {}

    if not sale_ids:
        return delivery_group_map

    delivery_rows = Delivery.objects.filter(
        sale_id__in=sale_ids
    ).values('sale_id', 'delivery_group', 'delivery_code', 'id')

    for delivery in delivery_rows:
        group_code = delivery['delivery_group'] or delivery['delivery_code']
        delivery_group_map[delivery['sale_id']] = group_code

    return delivery_group_map


def get_delivery_display_for_sale_map(sale_ids):
    delivery_display_map = {}

    if not sale_ids:
        return delivery_display_map

    delivery_rows = Delivery.objects.filter(
        sale_id__in=sale_ids
    ).values('sale_id', 'delivery_group', 'delivery_code', 'id')

    group_display_cache = {}

    for delivery in delivery_rows:
        group_code = delivery['delivery_group'] or delivery['delivery_code']

        if group_code not in group_display_cache:
            if delivery['delivery_group']:
                first_delivery = Delivery.objects.filter(
                    delivery_group=delivery['delivery_group']
                ).order_by('pk').first()

                group_display_cache[group_code] = (
                    first_delivery.display_id
                    if first_delivery
                    else delivery['delivery_code']
                )
            else:
                group_display_cache[group_code] = delivery['delivery_code']

        delivery_display_map[delivery['sale_id']] = group_display_cache[group_code]

    return delivery_display_map

def dashboard(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    total_products = Product.objects.filter(is_active=True).count()
    low_stock_count = Product.objects.filter(
        stock_quantity__gt=0,
        stock_quantity__lte=F('low_stock_threshold'),
        is_active=True
    ).count()
    out_of_stock_count = Product.objects.filter(
        stock_quantity=0,
        is_active=True
    ).count()
    recent_sales = Sale.objects.select_related('product').order_by('-sale_date')[:5]

    return render(
        request,
        'main/dashboard.html',
        {
            'current_user': current_user,
            'total_products': total_products,
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
            'recent_sales': recent_sales,
        }
    )

def sync_expense_income(expense):
    if expense.status not in ['Accepted', 'Converted']:
        return

    if expense.is_supplier_expense:
        expense.convert_to_supplier_purchase_and_delivery()


def remove_expense_income(expense):
    sale = expense.sale

    if sale:
        product = Product.objects.select_for_update().get(pk=sale.product.pk)
        product.stock_quantity += sale.quantity_sold
        product.save(update_fields=['stock_quantity'])

        Invoice.objects.filter(sale=sale).delete()
        expense.sale = None
        expense.save(update_fields=['sale', 'updated_at'])
        sale.delete()

    supplier_purchase = expense.supplier_purchase

    if supplier_purchase:
        supplier_product = SupplierProduct.objects.select_for_update().get(
            pk=supplier_purchase.supplier_product.pk
        )
        supplier_product.available_quantity += supplier_purchase.quantity
        supplier_product.save(update_fields=['available_quantity'])

        product = supplier_product.product

        if product:
            product = Product.objects.select_for_update().get(pk=product.pk)

            if product.stock_quantity < supplier_purchase.quantity:
                raise ValueError('Cannot reverse this supplier purchase because product stock is lower than the purchased quantity.')

            product.stock_quantity -= supplier_purchase.quantity
            product.save(update_fields=['stock_quantity'])

        SupplierDelivery.objects.filter(
            supplier_purchase=supplier_purchase
        ).delete()
        expense.supplier_purchase = None
        expense.save(update_fields=['supplier_purchase', 'updated_at'])
        supplier_purchase.delete()


def get_period_bounds(request):
    period = request.GET.get('period', 'all')
    today = timezone.localdate()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date and end_date:
        period = 'custom'

    if period == 'daily':
        start = end = today
    elif period == 'monthly':
        start = today.replace(day=1)
        end = today
    elif period == 'quarterly':
        start_month = ((today.month - 1) // 3) * 3 + 1
        start = today.replace(month=start_month, day=1)
        end = today
    elif period == 'bi_yearly':
        start = today.replace(month=1 if today.month <= 6 else 7, day=1)
        end = today
    elif period == 'yearly':
        start = today.replace(month=1, day=1)
        end = today
    elif period == 'custom' and start_date and end_date:
        start = parse_date(start_date)
        end = parse_date(end_date)

        if not start or not end:
            start = end = None
    else:
        start = end = None

    return period, start, end

def filter_queryset_by_period(queryset, field_name, start, end):
    if start and end:
        return queryset.filter(**{f'{field_name}__date__gte': start, f'{field_name}__date__lte': end})
    return queryset

def filter_queryset_by_date_period(queryset, field_name, start, end):
    if start and end:
        return queryset.filter(**{f'{field_name}__gte': start, f'{field_name}__lte': end})
    return queryset

def login_view(request):

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            admin_user = Admin.objects.get(
                username=username,
                password=password
            )

            if admin_user.pin_code and request.POST.get('pin_code') != admin_user.pin_code:
                return render(
                    request,
                    'main/login.html',
                    {
                        'pin_required': True,
                        'username': username,
                        'password': password,
                        'error': 'Enter your PIN to continue.'
                    }
                )

            request.session['admin_id'] = admin_user.pk

            return redirect('product_list')

        except Admin.DoesNotExist:
            return render(
                request,
                'main/login.html',
                {
                    'error': 'Invalid username or password'
                }
            )

    return render(request, 'main/login.html')

def logout_view(request):
    request.session.flush()
    return redirect('login')


def get_table_sort(request, allowed_sorts, default_ordering):
    sort = request.GET.get('sort', '').strip()
    order = request.GET.get('order', '').strip().lower()

    if sort not in allowed_sorts or order not in ('asc', 'desc'):
        return '', '', default_ordering

    field = allowed_sorts[sort]
    ordering = field if order == 'asc' else f'-{field}'

    return sort, order, [ordering]

def get_sort_query(search, sort, order):
    parts = []

    if search:
        parts.append(f'search={quote(search)}')

    if sort and order:
        parts.append(f'sort={quote(sort)}')
        parts.append(f'order={quote(order)}')

    return '&'.join(parts)

def product_list(request):

    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    search = request.GET.get('search', '').strip()

    product_sort_map = {
        'product': 'product_name',
        'product_id': 'id',
        'category': 'category__category_name',
        'supplier': 'supplier__supplier_name',
        'availability': 'stock_quantity',
        'price': 'price',
        'status': 'stock_quantity',
    }
    current_sort, current_order, product_ordering = get_table_sort(
        request,
        product_sort_map,
        ['product_name']
    )

    products = Product.objects.select_related(
        'category',
        'supplier'
    ).filter(
        Q(product_name__icontains=search) |
        Q(brand__icontains=search) |
        Q(model_name__icontains=search) |
        Q(category__category_name__icontains=search) |
        Q(supplier__supplier_name__icontains=search)
    ).order_by(*product_ordering)

    low_stock_count = Product.objects.filter(
        stock_quantity__gt=0,
        stock_quantity__lte=F('low_stock_threshold')
    ).count()

    out_of_stock_count = Product.objects.filter(
        stock_quantity=0
    ).count()

    paginator = Paginator(products, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    product_form = ProductForm()
    sale_form = SaleForm()
    categories = Category.objects.all().order_by('category_name')

    return render(
        request,
        'main/product_list.html',
        {
            'current_user': current_user,
            'page_obj': page_obj,
            'search': search,
            'product_form': product_form,
            'sale_form': sale_form,
            'categories': categories,
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
            'current_sort': current_sort,
            'current_order': current_order,
            'sort_query': get_sort_query(search, current_sort, current_order),
        }
    )

def add_product(request):

    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            return redirect('product_list')

    else:
        form = ProductForm()

    return render(
        request,
        'main/create_product.html',
        {
            'current_user': current_user,
            'form': form,
            'product_form': form
        }
    )

def product_detail(request, pk):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    product = get_object_or_404(
        Product.objects.select_related(
            'category',
            'supplier'
        ),
        pk=pk
    )

    related_sales = Sale.objects.filter(
        product=product
    ).order_by('-sale_date')[:10]

    total_sold = sum(
        sale.quantity_sold for sale in related_sales
    )

    return render(
        request,
        'main/product_detail.html',
        {
            'current_user': current_user,
            'product': product,
            'related_sales': related_sales,
            'total_sold': total_sold,
        }
    )

def edit_product(request, pk):

    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        form = ProductForm(
            request.POST,
            request.FILES,
            instance=product
        )

        if form.is_valid():
            form.save()

    return redirect('product_list')

def low_stock(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    search = request.GET.get('search', '').strip()

    low_stock_sort_map = {
        'product': 'product_name',
        'product_id': 'id',
        'category': 'category__category_name',
        'supplier': 'supplier__supplier_name',
        'stock': 'stock_quantity',
        'status': 'stock_quantity',
    }
    current_sort, current_order, low_stock_ordering = get_table_sort(
        request,
        low_stock_sort_map,
        ['stock_quantity', 'product_name']
    )

    products = Product.objects.select_related(
        'category',
        'supplier'
    ).filter(
        stock_quantity__lte=F('low_stock_threshold')
    ).filter(
        Q(product_name__icontains=search) |
        Q(brand__icontains=search) |
        Q(model_name__icontains=search) |
        Q(category__category_name__icontains=search) |
        Q(supplier__supplier_name__icontains=search)
    ).order_by(*low_stock_ordering)

    out_of_stock_count = products.filter(
        stock_quantity=0
    ).count()

    low_stock_count = products.filter(
        stock_quantity__gt=0
    ).count()

    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'main/low_stock.html',
        {
            'current_user': current_user,
            'low_stock_products': page_obj,
            'page_obj': page_obj,
            'search': search,
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
            'current_sort': current_sort,
            'current_order': current_order,
            'sort_query': get_sort_query(search, current_sort, current_order),
        }
    )


def delete_product(request, pk):

    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        try:
            product.delete()
        except ProtectedError:
            return HttpResponseForbidden(
                'Cannot delete this product because it is already used in sales or supplier records.'
            )

    return redirect('product_list')

def suppliers(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    search = request.GET.get('search', '').strip()

    supplier_sort_map = {
        'supplier': 'supplier_name',
        'email': 'email',
        'phone': 'contact_number',
        'address': 'address',
    }
    current_sort, current_order, supplier_ordering = get_table_sort(
        request,
        supplier_sort_map,
        ['supplier_name']
    )

    suppliers = Supplier.objects.filter(
        Q(supplier_name__icontains=search) |
        Q(email__icontains=search) |
        Q(contact_number__icontains=search) |
        Q(address__icontains=search)
    ).order_by(*supplier_ordering)

    return render(
        request,
        'main/suppliers.html',
        {
            'current_user': current_user,
            'suppliers': suppliers,
            'search': search,
            'current_sort': current_sort,
            'current_order': current_order,
        }
    )

def create_supplier(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    if request.method == 'POST':
        form = SupplierForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('suppliers')

    else:
        form = SupplierForm()

    return render(
        request,
        'main/create_supplier.html',
        {
            'current_user': current_user,
            'form': form,
            'supplier_form': form
        }
    )

def edit_supplier(request, pk):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    supplier = get_object_or_404(Supplier, pk=pk)

    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)

        if form.is_valid():
            form.save()

    return redirect('suppliers')

def delete_supplier(request, pk):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    supplier = get_object_or_404(Supplier, pk=pk)

    if request.method == 'POST':
        try:
            supplier.delete()
        except ProtectedError:
            return HttpResponseForbidden(
                'Cannot delete this supplier because it still has linked supplier products.'
            )

    return redirect('suppliers')
    
def supplier_products(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    search = request.GET.get('search', '').strip()

    supplier_product_sort_map = {
        'company': 'supplier__supplier_name',
        'product': 'product__product_name',
        'brand': 'product__brand',
        'model': 'product__model_name',
        'unit_price': 'unit_price',
        'available_stock': 'available_quantity',
    }
    current_sort, current_order, supplier_product_ordering = get_table_sort(
        request,
        supplier_product_sort_map,
        ['product__product_name']
    )

    supplier_products = SupplierProduct.objects.filter(
        Q(supplier__supplier_name__icontains=search) |
        Q(product__product_name__icontains=search) |
        Q(product__brand__icontains=search) |
        Q(product__model_name__icontains=search)
    ).select_related('supplier', 'product').order_by(*supplier_product_ordering)

    products = Product.objects.all().order_by('product_name')
    suppliers_list = Supplier.objects.all().order_by('supplier_name')

    return render(
        request,
        'main/supplier_products.html',
        {
            'current_user': current_user,
            'supplier_products': supplier_products,
            'products': products,
            'suppliers_list': suppliers_list,
            'search': search,
            'current_sort': current_sort,
            'current_order': current_order,
        }
    )
    
def add_supplier_products(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    if request.method == 'POST':
        form = SupplierProductForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('supplier_products')

    else:
        form = SupplierProductForm()

    return render(
        request,
        'main/add_supplier_products.html',
        {
            'current_user': current_user,
            'form': form
        }
    )
    
def edit_supplier_product(request, pk):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    supplier_product = get_object_or_404(SupplierProduct, pk=pk)

    if request.method == 'POST':
        form = SupplierProductForm(request.POST, instance=supplier_product)

        if form.is_valid():
            form.save()

    return redirect('supplier_products')

def delete_supplier_product(request, pk):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    supplier_product = get_object_or_404(SupplierProduct, pk=pk)

    if request.method == 'POST':
        try:
            supplier_product.delete()
        except ProtectedError:
            return HttpResponseForbidden(
                'Cannot delete this supplier product because it already has purchase records.'
            )

    return redirect('supplier_products')

def buy_supplier_products(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    supplier_expenses = Expense.objects.select_related(
        'supplier_product',
        'supplier_product__supplier',
        'supplier_product__product',
        'supplier_purchase'
    ).filter(
        supplier_product__isnull=False
    ).order_by('-expense_date', '-created_at')

    supplier_products = SupplierProduct.objects.select_related(
        'supplier',
        'product'
    ).order_by(
        'supplier__supplier_name',
        'product__product_name'
    )

    form = SupplierPurchaseForm()

    def add_supplier_purchase_error(message):
        if not hasattr(form, 'cleaned_data'):
            form.cleaned_data = {}
        form.add_error(None, message)

    selected_product_id = request.GET.get('product')
    selected_supplier_products = SupplierProduct.objects.none()

    if selected_product_id:
        selected_supplier_products = SupplierProduct.objects.filter(
            product_id=selected_product_id
        ).select_related(
            'supplier',
            'product'
        )

    if request.method == 'POST':
        product_ids = request.POST.getlist('supplier_product_ids[]')
        quantities = request.POST.getlist('quantities[]')

        if not product_ids:
            add_supplier_purchase_error(
                'Please add at least one supplier product before creating a supplier expense.'
            )

        elif len(product_ids) != len(quantities):
            add_supplier_purchase_error(
                'The selected supplier products and quantities do not match.'
            )

        else:
            has_error = False
            purchase_quantities = {}

            for product_id, quantity in zip(product_ids, quantities):
                try:
                    product_id = int(product_id)
                    quantity = int(quantity)
                except (TypeError, ValueError):
                    add_supplier_purchase_error('Supplier product and quantity must be valid numbers.')
                    has_error = True
                    continue

                if quantity <= 0:
                    add_supplier_purchase_error('Quantity must be greater than zero.')
                    has_error = True
                    continue

                purchase_quantities[product_id] = (
                    purchase_quantities.get(product_id, 0) + quantity
                )

            if not purchase_quantities and not has_error:
                add_supplier_purchase_error(
                    'Please select a supplier product and enter a valid quantity.'
                )
                has_error = True

            supplier_product_map = SupplierProduct.objects.filter(
                pk__in=purchase_quantities.keys()
            ).select_related('supplier', 'product').in_bulk()

            selected_supplier_ids = {
                supplier_product.supplier_id
                for supplier_product in supplier_product_map.values()
                if supplier_product
            }

            if len(selected_supplier_ids) > 1:
                add_supplier_purchase_error(
                    'Please select products from only one supplier when purchasing from the suppliers. Create a separate supplier expense for another supplier.'
                )
                has_error = True

            for product_id, quantity in purchase_quantities.items():
                supplier_product = supplier_product_map.get(product_id)

                if not supplier_product:
                    add_supplier_purchase_error('Selected supplier product does not exist.')
                    has_error = True
                    continue

                if quantity > supplier_product.available_quantity:
                    product_name = (
                        supplier_product.product.product_name
                        if supplier_product.product
                        else str(supplier_product)
                    )
                    add_supplier_purchase_error(
                        f'Not enough supplier stock for {product_name}.'
                    )
                    has_error = True

            if not has_error:
                with transaction.atomic():
                    locked_supplier_products = {
                        item.pk: item
                        for item in SupplierProduct.objects.select_for_update().filter(
                            pk__in=purchase_quantities.keys()
                        ).select_related('supplier', 'product')
                    }

                    for product_id, quantity in purchase_quantities.items():
                        supplier_product = locked_supplier_products.get(product_id)

                        if not supplier_product or quantity > supplier_product.available_quantity:
                            add_supplier_purchase_error(
                                'Not enough supplier stock available.'
                            )
                            has_error = True
                            break

                    if not has_error:
                        supplier_batch_code = generate_supplier_batch_code()

                        for product_id, quantity in purchase_quantities.items():
                            supplier_product = locked_supplier_products[product_id]

                            Expense.objects.create(
                                supplier_product=supplier_product,
                                quantity=quantity,
                                status='Sent',
                                remarks=f'SUPPLIER_BATCH={supplier_batch_code} Auto-generated from Buy Supplier Products. Accept or convert this expense to create the supplier purchase and delivery.'
                            )

                if not has_error:
                    return redirect('buy_supplier_products')

    return render(
        request,
        'main/buy_supplier_products.html',
        {
            'current_user': current_user,
            'form': form,
            'supplier_expenses': supplier_expenses,
            'purchases': supplier_expenses,
            'selected_product_id': selected_product_id,
            'selected_supplier_products': selected_supplier_products,
            'supplier_products': supplier_products
        }
    )

def edit_supplier_purchase(request, pk):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    purchase = get_object_or_404(SupplierPurchase, pk=pk)

    if request.method == 'POST':
        old_supplier_product = purchase.supplier_product
        old_quantity = purchase.quantity

        form = SupplierPurchaseForm(request.POST, instance=purchase)

        if form.is_valid():
            with transaction.atomic():
                edited_purchase = form.save(commit=False)
                new_supplier_product = edited_purchase.supplier_product
                new_quantity = edited_purchase.quantity

                locked_products = SupplierProduct.objects.select_for_update().filter(
                    pk__in=[
                        old_supplier_product.pk,
                        new_supplier_product.pk
                    ]
                ).select_related('supplier', 'product')

                locked_product_map = {
                    item.pk: item
                    for item in locked_products
                }

                old_supplier_product = locked_product_map[old_supplier_product.pk]
                new_supplier_product = locked_product_map[new_supplier_product.pk]

                old_inventory_product = old_supplier_product.product
                new_inventory_product = new_supplier_product.product

                if old_supplier_product.pk == new_supplier_product.pk:
                    quantity_difference = new_quantity - old_quantity

                    if quantity_difference > old_supplier_product.available_quantity:
                        form.add_error(
                            None,
                            'Not enough supplier stock available.'
                        )
                        return redirect('buy_supplier_products')

                    if (
                        old_inventory_product and
                        old_inventory_product.stock_quantity + quantity_difference < 0
                    ):
                        form.add_error(
                            None,
                            'Cannot reduce product stock below zero.'
                        )
                        return redirect('buy_supplier_products')

                    new_supplier_product.available_quantity -= quantity_difference
                    new_supplier_product.save(update_fields=['available_quantity'])

                    if old_inventory_product:
                        old_inventory_product.stock_quantity += quantity_difference
                        old_inventory_product.save(update_fields=['stock_quantity'])
                else:
                    if new_quantity > new_supplier_product.available_quantity:
                        form.add_error(
                            None,
                            'Not enough supplier stock available.'
                        )
                        return redirect('buy_supplier_products')

                    if old_inventory_product and old_inventory_product.stock_quantity < old_quantity:
                        form.add_error(
                            None,
                            'Cannot reduce product stock below zero.'
                        )
                        return redirect('buy_supplier_products')

                    old_supplier_product.available_quantity += old_quantity
                    old_supplier_product.save(update_fields=['available_quantity'])

                    if old_inventory_product:
                        old_inventory_product.stock_quantity -= old_quantity
                        old_inventory_product.save(update_fields=['stock_quantity'])

                    new_supplier_product.available_quantity -= new_quantity
                    new_supplier_product.save(update_fields=['available_quantity'])

                    if new_inventory_product:
                        new_inventory_product.stock_quantity += new_quantity
                        new_inventory_product.save(update_fields=['stock_quantity'])

                edited_purchase.supplier_product = new_supplier_product
                edited_purchase.total_price = (
                    new_supplier_product.unit_price *
                    edited_purchase.quantity
                )
                edited_purchase.save(update_fields=[
                    'supplier_product',
                    'quantity',
                    'total_price'
                ])

                SupplierDelivery.objects.filter(
                    supplier_purchase=edited_purchase
                ).update(
                    delivery_address=new_supplier_product.supplier.address,
                    status='Delivered'
                )

                Expense.objects.update_or_create(
                    supplier_purchase=edited_purchase,
                    defaults={
                        'supplier_product': new_supplier_product,
                        'quantity': new_quantity,
                        'status': 'Sent',
                        'remarks': 'Auto-updated from supplier purchase edit.'
                    }
                )

    return redirect('buy_supplier_products')

def delete_supplier_purchase(request, pk):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    purchase = get_object_or_404(SupplierPurchase, pk=pk)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                supplier_product = SupplierProduct.objects.select_for_update().get(
                    pk=purchase.supplier_product.pk
                )

                product = supplier_product.product

                if product:
                    product = Product.objects.select_for_update().get(pk=product.pk)

                    if product.stock_quantity < purchase.quantity:
                        raise ValueError(
                            'Cannot delete this supplier purchase because product stock is lower than the purchased quantity.'
                        )

                    product.stock_quantity -= purchase.quantity
                    product.save(update_fields=['stock_quantity'])

                supplier_product.available_quantity += purchase.quantity
                supplier_product.save(update_fields=['available_quantity'])

                SupplierDelivery.objects.filter(
                    supplier_purchase=purchase
                ).delete()

                Expense.objects.filter(
                    supplier_purchase=purchase
                ).delete()

                purchase.delete()
        except ValueError as error:
            return HttpResponseForbidden(str(error))

    return redirect('buy_supplier_products')

def delivery_list(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    delivery_sort_map = {
        'delivery_id': 'delivery_group',
        'customer': 'customer_name',
        'contact': 'contact_number',
        'address': 'delivery_address',
        'product_sale': 'sale__product__product_name',
        'expected_date': 'expected_delivery_date',
        'status': 'status',
    }
    current_sort, current_order, delivery_ordering = get_table_sort(
        request,
        delivery_sort_map,
        ['-created_at']
    )

    delivery_queryset = Delivery.objects.select_related(
        'sale',
        'sale__product'
    ).order_by(*delivery_ordering)

    grouped_delivery_map = {}

    for delivery in delivery_queryset:
        group_key = delivery.delivery_group or f'pk-{delivery.pk}'

        if group_key not in grouped_delivery_map:
            delivery.group_items = []
            grouped_delivery_map[group_key] = delivery

        grouped_delivery_map[group_key].group_items.append(delivery)

    deliveries = list(grouped_delivery_map.values())

    for delivery in deliveries:
        group_items = getattr(delivery, 'group_items', [delivery])
        delivery.group_display_id = delivery.display_id
        delivery.group_product_summary = summarize_customer_delivery_items(group_items)
        delivery.group_total_quantity = sum(
            item.sale.quantity_sold for item in group_items if item.sale
        )
        delivery.group_status = summarize_statuses(group_items)

    return render(
        request,
        'main/delivery_list.html',
        {
            'current_user': current_user,
            'deliveries': deliveries,
            'current_sort': current_sort,
            'current_order': current_order,
        }
    )
    
def delivery_detail(request, pk):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    delivery = get_object_or_404(
        Delivery.objects.select_related('sale', 'sale__product'),
        pk=pk
    )

    if delivery.delivery_group:
        delivery_items = Delivery.objects.select_related(
            'sale',
            'sale__product'
        ).filter(
            delivery_group=delivery.delivery_group
        ).order_by('pk')
    else:
        delivery_items = Delivery.objects.select_related(
            'sale',
            'sale__product'
        ).filter(
            pk=delivery.pk
        )

    total_amount = sum(
        item.sale.total_price for item in delivery_items if item.sale
    )

    total_quantity = sum(
        item.sale.quantity_sold for item in delivery_items if item.sale
    )

    return render(
        request,
        'main/delivery_detail.html',
        {
            'current_user': current_user,
            'delivery': delivery,
            'delivery_items': delivery_items,
            'total_amount': total_amount,
            'total_quantity': total_quantity,
        }
    )

def create_delivery(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    products = Product.objects.filter(
        is_active=True
    ).order_by('product_name')

    if request.method == 'POST':
        delivery_form = DeliveryForm(request.POST)
        sale_form = SaleForm(request.POST)

        product_ids = request.POST.getlist('product_ids[]')
        quantities = request.POST.getlist('quantities[]')
        customer_name = request.POST.get('customer_name', '').strip()
        selected_items = []
        custom_errors = []

        delivery_is_valid = delivery_form.is_valid()

        if not product_ids:
            custom_errors.append('Please add at least one product to the delivery.')

        if len(product_ids) != len(quantities):
            custom_errors.append('The selected products and quantities do not match.')

        if not customer_name:
            custom_errors.append('Customer name is required.')

        selected_quantities = {}

        for product_id, quantity in zip(product_ids, quantities):
            try:
                product_id = int(product_id)
                quantity = int(quantity)
            except (TypeError, ValueError):
                custom_errors.append('One selected product or quantity is invalid.')
                continue

            if quantity <= 0:
                custom_errors.append('Quantity must be greater than zero.')
                continue

            selected_quantities[product_id] = (
                selected_quantities.get(product_id, 0) + quantity
            )

        selected_items = list(selected_quantities.items())

        if product_ids and not selected_items and not custom_errors:
            custom_errors.append('Please select a product and enter a valid quantity.')

        for error in custom_errors:
            delivery_form.add_error(None, error)

        if delivery_is_valid and not delivery_form.errors and selected_items:
            delivery_group = generate_delivery_group_code()

            with transaction.atomic():
                locked_products = {
                    product.pk: product
                    for product in Product.objects.select_for_update().filter(
                        pk__in=[product_id for product_id, quantity in selected_items],
                        is_active=True
                    )
                }

                for product_id, quantity in selected_items:
                    product = locked_products.get(product_id)

                    if not product:
                        delivery_form.add_error(None, 'One selected product is invalid or inactive.')
                        break

                    if quantity > product.stock_quantity:
                        delivery_form.add_error(None, f'Not enough stock for {product.product_name}.')
                        break

                if delivery_form.errors:
                    transaction.set_rollback(True)
                else:
                    delivery_data = delivery_form.cleaned_data

                    try:
                        for product_id, quantity in selected_items:
                            product = locked_products[product_id]

                            sale = Sale.objects.create(
                                product=product,
                                customer_name=customer_name,
                                quantity_sold=quantity
                            )

                            Delivery.objects.create(
                                sale=sale,
                                customer_name=customer_name,
                                contact_number=delivery_data.get('contact_number'),
                                delivery_address=delivery_data.get('delivery_address'),
                                expected_delivery_date=delivery_data.get('expected_delivery_date'),
                                status=delivery_data.get('status') or 'Pending',
                                delivery_group=delivery_group
                            )

                            Invoice.objects.get_or_create(
                                sale=sale,
                                defaults={'status': 'Paid'}
                            )
                    except ValueError as error:
                        delivery_form.add_error(None, str(error))
                        transaction.set_rollback(True)

            if not delivery_form.errors:
                return redirect('delivery_list')

    else:
        sale_form = SaleForm()
        delivery_form = DeliveryForm()

    return render(
        request,
        'main/create_delivery.html',
        {
            'current_user': current_user,
            'sale_form': sale_form,
            'delivery_form': delivery_form,
            'form': delivery_form,
            'products': products,
        }
    )

def edit_delivery(request, pk):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    delivery = get_object_or_404(Delivery, pk=pk)

    if request.method == 'POST':
        form = DeliveryForm(request.POST, instance=delivery)

        if form.is_valid():
            with transaction.atomic():
                edited_delivery = form.save(commit=False)

                delivery_items = Delivery.objects.select_for_update().filter(
                    delivery_group=delivery.delivery_group
                ) if delivery.delivery_group else Delivery.objects.select_for_update().filter(pk=delivery.pk)

                customer_name = request.POST.get('customer_name', edited_delivery.customer_name)

                for item in delivery_items:
                    if item.sale:
                        item.sale.customer_name = customer_name
                        item.sale.save(update_fields=['customer_name'])

                    item.customer_name = customer_name
                    item.contact_number = edited_delivery.contact_number
                    item.delivery_address = edited_delivery.delivery_address
                    item.expected_delivery_date = edited_delivery.expected_delivery_date
                    item.status = edited_delivery.status
                    item.save(update_fields=[
                        'customer_name',
                        'contact_number',
                        'delivery_address',
                        'expected_delivery_date',
                        'status',
                        'updated_at'
                    ])

    return redirect('delivery_list')

def delete_delivery(request, pk):

    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    delivery = get_object_or_404(Delivery, pk=pk)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                delivery_items = Delivery.objects.select_for_update().filter(
                    delivery_group=delivery.delivery_group
                ) if delivery.delivery_group else Delivery.objects.select_for_update().filter(pk=delivery.pk)

                for item in delivery_items:
                    sale = item.sale

                    if sale:
                        product = Product.objects.select_for_update().get(
                            pk=sale.product.pk
                        )

                        product.stock_quantity += sale.quantity_sold
                        product.save(update_fields=['stock_quantity'])

                        Invoice.objects.filter(sale=sale).delete()
                        item.delete()
                        sale.delete()
                    else:
                        item.delete()

        except ProtectedError:
            return HttpResponseForbidden(
                'Cannot delete this delivery because it is linked to protected records.'
            )

    return redirect('delivery_list')

def supplier_delivery_list(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    supplier_delivery_queryset = SupplierDelivery.objects.select_related(
        'supplier_purchase',
        'supplier_purchase__supplier_product',
        'supplier_purchase__supplier_product__supplier',
        'supplier_purchase__supplier_product__product'
    ).order_by('-created_at')

    grouped_supplier_delivery_map = {}

    for delivery in supplier_delivery_queryset:
        group_key = get_supplier_delivery_group_code(delivery)

        if group_key not in grouped_supplier_delivery_map:
            delivery.group_items = []
            delivery.group_display_id = group_key
            grouped_supplier_delivery_map[group_key] = delivery

        grouped_supplier_delivery_map[group_key].group_items.append(delivery)

    deliveries = list(grouped_supplier_delivery_map.values())

    for delivery in deliveries:
        group_items = getattr(delivery, 'group_items', [delivery])
        first_purchase = delivery.supplier_purchase
        first_supplier_product = first_purchase.supplier_product if first_purchase else None
        first_supplier = first_supplier_product.supplier if first_supplier_product else None

        delivery.group_purchase_summary = summarize_supplier_delivery_items(group_items)
        delivery.group_total_quantity = sum(
            item.supplier_purchase.quantity for item in group_items
            if item.supplier_purchase
        )
        delivery.group_total_amount = sum(
            item.supplier_purchase.total_price or 0 for item in group_items
            if item.supplier_purchase
        )
        delivery.group_status = summarize_statuses(group_items)
        delivery.group_item_count = len(group_items)
        delivery.group_company_name = first_supplier.supplier_name if first_supplier else 'N/A'
        delivery.group_address = first_supplier.address if first_supplier else 'N/A'
        delivery.group_contact_number = first_supplier.contact_number if first_supplier else 'N/A'

    return render(
        request,
        'main/supplier_delivery_list.html',
        {
            'current_user': current_user,
            'deliveries': deliveries
        }

    )


def supplier_delivery_details(request, pk):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    delivery = get_object_or_404(
        SupplierDelivery.objects.select_related(
            'supplier_purchase',
            'supplier_purchase__supplier_product',
            'supplier_purchase__supplier_product__supplier',
            'supplier_purchase__supplier_product__product'
        ),
        pk=pk
    )

    group_code = get_supplier_delivery_group_code(delivery)
    delivery_items = []

    for item in SupplierDelivery.objects.select_related(
        'supplier_purchase',
        'supplier_purchase__supplier_product',
        'supplier_purchase__supplier_product__supplier',
        'supplier_purchase__supplier_product__product'
    ).order_by('pk'):
        if get_supplier_delivery_group_code(item) == group_code:
            delivery_items.append(item)

    if not delivery_items:
        delivery_items = [delivery]

    total_quantity = sum(
        item.supplier_purchase.quantity for item in delivery_items
        if item.supplier_purchase
    )
    total_amount = sum(
        item.supplier_purchase.total_price or 0 for item in delivery_items
        if item.supplier_purchase
    )
    statuses = summarize_statuses(delivery_items)

    return render(
        request,
        'main/supplier_delivery_details.html',
        {
            'current_user': current_user,
            'delivery': delivery,
            'delivery_items': delivery_items,
            'group_display_id': group_code,
            'total_quantity': total_quantity,
            'total_amount': total_amount,
            'group_status': statuses,
        }
    )
    
def create_supplier_delivery(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    if request.method == 'POST':
        form = SupplierDeliveryForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('supplier_delivery_list')

    else:
        form = SupplierDeliveryForm()

    return render(
        request,
        'main/create_supplier_delivery.html',
        {
            'current_user': current_user,
            'form': form
        }
    )

def edit_supplier_delivery(request, pk):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    delivery = get_object_or_404(SupplierDelivery, pk=pk)

    if request.method == 'POST':
        form = SupplierDeliveryForm(request.POST, instance=delivery)

        if form.is_valid():
            edited_delivery = form.save(commit=False)
            group_code = get_supplier_delivery_group_code(delivery)

            related_deliveries = []
            for item in SupplierDelivery.objects.select_related('supplier_purchase').all():
                if get_supplier_delivery_group_code(item) == group_code:
                    related_deliveries.append(item.pk)

            SupplierDelivery.objects.filter(pk__in=related_deliveries or [delivery.pk]).update(
                delivery_address=edited_delivery.delivery_address,
                expected_delivery_date=edited_delivery.expected_delivery_date,
                status=edited_delivery.status,
                updated_at=timezone.now()
            )

    return redirect('supplier_delivery_list')

def delete_supplier_delivery(request, pk):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    delivery = get_object_or_404(SupplierDelivery, pk=pk)

    if request.method == 'POST':
        group_code = get_supplier_delivery_group_code(delivery)
        related_delivery_ids = []

        for item in SupplierDelivery.objects.select_related('supplier_purchase').all():
            if get_supplier_delivery_group_code(item) == group_code:
                related_delivery_ids.append(item.pk)

        SupplierDelivery.objects.filter(pk__in=related_delivery_ids or [delivery.pk]).delete()

    return redirect('supplier_delivery_list')

def expenses(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    search = request.GET.get('search', '').strip()

    period, start, end = get_period_bounds(request)

    expense_queryset = Expense.objects.select_related(
        'product',
        'sale',
        'supplier_product',
        'supplier_product__supplier',
        'supplier_product__product',
        'supplier_purchase'
    ).filter(
        Q(expense_code__icontains=search) |
        Q(customer_name__icontains=search) |
        Q(product__product_name__icontains=search) |
        Q(supplier_product__supplier__supplier_name__icontains=search) |
        Q(supplier_product__product__product_name__icontains=search) |
        Q(status__icontains=search) |
        Q(remarks__icontains=search)
    ).order_by('-expense_date', '-created_at')

    expense_queryset = filter_queryset_by_date_period(expense_queryset, 'expense_date', start, end)

    grouped_expense_map = {}

    for expense in expense_queryset:
        supplier_batch_code = get_supplier_batch_code_from_expense(expense)
        group_key = supplier_batch_code if supplier_batch_code else f'expense-{expense.pk}'

        if group_key not in grouped_expense_map:
            expense.group_items = []
            expense.group_key = group_key
            expense.group_display_id = supplier_batch_code or expense.display_id
            expense.group_supplier_batch_code = supplier_batch_code
            grouped_expense_map[group_key] = expense

        grouped_expense_map[group_key].group_items.append(expense)

    expense_list = list(grouped_expense_map.values())

    for expense in expense_list:
        group_items = getattr(expense, 'group_items', [expense])
        expense.group_product_summary = summarize_expense_items(group_items)
        expense.group_receipt_items = build_expense_receipt_items(group_items)
        expense.group_total_quantity = sum(item.quantity for item in group_items)
        expense.group_total_price = sum(item.total_price or 0 for item in group_items)
        expense.group_status = summarize_statuses(group_items)
        expense.group_item_count = len(group_items)
        expense.group_company_name = expense.company_name
        expense.group_clean_remarks = strip_supplier_batch_marker(expense.remarks)

    return render(
        request,
        'main/expenses.html',
        {
            'current_user': current_user,
            'expenses': expense_list,
            'search': search,
            'period': period,
            'start_date': start,
            'end_date': end,
            'expense_form': ExpenseForm()
        }

    )


def expense_details(request, pk):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    expense = get_object_or_404(
        Expense.objects.select_related(
            'product',
            'sale',
            'supplier_product',
            'supplier_product__supplier',
            'supplier_product__product',
            'supplier_purchase'
        ),
        pk=pk
    )

    expense_items = list(
        get_expense_group_queryset(expense).select_related(
            'product',
            'sale',
            'supplier_product',
            'supplier_product__supplier',
            'supplier_product__product',
            'supplier_purchase'
        ).order_by('pk')
    )

    supplier_batch_code = get_supplier_batch_code_from_expense(expense)
    group_display_id = supplier_batch_code or expense.display_id
    total_quantity = sum(item.quantity for item in expense_items)
    total_amount = sum(item.total_price or 0 for item in expense_items)
    group_status = summarize_statuses(expense_items)
    product_summary = summarize_expense_items(expense_items)

    return render(
        request,
        'main/expense_details.html',
        {
            'current_user': current_user,
            'expense': expense,
            'expense_items': expense_items,
            'group_display_id': group_display_id,
            'total_quantity': total_quantity,
            'total_amount': total_amount,
            'group_status': group_status,
            'product_summary': product_summary,
            'clean_remarks': strip_supplier_batch_marker(expense.remarks),
        }
    )
    
def create_expense(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    if request.method == 'POST' and not CREATE_EXPENSE_PAGE_DISABLED:
        form = ExpenseForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                expense = form.save()
                sync_expense_income(expense)
            return redirect('expenses')

    else:
        form = ExpenseForm()

    return render(
        request,
        'main/create_expense.html',
        {
            'current_user': current_user,
            'form': form
        }
    )


def edit_expense(request, pk):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    expense = get_object_or_404(Expense, pk=pk)

    if request.method == 'POST':
        group_expenses = get_expense_group_queryset(expense)
        supplier_batch_code = get_supplier_batch_code_from_expense(expense)

        company_name = request.POST.get('company_name', '').strip()
        expense_date_value = request.POST.get('expense_date') or None
        valid_until_value = request.POST.get('valid_until') or None
        expense_date = parse_date(expense_date_value) if expense_date_value else None
        valid_until = parse_date(valid_until_value) if valid_until_value else None
        status = request.POST.get('status', '').strip()
        remarks = request.POST.get('remarks', '').strip()

        if supplier_batch_code and f'SUPPLIER_BATCH={supplier_batch_code}' not in remarks:
            remarks = f'{remarks} SUPPLIER_BATCH={supplier_batch_code}'.strip()

        with transaction.atomic():
            locked_expenses = list(
                group_expenses.select_for_update().select_related(
                    'supplier_product',
                    'supplier_product__supplier',
                    'supplier_purchase',
                    'sale'
                )
            )

            supplier_ids = {
                item.supplier_product.supplier_id
                for item in locked_expenses
                if item.supplier_product_id and item.supplier_product and item.supplier_product.supplier_id
            }

            if company_name and supplier_ids:
                Supplier.objects.filter(pk__in=supplier_ids).update(supplier_name=company_name)

            for item in locked_expenses:
                previous_income_status = item.status in ['Accepted', 'Converted']
                new_income_status = status in ['Accepted', 'Converted']

                if previous_income_status and not new_income_status:
                    remove_expense_income(item)

                update_fields = [
                    'expense_date',
                    'valid_until',
                    'status',
                    'remarks',
                    'updated_at'
                ]

                if not item.supplier_product_id:
                    item.customer_name = company_name
                    update_fields.insert(0, 'customer_name')

                item.expense_date = expense_date or item.expense_date
                item.valid_until = valid_until
                item.status = status
                item.remarks = remarks
                item.save(update_fields=update_fields)

                if new_income_status:
                    sync_expense_income(item)

    return redirect('expenses')


def delete_expense(request, pk):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    expense = get_object_or_404(Expense, pk=pk)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                grouped_expenses = list(
                    get_expense_group_queryset(expense).select_for_update().select_related(
                        'sale',
                        'sale__product',
                        'supplier_purchase',
                        'supplier_purchase__supplier_product',
                        'supplier_purchase__supplier_product__product'
                    )
                )

                for item in grouped_expenses:
                    remove_expense_income(item)

                Expense.objects.filter(
                    pk__in=[item.pk for item in grouped_expenses]
                ).delete()
        except ValueError as error:
            return HttpResponseForbidden(str(error))

    return redirect('expenses')


def invoices(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    search = request.GET.get('search', '').strip()

    period, start, end = get_period_bounds(request)

    invoice_queryset = Invoice.objects.select_related(
        'sale',
        'sale__product'
    ).filter(
        Q(invoice_code__icontains=search) |
        Q(sale__customer_name__icontains=search) |
        Q(sale__product__product_name__icontains=search) |
        Q(status__icontains=search)
    ).order_by('-invoice_date', '-created_at')

    invoice_queryset = filter_queryset_by_date_period(invoice_queryset, 'invoice_date', start, end)

    invoice_rows = list(invoice_queryset)
    sale_ids = [invoice.sale_id for invoice in invoice_rows if invoice.sale_id]
    delivery_group_map = get_delivery_group_for_sale_map(sale_ids)
    delivery_display_map = get_delivery_display_for_sale_map(sale_ids)

    grouped_invoice_map = {}

    for invoice in invoice_rows:
        group_key = delivery_group_map.get(invoice.sale_id) or f'invoice-{invoice.pk}'

        if group_key not in grouped_invoice_map:
            invoice.group_items = []
            invoice.group_key = group_key
            invoice.group_delivery_code = delivery_display_map.get(invoice.sale_id, '')
            invoice.group_display_id = delivery_display_map.get(invoice.sale_id) or invoice.display_id
            grouped_invoice_map[group_key] = invoice

        grouped_invoice_map[group_key].group_items.append(invoice)

    invoice_list = list(grouped_invoice_map.values())

    for invoice in invoice_list:
        group_items = getattr(invoice, 'group_items', [invoice])
        invoice.group_product_summary = summarize_invoice_items(group_items)
        invoice.group_receipt_items = build_invoice_receipt_items(group_items)
        invoice.group_total_quantity = sum(item.sale.quantity_sold for item in group_items if item.sale)
        invoice.group_total_amount = sum(item.amount or 0 for item in group_items)
        invoice.group_status = summarize_statuses(group_items)
        invoice.group_item_count = len(group_items)
        invoice.group_sale_summary = ', '.join(f"#{item.sale.pk}" for item in group_items if item.sale) or 'N/A'
        invoice.group_customer_name = invoice.sale.customer_name if invoice.sale else 'N/A'

    return render(
        request,
        'main/invoices.html',
        {
            'current_user': current_user,
            'invoices': invoice_list,
            'search': search,
            'period': period,
            'start_date': start,
            'end_date': end,
            'invoice_form': InvoiceForm()
        }

    )


def invoice_details(request, pk):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    invoice = get_object_or_404(
        Invoice.objects.select_related('sale', 'sale__product'),
        pk=pk
    )

    invoice_items = list(
        get_invoice_group_queryset(invoice).select_related(
            'sale',
            'sale__product'
        ).order_by('pk')
    )

    sale_ids = [item.sale_id for item in invoice_items if item.sale_id]
    delivery_display_map = get_delivery_display_for_sale_map(sale_ids)
    group_display_id = delivery_display_map.get(invoice.sale_id) or invoice.display_id
    total_quantity = sum(item.sale.quantity_sold for item in invoice_items if item.sale)
    total_amount = sum(item.amount or 0 for item in invoice_items)
    group_status = summarize_statuses(invoice_items)
    product_summary = summarize_invoice_items(invoice_items)

    return render(
        request,
        'main/invoice_details.html',
        {
            'current_user': current_user,
            'invoice': invoice,
            'invoice_items': invoice_items,
            'group_display_id': group_display_id,
            'total_quantity': total_quantity,
            'total_amount': total_amount,
            'group_status': group_status,
            'product_summary': product_summary,
        }
    )


def create_invoice(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    if request.method == 'POST' and not CREATE_INVOICE_PAGE_DISABLED:
        form = InvoiceForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('invoices')

    else:
        form = InvoiceForm()

    return render(
        request,
        'main/create_invoice.html',
        {
            'current_user': current_user,
            'form': form
        }
    )


def edit_invoice(request, pk):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    invoice = get_object_or_404(Invoice, pk=pk)

    if request.method == 'POST':
        group_invoices = get_invoice_group_queryset(invoice)

        customer_name = request.POST.get('customer_name', '').strip()
        invoice_date = request.POST.get('invoice_date') or None
        due_date = request.POST.get('due_date') or None
        status = request.POST.get('status', '').strip()
        notes = request.POST.get('notes', '').strip()

        with transaction.atomic():
            locked_invoices = list(group_invoices.select_for_update().select_related('sale'))
            sale_ids = [item.sale_id for item in locked_invoices if item.sale_id]

            if customer_name and sale_ids:
                Sale.objects.filter(pk__in=sale_ids).update(customer_name=customer_name)
                Delivery.objects.filter(sale_id__in=sale_ids).update(customer_name=customer_name)

            Invoice.objects.filter(pk__in=[item.pk for item in locked_invoices]).update(
                invoice_date=invoice_date,
                due_date=due_date,
                status=status,
                notes=notes
            )

    return redirect('invoices')


def delete_invoice(request, pk):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    invoice = get_object_or_404(Invoice, pk=pk)

    if request.method == 'POST':
        invoice_ids = list(
            get_invoice_group_queryset(invoice).values_list('pk', flat=True)
        )
        Invoice.objects.filter(pk__in=invoice_ids or [invoice.pk]).delete()

    return redirect('invoices')

def record_sale(request):

    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    search = request.GET.get('search', '').strip()

    products = Product.objects.filter(
        Q(product_name__icontains=search) |
        Q(brand__icontains=search) |
        Q(model_name__icontains=search) |
        Q(category__category_name__icontains=search)
    ).order_by('product_name')

    paginator = Paginator(products, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    product_form = ProductForm()

    if request.method == 'POST':
        sale_form = SaleForm(request.POST)

        if sale_form.is_valid():
            with transaction.atomic():
                sale = sale_form.save(commit=False)

                product = Product.objects.select_for_update().get(
                    pk=sale.product.pk
                )

                if sale.quantity_sold > product.stock_quantity:
                    sale_form.add_error(None, 'Not enough stock available.')
                else:
                    sale.product = product
                    sale.save()
                    return redirect('product_list')

    else:
        sale_form = SaleForm()

    return render(
        request,
        'main/product_list.html',
        {
            'current_user': current_user,
            'page_obj': page_obj,
            'search': search,
            'product_form': product_form,
            'form': sale_form,
            'sale_form': sale_form,
        }
    )
    
def sales_report(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    period, start, end = get_period_bounds(request)

    sales = Sale.objects.select_related(
        'product',
        'product__category',
        'product__supplier'
    ).order_by('-sale_date')

    sales = filter_queryset_by_period(sales, 'sale_date', start, end)

    total_income = sales.aggregate(total=Sum('total_price'))['total'] or 0
    total_orders = sales.count()
    total_items_sold = sales.aggregate(total=Sum('quantity_sold'))['total'] or 0

    return render(
        request,
        'main/sales_report.html',
        {
            'current_user': current_user,
            'sales': sales,
            'total_income': total_income,
            'total_orders': total_orders,
            'total_items_sold': total_items_sold,
            'period': period,
            'start_date': start,
            'end_date': end,
        }
    )

def income_report(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    period, start, end = get_period_bounds(request)

    paid_invoices = Invoice.objects.select_related(
        'sale',
        'sale__product',
        'sale__expense'
    ).filter(status='Paid').order_by('-invoice_date', '-created_at')

    paid_invoices = filter_queryset_by_date_period(paid_invoices, 'invoice_date', start, end)

    accepted_expenses = Expense.objects.filter(
        status__in=['Accepted', 'Converted']
    ).select_related(
        'product',
        'supplier_product',
        'supplier_product__supplier',
        'supplier_product__product',
        'supplier_purchase'
    ).order_by('-expense_date', '-created_at')
    accepted_expenses = filter_queryset_by_date_period(
        accepted_expenses,
        'expense_date',
        start,
        end
    )

    direct_purchase_expenses = SupplierPurchase.objects.filter(
        expense__isnull=True
    ).order_by('-purchase_date')
    direct_purchase_expenses = filter_queryset_by_period(
        direct_purchase_expenses,
        'purchase_date',
        start,
        end
    )

    total_sales = paid_invoices.aggregate(total=Sum('amount'))['total'] or 0
    total_orders = paid_invoices.count()
    expense_total = accepted_expenses.aggregate(total=Sum('total_price'))['total'] or 0
    direct_purchase_expense_total = direct_purchase_expenses.aggregate(total=Sum('total_price'))['total'] or 0
    total_expense_amount = expense_total + direct_purchase_expense_total
    net_income = total_sales - total_expense_amount
    total_expenses_count = accepted_expenses.count()
    total_expense_records = total_expenses_count + direct_purchase_expenses.count()
    average_sale = paid_invoices.aggregate(avg=Avg('amount'))['avg'] or 0

    return render(
        request,
        'main/income_report.html',
        {
            'current_user': current_user,
            'paid_invoices': paid_invoices,
            'accepted_expenses': accepted_expenses,
            'direct_purchase_expenses': direct_purchase_expenses,
            'total_sales': total_sales,
            'total_orders': total_orders,
            'expense_total': expense_total,
            'direct_purchase_expense_total': direct_purchase_expense_total,
            'total_expense_amount': total_expense_amount,
            'net_income': net_income,
            'total_expenses_count': total_expenses_count,
            'total_expense_records': total_expense_records,
            'expense_income': expense_total,
            'average_sale': average_sale,
            'period': period,
            'start_date': start,
            'end_date': end,
        }
    )

def add_category(request):

    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    if request.method == 'POST':
        form = CategoryForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('category_list')

    else:
        form = CategoryForm()

    return render(
        request,
        'main/add_category.html',
        {
            'form': form,
            'current_user': current_user
        }
    )

def category_list(request):

    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    categories = Category.objects.all().order_by('category_name')

    return render(
        request,
        'main/category_list.html',
        {
            'categories': categories,
            'current_user': current_user
        }
    )

def edit_category(request, pk):

    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    category = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)

        if form.is_valid():
            form.save()

    return redirect('category_list')

def delete_category(request, pk):

    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    category = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        category.delete()

    return redirect('category_list')

def settings_page(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    return render(
        request,
        'main/settings.html',
        {
            'current_user': current_user
        }
    )

def account_overview(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    clean_missing_profile_picture(current_user)

    if request.method == 'POST':
        form = AccountOverviewForm(
            request.POST,
            request.FILES or None,
            instance=current_user
        )

        if form.is_valid():
            form.save()
            return redirect('account_overview')

    else:
        form = AccountOverviewForm(instance=current_user)

    return render(request, 'main/account_overview.html', {
        'current_user': current_user,
        'form': form
    })

def change_password(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if request.method == 'POST':
        form = ChangePasswordForm(request.POST)

        if form.is_valid():
            current_password = form.cleaned_data.get('current_password')
            new_password = form.cleaned_data.get('new_password')
            confirm_password = form.cleaned_data.get('confirm_password')

            if current_password != current_user.password:
                form.add_error('current_password', 'Current password is incorrect.')

            elif new_password != confirm_password:
                form.add_error('confirm_password', 'New passwords do not match.')

            else:
                current_user.password = new_password
                current_user.save(update_fields=['password'])
                return redirect('settings')

    else:
        form = ChangePasswordForm()

    return render(request, 'main/change_password.html', {
        'current_user': current_user,
        'form': form
    })


def change_pin(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if request.method == 'POST':
        form = ChangePINForm(request.POST)

        if form.is_valid():
            current_pin = form.cleaned_data.get('current_pin')
            pin_code = form.cleaned_data.get('pin_code')
            confirm_pin_code = form.cleaned_data.get('confirm_pin_code')

            if current_user.pin_code and current_pin != current_user.pin_code:
                form.add_error('current_pin', 'Current PIN is incorrect.')

            elif pin_code != confirm_pin_code:
                form.add_error('confirm_pin_code', 'PIN codes do not match.')

            else:
                current_user.pin_code = pin_code
                current_user.save(update_fields=['pin_code'])
                return redirect('settings')

    else:
        form = ChangePINForm()

    return render(request, 'main/change_pin.html', {
        'current_user': current_user,
        'form': form
    })

def disable_pin(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    form = ChangePINForm(request.POST or None)

    if request.method == 'POST':
        current_pin = request.POST.get('current_pin', '').strip()

        if current_user.pin_code and current_pin != current_user.pin_code:
            form.add_error('current_pin', 'Current PIN is incorrect.')
            return render(request, 'main/change_pin.html', {
                'current_user': current_user,
                'form': form
            })

        current_user.pin_code = None
        current_user.save(update_fields=['pin_code'])

    return redirect('settings')

def contact_support(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if request.method == 'POST':
        form = ContactSupportForm(request.POST)

        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.admin = current_user
            ticket.save()
            return redirect('support_ticket_detail', pk=ticket.pk)
    else:
        form = ContactSupportForm(initial={
            'name': f'{current_user.first_name} {current_user.last_name}'.strip() or current_user.username,
            'email': current_user.email,
        })

    return render(request, 'main/contact_support.html', {
        'current_user': current_user,
        'form': form
    })

def support_tickets(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if current_user.is_admin:
        tickets = ContactSupport.objects.all().order_by('-created_at')
    else:
        tickets = ContactSupport.objects.filter(admin=current_user).order_by('-created_at')

    return render(request, 'main/support_tickets.html', {
        'current_user': current_user,
        'tickets': tickets
    })


def support_ticket_detail(request, pk):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if current_user.is_admin:
        ticket = get_object_or_404(ContactSupport, pk=pk)
    else:
        ticket = get_object_or_404(ContactSupport, pk=pk, admin=current_user)

    return render(request, 'main/support_ticket_detail.html', {
        'current_user': current_user,
        'ticket': ticket
    })

def account_creation(request):

    current_user = get_current_admin(request)
    is_admin_panel = bool(
        current_user and current_user.is_admin
    )
    show_role_field = is_admin_panel

    if request.method == 'POST':

        form = AdminForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            new_admin = form.save(commit=False)

            if not show_role_field:
                new_admin.role = 'Staff'

            new_admin.save()

            if is_admin_panel:
                return redirect('user_management')

            return redirect('login')

    else:

        form = AdminForm()

    template_name = (
        'main/admin_account_creation.html'
        if is_admin_panel
        else 'main/account_creation.html'
    )

    return render(
        request,
        template_name,
        {
            'form': form,
            'current_user': current_user,
            'show_role_field': show_role_field,
            'is_admin_panel': is_admin_panel,
        }
    )

def user_management(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    search = request.GET.get('search', '').strip()

    users = Admin.objects.filter(
        Q(username__icontains=search) |
        Q(first_name__icontains=search) |
        Q(last_name__icontains=search) |
        Q(email__icontains=search) |
        Q(role__icontains=search)
    ).order_by('role', 'username')

    return render(
        request,
        'main/user_management.html',
        {
            'current_user': current_user,
            'users': users,
            'search': search,
        }
    )

def edit_user(request, pk):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    user = get_object_or_404(Admin, pk=pk)
    original_role = user.role
    clean_missing_profile_picture(user)

    if request.method == 'POST':
        form = AdminUpdateForm(
            request.POST,
            request.FILES or None,
            instance=user
        )

        if form.is_valid():
            edited_user = form.save(commit=False)

            if user.pk == current_user.pk:
                edited_user.role = original_role

            edited_user.save()

    return redirect('user_management')

def delete_user(request, pk):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    user = get_object_or_404(Admin, pk=pk)

    if user.is_admin and user.pk != current_user.pk:
        return HttpResponseForbidden(
            'You cannot delete another admin account.'
        )

    if request.method == 'POST':
        deleting_self = user.pk == current_user.pk
        user.delete()

        if deleting_self:
            request.session.flush()
            return redirect('login')

    return redirect('user_management')
