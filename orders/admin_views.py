"""
Mr Store — Admin Dashboard API Views
Provides statistics, order management, refund processing, analytics.
"""
import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.contrib.admin.views.decorators import staff_member_required

from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from .models import Order, Payment, Refund, Notification, Product
from .serializers import (
    OrderDetailSerializer, 
    PaymentDetailSerializer,
    RefundSerializer,
    NotificationSerializer,
    AdminDashboardStatsSerializer,
)
from .tasks import process_refund, fulfill_order

logger = logging.getLogger('orders')


# =============================================================
# Dashboard Statistics API
# =============================================================
@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_dashboard_stats(request):
    """Get KPI stats for admin dashboard."""
    try:
        # Calculate metrics
        total_revenue = Payment.objects.filter(status='SUCCESS').aggregate(
            Sum('amount')
        )['amount__sum'] or 0
        
        today = timezone.now().date()
        today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
        today_end = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))
        
        today_revenue = Payment.objects.filter(
            status='SUCCESS',
            verified_at__range=[today_start, today_end]
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        total_orders = Order.objects.filter(is_soft_deleted=False).count()
        fulfilled_orders = Order.objects.filter(status='FULFILLED', is_soft_deleted=False).count()
        failed_orders = Order.objects.filter(status='FAILED', is_soft_deleted=False).count()
        pending_refunds = Refund.objects.filter(status__in=['REQUESTED', 'APPROVED']).count()
        today_orders = Order.objects.filter(
            created_at__range=[today_start, today_end],
            is_soft_deleted=False
        ).count()
        
        conversion_rate = (fulfilled_orders / total_orders * 100) if total_orders > 0 else 0
        
        stats = {
            'total_revenue': float(total_revenue),
            'total_orders': total_orders,
            'fulfilled_orders': fulfilled_orders,
            'failed_orders': failed_orders,
            'pending_refunds': pending_refunds,
            'today_revenue': float(today_revenue),
            'today_orders': today_orders,
            'conversion_rate': round(conversion_rate, 2),
        }
        
        return Response(stats)
    
    except Exception as exc:
        logger.error(f"Error fetching dashboard stats: {str(exc)}", exc_info=True)
        return Response({'error': 'Failed to fetch stats'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================================
# Order Management API
# =============================================================
@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_order_list(request):
    """List all orders with filtering and search."""
    try:
        queryset = Order.objects.select_related('user', 'product', 'payment').filter(is_soft_deleted=False)
        
        # Filtering
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Search
        search = request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(id__icontains=search) | 
                Q(player_id__icontains=search) | 
                Q(customer_email__icontains=search)
            )
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        start = (page - 1) * page_size
        end = start + page_size
        
        total = queryset.count()
        paginated = queryset[start:end]
        
        serializer = OrderDetailSerializer(paginated, many=True)
        return Response({
            'total': total,
            'page': page,
            'page_size': page_size,
            'results': serializer.data
        })
    
    except Exception as exc:
        logger.error(f"Error fetching orders: {str(exc)}", exc_info=True)
        return Response({'error': 'Failed to fetch orders'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_order_detail(request, order_id):
    """Get detailed info for a specific order."""
    try:
        order = Order.objects.select_related('user', 'product', 'payment').get(id=order_id)
        serializer = OrderDetailSerializer(order)
        return Response(serializer.data)
    
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as exc:
        logger.error(f"Error fetching order detail: {str(exc)}", exc_info=True)
        return Response({'error': 'Failed to fetch order'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_order_action(request, order_id):
    """Perform admin actions on orders (fulfill, fail, retry)."""
    try:
        order = Order.objects.get(id=order_id)
        action = request.data.get('action')
        
        if action == 'fulfill':
            order.status = 'FULFILLED'
            order.save()
            return Response({'status': 'Order marked as fulfilled'})
        
        elif action == 'fail':
            order.status = 'FAILED'
            order.failure_reason = request.data.get('reason', 'Admin marked as failed')
            order.save()
            return Response({'status': 'Order marked as failed'})
        
        elif action == 'retry':
            if order.is_retriable():
                fulfill_order.delay(order_id=str(order.id))
                return Response({'status': 'Retry queued'})
            else:
                return Response({'error': 'Order cannot be retried'}, status=status.HTTP_400_BAD_REQUEST)
        
        elif action == 'soft_delete':
            order.is_soft_deleted = True
            order.save()
            return Response({'status': 'Order soft deleted'})
        
        else:
            return Response({'error': 'Unknown action'}, status=status.HTTP_400_BAD_REQUEST)
    
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as exc:
        logger.error(f"Error performing order action: {str(exc)}", exc_info=True)
        return Response({'error': 'Failed to perform action'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================================
# Refund Management API
# =============================================================
@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_refund_list(request):
    """List all refunds with filtering."""
    try:
        queryset = Refund.objects.select_related('order').all()
        
        # Filtering
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        start = (page - 1) * page_size
        end = start + page_size
        
        total = queryset.count()
        paginated = queryset[start:end]
        
        serializer = RefundSerializer(paginated, many=True)
        return Response({
            'total': total,
            'page': page,
            'page_size': page_size,
            'results': serializer.data
        })
    
    except Exception as exc:
        logger.error(f"Error fetching refunds: {str(exc)}", exc_info=True)
        return Response({'error': 'Failed to fetch refunds'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_refund_action(request, refund_id):
    """Approve or reject refunds."""
    try:
        refund = Refund.objects.get(id=refund_id)
        action = request.data.get('action')
        
        if action == 'approve':
            refund.status = 'APPROVED'
            refund.approved_at = timezone.now()
            refund.admin_notes = request.data.get('notes', '')
            refund.save()
            
            # Queue refund processing
            process_refund.delay(refund_id=str(refund.id))
            return Response({'status': 'Refund approved and queued for processing'})
        
        elif action == 'reject':
            refund.status = 'REJECTED'
            refund.admin_notes = request.data.get('reason', 'Rejected by admin')
            refund.save()
            return Response({'status': 'Refund rejected'})
        
        else:
            return Response({'error': 'Unknown action'}, status=status.HTTP_400_BAD_REQUEST)
    
    except Refund.DoesNotExist:
        return Response({'error': 'Refund not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as exc:
        logger.error(f"Error performing refund action: {str(exc)}", exc_info=True)
        return Response({'error': 'Failed to perform action'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================================
# Analytics API
# =============================================================
@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_analytics(request):
    """Get analytics and insights."""
    try:
        # Time range
        days = int(request.query_params.get('days', 30))
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Orders by status
        orders_by_status = Order.objects.filter(
            created_at__gte=cutoff_date,
            is_soft_deleted=False
        ).values('status').annotate(count=Count('id')).order_by('status')
        
        # Top products
        top_products = Order.objects.filter(
            created_at__gte=cutoff_date,
            status='FULFILLED',
            is_soft_deleted=False
        ).values('product__name').annotate(
            count=Count('id'),
            revenue=Sum('product__price_ngn')
        ).order_by('-count')[:10]
        
        # Daily revenue
        daily_revenue = Payment.objects.filter(
            verified_at__gte=cutoff_date,
            status='SUCCESS'
        ).extra(
            select={'date': 'DATE(verified_at)'}
        ).values('date').annotate(
            revenue=Sum('amount'),
            orders=Count('id')
        ).order_by('date')
        
        analytics = {
            'orders_by_status': list(orders_by_status),
            'top_products': list(top_products),
            'daily_revenue': [
                {
                    'date': str(item['date']),
                    'revenue': float(item['revenue']),
                    'orders': item['orders']
                } for item in daily_revenue
            ]
        }
        
        return Response(analytics)
    
    except Exception as exc:
        logger.error(f"Error fetching analytics: {str(exc)}", exc_info=True)
        return Response({'error': 'Failed to fetch analytics'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_notifications_log(request):
    """Get notification activity log."""
    try:
        queryset = Notification.objects.select_related('order').all()
        
        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))
        start = (page - 1) * page_size
        end = start + page_size
        
        total = queryset.count()
        paginated = queryset.order_by('-created_at')[start:end]
        
        serializer = NotificationSerializer(paginated, many=True)
        return Response({
            'total': total,
            'page': page,
            'page_size': page_size,
            'results': serializer.data
        })
    
    except Exception as exc:
        logger.error(f"Error fetching notification log: {str(exc)}", exc_info=True)
        return Response({'error': 'Failed to fetch log'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
