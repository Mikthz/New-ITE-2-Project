from django import forms
from django.core.exceptions import ValidationError

from .models import (
    Admin,
    Category,
    Supplier,
    Product,
    Sale,
    SupplierProduct,
    SupplierPurchase,
    SupplierDelivery,
    Delivery
)


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = [
            'category_name'
        ]
        
        widgets = {
            'category_name': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'Enter category name'
            }),
        }


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = [
            'supplier_name',
            'contact_number',
            'email',
            'address'
        ]
        
        widgets = {
            'supplier_name': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'Company name'
            }),

            'contact_number': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'Company contact number'
            }),

            'email': forms.EmailInput(attrs={
                'class': 'input',
                'placeholder': 'Company email address'
            }),

            'address': forms.Textarea(attrs={
                'class': 'input',
                'rows': 4,
                'placeholder': 'Company address'
            }),
        }


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
        
        widgets = {
            'category': forms.Select(attrs={'class': 'search-select input', 'placeholder': 'Enter category name'}),
            'supplier': forms.Select(attrs={'class': 'search-select input', 'placeholder': 'Enter supplier name'}),
            'product_name': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Enter product name'}),
            'brand': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Enter brand name'}),
            'model_name': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Enter model name'}),
            'description': forms.Textarea(attrs={'class': 'input', 'rows': 4, 'placeholder': 'Enter a description'}),
            'price': forms.NumberInput(attrs={'class': 'input', 'placeholder': 'Enter price tag'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'input', 'placeholder': 'Enter stock quantity'}),
            'product_image': forms.FileInput(attrs={'class': 'input', 'placeholder': 'Insert Image'}),
        }


class SupplierProductForm(forms.ModelForm):

    class Meta:
        model = SupplierProduct

        fields = [
            'supplier',
            'product',
            'unit_price',
            'available_quantity'
        ]

        widgets = {
            'supplier': forms.Select(attrs={'class': 'search-select input', 'placeholder': 'Enter a supplier name'}),
            'product': forms.Select(attrs={'class': 'search-select input', 'placeholder': 'Enter a product name'}),
            'unit_price': forms.NumberInput(attrs={'class': 'input', 'placeholder': 'Enter price tag'}),
            'available_quantity': forms.NumberInput(attrs={'class': 'input', 'placeholder': 'Enter stock quantity'}),
        }


class SupplierPurchaseForm(forms.ModelForm):
    class Meta:
        model = SupplierPurchase
        fields = [
            'supplier_product',
            'quantity'
        ]
        
        widgets = {
            'supplier_product': forms.Select(attrs={'class': 'search-select input'}),
            'quantity': forms.NumberInput(attrs={'class': 'input'}),
        }

    def clean(self):
        cleaned_data = super().clean()

        supplier_product = cleaned_data.get('supplier_product')
        quantity = cleaned_data.get('quantity')

        if quantity is not None and quantity <= 0:
            raise ValidationError(
                'Quantity must be greater than zero.'
            )

        if supplier_product and quantity is not None:
            available_quantity = supplier_product.available_quantity

            if self.instance and self.instance.pk:
                if self.instance.supplier_product_id == supplier_product.pk:
                    available_quantity += self.instance.quantity

            if quantity > available_quantity:
                raise ValidationError(
                    'Not enough supplier stock available.'
                )

        return cleaned_data


class SupplierDeliveryForm(forms.ModelForm):
    class Meta:
        model = SupplierDelivery
        fields = [
            'supplier_purchase',
            'expected_delivery_date',
            'delivery_address',
            'status'
        ]
        
        widgets = {
            'supplier_purchase': forms.Select(attrs={'class': 'search-select input', 'placeholder': 'Enter supplier name'}),
            'expected_delivery_date': forms.DateInput(attrs={'class': 'input', 'type': 'date', 'placeholder': 'Enter date'}),
            'delivery_address': forms.Textarea(attrs={'class': 'input', 'placeholder': 'Enter delivery address'}),
            'status': forms.Select(attrs={'class': 'input', 'placeholder': 'Current status'}),
        }


class DeliveryForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = [
            'sale',
            'customer_name',
            'contact_number',
            'delivery_address',
            'expected_delivery_date',
            'status'
        ]
        
        widgets = {
            'sale': forms.Select(attrs={'class': 'search-select input', 'placeholder': 'Enter product name'}),
            'customer_name': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Enter customer name'}),
            'contact_number': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Enter contact number'}),
            'delivery_address': forms.Textarea(attrs={'class': 'input', 'placeholder': 'Enter delivery address'}),
            'expected_delivery_date': forms.DateInput(attrs={'class': 'input', 'type': 'date', 'placeholder': 'Enter expected delivery date'}),
            'status': forms.Select(attrs={'class': 'input', 'placeholder': 'Current Status'}),
        }


class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = [
            'product',
            'customer_name',
            'quantity_sold'
        ]
        
        widgets = {

            'product': forms.Select(attrs={
                'class': 'search-select input'
            }),

            'customer_name': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'Customer name'
            }),

            'quantity_sold': forms.NumberInput(attrs={
                'class': 'input',
                'placeholder': 'Quantity'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()

        product = cleaned_data.get('product')
        quantity_sold = cleaned_data.get('quantity_sold')

        if quantity_sold is not None and quantity_sold <= 0:
            raise ValidationError(
                'Quantity sold must be greater than zero.'
            )

        if product and quantity_sold is not None:
            if quantity_sold > product.stock_quantity:
                raise ValidationError(
                    'Not enough stock available.'
                )

        return cleaned_data


class AdminForm(forms.ModelForm):
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'input',
            'placeholder': 'Confirm password'
            })
        )

    password = forms.CharField(
            widget=forms.PasswordInput(attrs={
                'class': 'input',
                'placeholder': 'Password'
            })
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
        
        widgets = {

            'username': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'Username'
            }),

            'first_name': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'First name'
            }),

            'last_name': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'Last name'
            }),

            'email': forms.EmailInput(attrs={
                'class': 'input',
                'placeholder': 'Email address'
            }),

            'contact_number': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'Contact number'
            }),

            'address': forms.Textarea(attrs={
                'class': 'input',
                'rows': 4,
                'placeholder': 'Address'
            }),

            'role': forms.Select(attrs={
                'class': 'search-select input'
            }),

            'profile_picture': forms.FileInput(attrs={
                'class': 'input'
            }),
        }

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