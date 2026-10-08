/**
 * public-request.js — Public help request form controller
 * 
 * Handles the submission of help requests by anyone (no auth required).
 * This page is publicly accessible.
 */

(function() {
    const form = document.getElementById('helpRequestForm');
    const alertBox = document.getElementById('alert-box');
    const successMessage = document.getElementById('successMessage');
    const description = document.getElementById('description');
    const descriptionCount = document.getElementById('descriptionCount');

    description?.addEventListener('input', function() {
        descriptionCount.textContent = `${description.value.length}/500`;
    });
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Clear previous alerts
        alertBox.innerHTML = '';
        
        // Gather form data
        const data = {
            name: document.getElementById('name').value.trim(),
            location: document.getElementById('location').value.trim(),
            needType: document.getElementById('needType').value,
            urgency: parseInt(document.getElementById('urgency').value),
            contactPhone: document.getElementById('contactPhone').value.trim(),
            description: document.getElementById('description').value.trim()
        };
        
        // Client-side validation
        if (!data.name || !data.location || !data.needType || !data.urgency || !data.description) {
            alertBox.innerHTML = '<div class="alert alert-error" role="alert">Please fill in all required fields.</div>';
            return;
        }
        if (data.description.length < 10) {
            alertBox.innerHTML = '<div class="alert alert-error" role="alert">Please provide a little more detail about the help needed.</div>';
            return;
        }
        
        try {
            const btn = form.querySelector('button[type="submit"]');
            btn.disabled = true;
            btn.textContent = 'Submitting...';
            
            const result = await submitRequest(data);
            const requestId = document.getElementById('requestId');
            if (requestId && result.requestId) {
                requestId.textContent = result.requestId;
            }
            
            // Show success message, hide form
            form.style.display = 'none';
            successMessage.style.display = 'block';
            
        } catch (error) {
            alertBox.innerHTML = `<div class="alert alert-error" role="alert">Submission failed. Please try again.</div>`;
            
            const btn = form.querySelector('button[type="submit"]');
            btn.disabled = false;
            btn.textContent = 'Submit Help Request';
        }
    });

})();

/**
 * Resets the form to allow submitting another request.
 */
function resetForm() {
    const form = document.getElementById('helpRequestForm');
    const successMessage = document.getElementById('successMessage');
    
    form.reset();
    form.style.display = 'block';
    successMessage.style.display = 'none';
    document.getElementById('requestId').textContent = 'Not available';
    if (descriptionCount) descriptionCount.textContent = '0/500';
    
    const btn = form.querySelector('button[type="submit"]');
    btn.disabled = false;
    btn.textContent = 'Submit Help Request';
    
    document.getElementById('alert-box').innerHTML = '';
}
