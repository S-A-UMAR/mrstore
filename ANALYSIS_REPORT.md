# MR STORE — Project Audit & Improvement Report

**Project:** PUBG Mobile UC Store (Nigeria)  
**Tech Stack:** Django + DRF (Backend), Vanilla JS (Frontend)  
**Date:** June 2026

---

## 1. CURRENT STATE OVERVIEW

### What's Working
✅ **Core e-commerce flow** — Product listing → Player ID entry → Paystack checkout → Order fulfillment  
✅ **User authentication** — Registration, login/logout, session management  
✅ **Payment integration** — Paystack webhook processing, order status tracking  
✅ **Saved Player IDs** — Quick checkout shortcut for authenticated users  
✅ **Security basics** — CSRF protection, SSL enforced, rate limiting, secure headers  
✅ **PWA support** — Installable app, service worker skeleton  
✅ **Responsive design** — Mobile-first CSS, touch-friendly UI  

---

## 2. CRITICAL ISSUES & GAPS

### 🔴 HIGH PRIORITY

#### 2.1 **Database Schema Limitations**
- **Missing Fields:**
  - No `customer_email` in Order model (relies on user.email or fallback) → can't contact guest customers
  - No `refund_status` field → refunds not tracked
  - No `failure_reason` field → can't communicate why orders failed
  - No `metadata_json` for tracking custom fields beyond basics
  - SavedPlayerID lacks `is_default` flag → no quick-select priority

- **Soft Deletes Missing:** Deleted orders/payments are permanently removed instead of archived

**Impact:** Can't properly refund, track failures, or contact guest customers  
**Fix:** Add migration adding these fields

---

#### 2.2 **No Refund/Reversal System**
- No refund initiation API
- No refund status tracking
- No Paystack refund endpoint integration
- No rollback of UC if fulfillment fails
- No compensation handling for failed orders

**Impact:** Customers can't get refunds; customer support overhead  
**Fix:** Build complete refund pipeline with webhook handling

---

#### 2.3 **Incomplete Error Handling**
- No retry logic for failed wholesaler orders
- Webhook processing doesn't retry on transient failures
- No dead-letter queue for failed payments
- Silent failures in fulfillment don't notify customer

**Impact:** Orders stuck in FULFILLED state when UC delivery actually failed  
**Fix:** Add async task queue (Celery) for order fulfillment with retry logic

---

#### 2.4 **No Admin Dashboard**
- No way to view/manage orders, payments, or products
- Can't refund customers or manually fulfill orders
- No business metrics (revenue, top products, conversion rate)
- Django admin exists but untouched in views

**Impact:** No operational visibility; can't troubleshoot customer issues  
**Fix:** Build admin panel with orders, payments, refunds, analytics views

---

#### 2.5 **Guest Checkout Contact Issues**
- Guest orders (no login) can't receive email confirmation
- No email notifications at all
- Player ID validation only checks format (not against PUBG API)
- No duplicate order detection

**Impact:** Customers don't know if order succeeded; wrong Player IDs get processed  
**Fix:** Add email notifications + PUBG API player validation

---

### 🟠 MEDIUM PRIORITY

#### 2.6 **Frontend Security Gaps**
- No input sanitization (XSS risk if templates rendered unsafely)
- Player ID input accepts any numeric string (should validate against PUBG API)
- No CSRF token visible in forms (Django middleware present but check API calls)
- Paystack public key exposed (acceptable but could be enum)
- No rate limiting UI feedback (user can spam order creation)

**Fix:** Validate player ID via PUBG API, sanitize all inputs, add request debouncing

---

#### 2.7 **Missing Authentication Features**
- No password reset/recovery
- No email verification on signup
- No 2FA or security options
- Sessions not scoped (browser-wide logout required)
- No account deletion option

**Fix:** Add password reset flow, email verification, account management

---

#### 2.8 **Incomplete Order Tracking**
- Tracking only works for authenticated users in profile
- Guest users can't track orders after leaving site
- No email/SMS status updates
- No retry option if UC delivery failed
- Timeline UI exists but all steps show immediately (not state-driven)

**Fix:** Email-based order tracking link, SMS notifications, retry UI

---

#### 2.9 **No Analytics/Logging**
- Basic logging configured but not instrumented
- No event tracking (conversions, drop-off points)
- No performance monitoring
- No fraud detection signals

**Fix:** Add analytics SDK, structured logging, monitoring

---

#### 2.10 **Product Management Gaps**
- Products hardcoded via migrations (no CRUD endpoints)
- Can't add/update products without Django admin
- No inventory/stock tracking
- No A/B testing or price variation
- No promo codes or discounts

**Fix:** Add product admin CRUD, inventory tracking, discount system

---

### 🟡 LOW PRIORITY / POLISH

