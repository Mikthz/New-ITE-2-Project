from django import forms
from django.core.exceptions import ValidationError

from .models import (
    Admin,
    Category,
    Supplier,
    Product,
    Sale
)


class CategoryForm(forms.ModelForm):

    class Meta:
        model = Category
        fields = [
            'category_name'
        ]


class SupplierForm(forms.ModelForm):

    class Meta:
        model = Supplier
        fields = [
            'supplier_name',
            'contact_number',
            'email',
            'address'
        ]


class ProductForm(forms.ModelForm):

    class Meta:
        model = Product
        fields = [
            'category',
            'supplier',
            'product_name',
            'brand',
            'model_name',
            'description',
            'price',
            'stock_quantity',
            'product_image'
        ]


class SaleForm(forms.ModelForm):

    class Meta:
        model = Sale
        fields = [
            'product',
            'customer_name',
            'quantity_sold'
        ]

    def clean(self):
        cleaned_data = super().clean()

        product = cleaned_data.get('product')
        quantity_sold = cleaned_data.get('quantity_sold')

        if product and quantity_sold:
            if quantity_sold > product.stock_quantity:
                raise ValidationError(
                    'Not enough stock available.'
                )

        return cleaned_data


class AdminForm(forms.ModelForm):

    confirm_password = forms.CharField(
        widget=forms.PasswordInput()
    )

    password = forms.CharField(
        widget=forms.PasswordInput()
    )

    class Meta:
        model = Admin

        fields = [
            'username',
            'first_name',
            'last_name',
            'email',
            'contact_number',
            'address',
            'role',
            'password',
            'confirm_password',
            'profile_picture'
        ]

    def clean_username(self):
        username = self.cleaned_data.get('username')

        qs = Admin.objects.filter(
            username=username
        )

        if self.instance.pk:
            qs = qs.exclude(
                pk=self.instance.pk
            )

        if qs.exists():
            raise ValidationError(
                'Username already exists.'
            )

        return username

    def clean_profile_picture(self):
        picture = self.cleaned_data.get(
            'profile_picture'
        )

        if picture:
            if isinstance(picture, str):
                return picture

            if picture.size > 2 * 1024 * 1024:
                raise ValidationError(
                    'Image size must be below 2MB.'
                )

        return picture

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if not password and not confirm_password:
            return cleaned_data

        if password != confirm_password:
            raise ValidationError(
                'Passwords do not match.'
            )

        if password and len(password) < 8:
            raise ValidationError(
                'Password must be at least 8 characters.'
            )

        return cleaned_data