"""
Mr Store — Wholesaler B2B API Client

Abstracted HTTP client for the fulfilment provider (FazerCards/GamesDrop-style).
Replace the implementation of `_post` with the actual vendor endpoint + auth once
you have contracted with a provider.

All public methods raise `WholesalerError` on failure so callers can react gracefully.
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger('orders')


class WholesalerError(Exception):
    """Raised when the wholesaler API returns an error or times out."""
    pass


class WholesalerClient:
    """
    Thin REST client wrapping the B2B fulfilment API.

    Typical request body (adapt to your provider's schema):
    {
        "player_id": "5123456789",
        "sku":       "PUBG_NG_60UC",
        "reference": "ord_<uuid>",        # your internal order id
        "api_key":   "..."                 # injected from settings
    }

    Expected success response (HTTP 200/201):
    {
        "success": true,
        "order_id": "WH-20240101-XXXXX",  # wholesaler's own order id
        "status":   "completed"
    }
    """

    BASE_URL = settings.WHOLESALER_API_BASE_URL
    API_KEY = settings.WHOLESALER_API_KEY
    TIMEOUT = 20  # seconds — tune per SLA

    def place_order(self, *, player_id: str, sku: str, reference: str) -> dict:
        """
        Submit a top-up order to the wholesaler.

        Returns:
            dict with at minimum {"success": True, "order_id": "...", "status": "..."}

        Raises:
            WholesalerError on any failure.
        """
        payload = {
            'api_key': self.API_KEY,
            'player_id': player_id,
            'sku': sku,
            'reference': reference,
        }
        logger.info(
            'Wholesaler — placing order | player=%s sku=%s ref=%s',
            player_id, sku, reference,
        )
        return self._post('/orders/place', payload)

    def get_order_status(self, *, wholesaler_order_id: str) -> dict:
        """
        Query the status of a previously placed wholesaler order.
        Useful for async fulfilment scenarios.
        """
        payload = {
            'api_key': self.API_KEY,
            'order_id': wholesaler_order_id,
        }
        return self._post('/orders/status', payload)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _post(self, path: str, payload: dict) -> dict:
        url = f'{self.BASE_URL.rstrip("/")}{path}'
        try:
            response = requests.post(url, json=payload, timeout=self.TIMEOUT)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            logger.error('Wholesaler API timed out | url=%s', url)
            raise WholesalerError('Wholesaler API timed out. UC will be delivered shortly.')
        except requests.exceptions.ConnectionError as exc:
            logger.error('Wholesaler API connection error | url=%s | %s', url, exc)
            raise WholesalerError('Could not reach wholesaler. UC will be delivered shortly.')
        except requests.exceptions.HTTPError as exc:
            logger.error(
                'Wholesaler API HTTP error | url=%s | status=%s | body=%s',
                url, response.status_code, response.text,
            )
            raise WholesalerError(f'Wholesaler returned HTTP {response.status_code}.')

        try:
            data = response.json()
        except ValueError:
            logger.error('Wholesaler returned non-JSON response | url=%s', url)
            raise WholesalerError('Wholesaler returned an unexpected response format.')

        if not data.get('success'):
            msg = data.get('message', 'Unknown wholesaler error.')
            logger.error('Wholesaler order failed | url=%s | message=%s', url, msg)
            raise WholesalerError(msg)

        return data