#### 2.11 **UI/UX Polish**
- Loading states inconsistent across forms
- No skeleton loaders on async operations
- Form validation errors delayed (should be real-time)
- No undo/confirmation dialogs for destructive actions
- Saved Player IDs card has no empty state
- No success animations (purchase confirmation)

**Fix:** Add loading states, real-time validation, animations

---

#### 2.12 **Performance Issues**
- No API response caching (ProductSerializer called every request)
- All orders loaded on profile (no pagination)
- Order history table can have 100+ rows (no virtualization)
- Static files not versioned (cache busting)
- No database query optimization (N+1 queries possible)

**Fix:** Add caching, pagination, database indexing, query optimization

---

#### 2.13 **Mobile Experience**
- No mobile-specific optimizations (still works but clunky)
- No mobile payment confirmation (Paystack modal sometimes hidden)
- No app shortcuts or widgets
- PWA manifest incomplete (no screenshots, app icons)

**Fix:** Add mobile payment UX tweaks, complete PWA setup

---

#### 2.14 **Testing Coverage**
- No automated tests for API endpoints
- No payment webhook tests
- No UI interaction tests
- No load testing

**Fix:** Add pytest for backend, manual E2E tests for Paystack flow

---

#### 2.15 **Documentation & Code Quality**
- No API documentation (Swagger/OpenAPI)
- No deployment guide
- No environment setup docs
- Code has some type hints but incomplete
- Serializer validation could be stricter

**Fix:** Add API docs, deployment guide, type annotations

---

## 3. DATABASE SCHEMA RECOMMENDATIONS

### Missing Models/Fields

```python
# Add these fields to Order:
customer_email = models.EmailField(blank=True)  # For guest checkouts
failure_reason = models.TextField(blank=True)   # Why order failed
fulfillment_retry_count = models.PositiveIntegerField(default=0)
fulfillment_last_error = models.TextField(blank=True)

# Add these fields to Payment:
refund_id = models.CharField(max_length=120, blank=True)  # Paystack refund reference
refund_status = models.CharField(max_length=12, choices=REFUND_STATUS, default='NONE')
refunded_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
refund_reason = models.CharField(max_length=200, blank=True)

# Add fields to SavedPlayerID:
is_default = models.BooleanField(default=False)  # Quick select priority

# New model: OrderAuditLog
class OrderAuditLog(models.Model):
    order = ForeignKey(Order)
    event = CharField(choices=[CREATED, PAID, FULFILLED, FAILED, REFUNDED])
    timestamp = DateTimeField(auto_now_add=True)
    actor = CharField(choices=[SYSTEM, ADMIN, WEBHOOK])
    details = JSONField()  # Custom fields for event details

# New model: Refund
class Refund(models.Model):
    order = OneToOneField(Order)
    payment = ForeignKey(Payment)
    amount = DecimalField()
    reason = CharField(max_length=200)
    paystack_refund_id = CharField(max_length=120, unique=True)
    status = CharField(max_length=12, choices=REFUND_STATUS)
    initiated_at = DateTimeField(auto_now_add=True)
    completed_at = DateTimeField(null=True)
```

---

## 4. API ENDPOINTS MISSING

```
# Refund Management
POST   /api/orders/{order_id}/refund/        # Initiate refund
GET    /api/orders/{order_id}/refund/status/ # Check refund status
GET    /api/refunds/                         # List refunds (admin)

# Product Management (CRUD)
GET    /api/admin/products/                  # List (with filters)
POST   /api/admin/products/                  # Create
PATCH  /api/admin/products/{id}/             # Update
DELETE /api/admin/products/{id}/             # Delete

# Player Validation
POST   /api/validate-player-id/              # Validate against PUBG API

# Admin Orders
GET    /api/admin/orders/                    # List orders (filters, pagination)
GET    /api/admin/orders/{id}/               # Order details
PATCH  /api/admin/orders/{id}/               # Manual fulfillment/refund
POST   /api/admin/orders/{id}/retry-fulfill/ # Retry fulfillment

# Analytics (Admin)
GET    /api/analytics/summary/               # Revenue, order count, etc.
GET    /api/analytics/top-products/
GET    /api/analytics/conversion-funnel/

# Notifications
GET    /api/notifications/                   # User notifications
PATCH  /api/notifications/{id}/mark-read/

# Account Management
POST   /api/auth/password-reset/
POST   /api/auth/password-reset-confirm/
POST   /api/auth/verify-email/
DELETE /api/auth/delete-account/
```

---

## 5. SECURITY HARDENING CHECKLIST

