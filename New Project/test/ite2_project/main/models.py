from django.db import models


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
        default='N/A'
    )

    email = models.EmailField(
        blank=True,
        null=True
    )

    address = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        default='N/A'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

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
        default='N/A'
    )

    address = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        default='N/A'
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
        default='N/A'
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
        default='N/A'
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
        default='N/A'
    )

    contact_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        default='N/A'
    )

    delivery_address = models.CharField(
        max_length=255,
        default='N/A'
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