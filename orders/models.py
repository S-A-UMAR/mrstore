"""
Mr Store — Database Models
Exposes:
  - Product: UC packages available for sale
  - Order:   Customer purchase record (linked optionally to a User account)
  - Payment: Paystack payment record linked 1:1 to an Order
  - SavedPlayerID: User's saved numeric PUBG Player IDs for quick access
"""
import uuid
from django.db import models
from django.contrib.auth.models import User


class Product(models.Model):
    """
    A UC package available for purchase.
    `sku` is region-specific — must match the wholesaler's catalog exactly.
    `price_ngn` is the retail price in Nigerian Naira.
    """
    name = models.CharField(max_length=120, help_text="Display name, e.g. '60 UC'")
    sku = models.CharField(
        max_length=80,
        unique=True,
        help_text="Wholesaler/region-specific SKU, e.g. 'PUBG_NG_60UC'",
    )
    uc_amount = models.PositiveIntegerField(help_text="Number of UC this package grants")
    price_ngn = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Retail price in NGN (e.g. 750.00)",
    )
    badge = models.CharField(max_length=50, blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['price_ngn']
        verbose_name = 'UC Package'
        verbose_name_plural = 'UC Packages'

    def __str__(self):
        return f'{self.name} (₦{self.price_ngn})'

    @property
    def price_kobo(self):
        return int(self.price_ngn * 100)


class Order(models.Model):
    """
    A customer order. UUID primary key prevents sequential enumeration of orders.
    Associated optionally with an authenticated User.
    Transitions: PENDING → PAID → FULFILLED
                         ↘ FAILED
    """

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Payment'
        PAID = 'PAID', 'Payment Confirmed'
        FULFILLED = 'FULFILLED', 'UC Delivered'
        FAILED = 'FAILED', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        help_text="User account linked to this order, if authenticated.",
    )
    player_id = models.CharField(
        max_length=30,
        help_text="PUBG numeric Player ID supplied by the customer",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='orders',
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    wholesaler_order_id = models.CharField(max_length=120, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'

    def __str__(self):
        return f'Order {self.id} — {self.player_id} — {self.status}'


class Payment(models.Model):
    """
    Paystack payment record.
    OneToOne with Order ensures exactly one Payment per Order.
    The unique constraint on `paystack_reference` prevents double-spend processing.
    """

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Awaiting Verification'
        SUCCESS = 'SUCCESS', 'Verified Successful'
        FAILED = 'FAILED', 'Verification Failed'

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='payment',
    )
    paystack_reference = models.CharField(
        max_length=120,
        unique=True,
        help_text="Paystack transaction reference (globally unique)",
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Confirmed amount in NGN",
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
    )
    paystack_access_code = models.CharField(max_length=120, blank=True, default='')
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'

    def __str__(self):
        return f'Payment [{self.paystack_reference}] — {self.status}'


class SavedPlayerID(models.Model):
    """
    Saved Player IDs for authenticated users to allow one-click checkouts
    without entering numeric Player IDs manually.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='saved_player_ids',
    )
    player_id = models.CharField(
        max_length=30,
        help_text="PUBG numeric Player ID",
    )
    label = models.CharField(
        max_length=80,
        help_text="E.g. 'My Main Account', 'Second Profile'",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'player_id')
        verbose_name = 'Saved Player ID'
        verbose_name_plural = 'Saved Player IDs'

    def __str__(self):
        return f'{self.user.username} — {self.label} ({self.player_id})'
