/**
 * Mr Store — Fintech App JS
 * Features: Auth Management, Profile Details, Saved Player IDs list & checkout,
 * Transaction History table, SPA Router, Paystack setup, and order polling.
 */

'use strict';

// =============================================================
// Module: App State
// =============================================================
const state = {
  products: [],
  selectedProduct: null,
  config: null,
  user: null, // Holds profile info if logged in: { authenticated, user, saved_ids, orders }
  selectedSavedId: null,
  currentOrderId: null,
  pollTimer: null,
};

// =============================================================
// Module: DOM Helper & Refs
// =============================================================
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const dom = {
  loader:          () => $('#app-loader'),
  productsGrid:    () => $('#products-grid'),
  playerInput:     () => $('#player-id-input'),
  playerError:     () => $('#player-id-error'),
  checkoutEmail:   () => $('#checkout-email-input'),
  buyBtn:          () => $('#buy-btn'),
  buyBtnText:      () => $('#buy-btn-text'),
  buyBtnLoader:    () => $('#buy-btn-loader'),
  
  // Auth Nav Links
  navLinkLogin:    () => $('#nav-link-login'),
  navLinkProfile:  () => $('#nav-link-profile'),
  tabLinkLogin:    () => $('#tab-link-login'),
  tabLinkProfile:  () => $('#tab-link-profile'),

  // Checkout saved IDs shortcut
  checkoutSavedIdsWrap: () => $('#checkout-saved-ids-wrap'),
  checkoutSavedIdsList: () => $('#checkout-saved-ids-list'),

  // Forms
  formLogin:       () => $('#form-login'),
  formRegister:    () => $('#form-register'),
  formAddSavedId:  () => $('#form-add-saved-id'),

  // Profile fields
  profileUserName: () => $('#profile-user-name'),
  profileUserEmail:() => $('#profile-user-email'),
  profileJoinDate: () => $('#profile-join-date'),
  profileLogoutBtn:() => $('#profile-logout-btn'),
  savedIdsList:    () => $('#saved-ids-list'),
  historyRows:     () => $('#profile-order-history-rows'),

  // Tracking page details
  trackForm:       () => $('#track-form'),
  searchOrderId:   () => $('#search-order-id'),
  trackingResult:  () => $('#tracking-result'),
  resOrderId:      () => $('#res-order-id'),
  resStatusBadge:  () => $('#res-status-badge'),
  resPlayerId:     () => $('#res-player-id'),
  resProductName:  () => $('#res-product-name'),
  resPrice:        () => $('#res-price'),
  resTime:         () => $('#res-time'),
  stepPending:     () => $('#step-pending'),
  stepPaid:        () => $('#step-paid'),
  stepFulfilled:   () => $('#step-fulfilled'),

  // Overlays & Notifications
  payOverlay:      () => $('#payment-overlay'),
  overlayTitle:    () => $('#overlay-title'),
  overlaySub:      () => $('#overlay-sub'),
  overlayProgress: () => $('#overlay-progress'),
  overlayState:    () => $('#overlay-state'),
  toastContainer:  () => $('#toast-container'),
  waFab:           () => $('#wa-fab'),
};

// =============================================================
// Module: Toast Notifications
// =============================================================
function showToast(message, type = 'info', durationMs = 4000) {
  const container = dom.toastContainer();
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'opacity 0.2s, transform 0.2s';
    setTimeout(() => toast.remove(), 200);
  }, durationMs);
}

// =============================================================
// Module: CSRF Cookie Helper
// =============================================================
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// =============================================================
// Module: API Requests Wrapper
// =============================================================
async function apiFetch(url, options = {}) {
  const headers = { 'Content-Type': 'application/json' };
  const csrfToken = getCookie('csrftoken');
  if (csrfToken) {
    headers['X-CSRFToken'] = csrfToken;
  }
  const defaults = { headers };
  const response = await fetch(url, { ...defaults, ...options });
  const data = await response.json();
  if (!response.ok) {
    const msg = data?.error
      ? typeof data.error === 'string' ? data.error : JSON.stringify(data.error)
      : `Error: Request failed (${response.status})`;
    throw new Error(msg);
  }
  return data;
}

