/**
 * api.js — Central API configuration and HTTP helper
 */

const API_BASE_URL = 'https://qk6fhr7ko8.execute-api.ap-south-1.amazonaws.com/prod';

/**
 * Sends a request to API Gateway and returns the JSON response.
 */
async function apiRequest(method, path, body = null) {
    const url = `${API_BASE_URL}${path}`;
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        }
    };

    const user = getStoredUser();
    if (user && user.token) {
        options.headers['Authorization'] = 'Bearer ' + user.token;
    }

    if (body && (method === 'POST' || method === 'PUT')) {
        options.body = JSON.stringify(body);
    }

    try {
        const response = await fetch(url, options);
        const responseText = await response.text();
        let data = {};

        if (responseText) {
            try {
                data = JSON.parse(responseText);
            } catch {
                data = { rawResponse: responseText };
            }
        }

        if (!response.ok) {
            throw new Error(data.error || `HTTP ${response.status} from ${url}`);
        }

        return data;
    } catch (error) {
        if (error instanceof TypeError) {
            throw new Error(`Network or CORS error calling ${method} ${url}`);
        }

        console.error(`API Error [${method} ${path}]`, { url, error });
        throw error;
    }
}

async function loginUser(email, password) {
    return apiRequest('POST', '/auth/login', { email, password });
}

async function createCenter(data) {
    return apiRequest('POST', '/centers', data);
}

async function getCenter(centerId) {
    return apiRequest('GET', `/centers/${centerId}`);
}

async function listCenters(status = null) {
    const params = status ? `?status=${encodeURIComponent(status)}` : '';
    return apiRequest('GET', `/centers${params}`);
}

async function getInventory(centerId) {
    return apiRequest('GET', `/centers/${centerId}/inventory`);
}

async function updateInventory(centerId, data) {
    return apiRequest('PUT', `/centers/${centerId}/inventory`, data);
}

async function getLowStock() {
    return apiRequest('GET', '/inventory/low-stock');
}

async function submitRequest(data) {
    return apiRequest('POST', '/requests', data);
}

async function listRequests(status = null, sort = null) {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (sort) params.set('sort', sort);
    const queryString = params.toString();
    return apiRequest('GET', `/requests${queryString ? '?' + queryString : ''}`);
}

async function updateRequestStatus(requestId, data) {
    return apiRequest('PUT', `/requests/${requestId}`, data);
}

async function getStats() {
    return apiRequest('GET', '/stats');
}

function getStoredUser() {
    try {
        const raw = localStorage.getItem('drt_user');
        return raw ? JSON.parse(raw) : null;
    } catch {
        return null;
    }
}

function storeUser(user) {
    localStorage.setItem('drt_user', JSON.stringify(user));
}

function clearUser() {
    localStorage.removeItem('drt_user');
}

function logout() {
    clearUser();
    window.location.href = 'index.html';
}
