from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.db.models import Q
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models.deletion import ProtectedError

from django.db.models import Sum, Avg
from .models import Admin, Category, Product, Supplier, SupplierProduct, SupplierPurchase, SupplierDelivery, Delivery, Sale, Quotation, Invoice
from .forms import AdminForm, AdminUpdateForm, CategoryForm, ProductForm, SaleForm, SupplierForm, SupplierProductForm, SupplierPurchaseForm, SupplierDeliveryForm, DeliveryForm, QuotationForm, InvoiceForm

def get_current_admin(request):
    admin_pk = request.session.get('admin_id')

    if not admin_pk:
        return None

    try:
        return Admin.objects.get(pk=admin_pk)
    except Admin.DoesNotExist:
        request.session.flush()
        return None

def login_view(request):

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            admin_user = Admin.objects.get(
                username=username,
                password=password
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

    search = request.GET.get('search', '')

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

    products = Product.objects.filter(
        stock_quantity__lte=5
    ).order_by('stock_quantity')

    return render(
        request,
        'main/low_stock.html',
        {
            'current_user': current_user,
            'low_stock_products': products
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

    search = request.GET.get('search', '')

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

    search = request.GET.get('search', '')

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

    purchases = SupplierPurchase.objects.all().order_by('-purchase_date')
    supplier_products = SupplierProduct.objects.all().order_by(
        'product__product_name'
    )

    form = SupplierPurchaseForm()

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
                        f'Not enough stock for {product_name}.'
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

                            purchase = SupplierPurchase.objects.create(
                                supplier_product=supplier_product,
                                quantity=quantity
                            )

                            SupplierDelivery.objects.create(
                                supplier_purchase=purchase,
                                delivery_address=supplier_product.supplier.address,
                                status='Pending'
                            )

                            Quotation.objects.update_or_create(
                                supplier_purchase=purchase,
                                defaults={
                                    'supplier_product': supplier_product,
                                    'quantity': quantity,
                                    'status': 'Sent',
                                    'remarks': 'Auto-generated from supplier purchase.'
                                }
                            )

                if not has_error:
                    return redirect('buy_supplier_products')

    return render(
        request,
        'main/buy_supplier_products.html',
        {
            'current_user': current_user,
            'form': form,
            'purchases': purchases,
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

                Quotation.objects.update_or_create(
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

            Quotation.objects.filter(
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

    if request.method == 'POST':
        sale_form = SaleForm(request.POST)
        delivery_form = DeliveryForm(request.POST)

        if sale_form.is_valid() and delivery_form.is_valid():
            try:
                with transaction.atomic():
                    sale = sale_form.save(commit=False)

                    product = Product.objects.select_for_update().get(
                        pk=sale.product.pk
                    )

                    if sale.quantity_sold > product.stock_quantity:
                        sale_form.add_error(
                            None,
                            'Not enough stock available.'
                        )
                    else:
                        sale.product = product
                        sale.save()

                        delivery = delivery_form.save(commit=False)
                        delivery.sale = sale
                        delivery.customer_name = sale.customer_name
                        delivery.save()

                        Invoice.objects.get_or_create(
                            sale=sale,
                            defaults={
                                'status': 'Paid'
                            }
                        )

                        return redirect('delivery_list')

            except ValueError as error:
                sale_form.add_error(None, str(error))

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
            'form': sale_form
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
            form.save()

    return redirect('delivery_list')

def delete_delivery(request, pk):

    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    delivery = get_object_or_404(Delivery, pk=pk)

    if request.method == 'POST':
        delivery.delete()

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
        form = SupplierDeliveryForm, QuotationForm, InvoiceForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('supplier_delivery_list')

    else:
        form = SupplierDeliveryForm, QuotationForm, InvoiceForm()

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
        form = SupplierDeliveryForm, QuotationForm, InvoiceForm(request.POST, instance=delivery)

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

def quotations(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    search = request.GET.get('search', '')

    quotation_list = Quotation.objects.select_related(
        'supplier_product',
        'supplier_product__supplier',
        'supplier_product__product',
        'supplier_purchase'
    ).filter(
        Q(supplier_product__supplier__supplier_name__icontains=search) |
        Q(supplier_product__product__product_name__icontains=search) |
        Q(status__icontains=search)
    ).order_by('-quotation_date', '-created_at')

    return render(
        request,
        'main/quotations.html',
        {
            'current_user': current_user,
            'quotations': quotation_list,
            'search': search,
            'quotation_form': QuotationForm()
        }
    )
    
def create_quotation(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    if request.method == 'POST':
        form = QuotationForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('quotations')

    else:
        form = QuotationForm()

    return render(
        request,
        'main/create_quotation.html',
        {
            'current_user': current_user,
            'form': form
        }
    )


def edit_quotation(request, pk):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    quotation = get_object_or_404(Quotation, pk=pk)

    if request.method == 'POST':
        form = QuotationForm(request.POST, instance=quotation)

        if form.is_valid():
            form.save()

    return redirect('quotations')


def delete_quotation(request, pk):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    quotation = get_object_or_404(Quotation, pk=pk)

    if request.method == 'POST':
        quotation.delete()

    return redirect('quotations')


def invoices(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    search = request.GET.get('search', '')

    invoice_list = Invoice.objects.select_related(
        'sale',
        'sale__product'
    ).filter(
        Q(sale__customer_name__icontains=search) |
        Q(sale__product__product_name__icontains=search) |
        Q(status__icontains=search)
    ).order_by('-invoice_date', '-created_at')

    return render(
        request,
        'main/invoices.html',
        {
            'current_user': current_user,
            'invoices': invoice_list,
            'search': search,
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

    search = request.GET.get('search', '')

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

    sales = Sale.objects.select_related(
        'product',
        'product__category',
        'product__supplier'
    ).order_by('-sale_date')

    total_income = sales.aggregate(
        total=Sum('total_price')
    )['total'] or 0

    total_orders = sales.count()

    total_items_sold = sales.aggregate(
        total=Sum('quantity_sold')
    )['total'] or 0

    return render(
        request,
        'main/sales_report.html',
        {
            'current_user': current_user,
            'sales': sales,
            'total_income': total_income,
            'total_orders': total_orders,
            'total_items_sold': total_items_sold,
        }
    )

def income_report(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    paid_invoices = Invoice.objects.select_related(
        'sale',
        'sale__product'
    ).filter(
        status='Paid'
    ).order_by('-invoice_date', '-created_at')

    total_sales = paid_invoices.aggregate(total=Sum('amount'))['total'] or 0
    total_orders = paid_invoices.count()
    average_sale = paid_invoices.aggregate(avg=Avg('amount'))['avg'] or 0

    return render(
        request,
        'main/income_report.html',
        {
            'current_user': current_user,
            'paid_invoices': paid_invoices,
            'total_sales': total_sales,
            'total_orders': total_orders,
            'average_sale': average_sale,
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

def account_creation(request):

    current_user = get_current_admin(request)
    show_role_field = bool(current_user and current_user.is_admin)

    if request.method == 'POST':
        form = AdminForm(request.POST, request.FILES)

        if form.is_valid():
            new_admin = form.save(commit=False)

            if not show_role_field:
                new_admin.role = 'Staff'

            new_admin.save()

            if show_role_field:
                return redirect('user_management')

            return redirect('login')

    else:
        form = AdminForm()

    return render(
        request,
        'main/account_creation.html',
        {
            'form': form,
            'current_user': current_user,
            'show_role_field': show_role_field
        }
    )

def user_management(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if not current_user.is_admin:
        return HttpResponseForbidden('Access Forbidden')

    search = request.GET.get('search', '')

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

    if request.method == 'POST':
        form = AdminUpdateForm(
            request.POST,
            request.FILES,
            instance=user
        )

        if form.is_valid():
            edited_user = form.save(commit=False)

            if user.is_admin and user.pk != current_user.pk:
                edited_user.role = 'Admin'

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
