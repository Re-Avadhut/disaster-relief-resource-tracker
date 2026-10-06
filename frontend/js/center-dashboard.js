/**
 * center-dashboard.js — Staff dashboard controller
 * 
 * Loads and displays the staff member's relief center details,
 * inventory, and provides the update inventory form.
 */

(function() {
    // Require a staff account associated with a relief center
    const user = requireAuth('staff');
    if (!user) return;
    
    displayUserInfo();
    
    const centerId = user.centerId;
    
    if (!centerId) {
        document.getElementById('centerInfo').innerHTML = 
            '<p class="alert alert-error">No relief center is associated with your account. Contact an admin.</p>';
        return;
    }
    
    // Load center info and inventory on page load
    loadCenterInfo(centerId);
    loadInventory(centerId);
    
    // Set up the inventory update form
    document.getElementById('updateInventoryForm').addEventListener('submit', handleInventoryUpdate);
})();

/**
 * Fetches and displays the relief center details.
 */
async function loadCenterInfo(centerId) {
    const container = document.getElementById('centerInfo');
    
    try {
        const data = await getCenter(centerId);
        container.innerHTML = `
            <div class="info-grid">
                <div>
                    <p><strong>Name:</strong> ${escapeHtml(data.name)}</p>
                    <p><strong>Location:</strong> ${escapeHtml(data.location)}</p>
                </div>
                <div>
                    <p><strong>Phone:</strong> ${escapeHtml(data.contactPhone || 'N/A')}</p>
                    <p><strong>Email:</strong> ${escapeHtml(data.contactEmail || 'N/A')}</p>
                </div>
            </div>
        `;
    } catch (error) {
        container.innerHTML = `<p class="alert alert-error">Failed to load center info: ${error.message}</p>`;
    }
}

/**
 * Fetches and displays the full inventory grid.
 */
async function loadInventory(centerId) {
    const grid = document.getElementById('inventoryGrid');
    const lowStockCard = document.getElementById('lowStockCard');
    const lowStockAlerts = document.getElementById('lowStockAlerts');
    
    try {
        const data = await getInventory(centerId);
        const items = data.inventory || [];
        
        if (items.length === 0) {
            grid.innerHTML = '<p class="empty-state">No inventory items found.</p>';
            return;
        }
        
        // Build inventory cards
        grid.innerHTML = items.map(item => {
            const isLow = item.lowStock === 'true';
            return `
                <div class="inventory-item ${isLow ? 'low-stock' : ''}">
                    <div class="resource-label">${escapeHtml(item.resourceType)}</div>
                    <div class="quantity-display">${item.quantity}</div>
                    <div class="unit">${escapeHtml(item.unit)}</div>
                    <div class="inventory-threshold">
                        Threshold: ${item.threshold} ${escapeHtml(item.unit)}
                    </div>
                    ${isLow ? '<div class="badge badge-lowstock inventory-badge">LOW STOCK</div>' : ''}
                </div>
            `;
        }).join('');
        
        // Show low stock alerts section if there are low items
        const lowItems = items.filter(i => i.lowStock === 'true');
        if (lowItems.length > 0) {
            lowStockCard.style.display = 'block';
            lowStockAlerts.innerHTML = lowItems.map(item => `
                <div class="alert alert-warning">
                    <strong>${escapeHtml(item.resourceType)}</strong>: 
                    ${item.quantity} ${escapeHtml(item.unit)} (threshold: ${item.threshold})
                    — below minimum level!
                </div>
            `).join('');
        } else {
            lowStockCard.style.display = 'none';
        }
        
    } catch (error) {
        grid.innerHTML = `<p class="alert alert-error">Failed to load inventory: ${error.message}</p>`;
    }
}

/**
 * Handles the inventory update form submission.
 */
async function handleInventoryUpdate(e) {
    e.preventDefault();
    
    const alertDiv = document.getElementById('updateAlert');
    const centerId = getStoredUser().centerId;
    
    const resourceType = document.getElementById('resourceType').value;
    const quantity = document.getElementById('quantity').value;
    const unit = document.getElementById('unit').value;
    const threshold = document.getElementById('threshold').value;
    
    const payload = { resourceType };
    if (quantity) payload.quantity = parseFloat(quantity);
    if (unit) payload.unit = unit;
    if (threshold) payload.threshold = parseFloat(threshold);
    
    try {
        await updateInventory(centerId, payload);
        alertDiv.innerHTML = '<div class="alert alert-success">Inventory updated successfully!</div>';
        
        // Refresh the inventory display
        loadInventory(centerId);
        
        // Clear form
        document.getElementById('quantity').value = '';
        document.getElementById('threshold').value = '';
        
        // Auto-clear success message
        setTimeout(() => { alertDiv.innerHTML = ''; }, 3000);
        
    } catch (error) {
        alertDiv.innerHTML = `<div class="alert alert-error">Update failed: ${error.message}</div>`;
    }
}

/**
 * Simple HTML escaping to prevent XSS.
 */
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}
