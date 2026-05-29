from django.db import models
from django.utils import timezone
from datetime import timedelta


def make_business_code(prefix, pk):
    """Return readable IDs like D0001, EXP0001, and INV0001."""
    if not pk:
        return ''

    return f'{prefix}{pk:04d}'


class Category(models.Model):
    category_name = models.CharField(
        max_length=100,
        unique=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.category_name


class Supplier(models.Model):
    supplier_name = models.CharField(
        max_length=150
    )

    contact_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
    )

    email = models.EmailField(
        blank=True,
        null=True
    )

    address = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    @property
    def company_name(self):
        return self.supplier_name

    def __str__(self):
        return self.supplier_name


class Admin(models.Model):
    ROLE_CHOICES = [
        ('Admin', 'Admin'),
        ('Staff', 'Staff'),
    ]

    username = models.CharField(
        max_length=100,
        unique=True
    )

    first_name = models.CharField(
        max_length=100
    )

    last_name = models.CharField(
        max_length=100
    )

    password = models.CharField(
        max_length=255
    )

    email = models.EmailField(
        unique=True,
        blank=True,
        null=True
    )

    contact_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,

    )

    address = models.CharField(
        max_length=255,
        blank=True,
        null=True,

    )

    profile_picture = models.ImageField(
        upload_to='profiles/',
        blank=True,
        null=True,
        default='profiles/default-avatar.jpg'
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='Staff'
    )

    pin_code = models.CharField(
        max_length=6,
        blank=True,
        null=True,
        help_text='Optional 4-6 digit login PIN.'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    @property
    def is_admin(self):
        return self.role == 'Admin'

    def __str__(self):
        return self.username


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    product_name = models.CharField(
        max_length=150
    )

    brand = models.CharField(
        max_length=100
    )

    model_name = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    stock_quantity = models.PositiveIntegerField(
        default=0
    )

    low_stock_threshold = models.PositiveIntegerField(
    default=5
    )

    product_image = models.ImageField(
        upload_to='products/',
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def is_low_stock(self):
        return self.stock_quantity <= self.low_stock_threshold

    def __str__(self):
        return f"{self.brand} {self.product_name}"


class SupplierProduct(models.Model):
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='supplier_products',
        null=True,
        blank=True
    )

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    available_quantity = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        if self.product:
            return f"{self.supplier} - {self.product.product_name}"
        return f"{self.supplier} - No product selected"

class SupplierPurchase(models.Model):
    supplier_product = models.ForeignKey(
        SupplierProduct,
        on_delete=models.PROTECT
    )

    quantity = models.PositiveIntegerField()

    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    purchase_date = models.DateTimeField(
        auto_now_add=True
    )

    def save(self, *args, **kwargs):
        self.total_price = (
            self.supplier_product.unit_price * self.quantity
        )

        if not self.pk:
            if self.quantity > self.supplier_product.available_quantity:
                raise ValueError('Not enough supplier stock available.')

            self.supplier_product.available_quantity -= self.quantity
            self.supplier_product.save(update_fields=['available_quantity'])

            product = self.supplier_product.product

            if product:
                product.stock_quantity += self.quantity
                product.save(update_fields=['stock_quantity'])

        super().save(*args, **kwargs)

    def __str__(self):
        if self.supplier_product.product:
            return f"{self.supplier_product.product.product_name} - {self.quantity}"
        return f"No product selected - {self.quantity}"


class SupplierDelivery(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Delivered', 'Delivered'),
    ]


    delivery_code = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        editable=False
    )

    supplier_purchase = models.ForeignKey(
        SupplierPurchase,
        on_delete=models.PROTECT
    )

    expected_delivery_date = models.DateField(
        blank=True,
        null=True
    )

    delivery_address = models.CharField(
        max_length=255,
        blank=True,
        null=True,

    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    @property
    def display_id(self):
        return self.delivery_code or make_business_code('SD', self.pk)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not self.delivery_code:
            self.delivery_code = make_business_code('SD', self.pk)
            type(self).objects.filter(pk=self.pk).update(delivery_code=self.delivery_code)

    def __str__(self):
        return f"Supplier Delivery {self.display_id} - {self.supplier_purchase} - {self.status}"


class Sale(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT
    )

    customer_name = models.CharField(
        max_length=150,
        blank=True,
        null=True,

    )

    quantity_sold = models.PositiveIntegerField()

    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    sale_date = models.DateTimeField(
        auto_now_add=True
    )

    def save(self, *args, **kwargs):
        self.total_price = self.product.price * self.quantity_sold
    
        if not self.pk:
            if self.quantity_sold > self.product.stock_quantity:
                raise ValueError('Not enough stock available.')

            self.product.stock_quantity -= self.quantity_sold
            self.product.save()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.product_name} - {self.quantity_sold}"


