from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.db.models import Q
from django.core.paginator import Paginator

from .models import Admin, Category, Product, Supplier
from .forms import AdminForm, CategoryForm, ProductForm, SaleForm, SupplierForm


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
        product.delete()

    return redirect('product_list')

def suppliers(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    suppliers = Supplier.objects.all().order_by('supplier_name')

    return render(
        request,
        'main/suppliers.html',
        {
            'current_user': current_user,
            'suppliers': suppliers
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
            'supplier_form': form
        }
    )

def quotations(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    return render(
        request,
        'main/quotations.html',
        {
            'current_user': current_user
        }
    )
    
def create_quotation(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    return render(
        request,
        'main/create_quotation.html',
        {
            'current_user': current_user
        }
    )

def invoices(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    return render(
        request,
        'main/invoices.html',
        {
            'current_user': current_user
        }
    )

def create_invoice(request):
    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    return render(
        request,
        'main/create_invoice.html',
        {
            'current_user': current_user
        }
    )

def record_sale(request):

    current_user = get_current_admin(request)

    if not current_user:
        return redirect('login')

    if request.method == 'POST':
        form = SaleForm(request.POST)

        if form.is_valid():
            form.save()

    return redirect('product_list')


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

    if request.method == 'POST':
        form = AdminForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()

            if current_user and current_user.is_admin:
                return redirect('product_list')

            return redirect('login')

    else:
        form = AdminForm()

    return render(
        request,
        'main/account_creation.html',
        {
            'form': form,
            'current_user': current_user
        }
    )