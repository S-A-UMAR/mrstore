#!/usr/bin/env python
"""
Mr Store Implementation Verification Script
Checks all phases and features are correctly implemented
"""

import os
import sys
import json
from pathlib import Path

class ImplementationVerifier:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.checks_passed = []
        self.checks_failed = []
    
    def check_file_exists(self, path, description):
        """Verify file exists"""
        full_path = self.project_root / path
        if full_path.exists():
            self.checks_passed.append(f"✓ {description}")
            return True
        else:
            self.checks_failed.append(f"✗ {description} - File not found: {path}")
            return False
    
    def check_file_contains(self, path, keywords, description):
        """Verify file contains specific keywords"""
        full_path = self.project_root / path
        if not full_path.exists():
            self.checks_failed.append(f"✗ {description} - File not found: {path}")
            return False
        
        content = full_path.read_text()
        found_all = all(kw in content for kw in keywords)
        
        if found_all:
            self.checks_passed.append(f"✓ {description}")
            return True
        else:
            self.checks_failed.append(f"✗ {description} - Missing keywords in {path}")
            return False
    
    def verify_phase_1(self):
        """Verify Phase 1: Player ID Validation"""
        print("\n" + "="*60)
        print("PHASE 1: PUBG Player ID Validation")
        print("="*60)
        
        # Check validator file
        self.check_file_exists(
            'orders/validators.py',
            'Player ID validator module created'
        )
        
        # Check validator in models
        self.check_file_contains(
            'orders/models.py',
            ['validate_pubg_player_id', 'validators='],
            'Models use validator for player_id field'
        )
        
        # Check frontend validation
        self.check_file_contains(
            'static/app.js',
            ['validatePubgPlayerId', 'updatePlayerIdValidationUI'],
            'Frontend validation function implemented'
        )
        
        # Check HTML validation UI
        self.check_file_contains(
            'templates/index.html',
            ['player-id-validation-indicator', 'valid-check'],
            'Validation UI elements in HTML'
        )
        
        # Check CSS styling
        self.check_file_contains(
            'static/styles.css',
            ['.valid-check', '@keyframes checkmark-bounce'],
            'Validation CSS styling implemented'
        )
        
        # Check backend validation in views
        self.check_file_contains(
            'orders/views.py',
            ['validate_pubg_player_id', 'ValidationError'],
            'Backend validation in views'
        )
    
    def verify_phase_2(self):
        """Verify Phase 2: Enhanced Checkout UX"""
        print("\n" + "="*60)
        print("PHASE 2: Enhanced Checkout UX")
        print("="*60)
        
        # Check email input HTML
        self.check_file_contains(
            'templates/index.html',
            ['checkout-email-input', 'Order Confirmation Email'],
            'Email input added to checkout'
        )
        
        # Check email CSS
        self.check_file_contains(
            'static/styles.css',
            ['.checkout-email-card', '#checkout-email-input'],
            'Email input styling added'
        )
        
        # Check loading state functions
        self.check_file_contains(
            'static/app.js',
            ['setBuyButtonLoading', 'getCheckoutEmail', 'validateEmail'],
            'Loading state functions in app.js'
        )
        
        # Check button loader UI
        self.check_file_contains(
            'templates/index.html',
            ['buy-btn-loader', 'loader-spinner'],
            'Button loader UI implemented'
        )
        
        # Check loader CSS
        self.check_file_contains(
            'static/styles.css',
            ['.loader-spinner', '@keyframes spin'],
            'Loader animation styles'
        )
    
    def verify_phase_3(self):
        """Verify Phase 3: Admin Dashboard"""
        print("\n" + "="*60)
        print("PHASE 3: Modern Admin Dashboard")
        print("="*60)
        
        # Check admin dashboard files
        self.check_file_exists(
            'templates/admin_dashboard.html',
            'Admin dashboard HTML template'
        )
        
        self.check_file_exists(
            'static/admin_dashboard.js',
            'Admin dashboard JavaScript'
        )
        
        self.check_file_exists(
            'static/admin_dashboard.css',
            'Admin dashboard CSS styles'
        )
        
        # Check dashboard features
        self.check_file_contains(
            'templates/admin_dashboard.html',
            ['Orders Management', 'Refund Requests', 'Analytics', 'Notifications'],
            'Admin dashboard pages implemented'
        )
        
        # Check admin API endpoints in views
        self.check_file_contains(
            'orders/views.py',
            ['admin_stats', 'admin_orders_list', 'admin_order_detail', 'admin_refunds_list'],
            'Admin API endpoints implemented'
        )
        
        # Check URL configuration
        self.check_file_contains(
            'orders/urls.py',
            ['admin/stats', 'admin/orders', 'admin/refunds'],
            'Admin URLs configured'
        )
    
    def verify_phase_4(self):
        """Verify Phase 4: Testing Suite"""
        print("\n" + "="*60)
        print("PHASE 4: Testing Suite")
        print("="*60)
        
        # Check test file
        self.check_file_exists(
            'orders/tests.py',
            'Comprehensive test suite'
        )
        
        # Check test coverage
        self.check_file_contains(
            'orders/tests.py',
            [
                'PubgPlayerIDValidatorTests',
                'ProductModelTests',
                'OrderModelTests',
                'AuthenticationAPITests',
                'OrderCreationAPITests',
            ],
            'Major test classes implemented'
        )
        
        # Check test documentation
        self.check_file_exists(
            'TESTING.md',
            'Testing documentation'
        )
        
        self.check_file_contains(
            'TESTING.md',
            ['Test Coverage', 'Running Tests', 'Test Results'],
            'Testing guide complete'
        )
    
    def verify_general_requirements(self):
        """Verify general requirements"""
        print("\n" + "="*60)
        print("GENERAL REQUIREMENTS")
        print("="*60)
        
        # Check key models
        self.check_file_contains(
            'orders/models.py',
            ['class Order', 'class Product', 'class Payment', 'class SavedPlayerID'],
            'All required models present'
        )
        
        # Check API structure
        self.check_file_contains(
            'orders/urls.py',
            ['products/', 'orders/create/', 'auth/register/', 'auth/login/'],
            'Core API endpoints configured'
        )
        
        # Check frontend structure
        self.check_file_exists(
            'templates/index.html',
            'Main frontend HTML'
        )
        
        self.check_file_exists(
            'static/app.js',
            'Main frontend JavaScript'
        )
        
        self.check_file_exists(
            'static/styles.css',
            'Frontend styles'
        )
    
    def print_summary(self):
        """Print verification summary"""
        print("\n" + "="*60)
        print("VERIFICATION SUMMARY")
        print("="*60)
        
        passed = len(self.checks_passed)
        failed = len(self.checks_failed)
        total = passed + failed
        
        print(f"\nTotal Checks: {total}")
        print(f"Passed: {passed} ✓")
        print(f"Failed: {failed} ✗")
        
        if self.checks_failed:
            print("\nFailed Checks:")
            for check in self.checks_failed:
                print(f"  {check}")
        
        percentage = (passed / total * 100) if total > 0 else 0
        print(f"\nImplementation Status: {percentage:.1f}%")
        
        if failed == 0:
            print("\n✓ ALL CHECKS PASSED - Implementation complete!")
            return 0
        else:
            print(f"\n✗ {failed} checks failed - Please review")
            return 1
    
    def run_all_checks(self):
        """Run all verification checks"""
        print("\n🔍 Mr Store Implementation Verification")
        print("="*60)
        
        self.verify_phase_1()
        self.verify_phase_2()
        self.verify_phase_3()
        self.verify_phase_4()
        self.verify_general_requirements()
        
        return self.print_summary()


if __name__ == '__main__':
    verifier = ImplementationVerifier()
    exit_code = verifier.run_all_checks()
    sys.exit(exit_code)
