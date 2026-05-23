from django.db import models
from django.utils import timezone
from datetime import timedelta


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
        return self.stock_quantity <= 5

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
            self.supplier_product.save()

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

    def __str__(self):
        return f"Supplier Delivery - {self.supplier_purchase} - {self.status}"


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

    def __str__(self):
        return f"{self.customer_name} - {self.status}"

class Quotation(models.Model):
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Sent', 'Sent'),
        ('Accepted', 'Accepted'),
        ('Rejected', 'Rejected'),
    ]

    supplier_product = models.ForeignKey(
        SupplierProduct,
        on_delete=models.PROTECT,
        related_name='quotations'
    )

    supplier_purchase = models.OneToOneField(
        SupplierPurchase,
        on_delete=models.SET_NULL,
        related_name='quotation',
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

    quotation_date = models.DateField(
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
    def company_name(self):
        return self.supplier_product.supplier.company_name

    @property
    def product(self):
        return self.supplier_product.product

    @property
    def unit_price(self):
        return self.supplier_product.unit_price

    def save(self, *args, **kwargs):
        self.total_price = self.supplier_product.unit_price * self.quantity

        if not self.valid_until:
            self.valid_until = self.quotation_date + timedelta(days=7)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Quotation #{self.pk} - {self.company_name}"


class Invoice(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Overdue', 'Overdue'),
        ('Cancelled', 'Cancelled'),
    ]

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

    @property
    def customer_name(self):
        return self.sale.customer_name

    def __str__(self):
        return f"Invoice #{self.pk} - {self.customer_name}"
