"""
Mr Store — Upgraded DRF Serializers
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Product, Order, Payment, SavedPlayerID


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
