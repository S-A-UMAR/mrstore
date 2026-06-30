"""
Mr Store — Django Admin Registration
"""
from django.contrib import admin
from .models import Order, Payment, Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'uc_amount', 'price_ngn', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'sku']
    list_editable = ['is_active', 'price_ngn']
    ordering = ['price_ngn']


class PaymentInline(admin.StackedInline):
    model = Payment
    extra = 0
    readonly_fields = ['paystack_reference', 'amount', 'status', 'verified_at', 'created_at']
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'player_id', 'product', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['player_id', 'id', 'wholesaler_order_id']
    readonly_fields = ['id', 'created_at', 'updated_at', 'wholesaler_order_id']
    inlines = [PaymentInline]
    ordering = ['-created_at']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['paystack_reference', 'order', 'amount', 'status', 'verified_at']
    list_filter = ['status']
    search_fields = ['paystack_reference']
    readonly_fields = ['created_at', 'updated_at']
