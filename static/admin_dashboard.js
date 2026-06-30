/**
 * Mr Store Admin Dashboard
 * Real-time order management, refunds, analytics, and notifications
 */

'use strict';

// =====================================================================
// State Management
// =====================================================================
const adminState = {
  currentPage: 'stats',
  orders: [],
  refunds: [],
  notifications: [],
  stats: {},
  loading: false,
};

// =====================================================================
// DOM Helpers
// =====================================================================
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const adminDOM = {
  sidebar: () => $('.admin-sidebar'),
  navItems: () => $$('.sidebar-nav .nav-item'),
  pageTitle: () => $('#page-title'),
  pages: () => $$('.page'),
  ordersTBody: () => $('#orders-tbody'),
  refundsTBody: () => $('#refunds-tbody'),
  notificationsTBody: () => $('#notifications-tbody'),
  activityList: () => $('#activity-list'),
  modalOverlay: () => $('#modal-overlay'),
  orderDetailModal: () => $('#order-detail-modal'),
  modalBody: () => $('#modal-body'),
  logoutBtn: () => $('#logout-btn'),
};

// =====================================================================
// Utility Functions
// =====================================================================
async function apiCall(endpoint, options = {}) {
  const headers = { 'Content-Type': 'application/json' };
  const csrfToken = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='))?.split('=')[1];
  if (csrfToken) headers['X-CSRFToken'] = csrfToken;

  try {
    const response = await fetch(endpoint, { ...options, headers });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'API error');
    return data;
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

function formatCurrency(amount) {
  return `₦${parseFloat(amount).toLocaleString('en-NG', { minimumFractionDigits: 2 })}`;
}

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('en-NG', { dateStyle: 'short', timeStyle: 'short' });
}

function getStatusBadgeClass(status) {
  const map = {
    'PENDING': 'badge-warning',
    'PAID': 'badge-info',
    'FULFILLED': 'badge-success',
    'FAILED': 'badge-danger',
    'REFUNDED': 'badge-purple',
    'REQUESTED': 'badge-warning',
    'APPROVED': 'badge-info',
    'PROCESSING': 'badge-info',
    'COMPLETED': 'badge-success',
    'SENT': 'badge-success',
  };
  return map[status] || 'badge-secondary';
}

// =====================================================================
// Page Navigation
// =====================================================================
function switchPage(pageId) {
  adminState.currentPage = pageId;
  
  // Update nav
  adminDOM.navItems().forEach(item => {
    item.classList.toggle('active', item.dataset.page === pageId);
  });
  
  // Update pages
  adminDOM.pages().forEach(page => {
    page.classList.toggle('active', page.id === `page-${pageId}`);
  });
  
  // Update title
  const titles = {
    'stats': 'Dashboard',
    'orders': 'Orders Management',
    'refunds': 'Refund Requests',
    'analytics': 'Analytics & Reporting',
    'notifications': 'Notification Log',
  };
  adminDOM.pageTitle().textContent = titles[pageId] || 'Dashboard';
  
  // Load page data
  if (pageId === 'stats') loadDashboardStats();
  else if (pageId === 'orders') loadOrders();
  else if (pageId === 'refunds') loadRefunds();
  else if (pageId === 'notifications') loadNotifications();
}

// =====================================================================
// Dashboard Stats
// =====================================================================
async function loadDashboardStats() {
  try {
    const data = await apiCall('/api/admin/stats/');
    
    $('#stat-revenue').textContent = formatCurrency(data.total_revenue);
    $('#stat-orders').textContent = data.total_orders;
    $('#stat-fulfilled').textContent = data.fulfilled_orders;
    $('#stat-refunds').textContent = data.pending_refunds;
    
    // Load recent activity
    const orders = await apiCall('/api/admin/orders/?limit=5');
    renderActivity(orders.results || []);
  } catch (error) {
    console.error('Failed to load stats:', error);
    $('#stat-revenue').textContent = 'Error';
  }
}

function renderActivity(orders) {
  const list = adminDOM.activityList();
  if (!orders.length) {
    list.innerHTML = '<p class="empty-state">No recent activity</p>';
    return;
  }
  
  list.innerHTML = orders.map(order => `
    <div class="activity-item">
      <div class="activity-time">${formatDate(order.created_at)}</div>
      <div class="activity-content">
        <strong>${order.player_id}</strong> ordered ${order.product_details.name}
        <span class="badge ${getStatusBadgeClass(order.status)}">${order.status}</span>
      </div>
    </div>
  `).join('');
}

