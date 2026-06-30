"""
Mr Store — Notification Service
Sends emails and SMS to customers via SendGrid and Twilio.
"""
import logging
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

try:
    import sendgrid
    from sendgrid.helpers.mail import Mail, Email, To, Content
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False

try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

logger = logging.getLogger('orders')


class EmailService:
    """Send emails via SendGrid or Django email backend."""
    
    def __init__(self):
        self.api_key = settings.SENDGRID_API_KEY
        self.from_email = settings.DEFAULT_FROM_EMAIL
        self.use_sendgrid = SENDGRID_AVAILABLE and bool(self.api_key)
    
    def send_email(self, to_email, subject, message, html_message=None):
        """
        Send an email.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            message: Plain text message
            html_message: HTML message (optional)
        
        Returns:
            dict: {'success': bool, 'message_id': str or None, 'error': str or None}
        """
        try:
            if self.use_sendgrid:
                return self._send_via_sendgrid(to_email, subject, message, html_message)
            else:
                return self._send_via_django(to_email, subject, message, html_message)
        except Exception as exc:
            logger.error(f"Error sending email to {to_email}: {str(exc)}", exc_info=True)
            return {
                'success': False,
                'message_id': None,
                'error': str(exc),
            }
    
    def _send_via_sendgrid(self, to_email, subject, message, html_message=None):
        """Send via SendGrid API."""
        sg = sendgrid.SendGridAPIClient(self.api_key)
        
        mail = Mail(
            from_email=self.from_email,
            to_emails=To(to_email),
            subject=subject,
            plain_text_content=message,
            html_content=html_message or message,
        )
        
        response = sg.send(mail)
        message_id = response.headers.get('X-Message-ID', '')
        
        logger.info(f"Email sent to {to_email} via SendGrid: {message_id}")
        return {
            'success': True,
            'message_id': message_id,
            'error': None,
        }
    
    def _send_via_django(self, to_email, subject, message, html_message=None):
        """Fallback to Django email backend (console or SMTP)."""
        from django.core.mail import send_mail, EmailMultiAlternatives
        
        if html_message:
            msg = EmailMultiAlternatives(
                subject,
                message,
                self.from_email,
                [to_email],
            )
            msg.attach_alternative(html_message, "text/html")
            result = msg.send()
        else:
            result = send_mail(
                subject,
                message,
                self.from_email,
                [to_email],
            )
        
        logger.info(f"Email sent to {to_email} via Django backend")
        return {
            'success': result > 0,
            'message_id': None,
            'error': None,
        }


class SMSService:
    """Send SMS via Twilio."""
    
    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_PHONE_NUMBER
        self.available = TWILIO_AVAILABLE and bool(self.account_sid and self.auth_token)
    
    def send_sms(self, to_number, message):
        """
        Send an SMS message.
        
        Args:
            to_number: Recipient phone number (E.164 format, e.g. +2348000000000)
            message: SMS message content
        
        Returns:
            dict: {'success': bool, 'message_sid': str or None, 'error': str or None}
        """
        if not self.available:
            logger.warning("Twilio not configured, SMS sending disabled")
            return {
                'success': False,
                'message_sid': None,
                'error': 'SMS service not configured',
            }
        
        try:
            client = TwilioClient(self.account_sid, self.auth_token)
            sms = client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number,
            )
            
            logger.info(f"SMS sent to {to_number}: {sms.sid}")
            return {
                'success': True,
                'message_sid': sms.sid,
                'error': None,
            }
        
        except Exception as exc:
            logger.error(f"Error sending SMS to {to_number}: {str(exc)}", exc_info=True)
            return {
                'success': False,
                'message_sid': None,
                'error': str(exc),
            }


# Email templates
def get_order_confirmation_email(order):
    """Generate order confirmation email."""
    subject = f"{settings.STORE_NAME} - Order Confirmation"
    message = f"""
Dear Customer,

Your order has been confirmed!

Order ID: {order.id}
Product: {order.product.name}
Amount: ₦{order.product.price_ngn:,.2f}
PUBG Player ID: {order.player_id}

We will process your payment shortly. Once confirmed, your UC will be delivered immediately.

Track your order: {settings.STORE_NAME}/track/{order.id}

Thank you for your purchase!

Best regards,
{settings.STORE_NAME} Support Team
Contact: {settings.SUPPORT_WHATSAPP_NUMBER}
"""
    return subject, message


