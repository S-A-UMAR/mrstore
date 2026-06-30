"""
Mr Store — Upgraded DRF Serializers
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Product, Order, Payment, SavedPlayerID, Refund, Notification


class ProductSerializer(serializers.ModelSerializer):
    """Public-facing product serializer."""
    price_kobo = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'sku', 'uc_amount', 'price_ngn', 'price_kobo', 'badge']


class OrderCreateSerializer(serializers.Serializer):
    """Validates payload for POST /api/orders/create/"""
    player_id = serializers.CharField(
        max_length=30,
        min_length=4,
        trim_whitespace=True,
    )
    product_id = serializers.IntegerField()

    def validate_player_id(self, value):
        if not value.isdigit():
            raise serializers.ValidationError(
                'Player ID must contain only digits.'
            )
        return value

    def validate_product_id(self, value):
        try:
            product = Product.objects.get(pk=value, is_active=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError('Selected package is invalid.')
        return product


class OrderStatusSerializer(serializers.ModelSerializer):
    """Detailed order status for tracking page / order history."""
    product_name = serializers.CharField(source='product.name', read_only=True)
    price_ngn = serializers.DecimalField(source='product.price_ngn', max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'player_id', 'status', 'product_name', 'price_ngn', 'created_at']


class SavedPlayerIDSerializer(serializers.ModelSerializer):
    """Handles saving and reading user Player IDs."""
    
    class Meta:
        model = SavedPlayerID
        fields = ['id', 'player_id', 'label', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_player_id(self, value):
        value = value.strip()
        if not value.isdigit():
            raise serializers.ValidationError('Player ID must be numeric (digits only).')
        if len(value) < 4:
            raise serializers.ValidationError('Player ID must be at least 4 digits.')
        return value


class UserRegisterSerializer(serializers.Serializer):
    """Validates and processes user account registration."""
    username = serializers.CharField(max_length=150, min_length=3, trim_whitespace=True)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=6, write_only=True)

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('Username is already taken.')
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Email is already registered.')
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user


class UserSerializer(serializers.ModelSerializer):
    """Serializes user info for profile view."""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'date_joined']


# Admin Dashboard Serializers

class PaymentDetailSerializer(serializers.ModelSerializer):
    """Detailed payment info for admin dashboard."""
    order_id = serializers.CharField(source='order.id', read_only=True)
    
    class Meta:
        model = Payment
        fields = ['id', 'order_id', 'paystack_reference', 'amount', 'status', 'verified_at', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'paystack_reference']


class RefundSerializer(serializers.ModelSerializer):
    """Refund management serializer."""
    order_details = serializers.SerializerMethodField()
    
    class Meta:
        model = Refund
        fields = ['id', 'order', 'order_details', 'amount', 'reason', 'status', 'admin_notes', 'requested_at', 'approved_at', 'completed_at']
        read_only_fields = ['id', 'requested_at']
    
    def get_order_details(self, obj):
        return {
            'id': str(obj.order.id),
            'player_id': obj.order.player_id,
            'product': obj.order.product.name,
            'original_amount': str(obj.order.product.price_ngn),
        }


class NotificationSerializer(serializers.ModelSerializer):
    """Notification log serializer."""
    order_id = serializers.CharField(source='order.id', read_only=True)
    
    class Meta:
        model = Notification
        fields = ['id', 'order_id', 'notification_type', 'channel', 'recipient', 'status', 'sent_at', 'created_at']
        read_only_fields = ['id', 'created_at', 'sent_at']


class OrderDetailSerializer(serializers.ModelSerializer):
    """Detailed order info for admin dashboard."""
    user_email = serializers.SerializerMethodField()
    product_details = ProductSerializer(source='product', read_only=True)
    payment_details = PaymentDetailSerializer(source='payment', read_only=True)
    refund_details = RefundSerializer(source='refund', read_only=True)
    notification_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'player_id', 'customer_email', 'user_email', 'product_details',
            'status', 'wholesaler_order_id', 'failure_reason', 'failure_count',
            'payment_details', 'refund_details', 'notification_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'wholesaler_order_id']
    
    def get_user_email(self, obj):
        return obj.user.email if obj.user else None
    
    def get_notification_count(self, obj):
        return obj.notifications.count()


class AdminDashboardStatsSerializer(serializers.Serializer):
    """Dashboard KPI statistics."""
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_orders = serializers.IntegerField()
    fulfilled_orders = serializers.IntegerField()
    failed_orders = serializers.IntegerField()
    pending_refunds = serializers.IntegerField()
    today_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    today_orders = serializers.IntegerField()
    conversion_rate = serializers.FloatField()