// =====================================================================
// Orders Management
// =====================================================================
async function loadOrders() {
  try {
    const query = $('#orders-search')?.value || '';
    const status = $('#orders-filter')?.value || '';
    const url = `/api/admin/orders/?${query ? 'search=' + query : ''}${status ? '&status=' + status : ''}`;
    
    const data = await apiCall(url);
    adminState.orders = data.results || data;
    renderOrdersTable();
  } catch (error) {
    console.error('Failed to load orders:', error);
    adminDOM.ordersTBody().innerHTML = '<tr><td colspan="7" class="error-state">Failed to load orders</td></tr>';
  }
}

function renderOrdersTable() {
  const tbody = adminDOM.ordersTBody();
  if (!adminState.orders.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No orders found</td></tr>';
    return;
  }
  
  tbody.innerHTML = adminState.orders.map(order => `
    <tr class="order-row" data-order-id="${order.id}">
      <td><code>${order.id.substring(0, 8)}</code></td>
      <td>${order.player_id}</td>
      <td>${order.product_details.name}</td>
      <td>${formatCurrency(order.product_details.original_amount)}</td>
      <td><span class="badge ${getStatusBadgeClass(order.status)}">${order.status}</span></td>
      <td>${formatDate(order.created_at)}</td>
      <td>
        <button class="btn-sm btn-primary" onclick="viewOrderDetails('${order.id}')">View</button>
        ${order.status === 'FULFILLED' ? '<button class="btn-sm btn-secondary">Refund</button>' : ''}
      </td>
    </tr>
  `).join('');
}

async function viewOrderDetails(orderId) {
  try {
    const data = await apiCall(`/api/admin/orders/${orderId}/`);
    
    const modalBody = adminDOM.modalBody();
    modalBody.innerHTML = `
      <div class="detail-section">
        <h4>Order Information</h4>
        <div class="detail-row"><span>Order ID:</span> <code>${data.id}</code></div>
        <div class="detail-row"><span>Player ID:</span> <strong>${data.player_id}</strong></div>
        <div class="detail-row"><span>Status:</span> <span class="badge ${getStatusBadgeClass(data.status)}">${data.status}</span></div>
        <div class="detail-row"><span>Created:</span> ${formatDate(data.created_at)}</div>
      </div>
      
      <div class="detail-section">
        <h4>Payment Information</h4>
        <div class="detail-row"><span>Amount:</span> ${formatCurrency(data.product_details.original_amount)}</div>
        <div class="detail-row"><span>Product:</span> ${data.product_details.name}</div>
        <div class="detail-row"><span>Payment Status:</span> <span class="badge badge-success">${data.payment_details.status}</span></div>
      </div>
      
      ${data.refund_details ? `
        <div class="detail-section">
          <h4>Refund</h4>
          <div class="detail-row"><span>Amount:</span> ${formatCurrency(data.refund_details.amount)}</div>
          <div class="detail-row"><span>Status:</span> <span class="badge ${getStatusBadgeClass(data.refund_details.status)}">${data.refund_details.status}</span></div>
        </div>
      ` : ''}
    `;
    
    openModal();
  } catch (error) {
    console.error('Failed to load order details:', error);
  }
}

// =====================================================================
// Refunds Management
// =====================================================================
async function loadRefunds() {
  try {
    const status = $('#refunds-filter')?.value || '';
    const url = `/api/admin/refunds/?${status ? 'status=' + status : ''}`;
    
    const data = await apiCall(url);
    adminState.refunds = data.results || data;
    renderRefundsTable();
  } catch (error) {
    console.error('Failed to load refunds:', error);
    adminDOM.refundsTBody().innerHTML = '<tr><td colspan="7" class="error-state">Failed to load refunds</td></tr>';
  }
}

function renderRefundsTable() {
  const tbody = adminDOM.refundsTBody();
  if (!adminState.refunds.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No refunds found</td></tr>';
    return;
  }
  
  tbody.innerHTML = adminState.refunds.map(refund => `
    <tr class="refund-row" data-refund-id="${refund.id}">
      <td><code>${refund.id.substring(0, 8)}</code></td>
      <td><code>${refund.order.substring(0, 8)}</code></td>
      <td>${formatCurrency(refund.amount)}</td>
      <td>${refund.reason.substring(0, 40)}...</td>
      <td><span class="badge ${getStatusBadgeClass(refund.status)}">${refund.status}</span></td>
      <td>${formatDate(refund.requested_at)}</td>
      <td>
        ${refund.status === 'REQUESTED' ? `<button class="btn-sm btn-success" onclick="approveRefund('${refund.id}')">Approve</button>` : ''}
        ${refund.status === 'APPROVED' ? `<button class="btn-sm btn-info" onclick="processRefund('${refund.id}')">Process</button>` : ''}
      </td>
    </tr>
  `).join('');
}