class Delivery(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Delivered', 'Delivered'),
    ]


    delivery_code = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        editable=False
    )

    sale = models.ForeignKey(
        Sale,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    customer_name = models.CharField(
        max_length=150,

    )

    contact_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,

    )

    delivery_address = models.CharField(
        max_length=255,

    )

    expected_delivery_date = models.DateField(
        blank=True,
        null=True
    )
    
    delivery_group = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        db_index=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    @property
    def display_id(self):
        return self.delivery_code or make_business_code('D', self.pk)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not self.delivery_code:
            self.delivery_code = make_business_code('D', self.pk)
            type(self).objects.filter(pk=self.pk).update(delivery_code=self.delivery_code)

    def __str__(self):
        return f"Delivery {self.display_id} - {self.customer_name} - {self.status}"

class Expense(models.Model):
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Sent', 'Sent'),
        ('Accepted', 'Accepted'),
        ('Rejected', 'Rejected'),
        ('Converted', 'Converted'),
    ]


    expense_code = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        editable=False
    )

    # Expense fields. Accepted/converted expense records are
    # subtracted from paid invoice income in the income report.
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='customer_expenses',
        blank=True,
        null=True
    )

    customer_name = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )


    sale = models.OneToOneField(
        Sale,
        on_delete=models.SET_NULL,
        related_name='expense',
        blank=True,
        null=True
    )

    # Supplier expense links. These allow expense records to
    # connect to purchases/deliveries while preserving the supplier/company
    # name and products bought from the supplier.
    supplier_product = models.ForeignKey(
        SupplierProduct,
        on_delete=models.PROTECT,
        related_name='expenses',
        blank=True,
        null=True
    )

    supplier_purchase = models.OneToOneField(
        SupplierPurchase,
        on_delete=models.SET_NULL,
        related_name='expense',
        blank=True,
        null=True
    )

    quantity = models.PositiveIntegerField()

    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    expense_date = models.DateField(
        default=timezone.now
    )

    valid_until = models.DateField(
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Draft'
    )

    remarks = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    @property
    def is_customer_expense(self):
        return self.product_id is not None and bool(self.customer_name)

    @property
    def is_supplier_expense(self):
        return self.supplier_product_id is not None

    @property
    def company_name(self):
        # Direct expenses use the entered company name.
        # Supplier expenses are linked directly to the supplier company.
        if self.supplier_product:
            return self.supplier_product.supplier.company_name

        if self.customer_name:
            return self.customer_name

        return 'N/A'

    @property
    def display_product(self):
        if self.product:
            return self.product

        if self.supplier_product:
            return self.supplier_product.product

        return None

    @property
    def unit_price(self):
        if self.product:
            return self.product.price

        if self.supplier_product:
            return self.supplier_product.unit_price

        return 0

    def save(self, *args, **kwargs):
        self.total_price = self.unit_price * self.quantity

        if not self.valid_until:
            self.valid_until = self.expense_date + timedelta(days=7)

        super().save(*args, **kwargs)

        if not self.expense_code:
            self.expense_code = make_business_code('EXP', self.pk)
            type(self).objects.filter(pk=self.pk).update(expense_code=self.expense_code)

    @property
    def display_id(self):
        return self.expense_code or make_business_code('EXP', self.pk)

    def convert_to_supplier_purchase_and_delivery(self):
        if not self.is_supplier_expense:
            return None

        if self.supplier_purchase_id:
            purchase = self.supplier_purchase

            if purchase.supplier_product_id == self.supplier_product_id:
                quantity_difference = self.quantity - purchase.quantity

                if quantity_difference != 0:
                    if quantity_difference > self.supplier_product.available_quantity:
                        raise ValueError('Not enough supplier stock available.')

                    product = self.supplier_product.product

                    if product and product.stock_quantity + quantity_difference < 0:
                        raise ValueError('Cannot reduce product stock below zero.')

                    self.supplier_product.available_quantity -= quantity_difference
                    self.supplier_product.save(update_fields=['available_quantity'])

                    if product:
                        product.stock_quantity += quantity_difference
                        product.save(update_fields=['stock_quantity'])
            else:
                old_supplier_product = purchase.supplier_product
                old_product = old_supplier_product.product
                new_product = self.supplier_product.product

                if old_product and old_product.stock_quantity < purchase.quantity:
                    raise ValueError('Cannot reduce product stock below zero.')

                old_supplier_product.available_quantity += purchase.quantity
                old_supplier_product.save(update_fields=['available_quantity'])

                if old_product:
                    old_product.stock_quantity -= purchase.quantity
                    old_product.save(update_fields=['stock_quantity'])

                if self.quantity > self.supplier_product.available_quantity:
                    raise ValueError('Not enough supplier stock available.')

                self.supplier_product.available_quantity -= self.quantity
                self.supplier_product.save(update_fields=['available_quantity'])

                if new_product:
                    new_product.stock_quantity += self.quantity
                    new_product.save(update_fields=['stock_quantity'])

            purchase.supplier_product = self.supplier_product
            purchase.quantity = self.quantity
            purchase.total_price = self.total_price
            purchase.save(update_fields=['supplier_product', 'quantity', 'total_price'])

            SupplierDelivery.objects.get_or_create(
                supplier_purchase=purchase,
                defaults={
                    'delivery_address': self.supplier_product.supplier.address,
                    'status': 'Pending'
                }
            )
            SupplierDelivery.objects.filter(supplier_purchase=purchase).update(
                delivery_address=self.supplier_product.supplier.address
            )
            return purchase

        purchase = SupplierPurchase.objects.create(
            supplier_product=self.supplier_product,
            quantity=self.quantity
        )

        SupplierDelivery.objects.create(
            supplier_purchase=purchase,
            delivery_address=self.supplier_product.supplier.address,
            status='Pending'
        )

        self.supplier_purchase = purchase
        self.status = 'Converted'
        self.save(update_fields=['supplier_purchase', 'status', 'total_price', 'valid_until', 'updated_at'])
        return purchase

    def convert_to_sale_and_invoice(self, invoice_status='Paid'):
        if not self.is_customer_expense:
            return None

        if self.sale_id:
            sale = self.sale

            if sale.product_id == self.product_id:
                quantity_difference = self.quantity - sale.quantity_sold
                if quantity_difference != 0:
                    self.product.stock_quantity -= quantity_difference
                    self.product.save(update_fields=['stock_quantity'])
            else:
                old_product = sale.product
                old_product.stock_quantity += sale.quantity_sold
                old_product.save(update_fields=['stock_quantity'])

                self.product.stock_quantity -= self.quantity
                self.product.save(update_fields=['stock_quantity'])

            sale.product = self.product
            sale.customer_name = self.customer_name
            sale.quantity_sold = self.quantity
            sale.total_price = self.product.price * self.quantity
            sale.save(update_fields=['product', 'customer_name', 'quantity_sold', 'total_price'])

            invoice, created = Invoice.objects.get_or_create(
                sale=sale,
                defaults={
                    'status': invoice_status,
                    'notes': f'Auto-generated from Expense {self.display_id}.'
                }
            )
            if invoice.status != invoice_status or invoice.amount != sale.total_price:
                invoice.status = invoice_status
                invoice.amount = sale.total_price
                invoice.save(update_fields=['status', 'amount', 'due_date', 'updated_at'])
            return invoice

        sale = Sale.objects.create(
            product=self.product,
            customer_name=self.customer_name,
            quantity_sold=self.quantity
        )

        self.sale = sale
        self.status = 'Converted'
        self.save(update_fields=['sale', 'status', 'total_price', 'valid_until', 'updated_at'])

        invoice, created = Invoice.objects.get_or_create(
            sale=sale,
            defaults={
                'status': invoice_status,
                'notes': f'Auto-generated from Expense {self.display_id}.'
            }
        )

        return invoice

    def __str__(self):
        return f"Expense {self.display_id} - {self.company_name}"


