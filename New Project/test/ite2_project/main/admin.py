from django.contrib import admin

from .models import (
    Admin,
    Category,
    Supplier,
    Product,
    Sale,
    SupplierProduct,
    SupplierPurchase,
    Delivery
)


@admin.register(Admin)
class AdminAdmin(admin.ModelAdmin):

    list_display = (
        'username',
        'first_name',
        'last_name',
        'role',
        'email',
        'created_at'
    )

    search_fields = (
        'username',
        'first_name',
        'last_name',
        'email'
    )

    list_filter = (
        'role',
        'created_at'
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):

    list_display = (
        'category_name',
        'created_at'
    )

    search_fields = (
        'category_name',
    )


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):

    list_display = (
        'supplier_name',
        'contact_number',
        'email'
    )

    search_fields = (
        'supplier_name',
        'email'
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    list_display = (
        'product_name',
        'brand',
        'category',
        'price',
        'stock_quantity',
        'supplier'
    )

    search_fields = (
        'product_name',
        'brand',
        'model_name'
    )

    list_filter = (
        'category',
        'supplier'
    )


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):

    list_display = (
        'product',
        'customer_name',
        'quantity_sold',
        'total_price',
        'sale_date'
    )

    search_fields = (
        'product__product_name',
        'customer_name'
    )

    list_filter = (
        'sale_date',
    )
    
admin.site.register(SupplierProduct)
admin.site.register(SupplierPurchase)
admin.site.register(Delivery)