async function approveRefund(refundId) {
  if (!confirm('Approve this refund?')) return;
  
  try {
    await apiCall(`/api/admin/refunds/${refundId}/action/`, {
      method: 'POST',
      body: JSON.stringify({ action: 'approve' })
    });
    alert('Refund approved');
    loadRefunds();
  } catch (error) {
    alert('Failed to approve refund: ' + error.message);
  }
}

async function processRefund(refundId) {
  if (!confirm('Mark refund as processing?')) return;
  
  try {
    await apiCall(`/api/admin/refunds/${refundId}/action/`, {
      method: 'POST',
      body: JSON.stringify({ action: 'process' })
    });
    alert('Refund marked as processing');
    loadRefunds();
  } catch (error) {
    alert('Failed to process refund: ' + error.message);
  }
}

// =====================================================================
// Notifications Log
// =====================================================================
async function loadNotifications() {
  try {
    const type = $('#notifications-filter')?.value || '';
    const url = `/api/admin/notifications/?${type ? 'type=' + type : ''}`;
    
    const data = await apiCall(url);
    adminState.notifications = data.results || data;
    renderNotificationsTable();
  } catch (error) {
    console.error('Failed to load notifications:', error);
    adminDOM.notificationsTBody().innerHTML = '<tr><td colspan="6" class="error-state">Failed to load notifications</td></tr>';
  }
}

function renderNotificationsTable() {
  const tbody = adminDOM.notificationsTBody();
  if (!adminState.notifications.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No notifications found</td></tr>';
    return;
  }
  
  tbody.innerHTML = adminState.notifications.map(notif => `
    <tr class="notification-row">
      <td><strong>${notif.notification_type}</strong></td>
      <td>${notif.recipient}</td>
      <td><span class="badge">${notif.channel}</span></td>
      <td><span class="badge ${getStatusBadgeClass(notif.status)}">${notif.status}</span></td>
      <td>${notif.sent_at ? formatDate(notif.sent_at) : 'Pending'}</td>
      <td>
        ${notif.status === 'FAILED' ? `<button class="btn-sm btn-primary" onclick="resendNotification('${notif.id}')">Retry</button>` : ''}
      </td>
    </tr>
  `).join('');
}

async function resendNotification(notificationId) {
  if (!confirm('Resend this notification?')) return;
  
  try {
    await apiCall(`/api/admin/notifications/${notificationId}/action/`, {
      method: 'POST',
      body: JSON.stringify({ action: 'retry' })
    });
    alert('Notification queued for resend');
    loadNotifications();
  } catch (error) {
    alert('Failed to resend notification: ' + error.message);
  }
}

// =====================================================================
// Modal Management
// =====================================================================
function openModal() {
  adminDOM.modalOverlay().classList.remove('hidden');
  adminDOM.orderDetailModal().classList.remove('hidden');
}

function closeModal() {
  adminDOM.modalOverlay().classList.add('hidden');
  adminDOM.orderDetailModal().classList.add('hidden');
}

// =====================================================================
// Event Listeners
// =====================================================================
function initializeEventListeners() {
  // Page navigation
  adminDOM.navItems().forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      switchPage(item.dataset.page);
    });
  });
  
  // Filters and search
  $('#orders-search')?.addEventListener('input', loadOrders);
  $('#orders-filter')?.addEventListener('change', loadOrders);
  $('#refunds-filter')?.addEventListener('change', loadRefunds);
  $('#notifications-filter')?.addEventListener('change', loadNotifications);
  
  // Modal
  adminDOM.modalOverlay()?.addEventListener('click', closeModal);
  $('.modal-close')?.addEventListener('click', closeModal);
  
  // Logout
  adminDOM.logoutBtn()?.addEventListener('click', async () => {
    if (confirm('Logout?')) {
      try {
        await apiCall('/api/auth/logout/', { method: 'POST' });
        window.location.href = '/';
      } catch (error) {
        alert('Logout failed');
      }
    }
  });
}

// =====================================================================
// Initialization
// =====================================================================
document.addEventListener('DOMContentLoaded', () => {
  initializeEventListeners();
  switchPage('stats');
  
  // Auto-refresh stats every 30 seconds
  setInterval(() => {
    if (adminState.currentPage === 'stats') loadDashboardStats();
  }, 30000);
});
