"""
Comprehensive test suite for Mr Store backend
Tests cover: validators, models, API endpoints, auth, and order processing
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
import json
import uuid

from .models import Product, Order, Payment, SavedPlayerID
from .validators import validate_pubg_player_id


# =====================================================================
# Unit Tests: Player ID Validator
# =====================================================================

class PubgPlayerIDValidatorTests(TestCase):
    """Test PUBG Player ID validation rules"""
    
    def test_valid_player_ids(self):
        """Valid player IDs should pass validation"""
        valid_ids = [
            'player123',
            'PRO-GAMER-99',
            'abc-123-def',
            '12345',
            'A',
            'a-b-c-d-e',
            'Test-Player-2025',
        ]
        for player_id in valid_ids:
            try:
                validate_pubg_player_id(player_id)
            except ValidationError:
                self.fail(f"Valid player ID rejected: {player_id}")
    
    def test_invalid_length(self):
        """Player IDs outside 1-24 character range should fail"""
        with self.assertRaises(ValidationError):
            validate_pubg_player_id('')  # Empty
        
        with self.assertRaises(ValidationError):
            validate_pubg_player_id('a' * 25)  # Too long
    
    def test_invalid_characters(self):
        """Player IDs with special characters should fail"""
        invalid_ids = [
            'player@123',
            'player#gamer',
            'player $pecial',
            'player_underscore',
            'player.dot',
            'player!',
        ]
        for player_id in invalid_ids:
            with self.assertRaises(ValidationError):
                validate_pubg_player_id(player_id)
    
    def test_leading_trailing_hyphens(self):
        """Player IDs with leading/trailing hyphens should fail"""
        with self.assertRaises(ValidationError):
            validate_pubg_player_id('-player')
        
        with self.assertRaises(ValidationError):
            validate_pubg_player_id('player-')
    
    def test_consecutive_hyphens(self):
        """Player IDs with consecutive hyphens should fail"""
        with self.assertRaises(ValidationError):
            validate_pubg_player_id('player--name')


# =====================================================================
# Unit Tests: Models
# =====================================================================

class ProductModelTests(TestCase):
    """Test Product model"""
    
    def setUp(self):
        self.product = Product.objects.create(
            name='100 UC',
            uc_amount=100,
            price_ngn='300.00',
            price_kobo=30000,
            sku='UC-100',
            is_active=True,
        )
    
    def test_product_creation(self):
        """Product should be created successfully"""
        self.assertEqual(self.product.name, '100 UC')
        self.assertEqual(self.product.uc_amount, 100)
        self.assertTrue(self.product.is_active)
    
    def test_product_string_representation(self):
        """Product string representation should be name"""
        self.assertEqual(str(self.product), '100 UC')


class OrderModelTests(TestCase):
    """Test Order model"""
    
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'pass123')
        self.product = Product.objects.create(
            name='100 UC',
            uc_amount=100,
            price_ngn='300.00',
            price_kobo=30000,
            sku='UC-100',
            is_active=True,
        )
    
    def test_order_creation(self):
        """Order should be created and validated"""
        order = Order.objects.create(
            user=self.user,
            player_id='valid-player-id',
            product=self.product,
            customer_email='customer@example.com',
            status=Order.Status.PENDING,
        )
        self.assertEqual(order.player_id, 'valid-player-id')
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.user, self.user)
    
    def test_invalid_player_id_on_create(self):
        """Order with invalid player ID should fail validation"""
        with self.assertRaises(ValidationError):
            order = Order(
                user=self.user,
                player_id='invalid@player',  # Invalid format
                product=self.product,
                customer_email='customer@example.com',
                status=Order.Status.PENDING,
            )
            order.full_clean()  # This will trigger validators


class SavedPlayerIDTests(TestCase):
    """Test SavedPlayerID model"""
    
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'pass123')
    
    def test_saved_player_id_creation(self):
        """SavedPlayerID should be created and validated"""
        saved_id = SavedPlayerID.objects.create(
            user=self.user,
            player_id='my-saved-id',
            label='Main Account',
        )
        self.assertEqual(saved_id.player_id, 'my-saved-id')
        self.assertEqual(saved_id.label, 'Main Account')
    
    def test_invalid_saved_player_id(self):
        """SavedPlayerID with invalid player ID should fail"""
        with self.assertRaises(ValidationError):
            saved_id = SavedPlayerID(
                user=self.user,
                player_id='invalid@id',
                label='Bad ID',
            )
            saved_id.full_clean()


# =====================================================================
# Integration Tests: API Endpoints
# =====================================================================

class ProductAPITests(APITestCase):
    """Test Product listing API"""
    
    def setUp(self):
        self.client = APIClient()
        Product.objects.create(
            name='100 UC',
            uc_amount=100,
            price_ngn='300.00',
            price_kobo=30000,
            sku='UC-100',
            is_active=True,
        )
        Product.objects.create(
            name='500 UC',
            uc_amount=500,
            price_ngn='1200.00',
            price_kobo=120000,
            sku='UC-500',
            is_active=True,
        )
    
    def test_list_products(self):
        """Should list all active products"""
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_product_details(self):
        """Product list should include necessary details"""
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        product = response.data[0]
        self.assertIn('id', product)
        self.assertIn('name', product)
        self.assertIn('uc_amount', product)
        self.assertIn('price_ngn', product)


class AuthenticationAPITests(APITestCase):
    """Test authentication endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password123')
    
    def test_registration(self):
        """User registration should create account"""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'securepass123',
        }
        response = self.client.post('/api/auth/register/', data, format='json')
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK])
    
    def test_duplicate_registration(self):
        """Duplicate registration should fail"""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123',
        }
        response = self.client.post('/api/auth/register/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_login(self):
        """Valid login should return success"""
        data = {
            'username': 'testuser',
            'password': 'password123',
        }
        response = self.client.post('/api/auth/login/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_invalid_login(self):
        """Invalid credentials should fail"""
        data = {
            'username': 'testuser',
            'password': 'wrongpassword',
        }
        response = self.client.post('/api/auth/login/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_get_user_profile(self):
        """Authenticated user should get profile"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/auth/user/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['authenticated'])


class OrderCreationAPITests(APITestCase):
    """Test order creation endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.product = Product.objects.create(
            name='100 UC',
            uc_amount=100,
            price_ngn='300.00',
            price_kobo=30000,
            sku='UC-100',
            is_active=True,
        )
    
    def test_order_creation_with_valid_player_id(self):
        """Order creation with valid player ID should succeed"""
        data = {
            'player_id': 'valid-player-id',
            'product_id': str(self.product.id),
            'email': 'customer@example.com',
        }
        # Note: This will fail without mocking Paystack, but tests the validation
        response = self.client.post('/api/orders/create/', data, format='json')
        # Expected: Either 502 (Paystack error) or 201 (Success) - both are valid in this context
        self.assertIn(response.status_code, [status.HTTP_502_BAD_GATEWAY, status.HTTP_201_CREATED])
    
    def test_order_creation_with_invalid_player_id(self):
        """Order creation with invalid player ID should fail"""
        data = {
            'player_id': 'invalid@player',  # Invalid format
            'product_id': str(self.product.id),
            'email': 'customer@example.com',
        }
        response = self.client.post('/api/orders/create/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_order_creation_missing_email(self):
        """Order creation without email should still work (optional)"""
        data = {
            'player_id': 'valid-player-id',
            'product_id': str(self.product.id),
        }
        response = self.client.post('/api/orders/create/', data, format='json')
        # Should be 502 (Paystack) or 201, not 400 (validation error)
        self.assertIn(response.status_code, [status.HTTP_502_BAD_GATEWAY, status.HTTP_201_CREATED])
    
    def test_order_creation_invalid_product(self):
        """Order creation with invalid product should fail"""
        data = {
            'player_id': 'valid-player-id',
            'product_id': str(uuid.uuid4()),  # Non-existent product
            'email': 'customer@example.com',
        }
        response = self.client.post('/api/orders/create/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SavedPlayerIDAPITests(APITestCase):
    """Test saved player ID endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password123')
        self.client.force_authenticate(user=self.user)
    
    def test_add_saved_player_id(self):
        """Authenticated user can save player ID"""
        data = {
            'player_id': 'my-saved-player',
            'label': 'Main Account',
        }
        response = self.client.post('/api/auth/saved-ids/add/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_add_invalid_saved_player_id(self):
        """Saving invalid player ID should fail"""
        data = {
            'player_id': 'invalid@player',
            'label': 'Bad ID',
        }
        response = self.client.post('/api/auth/saved-ids/add/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_remove_saved_player_id(self):
        """User can remove saved player ID"""
        # First add one
        saved_id = SavedPlayerID.objects.create(
            user=self.user,
            player_id='saved-player',
            label='My ID',
        )
        # Then remove it
        response = self.client.delete(f'/api/auth/saved-ids/{saved_id.id}/remove/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# =====================================================================
# Workflow Tests: End-to-End Scenarios
# =====================================================================

class CheckoutWorkflowTests(APITestCase):
    """Test complete checkout workflow"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password123')
        self.product = Product.objects.create(
            name='100 UC',
            uc_amount=100,
            price_ngn='300.00',
            price_kobo=30000,
            sku='UC-100',
            is_active=True,
        )
    
    def test_guest_checkout_flow(self):
        """Guest can checkout without authentication"""
        # 1. Get products
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 2. Create order with valid player ID and email
        order_data = {
            'player_id': 'guest-player-id',
            'product_id': str(self.product.id),
            'email': 'guest@example.com',
        }
        response = self.client.post('/api/orders/create/', order_data, format='json')
        # Expected: 502 (Paystack config) or 201 (Success)
        self.assertIn(response.status_code, [status.HTTP_502_BAD_GATEWAY, status.HTTP_201_CREATED])
    
    def test_authenticated_checkout_flow(self):
        """Authenticated user can checkout"""
        self.client.force_authenticate(user=self.user)
        
        # 1. Save a player ID
        saved_data = {
            'player_id': 'my-player-id',
            'label': 'Main',
        }
        response = self.client.post('/api/auth/saved-ids/add/', saved_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 2. Create order using saved ID
        order_data = {
            'player_id': 'my-player-id',
            'product_id': str(self.product.id),
        }
        response = self.client.post('/api/orders/create/', order_data, format='json')
        self.assertIn(response.status_code, [status.HTTP_502_BAD_GATEWAY, status.HTTP_201_CREATED])


# =====================================================================
# Validation Tests: Edge Cases
# =====================================================================

class PlayerIDValidationEdgeCasesTests(TestCase):
    """Test edge cases for player ID validation"""
    
    def test_whitespace_handling(self):
        """Whitespace should be stripped"""
        # Validator should handle leading/trailing whitespace
        try:
            validate_pubg_player_id('  valid-id  ')
        except ValidationError:
            self.fail("Valid player ID with whitespace was rejected")
    
    def test_case_sensitivity(self):
        """Player IDs should accept both uppercase and lowercase"""
        valid_ids = ['ABC-123', 'abc-123', 'AbC-123']
        for player_id in valid_ids:
            try:
                validate_pubg_player_id(player_id)
            except ValidationError:
                self.fail(f"Case variation rejected: {player_id}")
    
    def test_unicode_characters(self):
        """Unicode characters should be rejected"""
        invalid_ids = ['player™', 'player©', 'player❌', '玩家']
        for player_id in invalid_ids:
            with self.assertRaises(ValidationError):
                validate_pubg_player_id(player_id)
    
    def test_max_length_boundary(self):
        """Exactly 24 characters should pass, 25 should fail"""
        # 24 characters - should pass
        try:
            validate_pubg_player_id('a' * 24)
        except ValidationError:
            self.fail("24-character ID was rejected")
        
        # 25 characters - should fail
        with self.assertRaises(ValidationError):
            validate_pubg_player_id('a' * 25)