// =============================================================
// Module: Player ID Validation
// =============================================================
function validatePubgPlayerId(playerId) {
  /**
   * Validate PUBG Mobile Player ID format
   * Rules: 1-24 chars, alphanumeric + hyphens only,
   * no leading/trailing hyphens, no consecutive hyphens
   */
  if (!playerId || playerId.trim().length === 0) {
    return { valid: false, error: 'Player ID is required' };
  }
  
  playerId = playerId.trim();
  
  // Check length
  if (playerId.length < 1 || playerId.length > 24) {
    return { 
      valid: false, 
      error: `Player ID must be 1-24 characters (currently ${playerId.length})` 
    };
  }
  
  // Check allowed characters (alphanumeric + hyphens only)
  if (!/^[a-zA-Z0-9\-]+$/.test(playerId)) {
    return { 
      valid: false, 
      error: 'Player ID can only contain letters, numbers, and hyphens' 
    };
  }
  
  // Cannot start or end with hyphen
  if (playerId.startsWith('-') || playerId.endsWith('-')) {
    return { 
      valid: false, 
      error: 'Player ID cannot start or end with a hyphen' 
    };
  }
  
  // No consecutive hyphens
  if (playerId.includes('--')) {
    return { 
      valid: false, 
      error: 'Player ID cannot contain consecutive hyphens' 
    };
  }
  
  return { valid: true, error: null };
}

function displayPlayerIdError(errorMsg) {
  const errorEl = dom.playerError();
  if (!errorEl) return;
  
  if (errorMsg) {
    errorEl.textContent = errorMsg;
    errorEl.classList.add('visible');
  } else {
    errorEl.classList.remove('visible');
    errorEl.textContent = '';
  }
}

function updatePlayerIdValidationUI() {
  const input = dom.playerInput();
  if (!input) return;
  
  const playerId = input.value.trim();
  const validation = validatePubgPlayerId(playerId);
  
  if (playerId.length === 0) {
    input.classList.remove('valid', 'invalid');
    displayPlayerIdError(null);
  } else if (validation.valid) {
    input.classList.add('valid');
    input.classList.remove('invalid');
    displayPlayerIdError(null);
  } else {
    input.classList.add('invalid');
    input.classList.remove('valid');
    displayPlayerIdError(validation.error);
  }
  
  updateBuyButton();
}

// =============================================================
// Module: Authentication Status Checker
// =============================================================
async function checkAuthStatus() {
  try {
    const profile = await apiFetch('/api/auth/user/');
    if (profile.authenticated) {
      state.user = profile;
      
      // Update Navbar layout
      dom.navLinkLogin().classList.add('hidden');
      dom.navLinkProfile().classList.remove('hidden');
      dom.tabLinkLogin().classList.add('hidden');
      dom.tabLinkProfile().classList.remove('hidden');

      renderProfile();
      renderCheckoutSavedIds();
    } else {
      state.user = null;
      dom.navLinkLogin().classList.remove('hidden');
      dom.navLinkProfile().classList.add('hidden');
      dom.tabLinkLogin().classList.remove('hidden');
      dom.tabLinkProfile().classList.add('hidden');
      dom.checkoutSavedIdsWrap().classList.add('hidden');
    }
  } catch (err) {
    console.error('Auth state check error:', err);
  }
}

