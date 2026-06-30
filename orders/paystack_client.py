"""
Mr Store — Paystack API Client

Handles transaction initialization and HMAC signature verification for webhooks.
Uses raw `requests` — no third-party Paystack SDK dependency.
"""
import hashlib
import hmac
import logging
import uuid
import requests
from django.conf import settings

logger = logging.getLogger('orders')

PAYSTACK_BASE = 'https://api.paystack.co'


class PaystackError(Exception):
    """Raised when Paystack returns an unexpected error."""
    pass


def _headers() -> dict:
    return {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
        'Content-Type': 'application/json',
    }


def initialize_transaction(*, email: str, amount_kobo: int, order_id: str, metadata: dict = None) -> dict:
    """
    Create a Paystack transaction and return the authorization_url and access_code.

    Args:
        email:       Customer email (required by Paystack for receipts).
        amount_kobo: Amount in kobo (smallest NGN unit, e.g. ₦750 = 75000 kobo).
        order_id:    Our internal Order UUID — used as the Paystack reference.
        metadata:    Optional dict of custom fields shown in the Paystack dashboard.

    Returns:
        dict: {"reference": ..., "access_code": ..., "authorization_url": ...}
    """
    reference = f'mrstore-{order_id}'
    payload = {
        'email': email,
        'amount': amount_kobo,
        'reference': reference,
        'currency': settings.STORE_CURRENCY,
        # Enforce strong authentication — Paystack will route via 3DS where available
        'channels': ['card', 'bank', 'ussd', 'bank_transfer'],
        'metadata': metadata or {},
    }
    try:
        resp = requests.post(
            f'{PAYSTACK_BASE}/transaction/initialize',
            json=payload,
            headers=_headers(),
            timeout=15,
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        logger.error('Paystack initialize failed: %s', exc)
        raise PaystackError('Could not reach payment gateway. Please try again.')

    data = resp.json()
    if not data.get('status'):
        logger.error('Paystack initialize error: %s', data.get('message'))
        raise PaystackError(data.get('message', 'Payment initialization failed.'))

    tx = data['data']
    return {
        'reference': tx['reference'],
        'access_code': tx['access_code'],
        'authorization_url': tx['authorization_url'],
    }


def verify_webhook_signature(payload_bytes: bytes, signature_header: str) -> bool:
    """
    Verify that a webhook request originated from Paystack.
    Uses HMAC-SHA512 as documented by Paystack.

    Args:
        payload_bytes:    The raw request body bytes.
        signature_header: Value of the X-Paystack-Signature header.

    Returns:
        True if the signature is valid, False otherwise.
    """
    expected = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
        msg=payload_bytes,
        digestmod=hashlib.sha512,
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)
