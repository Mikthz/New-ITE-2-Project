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
    Delivery,
    Expense,
    Invoice,
    ContactSupport
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
    
    low_stock_threshold = forms.IntegerField(
        required=True,
        min_value=1,
        error_messages={
            'required': 'Low stock warning is required.',
            'min_value': 'Low stock warning must be at least 1.',
            'invalid': 'Low stock warning must be a valid number.',
        },
        widget=forms.NumberInput(attrs={
            'class': 'input',
            'placeholder': 'Low stock threshold',
            'min': '1'
        })
    )
    
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
            'low_stock_threshold',
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

    def clean_price(self):
        price = self.cleaned_data.get('price')

        if price is not None and price <= 0:
            raise ValidationError(
                'Price must be greater than zero.'
            )

        return price

    def clean_stock_quantity(self):
        stock_quantity = self.cleaned_data.get('stock_quantity')

        if stock_quantity is not None and stock_quantity < 0:
            raise ValidationError(
                'Stock quantity cannot be negative.'
            )

        return stock_quantity

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


    def clean_unit_price(self):
        unit_price = self.cleaned_data.get('unit_price')

        if unit_price is not None and unit_price <= 0:
            raise ValidationError(
                'Unit price must be greater than zero.'
            )

        return unit_price

    def clean_available_quantity(self):
        available_quantity = self.cleaned_data.get('available_quantity')

        if available_quantity is not None and available_quantity < 0:
            raise ValidationError(
                'Available quantity cannot be negative.'
            )

        return available_quantity

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
            'contact_number',
            'delivery_address',
            'expected_delivery_date',
            'status'
        ]

        widgets = {
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
                'class': 'input'
            }),

            'profile_picture': forms.FileInput(attrs={
                'class': 'input'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['role'].required = False

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
            self.add_error(
                'confirm_password',
                'Passwords do not match.'
            )

        if password and len(password) < 8:
            self.add_error(
                'password',
                'Password must be at least 8 characters.'
            )

        return cleaned_data

class AdminUpdateForm(forms.ModelForm):
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
                'rows': 3,
                'placeholder': 'Address'
            }),
            'role': forms.Select(attrs={
                'class': 'input'
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


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = [
            'customer_name',
            'product',
            'supplier_product',
            'quantity',
            'expense_date',
            'valid_until',
            'status',
            'remarks'
        ]

        widgets = {
            'customer_name': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Customer / company name'}),
            'product': forms.Select(attrs={'class': 'search-select input'}),
            'supplier_product': forms.Select(attrs={'class': 'search-select input'}),
            'quantity': forms.NumberInput(attrs={'class': 'input', 'placeholder': 'Quantity', 'min': '1'}),
            'expense_date': forms.DateInput(attrs={'class': 'input', 'type': 'date'}),
            'valid_until': forms.DateInput(attrs={'class': 'input', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'input'}),
            'remarks': forms.Textarea(attrs={'class': 'input', 'rows': 4, 'placeholder': 'Expense remarks'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['customer_name'].required = False
        self.fields['product'].required = False
        self.fields['supplier_product'].required = False

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')

        if quantity is not None and quantity <= 0:
            raise ValidationError('Quantity must be greater than zero.')

        return quantity

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        supplier_product = cleaned_data.get('supplier_product')
        quantity = cleaned_data.get('quantity')
        customer_name = cleaned_data.get('customer_name')
        status = cleaned_data.get('status')

        if product and supplier_product:
            raise ValidationError(
                'Select either a direct product expense or a supplier product expense, not both.'
            )

        if not product and not supplier_product:
            raise ValidationError(
                'Please select a customer product or a supplier product for the expense.'
            )

        if product and not customer_name:
            raise ValidationError(
                'Please enter the company/supplier name for this expense.'
            )

        if supplier_product:
            cleaned_data['customer_name'] = None

        if product and quantity and status in ['Accepted', 'Converted']:
            existing_sale = getattr(self.instance, 'sale', None)
            existing_sale_quantity = (
                existing_sale.quantity_sold
                if existing_sale and existing_sale.product_id == product.pk
                else 0
            )
            available_stock = product.stock_quantity + existing_sale_quantity

            if quantity > available_stock:
                raise ValidationError(
                    'Accepted or converted expense quantity cannot be greater than available stock.'
                )

        if supplier_product and quantity and status in ['Accepted', 'Converted']:
            existing_purchase = getattr(self.instance, 'supplier_purchase', None)
            existing_purchase_quantity = (
                existing_purchase.quantity
                if existing_purchase and existing_purchase.supplier_product_id == supplier_product.pk
                else 0
            )
            available_supplier_stock = supplier_product.available_quantity + existing_purchase_quantity

            if quantity > available_supplier_stock:
                raise ValidationError(
                    'Accepted or converted supplier expense quantity cannot be greater than supplier stock.'
                )

        return cleaned_data


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            'sale',
            'invoice_date',
            'due_date',
            'status',
            'notes'
        ]

        widgets = {
            'sale': forms.Select(attrs={'class': 'search-select input'}),
            'invoice_date': forms.DateInput(attrs={'class': 'input', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'input', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'input'}),
            'notes': forms.Textarea(attrs={'class': 'input', 'rows': 4, 'placeholder': 'Invoice notes'}),
        }

    def clean_sale(self):
        sale = self.cleaned_data.get('sale')

        if sale:
            existing_invoice = Invoice.objects.filter(sale=sale)

            if self.instance and self.instance.pk:
                existing_invoice = existing_invoice.exclude(pk=self.instance.pk)

            if existing_invoice.exists():
                raise ValidationError('This sale already has an invoice.')

        return sale


class AccountOverviewForm(forms.ModelForm):
    current_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'input', 'placeholder': 'Current password'})
    )
    new_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'input', 'placeholder': 'New password'})
    )
    confirm_new_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'input', 'placeholder': 'Confirm new password'})
    )
    pin_code = forms.CharField(
        required=False,
        max_length=6,
        widget=forms.PasswordInput(attrs={'class': 'input', 'placeholder': 'Optional 4-6 digit PIN', 'inputmode': 'numeric'})
    )

    class Meta:
        model = Admin
        fields = [
            'username', 'first_name', 'last_name', 'email',
            'contact_number', 'address', 'profile_picture', 'pin_code'
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'input'}),
            'first_name': forms.TextInput(attrs={'class': 'input'}),
            'last_name': forms.TextInput(attrs={'class': 'input'}),
            'email': forms.EmailInput(attrs={'class': 'input'}),
            'contact_number': forms.TextInput(attrs={'class': 'input'}),
            'address': forms.Textarea(attrs={'class': 'input', 'rows': 3}),
            'profile_picture': forms.FileInput(attrs={'class': 'input'}),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        qs = Admin.objects.filter(username=username)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Username already exists.')
        return username

    def clean_pin_code(self):
        pin = self.cleaned_data.get('pin_code')
        if pin and (not pin.isdigit() or len(pin) < 4 or len(pin) > 6):
            raise ValidationError('PIN must be 4 to 6 digits only.')
        return pin

    def clean(self):
        cleaned_data = super().clean()
        current_password = cleaned_data.get('current_password')
        new_password = cleaned_data.get('new_password')
        confirm_new_password = cleaned_data.get('confirm_new_password')

        if new_password or confirm_new_password:
            if current_password != self.instance.password:
                self.add_error('current_password', 'Current password is incorrect.')
            if new_password != confirm_new_password:
                self.add_error('confirm_new_password', 'New passwords do not match.')
            if new_password and len(new_password) < 8:
                self.add_error('new_password', 'Password must be at least 8 characters.')

        return cleaned_data

    def save(self, commit=True):
        admin = super().save(commit=False)
        new_password = self.cleaned_data.get('new_password')
        if new_password:
            admin.password = new_password
        if commit:
            admin.save()
        return admin


