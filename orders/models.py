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
from .validators import validate_pubg_player_id


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
    Enhanced with customer email, failure tracking, and refund support.
    Transitions: PENDING → PAID → FULFILLED
                         ↘ FAILED → REFUNDED
    """

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Payment'
        PAID = 'PAID', 'Payment Confirmed'
        FULFILLED = 'FULFILLED', 'UC Delivered'
        FAILED = 'FAILED', 'Failed'
        REFUNDED = 'REFUNDED', 'Refunded'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        help_text="User account linked to this order, if authenticated.",
    )
    customer_email = models.EmailField(
        blank=True,
        default='',
        db_index=True,
        help_text="Customer email for notifications (guest or registered user)",
    )
    player_id = models.CharField(
        max_length=30,
        validators=[validate_pubg_player_id],
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
    failure_reason = models.TextField(
        blank=True,
        default='',
        help_text="Reason for order failure (fulfillment/payment/etc)",
    )
    failure_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of fulfillment retry attempts",
    )
    last_retry_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last retry attempt",
    )
    metadata_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Extra tracking data (validation errors, user agent, etc)",
    )
    is_soft_deleted = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Soft delete flag for archival",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['customer_email', 'status']),
            models.Index(fields=['is_soft_deleted', 'created_at']),
        ]

    def __str__(self):
        return f'Order {self.id} — {self.player_id} — {self.status}'
    
    def is_retriable(self):
        """Check if order can be retried"""
        return self.status == 'FAILED' and self.failure_count < 3


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


class Refund(models.Model):
    """
    Refund record for orders. Tracks refund requests, approvals, and payouts.
    Supports partial refunds (though typically full).
    """

    class Status(models.TextChoices):
        REQUESTED = 'REQUESTED', 'Refund Requested'
        APPROVED = 'APPROVED', 'Approved by Admin'
        PROCESSING = 'PROCESSING', 'Paystack Processing'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
        REJECTED = 'REJECTED', 'Rejected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='refund',
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Refund amount in NGN",
    )
    reason = models.TextField(
        help_text="Customer's reason for refund request",
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.REQUESTED,
        db_index=True,
    )
    paystack_transfer_id = models.CharField(
        max_length=120,
        blank=True,
        default='',
        help_text="Paystack transfer recipient code or reference",
    )
    admin_notes = models.TextField(
        blank=True,
        default='',
        help_text="Internal notes from admin",
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-requested_at']
        verbose_name = 'Refund'
        verbose_name_plural = 'Refunds'
        indexes = [
            models.Index(fields=['status', 'requested_at']),
            models.Index(fields=['order']),
        ]

    def __str__(self):
        return f'Refund {self.id} — {self.amount} NGN — {self.status}'


class Notification(models.Model):
    """
    Notification record for order status updates.
    Tracks emails and SMS sent to customers.
    """

    class Channel(models.TextChoices):
        EMAIL = 'EMAIL', 'Email'
        SMS = 'SMS', 'SMS'
        BOTH = 'BOTH', 'Both Email and SMS'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Send'
        SENT = 'SENT', 'Successfully Sent'
        FAILED = 'FAILED', 'Failed'
        QUEUED = 'QUEUED', 'Queued for Retry'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    channel = models.CharField(
        max_length=10,
        choices=Channel.choices,
        default=Channel.EMAIL,
    )
    notification_type = models.CharField(
        max_length=50,
        choices=[
            ('order_created', 'Order Created'),
            ('payment_confirmed', 'Payment Confirmed'),
            ('uc_delivered', 'UC Delivered'),
            ('order_failed', 'Order Failed'),
            ('refund_requested', 'Refund Requested'),
            ('refund_approved', 'Refund Approved'),
            ('refund_completed', 'Refund Completed'),
        ],
        db_index=True,
    )
    recipient = models.CharField(
        max_length=255,
        help_text="Email address or phone number",
    )
    subject = models.CharField(max_length=255, blank=True, default='')
    message = models.TextField()
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    error_message = models.TextField(blank=True, default='')
    retry_count = models.PositiveIntegerField(default=0)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        indexes = [
            models.Index(fields=['order', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f'Notification {self.id} — {self.notification_type} — {self.status}'


class SavedPlayerID(models.Model):
    """
    Saved Player IDs for authenticated users to allow one-click checkouts
    without entering numeric Player IDs manually.
    Enhanced with is_default flag for quick-select priority.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='saved_player_ids',
    )
    player_id = models.CharField(
        max_length=30,
        validators=[validate_pubg_player_id],
        help_text="PUBG numeric Player ID",
    )
    label = models.CharField(
        max_length=80,
        help_text="E.g. 'My Main Account', 'Second Profile'",
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Mark as default for quick-select",
    )
    is_valid = models.BooleanField(
        default=True,
        help_text="Flag set to False if PUBG API validation fails",
    )
    validation_error = models.TextField(
        blank=True,
        default='',
        help_text="Error message from PUBG API validation",
    )
    last_validated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time Player ID was validated against PUBG API",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-created_at']
        unique_together = ('user', 'player_id')
        verbose_name = 'Saved Player ID'
        verbose_name_plural = 'Saved Player IDs'
        indexes = [
            models.Index(fields=['user', 'is_default']),
            models.Index(fields=['is_valid']),
        ]

    def __str__(self):
        return f'{self.user.username} — {self.label} ({self.player_id})'
