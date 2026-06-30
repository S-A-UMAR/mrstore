"""
orders URL configuration
"""
from django.urls import path
from . import views
from . import admin_views

app_name = 'orders'

urlpatterns = [
    # Config & Catalog
    path('config/',                views.frontend_config,          name='frontend-config'),
    path('products/',              views.product_list,             name='product-list'),
    
    # Orders Checkout
    path('orders/create/',         views.OrderCreateView.as_view(), name='order-create'),
    path('orders/<uuid:order_id>/status/', views.order_status,    name='order-status'),
    path('paystack-webhook/',      views.PaystackWebhookView.as_view(), name='paystack-webhook'),

    # User Authentication & Profiles
    path('auth/register/',         views.auth_register,            name='auth-register'),
    path('auth/login/',            views.auth_login,               name='auth-login'),
    path('auth/logout/',           views.auth_logout,              name='auth-logout'),
    path('auth/user/',             views.get_user_profile,         name='auth-user'),
    path('auth/saved-ids/add/',    views.saved_id_add,             name='saved-id-add'),
    path('auth/saved-ids/<int:record_id>/remove/', views.saved_id_remove, name='saved-id-remove'),
    
    # Admin Dashboard API
    path('admin/stats/',                   admin_views.admin_dashboard_stats,      name='admin-stats'),
    path('admin/orders/',                  admin_views.admin_order_list,           name='admin-orders-list'),
    path('admin/orders/<uuid:order_id>/',  admin_views.admin_order_detail,         name='admin-order-detail'),
    path('admin/orders/<uuid:order_id>/action/', admin_views.admin_order_action,   name='admin-order-action'),
    path('admin/refunds/',                 admin_views.admin_refund_list,          name='admin-refunds-list'),
    path('admin/refunds/<uuid:refund_id>/action/', admin_views.admin_refund_action, name='admin-refund-action'),
    path('admin/analytics/',               admin_views.admin_analytics,            name='admin-analytics'),
    path('admin/notifications/',           admin_views.admin_notifications_log,    name='admin-notifications'),
]
