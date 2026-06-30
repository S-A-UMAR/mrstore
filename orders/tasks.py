"""
Celery tasks for async operations:
- Order fulfillment with retries
- Email/SMS notifications
- Order status tracking
- Refund processing
"""
import logging
from datetime import timedelta
from django.utils import timezone
from celery import shared_task
from django.conf import settings
from .models import Order, Notification, Refund, Payment
from .paystack_client import PaystackError
from .wholesaler_client import WholesalerError
from .notification_service import (
    send_order_notification as send_order_email,
    send_sms_notification,
    get_order_confirmation_email,
    get_payment_confirmed_email,
    get_uc_delivered_email,
    get_order_failed_email,
    get_refund_approved_email,
)

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def fulfill_order(self, order_id):
    """
    Async task to fulfill an order (deliver UC via wholesaler).
    Implements exponential backoff retry logic.
    """
    try:
        order = Order.objects.get(id=order_id)
        if order.status != 'PAID':
            logger.warning(f"Order {order_id} is not in PAID status, skipping fulfillment")
            return {'status': 'skipped', 'reason': 'not_paid'}
        
        logger.info(f"Starting fulfillment for order {order_id}")
        
        # Call wholesaler API to deliver UC
        wholesaler = WholesalerClient()
        result = wholesaler.deliver_uc(
            player_id=order.player_id,
            product_sku=order.product.sku,
            uc_amount=order.product.uc_amount,
            order_id=str(order.id),
        )
        
        if result['success']:
            order.status = 'FULFILLED'
            order.wholesaler_order_id = result.get('wholesaler_order_id', '')
            order.save()
            
            # Send success notification
            send_order_notification.delay(
                order_id=order_id,
                notification_type='uc_delivered',
            )
            
            logger.info(f"Order {order_id} fulfilled successfully")
            return {'status': 'fulfilled', 'wholesaler_id': order.wholesaler_order_id}
        else:
            raise Exception(f"Wholesaler returned error: {result.get('error', 'Unknown')}")
    
    except Exception as exc:
        logger.error(f"Error fulfilling order {order_id}: {str(exc)}", exc_info=True)
        order.failure_count += 1
        order.failure_reason = str(exc)
        order.last_retry_at = timezone.now()
        
        if order.failure_count >= 3:
            order.status = 'FAILED'
            order.save()
            
            # Send failure notification
            send_order_notification.delay(
                order_id=order_id,
                notification_type='order_failed',
            )
            
            logger.error(f"Order {order_id} marked FAILED after 3 retries")
            return {'status': 'failed', 'error': str(exc)}
        else:
            order.save()
            # Retry with exponential backoff: 1min, 5min, 15min
            retry_delays = [60, 300, 900]
            countdown = retry_delays[order.failure_count - 1]
            raise self.retry(exc=exc, countdown=countdown)


