"""
Mr Store — REST API Views
Features User Authentication, Profile Loading, Saved Player IDs management,
Order Creation with user linking, and Paystack Webhook processing.
"""
import json
import logging
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User

from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes, permission_classes
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from .models import Order, Payment, Product, SavedPlayerID
from .paystack_client import PaystackError, initialize_transaction, verify_webhook_signature
from .serializers import (
    OrderCreateSerializer, 
    OrderStatusSerializer, 
    ProductSerializer, 
    SavedPlayerIDSerializer,
    UserRegisterSerializer,
    UserSerializer
)
from .wholesaler_client import WholesalerClient, WholesalerError

logger = logging.getLogger('orders')


class OrderCreateThrottle(AnonRateThrottle):
    scope = 'order_create'


# =============================================================
# Products Listing & Frontend Configuration
# =============================================================
@api_view(['GET'])
def product_list(request):
    """Retrieve all active UC packages."""
    products = Product.objects.filter(is_active=True)
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def frontend_config(request):
    """Expose only safe public credentials to the frontend."""
    from django.conf import settings
    return Response({
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
        'store_name': settings.STORE_NAME,
        'currency': settings.STORE_CURRENCY,
        'support_whatsapp': settings.SUPPORT_WHATSAPP_NUMBER,
    })


