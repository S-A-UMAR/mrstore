"""
Mr Store — Django Admin Registration
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count, Q
from django.utils import timezone
from .models import Order, Payment, Product, Refund, Notification, SavedPlayerID


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





@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['paystack_reference', 'order', 'amount', 'status_badge', 'verified_at']
    list_filter = ['status']
    search_fields = ['paystack_reference']
    readonly_fields = ['created_at', 'updated_at', 'paystack_reference']
    
    def status_badge(self, obj):
        colors = {
            'PENDING': '#ffc107',
            'SUCCESS': '#28a745',
            'FAILED': '#dc3545',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display(),
        )
    status_badge.short_description = 'Status'


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'amount', 'status_badge', 'requested_at', 'approved_at']
    list_filter = ['status', 'requested_at']
    search_fields = ['id', 'order__id', 'order__player_id']
    readonly_fields = ['id', 'requested_at']
    fieldsets = (
        ('Refund Info', {
            'fields': ('id', 'order', 'amount', 'reason', 'status')
        }),
        ('Paystack', {
            'fields': ('paystack_transfer_id',),
            'classes': ('collapse',)
        }),
        ('Admin Notes', {
            'fields': ('admin_notes',),
        }),
        ('Timestamps', {
            'fields': ('requested_at', 'approved_at', 'completed_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    actions = ['approve_refund', 'mark_as_processing']
    
    def status_badge(self, obj):
        colors = {
            'REQUESTED': '#ffc107',
            'APPROVED': '#0dcaf0',
            'PROCESSING': '#0d6efd',
            'COMPLETED': '#28a745',
            'FAILED': '#dc3545',
            'REJECTED': '#6c757d',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display(),
        )
    status_badge.short_description = 'Status'
    
    def approve_refund(self, request, queryset):
        updated = queryset.filter(status='REQUESTED').update(status='APPROVED', approved_at=timezone.now())
        self.message_user(request, f'{updated} refund(s) approved.')
    approve_refund.short_description = 'Approve selected refunds'
    
    def mark_as_processing(self, request, queryset):
        updated = queryset.filter(status='APPROVED').update(status='PROCESSING')
        self.message_user(request, f'{updated} refund(s) marked as processing.')
    mark_as_processing.short_description = 'Mark as processing'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'notification_type', 'channel', 'status_badge', 'sent_at']
    list_filter = ['status', 'notification_type', 'channel', 'created_at']
    search_fields = ['id', 'order__id', 'recipient']
    readonly_fields = ['id', 'created_at', 'sent_at']
    date_hierarchy = 'created_at'
    
    def status_badge(self, obj):
        colors = {
            'PENDING': '#ffc107',
            'SENT': '#28a745',
            'FAILED': '#dc3545',
            'QUEUED': '#0d6efd',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display(),
        )
    status_badge.short_description = 'Status'


@admin.register(SavedPlayerID)
class SavedPlayerIDAdmin(admin.ModelAdmin):
    list_display = ['user', 'label', 'player_id', 'is_default', 'is_valid', 'last_validated_at']
    list_filter = ['is_default', 'is_valid', 'created_at']
    search_fields = ['user__username', 'player_id', 'label']
    readonly_fields = ['created_at', 'updated_at', 'last_validated_at']
    actions = ['mark_as_invalid']
    
    def mark_as_invalid(self, request, queryset):
        updated = queryset.update(is_valid=False)
        self.message_user(request, f'{updated} saved Player ID(s) marked as invalid.')
    mark_as_invalid.short_description = 'Mark as invalid'


# Update OrderAdmin with enhanced features
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_id_link', 'player_id', 'product', 'status_badge', 'customer_email_display', 'created_at']
    list_filter = ['status', 'created_at', 'is_soft_deleted']
    search_fields = ['id', 'player_id', 'customer_email', 'wholesaler_order_id']
    readonly_fields = ['id', 'created_at', 'updated_at', 'wholesaler_order_id', 'failure_reason', 'metadata_display']
    fieldsets = (
        ('Order Info', {
            'fields': ('id', 'player_id', 'customer_email', 'user', 'product', 'status')
        }),
        ('Fulfillment', {
            'fields': ('wholesaler_order_id', 'failure_reason', 'failure_count', 'last_retry_at')
        }),
        ('Metadata', {
            'fields': ('metadata_display', 'is_soft_deleted'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = [PaymentInline]
    actions = ['mark_as_fulfilled', 'mark_as_failed', 'soft_delete_order']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    def order_id_link(self, obj):
        return format_html('<a href="#{}">{}</a>', obj.id, str(obj.id)[:8])
    order_id_link.short_description = 'Order ID'
    
    def status_badge(self, obj):
        colors = {
            'PENDING': '#ffc107',
            'PAID': '#0d6efd',
            'FULFILLED': '#28a745',
            'FAILED': '#dc3545',
            'REFUNDED': '#6f42c1',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display(),
        )
    status_badge.short_description = 'Status'
    
    def customer_email_display(self, obj):
        return obj.customer_email or (obj.user.email if obj.user else 'N/A')
    customer_email_display.short_description = 'Email'
    
    def metadata_display(self, obj):
        import json
        return format_html('<pre>{}</pre>', json.dumps(obj.metadata_json, indent=2))
    metadata_display.short_description = 'Metadata'
    
    def mark_as_fulfilled(self, request, queryset):
        updated = queryset.filter(status__in=['PAID', 'FAILED']).update(status='FULFILLED')
        self.message_user(request, f'{updated} order(s) marked as fulfilled.')
    mark_as_fulfilled.short_description = 'Mark selected as fulfilled'
    
    def mark_as_failed(self, request, queryset):
        updated = queryset.filter(status__in=['PENDING', 'PAID']).update(status='FAILED')
        self.message_user(request, f'{updated} order(s) marked as failed.')
    mark_as_failed.short_description = 'Mark selected as failed'
    
    def soft_delete_order(self, request, queryset):
        updated = queryset.update(is_soft_deleted=True)
        self.message_user(request, f'{updated} order(s) soft deleted.')
    soft_delete_order.short_description = 'Soft delete selected orders'


# Admin site customization
admin.site.site_header = 'Mr Store Admin'
admin.site.site_title = 'Mr Store'
admin.site.index_title = 'Dashboard'
