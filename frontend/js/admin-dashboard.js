/**
 * admin-dashboard.js — Admin dashboard controller
 * 
 * Loads and displays all system data: stats, help requests,
 * low stock alerts, and relief centers. Admin only.
 */

(function() {
    // Require admin role
    const user = requireAuth('admin');
    if (!user) return;
    
    displayUserInfo();
    
    // Load all data on page load
    loadStats();
    loadRequests();
    loadLowStock();
    loadCenters();
    
    // Set up filter event listeners
    document.getElementById('filterStatus').addEventListener('change', loadRequests);
    document.getElementById('filterSort').addEventListener('change', loadRequests);
    document.getElementById('filterLocation').addEventListener('input', debounce(loadRequests, 300));
    
    // Set up register center form
    document.getElementById('registerCenterForm').addEventListener('submit', handleRegisterCenter);
})();

/**
 * Loads and displays dashboard statistics.
 */
async function loadStats() {
    try {
        const stats = await getStats();
        
        document.getElementById('statCenters').textContent = stats.totalCenters || 0;
        document.getElementById('statPending').textContent = stats.totalPendingRequests || 0;
        document.getElementById('statUrgent').textContent = stats.urgentPendingRequests || 0;
        document.getElementById('statLowStock').textContent = stats.criticalLowStock || 0;
        
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

/**
 * Loads help requests based on current filter selections.
 */
async function loadRequests() {
    const tbody = document.getElementById('requestsTableBody');
    const status = document.getElementById('filterStatus').value;
    const sort = document.getElementById('filterSort').value;
    const locationFilter = document.getElementById('filterLocation').value.trim().toLowerCase();
    
    try {
        const data = await listRequests(status || null, sort);
        let requests = data.requests || [];
        
        // Apply client-side location filter
        if (locationFilter) {
            requests = requests.filter(r => 
                r.location.toLowerCase().includes(locationFilter)
            );
        }
        
        if (requests.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No requests found.</td></tr>';
            return;
        }
        
        tbody.innerHTML = requests.map(req => `
            <tr>
                <td>${escapeHtml(req.name)}</td>
                <td>${escapeHtml(req.location)}</td>
                <td>${escapeHtml(req.needType)}</td>
                <td><span class="badge badge-${req.urgencyLabel}">${escapeHtml(req.urgencyLabel)}</span></td>
                <td><span class="badge badge-${req.status}">${escapeHtml(req.status)}</span></td>
                <td>${formatDate(req.createdAt)}</td>
                <td>
                    ${req.status === 'pending' ? 
                        `<button class="btn btn-sm btn-success" onclick="assignRequest('${req.requestId}')">Assign</button>` :
                        req.status === 'assigned' ?
                        `<button class="btn btn-sm btn-primary" onclick="resolveRequest('${req.requestId}')">Resolve</button>` :
                        '<span class="done-text">Done</span>'
                    }
                </td>
            </tr>
        `).join('');
        
    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="7" class="alert alert-error">Failed to load requests: ${error.message}</td></tr>`;
    }
}

/**
 * Loads low stock alerts for all centers.
 */
async function loadLowStock() {
    const tbody = document.getElementById('lowStockTableBody');
    
    try {
        const data = await getLowStock();
        const items = data.lowStockItems || [];
        
        if (items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-state">All resources are adequately stocked.</td></tr>';
            return;
        }
        
        tbody.innerHTML = items.map(item => `
            <tr>
                <td>${escapeHtml(item.centerName)}</td>
                <td>${escapeHtml(item.centerLocation)}</td>
                <td><span class="badge badge-lowstock">${escapeHtml(item.resourceType)}</span></td>
                <td class="low-stock-value">${item.quantity} ${escapeHtml(item.unit)}</td>
                <td>${item.threshold} ${escapeHtml(item.unit)}</td>
            </tr>
        `).join('');
        
    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="5" class="alert alert-error">Failed to load low stock data: ${error.message}</td></tr>`;
    }
}

/**
 * Loads all relief centers.
 */
async function loadCenters() {
    const tbody = document.getElementById('centersTableBody');
    
    try {
        const data = await listCenters();
        const centers = data.centers || [];
        
        if (centers.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No relief centers registered.</td></tr>';
            return;
        }
        
        tbody.innerHTML = centers.map(c => `
            <tr>
                <td>${escapeHtml(c.name)}</td>
                <td>${escapeHtml(c.location)}</td>
                <td>${escapeHtml(c.contactPhone || 'N/A')}</td>
                <td>${escapeHtml(c.staffEmail)}</td>
                <td><span class="badge badge-${c.status === 'active' ? 'resolved' : 'pending'}">${escapeHtml(c.status)}</span></td>
            </tr>
        `).join('');
        
    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="5" class="alert alert-error">Failed to load centers: ${error.message}</td></tr>`;
    }
}

/**
 * Marks a pending request as "assigned".
 * In a real app, you'd select which center to assign.
 */
async function assignRequest(requestId) {
    try {
        const data = await listCenters('active');
        const activeCenters = data.centers || [];

        if (!activeCenters.length) {
            alert('No active relief centers are available to assign this request.');
            return;
        }

        const assignedCenterId = activeCenters[0].centerId;
        await updateRequestStatus(requestId, {
            status: 'assigned',
            assignedCenterId
        });

        loadRequests();
        loadStats();
    } catch (error) {
        alert('Failed to assign request: ' + error.message);
    }
}

/**
 * Marks an assigned request as "resolved".
 */
async function resolveRequest(requestId) {
    try {
        await updateRequestStatus(requestId, { status: 'resolved' });
        loadRequests();
        loadStats();
    } catch (error) {
        alert('Failed to resolve request: ' + error.message);
    }
}

/**
 * Handles registration of a new relief center.
 */
async function handleRegisterCenter(e) {
    e.preventDefault();
    const alertDiv = document.getElementById('registerAlert');
    
    const data = {
        name: document.getElementById('centerName').value.trim(),
        location: document.getElementById('centerLocation').value.trim(),
        contactPhone: document.getElementById('contactPhone').value.trim(),
        contactEmail: document.getElementById('contactEmail').value.trim(),
        staffEmail: document.getElementById('staffEmail').value.trim(),
        staffPassword: document.getElementById('staffPassword').value
    };
    
    try {
        await createCenter(data);
        alertDiv.innerHTML = '<div class="alert alert-success">Center registered successfully!</div>';
        document.getElementById('registerCenterForm').reset();
        
        // Refresh the centers table
        loadCenters();
        loadStats();
        
        setTimeout(() => { alertDiv.innerHTML = ''; }, 4000);
    } catch (error) {
        alertDiv.innerHTML = `<div class="alert alert-error">Registration failed: ${error.message}</div>`;
    }
}

/* =====================================================
   Utility functions
   ===================================================== */

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function formatDate(isoString) {
    if (!isoString) return 'N/A';
    const d = new Date(isoString);
    return d.toLocaleDateString('en-IN', { 
        day: 'numeric', month: 'short', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
    });
}

function debounce(fn, delay) {
    let timer;
    return function(...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}
