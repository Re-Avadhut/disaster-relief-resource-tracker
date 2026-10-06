/**
 * auth.js — Authentication guard and user session management
 * 
 * Protects staff/admin pages by checking if a user is logged in.
 * Redirects to login page if no valid session exists.
 */

/**
 * Checks if user is logged in. Returns user object or null.
 * Also validates that the user's role matches the required role.
 */
function requireAuth(requiredRole = null) {
    const user = getStoredUser();
    
    if (!user) {
        window.location.href = 'index.html';
        return null;
    }
    
    if (requiredRole && user.role !== requiredRole) {
        window.location.href = 'index.html';
        return null;
    }
    
    return user;
}

/**
 * Display user info in the navbar
 */
function displayUserInfo() {
    const user = getStoredUser();
    const el = document.getElementById('userInfo');
    if (el && user) {
        el.textContent = `${user.name} (${user.role})`;
    }
}