// =============================================================
// Module: Profile Detail Renderers
// =============================================================
function renderProfile() {
  if (!state.user) return;
  const { user, saved_ids, orders } = state.user;

  // Render info
  dom.profileUserName().textContent = user.username;
  dom.profileUserEmail().textContent = user.email;
  const joinDate = new Date(user.date_joined);
  dom.profileJoinDate().textContent = joinDate.toLocaleDateString('en-NG', { dateStyle: 'medium' });

  // Render Saved IDs list
  const listEl = dom.savedIdsList();
  listEl.innerHTML = '';
  if (!saved_ids.length) {
    listEl.innerHTML = '<p class="text-muted" style="font-size:0.8rem;text-align:center;padding:12px;">No saved account profiles yet.</p>';
  } else {
    saved_ids.forEach((idRecord) => {
      const row = document.createElement('div');
      row.className = 'saved-id-row';
      row.innerHTML = `
        <div class="saved-id-info">
          <span class="saved-id-label">${idRecord.label}</span>
          <span class="saved-id-number">${idRecord.player_id}</span>
        </div>
        <button class="saved-id-delete-btn" aria-label="Delete saved ID" data-id="${idRecord.id}">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
        </button>
      `;
      row.querySelector('.saved-id-delete-btn').addEventListener('click', (e) => {
        e.stopPropagation();
        removeSavedPlayerId(idRecord.id);
      });
      listEl.appendChild(row);
    });
  }

  // Render History Table
  const tableBody = dom.historyRows();
  tableBody.innerHTML = '';
  if (!orders.length) {
    tableBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No orders found. Pack your first UC package!</td></tr>';
  } else {
    orders.forEach((order) => {
      const tr = document.createElement('tr');
      const orderDate = new Date(order.created_at);
      const formattedDate = orderDate.toLocaleDateString('en-NG', { dateStyle: 'short' });
      
      tr.innerHTML = `
        <td><strong>${order.product_name}</strong></td>
        <td><code>${order.player_id}</code></td>
        <td>₦${Number(order.price_ngn).toLocaleString('en-NG')}</td>
        <td><span class="badge ${order.status.toLowerCase()}">${order.status}</span></td>
        <td>${formattedDate}</td>
        <td><a href="#track?id=${order.id}" class="history-track-btn">Track</a></td>
      `;
      tableBody.appendChild(tr);
    });
  }
}

function renderCheckoutSavedIds() {
  const wrap = dom.checkoutSavedIdsWrap();
  const list = dom.checkoutSavedIdsList();
  
  if (!state.user || !state.user.saved_ids.length) {
    wrap.classList.add('hidden');
    return;
  }

  list.innerHTML = '';
  state.user.saved_ids.forEach((idRecord) => {
    const card = document.createElement('div');
    card.className = 'checkout-saved-id-card';
    card.dataset.id = idRecord.id;
    card.innerHTML = `
      <span class="saved-id-label" style="font-size: 0.72rem; font-weight:600; color:var(--clr-text-muted);">${idRecord.label}</span>
      <span class="saved-id-number" style="font-weight:700;">${idRecord.player_id}</span>
    `;
    card.addEventListener('click', () => {
      selectCheckoutSavedId(idRecord, card);
    });
    list.appendChild(card);
  });
  wrap.classList.remove('hidden');
}

function selectCheckoutSavedId(idRecord, cardEl) {
  $$('.checkout-saved-id-card').forEach((c) => c.classList.remove('selected'));
  
  // If clicked again, deselect
  if (state.selectedSavedId === idRecord.id) {
    state.selectedSavedId = null;
    dom.playerInput().value = '';
  } else {
    state.selectedSavedId = idRecord.id;
    cardEl.classList.add('selected');
    dom.playerInput().value = idRecord.player_id;
  }
  
  dom.playerError().classList.remove('visible');
  updateBuyButton();
}

// =============================================================
// Module: SPA Client Router
// =============================================================
function switchAuthPanel(panel) {
  if (panel === 'login') {
    $('#auth-panel-login').classList.remove('hidden');
    $('#auth-panel-register').classList.add('hidden');
  } else {
    $('#auth-panel-login').classList.add('hidden');
    $('#auth-panel-register').classList.remove('hidden');
  }
}
window.switchAuthPanel = switchAuthPanel; // expose globally for inline switcher click

