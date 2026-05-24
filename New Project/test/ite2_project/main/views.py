from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.db.models import Q, F
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models.deletion import ProtectedError
from django.core.files.storage import default_storage

from django.db.models import Sum, Avg
from django.utils import timezone
from .models import Admin, Category, Product, Supplier, SupplierProduct, SupplierPurchase, SupplierDelivery, Delivery, Sale, Expense, Invoice, ContactSupport
from .forms import AdminForm, AdminUpdateForm, AccountOverviewForm, ContactSupportForm, CategoryForm, ProductForm, SaleForm, SupplierForm, SupplierProductForm, SupplierPurchaseForm, SupplierDeliveryForm, DeliveryForm, ExpenseForm, InvoiceForm, ChangePINForm, ChangePasswordForm

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
        start = start_date
        end = end_date
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

def product_list(request):

    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    search = request.GET.get('search', '').strip()

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
    ).order_by('stock_quantity', 'product_name')

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

    return render(
        request,
        'main/product_list.html',
        {
            'current_user': current_user,
            'page_obj': page_obj,
            'search': search,
            'product_form': product_form,
            'sale_form': sale_form,
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
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
    ).order_by('stock_quantity', 'product_name')

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

    suppliers = Supplier.objects.filter(
        Q(supplier_name__icontains=search) |
        Q(email__icontains=search) |
        Q(contact_number__icontains=search) |
        Q(address__icontains=search)
    ).order_by('supplier_name')

    return render(
        request,
        'main/suppliers.html',
        {
            'current_user': current_user,
            'suppliers': suppliers,
            'search': search,
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

    supplier_products = SupplierProduct.objects.filter(
        Q(supplier__supplier_name__icontains=search) |
        Q(product__product_name__icontains=search) |
        Q(product__brand__icontains=search) |
        Q(product__model_name__icontains=search)
    ).select_related('supplier', 'product').order_by('product__product_name')

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

    supplier_products = SupplierProduct.objects.all().order_by(
        'product__product_name'
    )

    form = SupplierPurchaseForm()

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
            form.add_error(
                None,
                'Please add at least one supplier product.'
            )

        else:
            has_error = False
            purchase_quantities = {}

            for product_id, quantity in zip(product_ids, quantities):
                try:
                    product_id = int(product_id)
                    quantity = int(quantity)
                except (TypeError, ValueError):
                    form.add_error(None, 'Supplier product and quantity must be valid numbers.')
                    has_error = True
                    continue

                if quantity <= 0:
                    form.add_error(None, 'Quantity must be greater than zero.')
                    has_error = True
                    continue

                purchase_quantities[product_id] = (
                    purchase_quantities.get(product_id, 0) + quantity
                )

            supplier_product_map = SupplierProduct.objects.filter(
                pk__in=purchase_quantities.keys()
            ).select_related('supplier', 'product').in_bulk()

            for product_id, quantity in purchase_quantities.items():
                supplier_product = supplier_product_map.get(product_id)

                if not supplier_product:
                    form.add_error(None, 'Selected supplier product does not exist.')
                    has_error = True
                    continue

                if quantity > supplier_product.available_quantity:
                    product_name = (
                        supplier_product.product.product_name
                        if supplier_product.product
                        else str(supplier_product)
                    )
                    form.add_error(
                        None,
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
                            form.add_error(
                                None,
                                'Not enough supplier stock available.'
                            )
                            has_error = True
                            break

                    if not has_error:
                        for product_id, quantity in purchase_quantities.items():
                            supplier_product = locked_supplier_products[product_id]

                            Expense.objects.create(
                                supplier_product=supplier_product,
                                quantity=quantity,
                                status='Sent',
                                remarks='Auto-generated from Buy Supplier Products. Accept or convert this expense to create the supplier purchase and delivery.'
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

                if old_supplier_product.pk == new_supplier_product.pk:
                    quantity_difference = new_quantity - old_quantity

                    if quantity_difference > old_supplier_product.available_quantity:
                        form.add_error(
                            None,
                            'Not enough supplier stock available.'
                        )
                        return redirect('buy_supplier_products')

                    new_supplier_product.available_quantity -= quantity_difference
                    new_supplier_product.save()
                else:
                    if new_quantity > new_supplier_product.available_quantity:
                        form.add_error(
                            None,
                            'Not enough supplier stock available.'
                        )
                        return redirect('buy_supplier_products')

                    old_supplier_product.available_quantity += old_quantity
                    old_supplier_product.save()

                    new_supplier_product.available_quantity -= new_quantity
                    new_supplier_product.save()

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
                    delivery_address=new_supplier_product.supplier.address
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
        with transaction.atomic():
            supplier_product = SupplierProduct.objects.select_for_update().get(
                pk=purchase.supplier_product.pk
            )
            supplier_product.available_quantity += purchase.quantity
            supplier_product.save()

            SupplierDelivery.objects.filter(
                supplier_purchase=purchase
            ).delete()

            Expense.objects.filter(
                supplier_purchase=purchase
            ).delete()

            purchase.delete()

    return redirect('buy_supplier_products')

def delivery_list(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    deliveries = Delivery.objects.all().order_by('-created_at')

    return render(
        request,
        'main/delivery_list.html',
        {
            'current_user': current_user,
            'deliveries': deliveries
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
        sale_form = SaleForm()

        product_ids = request.POST.getlist('product_ids[]')
        quantities = request.POST.getlist('quantities[]')
        sale_form = SaleForm(request.POST)
        customer_name = sale_form.data.get('customer_name', '').strip()

        if not product_ids:
            sale_form.add_error(None, 'Please add at least one product.')

        if not customer_name:
            sale_form.add_error(None, 'Customer name is required.')

        if delivery_form.is_valid() and product_ids and customer_name:
            with transaction.atomic():
                for product_id, quantity in zip(product_ids, quantities):
                    product = Product.objects.select_for_update().get(pk=product_id)
                    quantity = int(quantity)

                    if quantity <= 0:
                        sale_form.add_error(None, 'Quantity must be greater than zero.')
                        break

                    if quantity > product.stock_quantity:
                        sale_form.add_error(None, f'Not enough stock for {product.product_name}.')
                        break

                    sale = Sale.objects.create(
                        product=product,
                        customer_name=customer_name,
                        quantity_sold=quantity
                    )

                    delivery = delivery_form.save(commit=False)
                    delivery.sale = sale
                    delivery.customer_name = customer_name
                    delivery.save()

                    Invoice.objects.get_or_create(
                        sale=sale,
                        defaults={
                            'status': 'Paid'
                        }
                    )

                if not sale_form.errors:
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
            'form': sale_form if sale_form.errors else delivery_form,
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

                if delivery.sale:
                    sale = Sale.objects.select_for_update().get(
                        pk=delivery.sale.pk
                    )
                    sale.customer_name = request.POST.get('customer_name', edited_delivery.customer_name)
                    sale.save(update_fields=['customer_name'])

                edited_delivery.customer_name = request.POST.get('customer_name', edited_delivery.customer_name)
                edited_delivery.save()

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
                sale = delivery.sale

                if sale:
                    product = Product.objects.select_for_update().get(
                        pk=sale.product.pk
                    )

                    product.stock_quantity += sale.quantity_sold
                    product.save(update_fields=['stock_quantity'])

                    Invoice.objects.filter(sale=sale).delete()
                    delivery.delete()
                    sale.delete()
                else:
                    delivery.delete()

        except ProtectedError:
            return HttpResponseForbidden(
                'Cannot delete this delivery because it is linked to protected records.'
            )

    return redirect('delivery_list')

def supplier_delivery_list(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    deliveries = SupplierDelivery.objects.all().order_by('-created_at')

    return render(
        request,
        'main/supplier_delivery_list.html',
        {
            'current_user': current_user,
            'deliveries': deliveries
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
            form.save()

    return redirect('supplier_delivery_list')

def delete_supplier_delivery(request, pk):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    delivery = get_object_or_404(SupplierDelivery, pk=pk)

    if request.method == 'POST':
        delivery.delete()

    return redirect('supplier_delivery_list')

def expenses(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    search = request.GET.get('search', '').strip()

    period, start, end = get_period_bounds(request)

    expense_list = Expense.objects.select_related(
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
        Q(status__icontains=search)
    ).order_by('-expense_date', '-created_at')

    expense_list = filter_queryset_by_date_period(expense_list, 'expense_date', start, end)

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
    
def create_expense(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    if request.method == 'POST':
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
        form = ExpenseForm(request.POST, instance=expense)

        if form.is_valid():
            with transaction.atomic():
                expense = form.save()
                sync_expense_income(expense)

    return redirect('expenses')


def delete_expense(request, pk):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    expense = get_object_or_404(Expense, pk=pk)

    if request.method == 'POST':
        with transaction.atomic():
            remove_expense_income(expense)
            expense.delete()

    return redirect('expenses')


def invoices(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    search = request.GET.get('search', '').strip()

    period, start, end = get_period_bounds(request)

    invoice_list = Invoice.objects.select_related(
        'sale',
        'sale__product'
    ).filter(
        Q(invoice_code__icontains=search) |
        Q(sale__customer_name__icontains=search) |
        Q(sale__product__product_name__icontains=search) |
        Q(status__icontains=search)
    ).order_by('-invoice_date', '-created_at')

    invoice_list = filter_queryset_by_date_period(invoice_list, 'invoice_date', start, end)

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


def create_invoice(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    if request.method == 'POST':
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
        form = InvoiceForm(request.POST, instance=invoice)

        if form.is_valid():
            form.save()

    return redirect('invoices')


def delete_invoice(request, pk):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    invoice = get_object_or_404(Invoice, pk=pk)

    if request.method == 'POST':
        invoice.delete()

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
                edited_user.role = user.role

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
