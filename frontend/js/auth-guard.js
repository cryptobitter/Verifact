/**
 * Verifact Client Authentication Guard & Session Sentinel
 * Strict route protection, branded loading gate, and 401 interceptor.
 */

const API_BASE = (typeof import.meta !== 'undefined' && import.meta.env && (import.meta.env.VITE_API_BASE || import.meta.env.VITE_API_URL))
    || window.__VERIFACT_API_URL__
    || localStorage.getItem('VERIFACT_API_URL')
    || (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
        ? 'http://127.0.0.1:8000'
        : 'https://verifact-josv.onrender.com');

// Auth-only routes (redirect to Overview if already logged in)
const AUTH_ONLY_PATHS = ['/login', '/login.html', '/signup', '/signup.html'];

// Public routes that do not require authentication
const PUBLIC_PATHS = ['/', '/index', '/index.html', '/about.html', '/how-it-works.html', '/404', '/404.html', ...AUTH_ONLY_PATHS];

export function isAuthOnlyPage() {
    const path = window.location.pathname.toLowerCase();
    return AUTH_ONLY_PATHS.some(p => path === p || path.endsWith(p));
}

export function isPublicPage() {
    const path = window.location.pathname.toLowerCase();
    if (path === '' || path === '/') return true;
    return PUBLIC_PATHS.some(p => path === p || path.endsWith(p));
}

// 1. Immediate Pre-Render Security Shield (Prevents protected UI flash)
let authShieldElement = null;

function mountAuthShield() {
    if (isPublicPage()) return;
    authShieldElement = document.createElement('div');
    authShieldElement.id = 'verifact-auth-shield';
    authShieldElement.style.cssText = `
        position: fixed;
        inset: 0;
        z-index: 999999;
        background-color: #FFFFFF;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        font-family: 'Geist', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #1F1612;
        transition: opacity 0.2s ease-out;
    `;
    authShieldElement.innerHTML = `
        <div style="display:flex; flex-direction:column; align-items:center; gap:16px;">
            <div style="width:52px; height:52px; border-radius:12px; background:#FBE3D6; border:1px solid #EADFD3; display:flex; align-items:center; justify-content:center; box-shadow:0 2px 8px rgba(58,31,20,0.06);">
                <svg width="28" height="28" viewBox="0 0 256 256" fill="#C8512D" xmlns="http://www.w3.org/2000/svg">
                    <path d="M208,80H176V48a48,48,0,0,0-96,0V80H48A16,16,0,0,0,32,96V208a16,16,0,0,0,16,16H208a16,16,0,0,0,16-16V96A16,16,0,0,0,208,80ZM96,48a32,32,0,0,1,64,0V80H96ZM208,208H48V96H208V208Zm-80-64a20,20,0,1,1-20,20A20,20,0,0,1,128,144Z"/>
                </svg>
            </div>
            <div style="text-align:center;">
                <div style="font-size:16px; font-weight:700; letter-spacing:-0.02em; color:#1F1612;">VERIFACT PACS</div>
                <div style="font-size:12px; color:#6B5B52; font-family:monospace; margin-top:4px;">VERIFYING CLINICAL CREDENTIALS...</div>
            </div>
        </div>
    `;
    document.documentElement.appendChild(authShieldElement);
}

function unmountAuthShield() {
    if (authShieldElement && authShieldElement.parentNode) {
        authShieldElement.style.opacity = '0';
        setTimeout(() => {
            if (authShieldElement && authShieldElement.parentNode) {
                authShieldElement.parentNode.removeChild(authShieldElement);
            }
        }, 180);
    }
}

// Execute shield as early as possible
if (typeof document !== 'undefined') {
    if (document.body) {
        mountAuthShield();
    } else {
        document.addEventListener('DOMContentLoaded', mountAuthShield, { once: true });
    }
}

// 2. Session Verification
export async function checkAuthSession() {
    const isPublic = isPublicPage();
    const token = sessionStorage.getItem('verifact_token') || localStorage.getItem('verifact_token');

    const headers = { 'Accept': 'application/json' };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    try {
        const res = await fetch(`${API_BASE}/auth/me`, {
            method: 'GET',
            headers: headers,
            credentials: 'include' // Cross-domain cookie delivery
        });

        if (res.ok) {
            const userData = await res.json();
            sessionStorage.setItem('verifact_user', JSON.stringify(userData));

            // If user is already logged in and visiting login/signup, redirect to next or Overview
            if (isAuthOnlyPage()) {
                const params = new URLSearchParams(window.location.search);
                const next = params.get('next') || '/index.html';
                window.location.href = next;
                return;
            }

            unmountAuthShield();
            return userData;
        } else if (res.status === 401) {
            handleUnauthorized(isPublic);
        } else {
            handleUnauthorized(isPublic);
        }
    } catch (err) {
        console.warn('[AUTH] Session verification network error:', err);
        // If network error on protected page and no cached user, send to login
        handleUnauthorized(isPublic);
    }
}

function handleUnauthorized(isPublic) {
    sessionStorage.removeItem('verifact_user');
    sessionStorage.removeItem('verifact_token');
    localStorage.removeItem('verifact_token');

    if (!isPublic) {
        const nextUrl = encodeURIComponent(window.location.pathname + window.location.search);
        window.location.href = `/login.html?next=${nextUrl}`;
    } else {
        unmountAuthShield();
    }
}

// 3. Global Logout Helper
export async function authLogout() {
    const token = sessionStorage.getItem('verifact_token') || localStorage.getItem('verifact_token');
    const headers = { 'Content-Type': 'application/json' };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    try {
        await fetch(`${API_BASE}/auth/logout`, {
            method: 'POST',
            headers: headers,
            credentials: 'include'
        });
    } catch (e) {
        console.warn('[AUTH] Logout network error:', e);
    }
    sessionStorage.removeItem('verifact_user');
    sessionStorage.removeItem('verifact_token');
    localStorage.removeItem('verifact_token');
    window.location.href = '/login.html';
}
if (typeof window !== 'undefined') {
    window.authLogout = authLogout;
}

// 4. Global 401 Interceptor for active operations
const originalFetch = window.fetch;
window.fetch = async function(...args) {
    const response = await originalFetch.apply(this, args);
    if (response.status === 401 && !isPublicPage()) {
        const url = args[0] ? args[0].toString() : '';
        // Only intercept app API calls, not external assets
        if (url.includes('/auth/') || url.includes('/analysis') || url.includes('/analyze') || url.includes('/samples')) {
            sessionStorage.setItem('verifact_flash_message', 'Session expired, please sign in again.');
            handleUnauthorized(false);
        }
    }
    return response;
};

// 5. Run session check on DOM ready
if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', checkAuthSession);
    } else {
        checkAuthSession();
    }
}