function navigateToView(viewName, queryParams = {}) {
  // Guard Profile page access
  if (viewName === 'profile' && !state.user) {
    window.location.hash = '#login';
    return;
  }
  if (viewName === 'login' && state.user) {
    window.location.hash = '#profile';
    return;
  }

  // Swap active classes
  $$('.spa-view').forEach((v) => v.classList.remove('active'));
  const activeView = $(`#view-${viewName}`);
  if (activeView) activeView.classList.add('active');

  // Update tabs active highlights
  $$('.nav-link, .tab-link').forEach((link) => {
    if (link.dataset.target === viewName) {
      link.classList.add('active');
    } else {
      link.classList.remove('active');
    }
  });

  // Action hook on entry
  if (viewName === 'track') {
    const id = queryParams.id;
    if (id) {
      dom.searchOrderId().value = id;
      fetchAndRenderOrderDetails(id);
    }
  }

  window.scrollTo({ top: 0, behavior: 'instant' });
}

function handleHashChange() {
  const hash = window.location.hash || '#home';
  const cleanHash = hash.split('?')[0];
  const viewName = cleanHash.replace('#', '');

  // Parse queries
  const queryParams = {};
  const queryString = hash.split('?')[1];
  if (queryString) {
    queryString.split('&').forEach((pair) => {
      const [key, val] = pair.split('=');
      if (key && val) {
        queryParams[decodeURIComponent(key)] = decodeURIComponent(val);
      }
    });
  }

  const views = ['home', 'login', 'profile', 'track', 'faq', 'security'];
  if (views.includes(viewName)) {
    navigateToView(viewName, queryParams);
  } else {
    navigateToView('home');
  }
}

// =============================================================
// Module: Saved Player ID Actions
// =============================================================
async function addSavedPlayerId() {
  const pVal = $('#add-id-value').value.trim();
  const pLabel = $('#add-id-label').value.trim();

  try {
    await apiFetch('/api/auth/saved-ids/add/', {
      method: 'POST',
      body: JSON.stringify({ player_id: pVal, label: pLabel })
    });
    $('#add-id-value').value = '';
    $('#add-id-label').value = '';
    showToast('Player ID profile saved successfully.', 'success');
    
    // Refresh auth data
    await checkAuthStatus();
  } catch (err) {
    showToast(err.message || 'Could not save ID.', 'error');
  }
}

async function removeSavedPlayerId(recordId) {
  try {
    await apiFetch(`/api/auth/saved-ids/${recordId}/remove/`, {
      method: 'DELETE'
    });
    showToast('Saved Player ID record deleted.', 'info');
    await checkAuthStatus();
  } catch (err) {
    showToast(err.message || 'Could not remove ID.', 'error');
  }
}

// =============================================================
// Module: Catalog Renderers
// =============================================================
function renderSkeletons() {
  const grid = dom.productsGrid();
  if (!grid) return;
  grid.innerHTML = '';
  for (let i = 0; i < 6; i++) {
    const card = document.createElement('div');
    card.className = 'product-card skeleton';
    card.style.height = '130px';
    grid.appendChild(card);
  }
}

function renderProducts(products) {
  const grid = dom.productsGrid();
  if (!grid) return;
  grid.innerHTML = '';

  if (!products.length) {
    grid.innerHTML = '<p class="text-muted text-center" style="grid-column:1/-1;padding:2rem;">No products catalog available.</p>';
    return;
  }

  products.forEach((product) => {
    const card = document.createElement('div');
    card.className = 'product-card';
    card.dataset.productId = product.id;
    card.setAttribute('role', 'radio');
    card.setAttribute('aria-checked', 'false');
    card.setAttribute('tabindex', '0');

    const hasBadge = product.badge && product.badge.trim();
    card.innerHTML = `
      <div class="product-badge ${hasBadge ? '' : 'hidden'}">${product.badge || ''}</div>
      <img src="/static/icons/UC.png" alt="UC" class="product-icon">
      <div class="product-uc">${product.uc_amount}</div>
      <div class="product-label">UC</div>
      <div class="product-price">₦${Number(product.price_ngn).toLocaleString('en-NG')}</div>
      <div class="product-name">${product.name}</div>
    `;

    card.addEventListener('click', () => selectProduct(product, card));
    card.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        selectProduct(product, card);
      }
    });

    grid.appendChild(card);
  });
}

