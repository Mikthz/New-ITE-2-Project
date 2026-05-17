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
        null=True
    )

    email = models.EmailField(
        blank=True,
        null=True
    )

    address = models.CharField(
        max_length=255,
        blank=True,
        null=True
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
        null=True
    )

    address = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    profile_picture = models.ImageField(
        upload_to='admins/',
        default='admins/default-avatar.jpg',
        blank=True,
        null=True
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

    def __str__(self):
        return self.username

    @property
    def is_admin(self):
        return self.role == 'Admin'

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


class Sale(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    customer_name = models.CharField(
        max_length=150,
        blank=True,
        null=True
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
        if not self.total_price:
            self.total_price = self.product.price * self.quantity_sold

        if not self.pk:
            self.product.stock_quantity -= self.quantity_sold
            self.product.save()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.product_name} - {self.quantity_sold}"