class ContactSupportForm(forms.ModelForm):
    class Meta:
        model = ContactSupport
        fields = ['name', 'email', 'subject', 'priority', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Your name'}),
            'email': forms.EmailInput(attrs={'class': 'input', 'placeholder': 'Your email'}),
            'subject': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Support subject'}),
            'priority': forms.Select(attrs={'class': 'input'}),
            'message': forms.Textarea(attrs={'class': 'input', 'rows': 5, 'placeholder': 'Describe your issue'}),
        }

class ChangePINForm(forms.Form):
    current_pin = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'input',
            'placeholder': 'Current PIN'
        })
    )

    pin_code = forms.CharField(
        required=True,
        max_length=6,
        widget=forms.PasswordInput(attrs={
            'class': 'input',
            'placeholder': 'New PIN'
        })
    )

    confirm_pin_code = forms.CharField(
        required=True,
        max_length=6,
        widget=forms.PasswordInput(attrs={
            'class': 'input',
            'placeholder': 'Confirm New PIN'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        pin_code = cleaned_data.get('pin_code')
        confirm_pin_code = cleaned_data.get('confirm_pin_code')

        for field_name, pin_value in (
            ('pin_code', pin_code),
            ('confirm_pin_code', confirm_pin_code),
        ):
            if pin_value and (not pin_value.isdigit() or len(pin_value) < 4 or len(pin_value) > 6):
                self.add_error(field_name, 'PIN must be 4 to 6 digits only.')

        if pin_code and confirm_pin_code and pin_code != confirm_pin_code:
            self.add_error('confirm_pin_code', 'PIN codes do not match.')

        return cleaned_data

class ChangePasswordForm(forms.Form):
    current_password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'input',
            'placeholder': 'Current Password'
        })
    )

    new_password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'input',
            'placeholder': 'New Password'
        })
    )

    confirm_password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'input',
            'placeholder': 'Confirm New Password'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and len(new_password) < 8:
            self.add_error('new_password', 'Password must be at least 8 characters.')

        if new_password and confirm_password and new_password != confirm_password:
            self.add_error('confirm_password', 'New passwords do not match.')

        return cleaned_data