function selectProduct(product, cardEl) {
  $$('.product-card').forEach((c) => {
    c.classList.remove('selected');
    c.setAttribute('aria-checked', 'false');
  });
  cardEl.classList.add('selected');
  cardEl.setAttribute('aria-checked', 'true');
  state.selectedProduct = product;
  updateBuyButton();
}

async function loadProducts() {
  renderSkeletons();
  try {
    const products = await apiFetch('/api/products/');
    state.products = products;
    renderProducts(products);
  } catch (err) {
    console.error('Products catalog failed to load:', err);
    dom.productsGrid().innerHTML = '<p class="text-muted text-center" style="grid-column:1/-1;padding:2rem;">⚠️ Failed to load catalog.</p>';
  }
}

// =============================================================
// Module: Order Tracker Console
// =============================================================
async function fetchAndRenderOrderDetails(orderId) {
  const resultCard = dom.trackingResult();
  const submitBtn = $('#search-submit-btn');

  submitBtn.disabled = true;
  submitBtn.textContent = 'Searching...';
  resultCard.classList.add('hidden');

  try {
    const order = await apiFetch(`/api/orders/${orderId}/status/`);
    
    dom.resOrderId().textContent = order.id.substring(0, 18) + '...';
    dom.resPlayerId().textContent = order.player_id;
    dom.resProductName().textContent = order.product_name || 'PUBG Mobile UC';
    dom.resPrice().textContent = order.price_ngn ? `₦${Number(order.price_ngn).toLocaleString('en-NG')}` : '₦...';
    
    const date = new Date(order.created_at);
    dom.resTime().textContent = date.toLocaleString('en-NG');

    const badge = dom.resStatusBadge();
    badge.className = `badge ${order.status.toLowerCase()}`;
    badge.textContent = order.status;

    // Reset timelines
    const steps = [dom.stepPending(), dom.stepPaid(), dom.stepFulfilled()];
    steps.forEach((s) => s.className = 'timeline-step');

    const status = order.status;
    if (status === 'PENDING') {
      dom.stepPending().classList.add('active');
    } else if (status === 'PAID') {
      dom.stepPending().classList.add('completed');
      dom.stepPaid().classList.add('active');
    } else if (status === 'FULFILLED') {
      dom.stepPending().classList.add('completed');
      dom.stepPaid().classList.add('completed');
      dom.stepFulfilled().classList.add('completed');
    } else if (status === 'FAILED') {
      dom.stepPending().classList.add('completed');
      dom.stepPaid().classList.add('active');
      dom.stepFulfilled().className = 'timeline-step';
    }

    resultCard.classList.remove('hidden');
  } catch (err) {
    showToast(err.message || 'Reference not found.', 'error');
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Track';
  }
}