@shared_task(bind=True, max_retries=3)
def send_order_notification(self, order_id, notification_type):
    """
    Send email/SMS notification to customer about order status.
    Retries up to 3 times on failure with exponential backoff.
    """
    try:
        order = Order.objects.get(id=order_id)
        customer_email = order.customer_email or (order.user.email if order.user else None)
        
        if not customer_email:
            logger.warning(f"No email found for order {order_id}, skipping notification")
            return {'status': 'skipped', 'reason': 'no_email'}
        
        # Send email via notification service
        result = send_order_email(order, notification_type)
        
        if result['success']:
            # Log successful notification
            templates = {
                'order_created': get_order_confirmation_email,
                'payment_confirmed': lambda o: get_payment_confirmed_email(o, o.payment),
                'uc_delivered': get_uc_delivered_email,
                'order_failed': get_order_failed_email,
                'refund_approved': lambda o: get_refund_approved_email(o, o.refund),
            }
            subject, message = templates.get(notification_type, lambda o: ('', ''))(order)
            
            Notification.objects.create(
                order=order,
                channel='EMAIL',
                notification_type=notification_type,
                recipient=customer_email,
                subject=subject,
                message=message,
                status='SENT',
                sent_at=timezone.now(),
            )
            logger.info(f"Sent {notification_type} notification to {customer_email}")
            return {'status': 'sent', 'email': customer_email}
        else:
            raise Exception(f"Email sending failed: {result.get('error', 'Unknown error')}")
    
    except Exception as exc:
        logger.error(f"Error sending notification for order {order_id}: {str(exc)}", exc_info=True)
        try:
            order = Order.objects.get(id=order_id)
            Notification.objects.create(
                order=order,
                channel='EMAIL',
                notification_type=notification_type,
                recipient=order.customer_email or '',
                status='FAILED',
                error_message=str(exc),
                message='',
            )
        except:
            pass
        
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def retry_failed_orders():
    """
    Periodically check for failed orders and retry fulfillment.
    Runs every 5 minutes via Celery Beat.
    """
    try:
        # Get orders that failed < 3 times and haven't been retried in last minute
        cutoff_time = timezone.now() - timedelta(minutes=1)
        failed_orders = Order.objects.filter(
            status='FAILED',
            failure_count__lt=3,
            last_retry_at__lt=cutoff_time,
            is_soft_deleted=False,
        )[:10]  # Limit to 10 per run
        
        for order in failed_orders:
            logger.info(f"Retrying order {order.id}")
            fulfill_order.delay(order_id=order.id)
        
        return {'retried': failed_orders.count()}
    
    except Exception as exc:
        logger.error(f"Error in retry_failed_orders: {str(exc)}", exc_info=True)
        return {'error': str(exc)}


@shared_task
def check_order_status():
    """
    Check status of PAID orders that haven't been fulfilled yet.
    Runs every 10 minutes via Celery Beat.
    """
    try:
        # Get orders in PAID state for > 30 seconds
        cutoff_time = timezone.now() - timedelta(seconds=30)
        pending_fulfillment = Order.objects.filter(
            status='PAID',
            updated_at__lt=cutoff_time,
            is_soft_deleted=False,
        )[:5]
        
        for order in pending_fulfillment:
            logger.info(f"Triggering fulfillment for order {order.id}")
            fulfill_order.delay(order_id=order.id)
        
        return {'triggered': pending_fulfillment.count()}
    
    except Exception as exc:
        logger.error(f"Error in check_order_status: {str(exc)}", exc_info=True)
        return {'error': str(exc)}


@shared_task
def process_refund(refund_id):
    """
    Process a refund via Paystack API.
    """
    try:
        refund = Refund.objects.get(id=refund_id)
        order = refund.order
        
        if refund.status != 'APPROVED':
            logger.warning(f"Refund {refund_id} not in APPROVED status")
            return {'status': 'skipped', 'reason': 'not_approved'}
        
        # Get original payment
        payment = Payment.objects.get(order=order)
        
        # Call Paystack to process refund
        paystack = PaystackClient()
        result = paystack.refund_transaction(
            reference=payment.paystack_reference,
            amount=int(refund.amount * 100),  # Convert to kobo
        )
        
        if result['status']:
            refund.status = 'PROCESSING'
            refund.paystack_transfer_id = result.get('data', {}).get('transfer_code', '')
            refund.save()
            
            # Send notification
            send_order_notification.delay(
                order_id=order.id,
                notification_type='refund_approved',
            )
            
            logger.info(f"Refund {refund_id} initiated with Paystack")
            return {'status': 'processing', 'transfer_code': refund.paystack_transfer_id}
        else:
            raise Exception(f"Paystack error: {result.get('message', 'Unknown')}")
    
    except Exception as exc:
        logger.error(f"Error processing refund {refund_id}: {str(exc)}", exc_info=True)
        refund.status = 'FAILED'
        refund.save()
        return {'status': 'failed', 'error': str(exc)}


@shared_task
def cleanup_old_soft_deleted():
    """
    Clean up orders soft deleted > 90 days ago.
    Runs daily via Celery Beat.
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=90)
        deleted = Order.objects.filter(
            is_soft_deleted=True,
            updated_at__lt=cutoff_date,
        ).delete()
        
        logger.info(f"Cleaned up {deleted[0]} soft-deleted orders")
        return {'deleted': deleted[0]}
    
    except Exception as exc:
        logger.error(f"Error in cleanup_old_soft_deleted: {str(exc)}", exc_info=True)
        return {'error': str(exc)}
