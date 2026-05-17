from django.urls import path
from . import views

urlpatterns = [

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
        'products/add/',
        views.add_product,
        name='add_product'
    ),

    path(
        'products/edit/<int:pk>/',
        views.edit_product,
        name='edit_product'
    ),

    path(
        'products/delete/<int:pk>/',
        views.delete_product,
        name='delete_product'
    ),

    path(
        'sales/record/',
        views.record_sale,
        name='record_sale'
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