// =============================================================
// Module: Checkout Order Creation
// =============================================================
function startOrderPolling(orderId) {
  state.currentOrderId = orderId;
  let attempts = 0;
  const MAX_ATTEMPTS = 30; // 2 minutes

  state.pollTimer = setInterval(async () => {
    attempts++;
    try {
      const order = await apiFetch(`/api/orders/${orderId}/status/`);
      const status = order.status;

      if (status === 'FULFILLED') {
        clearInterval(state.pollTimer);
        setOverlayState(
          'success',
          'UC Credited!',
          `Direct top-up succeeded for Player ID ${getPlayerId()}. Check your PUBG client now.`
        );
        // Refresh orders list
        await checkAuthStatus();
      } else if (status === 'FAILED') {
        clearInterval(state.pollTimer);
        setOverlayState(
          'fail',
          'Fulfillment Error',
          `Payment cleared but automated direct UC delivery timed out. Support has been notified. Reference: ${orderId}`
        );
        await checkAuthStatus();
      }
    } catch (err) {
      console.warn('Poll exception:', err);
    }

    if (attempts >= MAX_ATTEMPTS) {
      clearInterval(state.pollTimer);
      setOverlayState(
        'fail',
        'Fulfillment Delayed',
        `Payment was cleared. Direct credit is taking longer than expected. Contact support with Order ID: ${orderId}`
      );
    }
  }, 4000);
}

async function handleBuyClick() {
  if (!validateForm()) return;
  
  // Validate email if provided
  const email = getCheckoutEmail();
  if (email && !validateEmail(email)) {
    showToast('Please enter a valid email address.', 'error');
    dom.checkoutEmail()?.focus();
    return;
  }
  
  if (!state.selectedProduct) {
    showToast('Select a UC package first.', 'error');
    return;
  }
  if (!state.config?.paystack_public_key) {
    showToast('Fulfillment systems config missing.', 'error');
    return;
  }

  setBuyButtonLoading(true);
  
  showPaymentOverlay(
    'Connecting Paystack Gate...',
    'Redirecting to secure gateway.',
    true
  );

  let orderData;
  try {
    orderData = await apiFetch('/api/orders/create/', {
      method: 'POST',
      body: JSON.stringify({
        player_id: getPlayerId(),
        product_id: state.selectedProduct.id,
        email: email,
      }),
    });
  } catch (err) {
    closeOverlay();
    setBuyButtonLoading(false);
    showToast(err.message || 'Check out failed.', 'error');
    return;
  }

  const { order_id, access_code, amount } = orderData;

  /* global PaystackPop */
  const handler = PaystackPop.setup({
    key:         state.config.paystack_public_key,
    access_code: access_code,
    amount:      amount,
    currency:    state.config.currency || 'NGN',
    ref:         orderData.reference,

    onSuccess(tx) {
      showPaymentOverlay(
        'Verifying Payment & Automated Top-Up...',
        'Confirming receipt values. Do not close this window.',
        true
      );
      startOrderPolling(order_id);
    },
    onCancel() {
      closeOverlay();
      setBuyButtonLoading(false);
      showToast('Payment window dismissed.', 'info');
    },
  });

  handler.openIframe();
}

// =============================================================
// Module: Auth Submit Actions
// =============================================================
async function handleLoginSubmit() {
  const u = $('#login-username').value.trim();
  const p = $('#login-password').value;

  try {
    await apiFetch('/api/auth/login/', {
      method: 'POST',
      body: JSON.stringify({ username: u, password: p })
    });
    
    $('#login-username').value = '';
    $('#login-password').value = '';
    showToast('Logged in successfully.', 'success');
    
    await checkAuthStatus();
    window.location.hash = '#profile';
  } catch (err) {
    showToast(err.message || 'Login credentials incorrect.', 'error');
  }
}

async function handleRegisterSubmit() {
  const u = $('#register-username').value.trim();
  const e = $('#register-email').value.trim();
  const p = $('#register-password').value;

  try {
    await apiFetch('/api/auth/register/', {
      method: 'POST',
      body: JSON.stringify({ username: u, email: e, password: p })
    });
    
    $('#register-username').value = '';
    $('#register-email').value = '';
    $('#register-password').value = '';
    showToast('Registration successful! Account logged in.', 'success');
    
    await checkAuthStatus();
    window.location.hash = '#profile';
  } catch (err) {
    showToast(err.message || 'Registration details invalid.', 'error');
  }
}

