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
    document.getElementById('refreshDashboard')?.addEventListener('click', refreshDashboard);
    document.getElementById('closeRequestModal')?.addEventListener('click', closeRequestModal);
    document.getElementById('closeAssignModal')?.addEventListener('click', closeAssignModal);
    document.getElementById('cancelAssign')?.addEventListener('click', closeAssignModal);
    document.getElementById('assignRequestForm')?.addEventListener('submit', confirmAssignment);
    document.getElementById('requestModal')?.addEventListener('click', (event) => {
        if (event.target.id === 'requestModal') closeRequestModal();
    });
    document.getElementById('assignModal')?.addEventListener('click', (event) => {
        if (event.target.id === 'assignModal') closeAssignModal();
    });
    
    // Set up filter event listeners
    document.getElementById('filterStatus').addEventListener('change', loadRequests);
    document.getElementById('filterSort').addEventListener('change', loadRequests);
    document.getElementById('filterLocation').addEventListener('input', debounce(loadRequests, 300));
    
    // Set up register center form
    document.getElementById('registerCenterForm').addEventListener('submit', handleRegisterCenter);
})();

async function refreshDashboard() {
    const button = document.getElementById('refreshDashboard');
    if (button) { button.disabled = true; button.textContent = 'Refreshing...'; }
    await Promise.all([loadStats(), loadRequests(), loadLowStock(), loadCenters()]);
    const lastUpdated = document.getElementById('lastUpdated');
    if (lastUpdated) lastUpdated.textContent = `Updated ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    if (button) { button.disabled = false; button.textContent = 'Refresh data'; }
}

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
        tbody.innerHTML = '<tr><td colspan="7" class="loading-state">Loading requests...</td></tr>';
        const data = await listRequests(status || null, sort);
        let requests = data.requests || [];
        
        // Apply client-side location filter
        if (locationFilter) {
            requests = requests.filter(r => 
                r.location.toLowerCase().includes(locationFilter)
            );
        }
        
        if (requests.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="empty-state"><strong>No requests found</strong>New requests will appear here.</td></tr>';
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
                        `<div class="request-actions"><button class="btn btn-sm btn-outline" onclick="showRequestDetails(${JSON.stringify(req).replace(/"/g, '&quot;')})">View</button> <button class="btn btn-sm btn-success" onclick="assignRequest(${JSON.stringify(req).replace(/"/g, '&quot;')})">Assign</button></div>` :
                        req.status === 'assigned' ?
                        `<div class="request-actions"><button class="btn btn-sm btn-outline" onclick="showRequestDetails(${JSON.stringify(req).replace(/"/g, '&quot;')})">View</button> <button class="btn btn-sm btn-primary" onclick="resolveRequest('${req.requestId}')">Resolve</button></div>` :
                        `<button class="btn btn-sm btn-outline" onclick="showRequestDetails(${JSON.stringify(req).replace(/"/g, '&quot;')})">View</button>`
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

let requestBeingAssigned = null;

/**
 * Opens the assignment dialog and lets the admin choose an active center.
 */
async function assignRequest(request) {
    try {
        const data = await listCenters('active');
        const activeCenters = data.centers || [];

        if (!activeCenters.length) {
            alert('No active relief centers are available to assign this request.');
            return;
        }

        requestBeingAssigned = request;
        const select = document.getElementById('assignCenterSelect');
        const summary = document.getElementById('assignSummary');
        if (!select || !summary) return;
        select.innerHTML = '<option value="">Select an active relief center</option>' +
            activeCenters.map(center =>
                `<option value="${escapeHtml(center.centerId)}">${escapeHtml(center.name)} — ${escapeHtml(center.location)}</option>`
            ).join('');
        summary.textContent = `${request.name} · ${request.needType} · ${request.location}`;
        document.getElementById('assignAlert').innerHTML = '';
        document.getElementById('assignModal').hidden = false;
    } catch (error) {
        alert('Failed to assign request: ' + error.message);
    }
}

async function confirmAssignment(event) {
    event.preventDefault();
    if (!requestBeingAssigned) return;
    const centerId = document.getElementById('assignCenterSelect').value;
    const alertDiv = document.getElementById('assignAlert');
    const button = document.getElementById('confirmAssign');
    if (!centerId) {
        alertDiv.innerHTML = '<div class="alert alert-warning">Select a relief center first.</div>';
        return;
    }
    button.disabled = true;
    button.textContent = 'Assigning...';
    try {
        await updateRequestStatus(requestBeingAssigned.requestId, {
            status: 'assigned',
            assignedCenterId: centerId
        });
        closeAssignModal();
        await Promise.all([loadRequests(), loadStats()]);
    } catch (error) {
        alertDiv.innerHTML = `<div class="alert alert-error">Failed to assign request: ${escapeHtml(error.message)}</div>`;
    } finally {
        button.disabled = false;
        button.textContent = 'Assign request';
    }
}

/**
 * Marks an assigned request as "resolved".
 */
async function resolveRequest(requestId) {
    try {
        if (!window.confirm('Mark this request as resolved?')) return;
        await updateRequestStatus(requestId, { status: 'resolved' });
        loadRequests();
        loadStats();
    } catch (error) {
        alert('Failed to resolve request: ' + error.message);
    }
}

function showRequestDetails(request) {
        const modal = document.getElementById('requestModal');
        const body = document.getElementById('requestModalBody');
        if (!modal || !body) return;
        body.innerHTML = `
            <div class="detail-grid">
                <div class="detail-item"><small>Requester</small><p>${escapeHtml(request.name)}</p></div>
                <div class="detail-item"><small>Location</small><p>${escapeHtml(request.location)}</p></div>
                <div class="detail-item"><small>Need</small><p>${escapeHtml(request.needType)}</p></div>
                <div class="detail-item"><small>Urgency</small><p><span class="badge badge-${escapeHtml(request.urgencyLabel)}">${escapeHtml(request.urgencyLabel)}</span></p></div>
                <div class="detail-item"><small>Status</small><p><span class="badge badge-${escapeHtml(request.status)}">${escapeHtml(request.status)}</span></p></div>
                <div class="detail-item"><small>Contact</small><p>${escapeHtml(request.contactPhone || 'Not provided')}</p></div>
            </div>
            <div class="detail-item" style="margin-top: .9rem"><small>Description</small><p>${escapeHtml(request.description)}</p></div>
            <p class="muted-text" style="margin-top: .8rem">Received ${formatDate(request.createdAt)}</p>
        `;
        modal.hidden = false;
    }

function closeRequestModal() {
        const modal = document.getElementById('requestModal');
        if (modal) modal.hidden = true;
}

function closeAssignModal() {
    const modal = document.getElementById('assignModal');
    if (modal) modal.hidden = true;
    requestBeingAssigned = null;
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
