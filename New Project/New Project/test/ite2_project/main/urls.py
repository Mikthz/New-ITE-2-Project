from django.urls import path
from . import views

urlpatterns = [

    path(
        'dashboard/',
        views.dashboard,
        name='dashboard'
    ),

    path(
        '',
        views.product_list,
        name='product_list'
    ),

    path(
        'login/',
        views.login_view,
        name='login'
    ),

    path(
        'logout/',
        views.logout_view,
        name='logout'
    ),

    path(
        'account-creation/',
        views.account_creation,
        name='account_creation'
    ),

    path(
        'users/',
        views.user_management,
        name='user_management'
    ),

    path(
        'users/edit/<int:pk>/',
        views.edit_user,
        name='edit_user'
    ),

    path(
        'users/delete/<int:pk>/',
        views.delete_user,
        name='delete_user'
    ),

    path(
        'products/add/',
        views.add_product,
        name='add_product'
    ),

    path(
        'products/<int:pk>/',
        views.product_detail,
        name='product_detail'
    ),

    path(
        'products/edit/<int:pk>/',
        views.edit_product,
        name='edit_product'
    ),
    
    path(
        'low-stock/',
        views.low_stock,
        name='low_stock'
        ),

    path(
        'products/delete/<int:pk>/',
        views.delete_product,
        name='delete_product'
    ),
    
    path(
        'suppliers/',
        views.suppliers,
        name='suppliers'
        ),
    
    path(
        'create-supplier/',
        views.create_supplier,
        name='create_supplier'
        ),
    
    path(
        'suppliers/edit/<int:pk>/',
        views.edit_supplier,
        name='edit_supplier'
    ),

    path(
        'suppliers/delete/<int:pk>/',
        views.delete_supplier,
        name='delete_supplier'
    ),
    
    path(
        'supplier-products/',
        views.supplier_products,
        name='supplier_products'
    ),
    
    path(
        'supplier-products/add/',
        views.add_supplier_products,
        name='add_supplier_products'
    ),
    
    path(
        'supplier-products/edit/<int:pk>/',
        views.edit_supplier_product,
        name='edit_supplier_product'
    ),
    
    path(
        'supplier-products/delete/<int:pk>/',
        views.delete_supplier_product,
        name='delete_supplier_product'
    ),
    
    path(
        'supplier-products/buy/',
        views.buy_supplier_products,
        name='buy_supplier_products'
    ),

    path(
        'supplier-purchases/edit/<int:pk>/',
        views.edit_supplier_purchase,
        name='edit_supplier_purchase'
    ),
    
    path(
        'supplier-purchases/delete/<int:pk>/',
        views.delete_supplier_purchase,
        name='delete_supplier_purchase'
    ),

    path(
        'deliveries/',
        views.delivery_list,
        name='delivery_list'
    ),
    
    path(
        'deliveries/create/',
        views.create_delivery,
        name='create_delivery'
    ),
    
    path(
        'deliveries/<int:pk>/',
        views.delivery_detail,
        name='delivery_detail'
    ),

    path(
        'deliveries/edit/<int:pk>/',
        views.edit_delivery,
        name='edit_delivery'
    ),
    
    path(
        'deliveries/delete/<int:pk>/',
        views.delete_delivery,
        name='delete_delivery'
    ),
    
    path(
        'supplier-deliveries/',
        views.supplier_delivery_list,
        name='supplier_delivery_list'
    ),

    path(
        'supplier-deliveries/create/',
        views.create_supplier_delivery,
        name='create_supplier_delivery'
    ),
    
        path(
        'supplier-deliveries/edit/<int:pk>/',
        views.edit_supplier_delivery,
        name='edit_supplier_delivery'
    ),

    path(
        'supplier-deliveries/delete/<int:pk>/',
        views.delete_supplier_delivery,
        name='delete_supplier_delivery'
    ),
    
    path(
        'expenses/',
        views.expenses,
        name='expenses'
        ),
    
    path(
        'create-expense/',
        views.create_expense,
        name='create_expense'
        ),

    path(
        'expenses/edit/<int:pk>/',
        views.edit_expense,
        name='edit_expense'
    ),

    path(
        'expenses/delete/<int:pk>/',
        views.delete_expense,
        name='delete_expense'
    ),
    
    path(
        'invoices/',
        views.invoices,
        name='invoices'
        ),
    
    path(
        'create-invoice/',
        views.create_invoice,
        name='create_invoice'
        ),

    path(
        'invoices/edit/<int:pk>/',
        views.edit_invoice,
        name='edit_invoice'
    ),

    path(
        'invoices/delete/<int:pk>/',
        views.delete_invoice,
        name='delete_invoice'
    ),


    path(
        'settings/',
        views.settings_page,
        name='settings'
        ),

    path(
        'account-overview/',
        views.account_overview,
        name='account_overview'
    ),
    
    path(
        'change-password/',
        views.change_password,
        name='change_password'
        ),
    
    path(
        'change-pin/',
        views.change_pin,
        name='change_pin'
        ),

    path(
    'disable-pin/',
    views.disable_pin,
    name='disable_pin'
    ),

    path(
        'contact-support/',
        views.contact_support,
        name='contact_support'
    ),

    path(
    'support-tickets/',
    views.support_tickets,
    name='support_tickets'
    ),

    path(
        'support-tickets/<int:pk>/',
        views.support_ticket_detail,
        name='support_ticket_detail'
    ),

    path(
        'sales/record/',
        views.record_sale,
        name='record_sale'
    ),

    path(
        'sales-report/',
        views.sales_report,
        name='sales_report'
    ),
    
    path(
        'income-report/',
        views.income_report,
        name='income_report'
        ),

    path(
        'categories/',
        views.category_list,
        name='category_list'
    ),

    path(
        'categories/add/',
        views.add_category,
        name='add_category'
    ),

    path(
        'categories/edit/<int:pk>/',
        views.edit_category,
        name='edit_category'
    ),

    path(
        'categories/delete/<int:pk>/',
        views.delete_category,
        name='delete_category'
    ),
]