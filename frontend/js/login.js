/**
 * login.js — Login page controller
 * 
 * Handles the login form submission, validates credentials via the
 * login_user Lambda, and redirects to the appropriate dashboard.
 */

(function() {
    // If already logged in, redirect to appropriate page
    const user = getStoredUser();
    if (user) {
        if (user.role === 'admin') {
            window.location.href = 'admin-dashboard.html';
        } else {
            window.location.href = 'center-dashboard.html';
        }
        return;
    }
    
    const form = document.getElementById('loginForm');
    const alertBox = document.getElementById('alert-box');
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;
        
        // Clear previous alerts
        alertBox.innerHTML = '';
        
        // Basic validation
        if (!email || !password) {
            showAlert(alertBox, 'Please enter both email and password.', 'error');
            return;
        }
        
        try {
            const btn = form.querySelector('button[type="submit"]');
            btn.disabled = true;
            btn.textContent = 'Signing in...';

            const result = await loginUser(email, password);
            const sessionUser = {
                ...result.user,
                token: result.token || result.user?.token || null
            };

            storeUser(sessionUser);

            if (sessionUser.role === 'admin') {
                window.location.href = 'admin-dashboard.html';
            } else {
                window.location.href = 'center-dashboard.html';
            }

        } catch (error) {
            showAlert(alertBox, error.message || 'Login failed. Please try again.', 'error');

            const btn = form.querySelector('button[type="submit"]');
            btn.disabled = false;
            btn.textContent = 'Sign In';
        }
    });
})();

/**
 * Shows an alert message inside the given container.
 */
function showAlert(container, message, type) {
    container.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
}