- [ ] SQL Injection: Using ORM but verify all queries are parameterized ✅ (mostly done)
- [ ] XSS: Input sanitization on frontend (add DOMPurify)
- [ ] CSRF: Tokens in POST/PUT/DELETE (check API views)
- [ ] Player ID Validation: Call PUBG API to verify Player ID exists
- [ ] Webhook Signature Verification: Already implemented ✅
- [ ] Rate Limiting: Per-IP order creation throttled (10/min) ✅
- [ ] PII Protection: No logging of sensitive data
- [ ] API Authentication: No public order access (check order_status view) 🔴 **ALLOW GUEST ACCESS** — add read-only token validation
- [ ] Environment Variables: Check `.env` not committed ✅ (using .gitignore)
- [ ] HTTPS Enforcement: SSL redirect in production ✅
- [ ] Secret Key Rotation: Ensure `SECRET_KEY` is strong and rotated

**Action Items:**
1. Add PUBG API player validation
2. Add DOMPurify to frontend for output encoding
3. Verify CSRF tokens in all POST API calls
4. Add PII audit logging (what data logged?)

---

## 6. FEATURE ROADMAP (By Priority)

### Phase 1: Critical (Weeks 1-2)
1. Add refund system (Paystack API, Order model fields)
2. Build admin dashboard (orders, payments, products CRUD)
3. Add email notifications (order confirmation, status updates)
4. Player ID validation against PUBG API
5. Fix guest order contact (store customer_email)

### Phase 2: Important (Weeks 3-4)
1. Add Celery task queue for reliable fulfillment retry
2. Build analytics dashboard (revenue, conversion, top products)
3. Add password reset + email verification
4. Pagination for order history
5. Order failure notifications + manual retry

### Phase 3: Polish (Weeks 5-6)
1. SMS notifications for order status
2. Discount/promo code system
3. Admin bulk operations (refund multiple, export CSV)
4. Mobile app optimization
5. Performance optimization (caching, query optimization)

---

## 7. DEPLOYMENT & DEVOPS

### Current Setup Issues
- No Docker (manual setup required)
- No CI/CD pipeline
- No staging environment
- No backup strategy for database
- No monitoring/alerting

### Recommendations
```yaml
# Add:
- Docker + Docker Compose for local dev
- GitHub Actions CI/CD (test, lint, deploy)
- Vercel or Railway for hosting (with auto-deploys)
- PostgreSQL (from SQLite) for production
- Sentry for error monitoring
- New Relic or DataDog for performance
- Uptime Robot for health checks
```

---

## 8. TECH DEBT & CLEANUP

| Issue | Severity | Fix |
|-------|----------|-----|
| Vanilla JS → React/Vue for state mgmt | Medium | Refactor to Next.js or Svelte |
| Django + vanilla JS separation | Low | Consider API-only backend |
| CSS not minified/optimized | Low | Add Tailwind or PostCSS |
| No type hints in Python | Medium | Add Pydantic models for validation |
| Serializer validation weak | Medium | Use Pydantic or stricter validators |
| No async tasks | High | Add Celery + Redis |
| No multi-region support | Low | Add CDN, consider Cloudflare |

---

## 9. QUICK WINS (Easy High-Impact Fixes)

1. **Add customer_email to Order model** (1 hour) — enables guest notifications
2. **Email on order completion** (2 hours) — massive UX improvement
3. **Order retry button in admin** (2 hours) — handles fulfillment failures
4. **Pagination on order history** (1.5 hours) — improves performance
5. **Success animation on checkout** (1 hour) — better UX feedback
6. **Form validation errors real-time** (1 hour) — better UX
7. **Add favicon/PWA icons** (0.5 hours) — polish
8. **API docs with Swagger** (2 hours) — developer experience

---

## 10. SUMMARY TABLE

| Category | Status | Impact | Effort |
|----------|--------|--------|--------|
| **Features** | ⚠️ Core only | 40% of MVP | Medium |
| **Security** | ✅ Good | Low-risk | Low |
| **Performance** | ⚠️ Okay | 70% / needs optimize | Medium |
| **UI/UX** | ✅ Solid | 85% complete | Low |
| **Testing** | 🔴 None | High-risk | High |
| **Ops/DevOps** | 🔴 Manual | High-friction | High |
| **Documentation** | 🔴 Minimal | Onboarding hard | Low |

---

## CONCLUSION

**MR STORE is a solid MVP** with working checkout, auth, and payment integration. However, it's missing **critical operational features** (refunds, admin tools, notifications) and **reliability patterns** (retry logic, error handling, monitoring).

**To take it to production, prioritize:**
1. ✅ Refund system (compliance + customer trust)
2. ✅ Admin dashboard (operational control)
3. ✅ Email notifications (customer confidence)
4. ✅ Task queue + monitoring (reliability)
5. ✅ Testing + CI/CD (quality gates)

**Estimated effort to production-ready: 6-8 weeks**