class Invoice(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Overdue', 'Overdue'),
        ('Cancelled', 'Cancelled'),
    ]



    invoice_code = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        editable=False
    )

    sale = models.OneToOneField(
        Sale,
        on_delete=models.PROTECT,
        related_name='invoice'
    )

    invoice_date = models.DateField(
        default=timezone.now
    )

    due_date = models.DateField(
        blank=True,
        null=True
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending'
    )

    notes = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def save(self, *args, **kwargs):
        self.amount = self.sale.total_price

        if not self.due_date:
            self.due_date = self.invoice_date + timedelta(days=7)

        super().save(*args, **kwargs)

        if not self.invoice_code:
            self.invoice_code = make_business_code('INV', self.pk)
            type(self).objects.filter(pk=self.pk).update(invoice_code=self.invoice_code)

    @property
    def display_id(self):
        return self.invoice_code or make_business_code('INV', self.pk)

    @property
    def customer_name(self):
        return self.sale.customer_name

    def __str__(self):
        return f"Invoice {self.display_id} - {self.customer_name}"


class ContactSupport(models.Model):
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('In Progress', 'In Progress'),
        ('Closed', 'Closed'),
    ]

    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Normal', 'Normal'),
        ('High', 'High'),
        ('Urgent', 'Urgent'),
    ]

    admin = models.ForeignKey(
        Admin,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='support_requests'
    )

    name = models.CharField(max_length=150)
    email = models.EmailField(blank=True, null=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Normal')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.subject} - {self.status}'