async function handleLogoutClick() {
  try {
    await apiFetch('/api/auth/logout/', { method: 'POST' });
    showToast('Logged out successfully.', 'info');
    
    // Clear user state
    state.user = null;
    state.selectedSavedId = null;
    await checkAuthStatus();
    window.location.hash = '#home';
  } catch (err) {
    showToast('Could not sign out properly.', 'error');
  }
}

// =============================================================
// Module: Core Form Event Wireups
// =============================================================
function initFormListeners() {
  // Buy / Checkout Button
  dom.buyBtn()?.addEventListener('click', handleBuyClick);

  // Login Form
  dom.formLogin()?.addEventListener('submit', (e) => { e.preventDefault(); handleLoginSubmit(); });

  // Register Form
  dom.formRegister()?.addEventListener('submit', (e) => { e.preventDefault(); handleRegisterSubmit(); });

  // Profile Saved ID Form
  dom.formAddSavedId()?.addEventListener('submit', (e) => {
    e.preventDefault();
    addSavedPlayerId();
  });

  // Track Form
  dom.trackForm()?.addEventListener('submit', (e) => {
    e.preventDefault();
    const orderId = dom.searchOrderId().value.trim();
    if (orderId) fetchAndRenderOrderDetails(orderId);
  });

  // Log Out button
  dom.profileLogoutBtn()?.addEventListener('click', handleLogoutClick);

  // Overlay close (clicking backdrop)
  dom.payOverlay()?.addEventListener('click', (e) => {
    if (e.target === dom.payOverlay()) closeOverlay();
  });
}

// =============================================================
// Module: FAQ triggers
// =============================================================
function initFaqAccordion() {
  $$('.faq-trigger').forEach((trigger) => {
    trigger.addEventListener('click', () => {
      const isExpanded = trigger.getAttribute('aria-expanded') === 'true';
      const content = trigger.nextElementSibling;

      $$('.faq-trigger').forEach((t) => {
        t.setAttribute('aria-expanded', 'false');
        t.nextElementSibling.style.maxHeight = null;
      });

      if (!isExpanded) {
        trigger.setAttribute('aria-expanded', 'true');
        content.style.maxHeight = content.scrollHeight + 'px';
      }
    });
  });
}

// =============================================================
// Module: WhatsApp FAB trigger
// =============================================================
function initSupportFAB() {
  const fab = dom.waFab();
  if (!fab) return;
  fab.addEventListener('click', () => {
    if (!state.config?.support_whatsapp) {
      showToast('Support number details loading.', 'error');
      return;
    }
    const cleanNum = state.config.support_whatsapp.replace(/\D/g, '');
    const defaultText = encodeURIComponent('Hi Mr Store support, I need help with my PUBG Mobile UC top-up order.');
    window.open(`https://wa.me/${cleanNum}?text=${defaultText}`, '_blank', 'noopener');
  });
}

// =============================================================
// Module: Checkout Input Live check
// =============================================================
function initInputListeners() {
  const input = dom.playerInput();
  if (!input) return;
  
  input.addEventListener('input', () => {
    // Deselect any highlighted quick select card
    if (state.selectedSavedId) {
      state.selectedSavedId = null;
      $$('.checkout-saved-id-card').forEach((c) => c.classList.remove('selected'));
    }

    // Real-time validation with visual feedback
    updatePlayerIdValidationUI();
  });

  input.addEventListener('blur', () => {
    // Final validation on blur
    updatePlayerIdValidationUI();
  });
}

// =============================================================
// Module: Checkout Loading & UX States
// =============================================================
function setBuyButtonLoading(isLoading) {
  const btn = dom.buyBtn();
  const text = dom.buyBtnText();
  const loader = dom.buyBtnLoader();
  
  if (!btn || !text || !loader) return;
  
  if (isLoading) {
    btn.disabled = true;
    text.classList.add('hidden');
    loader.classList.remove('hidden');
  } else {
    btn.disabled = false;
    text.classList.remove('hidden');
    loader.classList.add('hidden');
  }
}