def get_payment_confirmed_email(order, payment):
    """Generate payment confirmation email."""
    subject = f"{settings.STORE_NAME} - Payment Confirmed"
    message = f"""
Dear Customer,

Your payment has been confirmed!

Order ID: {order.id}
Amount Paid: ₦{payment.amount:,.2f}
Reference: {payment.paystack_reference}

We're now delivering your {order.product.uc_amount} UC to your PUBG account.
This usually takes 1-5 minutes.

If you don't see the UC within 10 minutes, please contact our support team.

Best regards,
{settings.STORE_NAME} Support Team
WhatsApp: {settings.SUPPORT_WHATSAPP_NUMBER}
"""
    return subject, message


def get_uc_delivered_email(order):
    """Generate UC delivery confirmation email."""
    subject = f"{settings.STORE_NAME} - UC Delivered Successfully!"
    message = f"""
Dear Customer,

Great news! Your {order.product.uc_amount} UC has been successfully delivered!

Order ID: {order.id}
Player ID: {order.player_id}
UC Amount: {order.product.uc_amount}

Please check your PUBG account. The UC should be visible within a few minutes.

If you don't see it, try:
1. Refreshing your game
2. Checking your transaction history in PUBG
3. Restarting the game

Still having issues? Contact us via WhatsApp: {settings.SUPPORT_WHATSAPP_NUMBER}

Thank you for choosing {settings.STORE_NAME}!
"""
    return subject, message


def get_order_failed_email(order):
    """Generate order failure notification email."""
    subject = f"{settings.STORE_NAME} - Order Failed (Refund Processing)"
    message = f"""
Dear Customer,

We're sorry, but your order could not be completed.

Order ID: {order.id}
Reason: {order.failure_reason or 'System error'}

Don't worry! Your payment will be refunded automatically within 3-5 business days.

If you'd like to retry or have any questions, please contact our support team:
WhatsApp: {settings.SUPPORT_WHATSAPP_NUMBER}
Email: support@{settings.STORE_NAME}

We apologize for the inconvenience.

Best regards,
{settings.STORE_NAME} Support Team
"""
    return subject, message


def get_refund_approved_email(order, refund):
    """Generate refund approval notification email."""
    subject = f"{settings.STORE_NAME} - Refund Approved"
    message = f"""
Dear Customer,

Your refund has been approved!

Order ID: {order.id}
Refund Amount: ₦{refund.amount:,.2f}

Your refund will be processed to your original payment method within 3-5 business days.

If you have any questions, contact us:
WhatsApp: {settings.SUPPORT_WHATSAPP_NUMBER}

Thank you for your patience.

Best regards,
{settings.STORE_NAME} Support Team
"""
    return subject, message


# Public API functions
email_service = EmailService()
sms_service = SMSService()


def send_order_notification(order, notification_type):
    """
    Send order notification to customer.
    
    Args:
        order: Order instance
        notification_type: One of 'order_created', 'payment_confirmed', 'uc_delivered', 'order_failed', 'refund_approved'
    
    Returns:
        dict: Success status and details
    """
    customer_email = order.customer_email or (order.user.email if order.user else None)
    
    if not customer_email:
        return {
            'success': False,
            'error': 'No email address found',
        }
    
    templates = {
        'order_created': get_order_confirmation_email,
        'payment_confirmed': lambda o: get_payment_confirmed_email(o, o.payment),
        'uc_delivered': get_uc_delivered_email,
        'order_failed': get_order_failed_email,
        'refund_approved': lambda o: get_refund_approved_email(o, o.refund),
    }
    
    if notification_type not in templates:
        return {
            'success': False,
            'error': f'Unknown notification type: {notification_type}',
        }
    
    try:
        subject, message = templates[notification_type](order)
        result = email_service.send_email(customer_email, subject, message)
        
        if result['success']:
            logger.info(f"Sent {notification_type} email to {customer_email}")
        
        return result
    
    except Exception as exc:
        logger.error(f"Error sending {notification_type} notification: {str(exc)}", exc_info=True)
        return {
            'success': False,
            'error': str(exc),
        }


def send_sms_notification(phone_number, notification_type, order=None):
    """
    Send SMS notification.
    
    Args:
        phone_number: Recipient phone number
        notification_type: Type of notification
        order: Order instance (optional, for context)
    
    Returns:
        dict: Success status and details
    """
    messages = {
        'payment_confirmed': f"Payment confirmed! Your UC delivery will start soon. -  {settings.STORE_NAME}",
        'uc_delivered': f"Your UC has been delivered! Check your PUBG account. -{settings.STORE_NAME}",
        'order_failed': f"Your order failed. A refund is being processed. Contact support for help. -{settings.STORE_NAME}",
    }
    
    if notification_type not in messages:
        return {
            'success': False,
            'error': f'Unknown SMS notification type: {notification_type}',
        }
    
    return sms_service.send_sms(phone_number, messages[notification_type])