# =============================================================
# User Authentication API Views
# =============================================================
@api_view(['POST'])
def auth_register(request):
    """Register a new user account and log them in instantly."""
    serializer = UserRegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    user = serializer.save()
    login(request, user)
    return Response({
        'status': 'success',
        'user': UserSerializer(user).data
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def auth_login(request):
    """Log in an existing user using credentials."""
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '')

    if not username or not password:
        return Response({'error': 'Username and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return Response({
            'status': 'success',
            'user': UserSerializer(user).data
        })
    return Response({'error': 'Invalid username or password.'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
def auth_logout(request):
    """Log out the current user session."""
    logout(request)
    return Response({'status': 'success'})


@api_view(['GET'])
def get_user_profile(request):
    """
    Retrieve logged-in user profile, list of saved Player IDs,
    and complete order history.
    """
    if not request.user.is_authenticated:
        return Response({'authenticated': False}, status=status.HTTP_200_OK)

    # Fetch saved Player IDs
    saved_ids = SavedPlayerID.objects.filter(user=request.user)
    saved_ids_serializer = SavedPlayerIDSerializer(saved_ids, many=True)

    # Fetch user's order history
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    orders_serializer = OrderStatusSerializer(orders, many=True)

    return Response({
        'authenticated': True,
        'user': UserSerializer(request.user).data,
        'saved_ids': saved_ids_serializer.data,
        'orders': orders_serializer.data,
    })


# =============================================================
# Saved Player IDs Management API
# =============================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def saved_id_add(request):
    """Add a new Player ID card to the user's profile."""
    serializer = SavedPlayerIDSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    # Check for duplicates
    pid = serializer.validated_data['player_id']
    if SavedPlayerID.objects.filter(user=request.user, player_id=pid).exists():
        return Response({'error': 'This Player ID is already saved.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer.save(user=request.user)
    return Response({
        'status': 'success',
        'saved_id': serializer.data
    }, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def saved_id_remove(request, record_id):
    """Delete a saved Player ID record."""
    try:
        record = SavedPlayerID.objects.get(pk=record_id, user=request.user)
        record.delete()
        return Response({'status': 'success'})
    except SavedPlayerID.DoesNotExist:
        return Response({'error': 'Record not found.'}, status=status.HTTP_404_NOT_FOUND)


# =============================================================
# Order & Checkout Handling
# =============================================================
class OrderCreateView(APIView):
    """
    Creates a PENDING order (linked to request.user if logged in)
    and returns Paystack metadata.
    """
    throttle_classes = [OrderCreateThrottle]

    def post(self, request, *args, **kwargs):
        from django.conf import settings

        serializer = OrderCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        player_id = serializer.validated_data['player_id']
        product: Product = serializer.validated_data['product_id']
        
        # Determine order link
        user = request.user if request.user.is_authenticated else None
        customer_email = request.data.get('email', '').strip()  # Get email from request for guests
        
        if not customer_email:
            customer_email = user.email if (user and user.email) else ''

        try:
            with transaction.atomic():
                order = Order.objects.create(
                    user=user,
                    player_id=player_id,
                    customer_email=customer_email,
                    product=product,
                    status=Order.Status.PENDING,
                )
                paystack_data = initialize_transaction(
                    email=customer_email or user.email if user else 'noreply@mrstore.ng',
                    amount_kobo=product.price_kobo,
                    order_id=str(order.id),
                    metadata={
                        'player_id': player_id,
                        'product_name': product.name,
                        'uc_amount': product.uc_amount,
                        'order_id': str(order.id),
                        'user_id': user.id if user else None,
                        'custom_fields': [
                            {'display_name': 'Player ID', 'variable_name': 'player_id', 'value': player_id},
                            {'display_name': 'Package',   'variable_name': 'package',   'value': product.name},
                        ],
                    },
                )
                Payment.objects.create(
                    order=order,
                    paystack_reference=paystack_data['reference'],
                    amount=product.price_ngn,
                    paystack_access_code=paystack_data['access_code'],
                    status=Payment.Status.PENDING,
                )

        except PaystackError as exc:
            logger.error('Order creation failed (Paystack) | player=%s | %s', player_id, exc)
            return Response({'error': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as exc:
            logger.exception('Unexpected error during order creation | player=%s', player_id)
            return Response({'error': 'An unexpected error occurred.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.info(
            'Order created | id=%s player=%s product=%s',
            order.id, player_id, product.sku,
        )
        return Response({
            'order_id': str(order.id),
            'reference': paystack_data['reference'],
            'access_code': paystack_data['access_code'],
            'amount': product.price_kobo,
            'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
        }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def order_status(request, order_id):
    """Fetch status for loader updates."""
    try:
        order = Order.objects.get(pk=order_id)
    except (Order.DoesNotExist, ValueError):
        return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

    return Response(OrderStatusSerializer(order).data)


# =============================================================
# Paystack Webhook Handler
# =============================================================
class PaystackWebhookView(APIView):
    """Receives and parses Paystack callback webhooks with signature checks."""

    def post(self, request, *args, **kwargs):
        raw_body = request.body
        signature = request.headers.get('X-Paystack-Signature', '')

        if not signature:
            return Response({'error': 'Missing signature.'}, status=status.HTTP_400_BAD_REQUEST)

        if not verify_webhook_signature(raw_body, signature):
            return Response({'error': 'Invalid signature.'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            return Response({'error': 'Invalid JSON.'}, status=status.HTTP_400_BAD_REQUEST)

        event = payload.get('event')
        if event != 'charge.success':
            return Response({'status': 'ignored'}, status=status.HTTP_200_OK)

        data = payload.get('data', {})
        reference = data.get('reference', '')
        paid_amount_kobo = data.get('amount', 0)

        try:
            payment = Payment.objects.select_related('order__product').get(
                paystack_reference=reference,
            )
        except Payment.DoesNotExist:
            return Response({'error': 'Payment not found.'}, status=status.HTTP_404_NOT_FOUND)

        if payment.status == Payment.Status.SUCCESS:
            return Response({'status': 'already_processed'}, status=status.HTTP_200_OK)

        order = payment.order
        expected_kobo = order.product.price_kobo
        if paid_amount_kobo != expected_kobo:
            with transaction.atomic():
                payment.status = Payment.Status.FAILED
                payment.save(update_fields=['status', 'updated_at'])
                order.status = Order.Status.FAILED
                order.save(update_fields=['status', 'updated_at'])
            return Response({'status': 'amount_mismatch'}, status=status.HTTP_200_OK)

        with transaction.atomic():
            payment.status = Payment.Status.SUCCESS
            payment.verified_at = timezone.now()
            payment.save(update_fields=['status', 'verified_at', 'updated_at'])
            order.status = Order.Status.PAID
            order.save(update_fields=['status', 'updated_at'])

        # Auto-credit UC
        self._fulfill_order(order, payment)
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)

    @staticmethod
    def _fulfill_order(order: Order, payment: Payment):
        client = WholesalerClient()
        try:
            result = client.place_order(
                player_id=order.player_id,
                sku=order.product.sku,
                reference=str(order.id),
            )
            wholesaler_order_id = result.get('order_id', '')
            order.wholesaler_order_id = wholesaler_order_id
            order.status = Order.Status.FULFILLED
            order.save(update_fields=['status', 'wholesaler_order_id', 'updated_at'])
        except WholesalerError as exc:
            order.status = Order.Status.FAILED
            order.save(update_fields=['status', 'updated_at'])
            logger.error('Fulfillment error on webhook: %s', exc)