function getCheckoutEmail() {
  return (dom.checkoutEmail()?.value.trim() || '').toLowerCase();
}

function validateEmail(email) {
  if (!email) return true; // Email is optional
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

// =============================================================
// Module: Config Loader
// =============================================================
async function loadConfig() {
  try {
    state.config = await apiFetch('/api/config/');
  } catch (err) {
    console.error('Config load failed:', err);
    state.config = {};
  }
}

// =============================================================
// Module: Checkout Form Utilities
// =============================================================
function getPlayerId() {
  return dom.playerInput()?.value.trim() || '';
}

function validateForm() {
  const id = getPlayerId();
  const validation = validatePubgPlayerId(id);
  
  if (!validation.valid) {
    displayPlayerIdError(validation.error);
    dom.playerInput()?.focus();
    return false;
  }
  if (!state.selectedProduct) {
    showToast('Please select a UC package first.', 'error');
    return false;
  }
  return true;
}

function updateBuyButton() {
  const btn = dom.buyBtn();
  if (!btn) return;
  const id = getPlayerId();
  const validation = validatePubgPlayerId(id);
  const hasProduct = !!state.selectedProduct;
  const hasValidId = validation.valid;
  btn.disabled = !(hasProduct && hasValidId);
}

// =============================================================
// Module: Payment Overlay
// =============================================================
function showPaymentOverlay(title, sub, showProgress = false) {
  const overlay = dom.payOverlay();
  if (!overlay) return;
  dom.overlayTitle().textContent = title;
  dom.overlaySub().textContent = sub;
  if (dom.overlayProgress()) {
    dom.overlayProgress().style.display = showProgress ? 'block' : 'none';
  }
  if (dom.overlayState()) dom.overlayState().className = 'overlay-state';
  overlay.classList.remove('hidden');
  overlay.setAttribute('aria-hidden', 'false');
}

function setOverlayState(type, title, message) {
  dom.overlayTitle().textContent = title;
  dom.overlaySub().textContent = message;
  if (dom.overlayProgress()) dom.overlayProgress().style.display = 'none';
  if (dom.overlayState()) {
    dom.overlayState().className = `overlay-state ${type}`;
    dom.overlayState().innerHTML = type === 'success'
      ? `<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="9 12 11 14 15 10"/></svg>`
      : `<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;
  }
  // Auto-close after 6s on success
  if (type === 'success') {
    setTimeout(closeOverlay, 6000);
  }
}

function closeOverlay() {
  const overlay = dom.payOverlay();
  if (!overlay) return;
  overlay.classList.add('hidden');
  overlay.setAttribute('aria-hidden', 'true');
  if (state.pollTimer) {
    clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
  const btn = dom.buyBtn();
  if (btn) btn.disabled = false;
}

// =============================================================
// Module: App Bootstrap
// =============================================================
function registerSW() {
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/static/sw.js')
        .then((reg) => console.log('[SW] Scope:', reg.scope))
        .catch((err) => console.warn('[SW] Registration failed:', err));
    });
  }
}

async function bootstrap() {
  registerSW();

  try {
    // Load config & catalog in parallel
    await Promise.all([loadConfig(), loadProducts()]);

    // Check auth session
    await checkAuthStatus();

    // Wire up all events
    initFormListeners();
    initInputListeners();
    initFaqAccordion();
    initSupportFAB();

    // Initialize hash router
    window.addEventListener('hashchange', handleHashChange);
    handleHashChange();
  } catch (err) {
    console.error('[Mr Store] Bootstrap error:', err);
  } finally {
    // Always dismiss the splash screen
    const loader = dom.loader();
    if (loader) {
      loader.classList.add('hidden');
    }
  }
}

document.addEventListener('DOMContentLoaded', bootstrap);

