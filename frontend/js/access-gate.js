/**
 * Verifact Clinical Access Gate
 * Gates access to all diagnostic, PACS, and triage tools behind physician authentication,
 * while allowing public access to the landing page hero and clinical benchmark metrics.
 */

const API_BASE = (typeof import.meta !== 'undefined' && import.meta.env && (import.meta.env.VITE_API_BASE || import.meta.env.VITE_API_URL))
    || window.__VERIFACT_API_URL__
    || localStorage.getItem('VERIFACT_API_URL')
    || (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
        ? 'http://127.0.0.1:8000'
        : 'https://verifact-josv.onrender.com');

let currentDestination = '/worklist.html';
let gateModalEl = null;

export function isUserLoggedIn() {
    return !!sessionStorage.getItem('verifact_user') || !!sessionStorage.getItem('verifact_token');
}

export function openAccessGate(destination = '/worklist.html') {
    if (isUserLoggedIn()) {
        window.location.href = destination;
        return;
    }

    currentDestination = destination;
    ensureModalDOM();

    if (gateModalEl) {
        gateModalEl.classList.remove('hidden');
        gateModalEl.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
        
        const demoBtn = document.getElementById('gate-demo-login-btn');
        if (demoBtn) demoBtn.focus();
    }
}

export function closeAccessGate() {
    if (gateModalEl) {
        gateModalEl.classList.add('hidden');
        gateModalEl.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
    }
}

function ensureModalDOM() {
    if (document.getElementById('verifact-access-gate-modal')) {
        gateModalEl = document.getElementById('verifact-access-gate-modal');
        return;
    }

    const modal = document.createElement('div');
    modal.id = 'verifact-access-gate-modal';
    modal.className = 'fixed inset-0 z-[10000] flex items-center justify-center p-4 bg-[#1F1612]/70 backdrop-blur-sm transition-opacity duration-200';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('aria-labelledby', 'gate-modal-title');
    modal.setAttribute('aria-hidden', 'true');

    modal.innerHTML = `
        <div class="relative w-full max-w-lg bg-white rounded-2xl border border-[#EADFD3] shadow-[0_20px_50px_rgba(58,31,20,0.25)] overflow-hidden transition-all transform animate-in fade-in zoom-in-95 duration-200">
            <!-- Top Status Accent Band -->
            <div class="h-2 w-full bg-[#C8512D]"></div>

            <div class="p-6 sm:p-8">
                <!-- Close Button -->
                <button type="button" id="gate-close-btn" class="absolute top-5 right-5 w-8 h-8 rounded-lg text-[#6B5B52] hover:text-[#1F1612] hover:bg-[#FAF6F1] flex items-center justify-center transition-colors focus:outline-none focus:ring-2 focus:ring-[#C8512D]" aria-label="Close modal">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>

                <!-- Icon & Badge Header -->
                <div class="flex items-center gap-3 mb-4">
                    <div class="w-12 h-12 rounded-xl bg-[#FBE3D6] border border-[#EADFD3] flex items-center justify-center text-[#C8512D] shadow-sm shrink-0">
                        <svg width="24" height="24" viewBox="0 0 256 256" fill="currentColor">
                            <path d="M208,80H176V48a48,48,0,0,0-96,0V80H48A16,16,0,0,0,32,96V208a16,16,0,0,0,16,16H208a16,16,0,0,0,16-16V96A16,16,0,0,0,208,80ZM96,48a32,32,0,0,1,64,0V80H96ZM208,208H48V96H208V208Zm-80-64a20,20,0,1,1-20,20A20,20,0,0,1,128,144Z"/>
                        </svg>
                    </div>
                    <div>
                        <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[11px] font-mono font-semibold bg-[#FFF4E8] text-[#C8512D] border border-[#C8512D]/30 tracking-wide uppercase">
                            Clinical Gate
                        </span>
                        <div class="text-[12px] font-mono text-[#6B5B52] mt-0.5">HIPAA &amp; DICOM ENFORCED</div>
                    </div>
                </div>

                <!-- Title & Explanation -->
                <h3 id="gate-modal-title" class="text-xl sm:text-2xl font-bold text-[#1F1612] tracking-tight leading-tight">
                    Physician Authentication Required
                </h3>
                <p class="text-sm text-[#6B5B52] mt-2 leading-relaxed">
                    Access to the emergency PACS viewer, DenseNet-121 inference heatmaps, hospital worklist, and diagnostic reports requires verified clinical credentials.
                </p>

                <!-- Clinical Value Points -->
                <div class="my-5 p-4 rounded-xl bg-[#FAF6F1] border border-[#EADFD3] space-y-2 text-xs text-[#1F1612] font-mono">
                    <div class="flex items-center gap-2">
                        <span class="w-1.5 h-1.5 rounded-full bg-[#C8512D]"></span>
                        <span>0 KB PHI Retention · Local in-memory sanitization</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="w-1.5 h-1.5 rounded-full bg-[#F5A524]"></span>
                        <span>Dual-Engine Neural Consensus CADt pipeline</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="w-1.5 h-1.5 rounded-full bg-[#3A1F14]"></span>
                        <span>Attending Radiologist attestation &amp; audit logging</span>
                    </div>
                </div>

                <!-- Action Buttons -->
                <div class="flex flex-col gap-3">
                    <!-- Quick Demo Doctor Access Button -->
                    <button type="button" id="gate-demo-login-btn" class="w-full h-11 px-4 rounded-xl bg-[#C8512D] hover:bg-[#B04624] text-white text-sm font-semibold tracking-wide flex items-center justify-center gap-2 shadow-sm transition-all active:scale-[0.99] focus:outline-none focus:ring-2 focus:ring-[#C8512D] focus:ring-offset-2">
                        <svg width="18" height="18" viewBox="0 0 256 256" fill="currentColor">
                            <path d="M224,128a96,96,0,1,1-96-96A96,96,0,0,1,224,128Z" opacity="0.2"/>
                            <path d="M128,24A104,104,0,1,0,232,128,104.11,104.11,0,0,0,128,24Zm0,192a88,88,0,1,1,88-88A88.1,88.1,0,0,1,128,216ZM156,128a12,12,0,1,1-12-12A12,12,0,0,1,156,128Z"/>
                        </svg>
                        <span id="gate-demo-btn-text">1-Click Demo Doctor Access</span>
                        <div id="gate-demo-spinner" class="hidden w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin"></div>
                    </button>

                    <!-- Standard Sign In -->
                    <button type="button" id="gate-signin-btn" class="w-full h-11 px-4 rounded-xl border border-[#EADFD3] bg-white hover:bg-[#FAF6F1] text-[#1F1612] text-sm font-semibold flex items-center justify-center gap-2 transition-colors focus:outline-none focus:ring-2 focus:ring-[#C8512D]">
                        Sign in with Credentials
                    </button>
                </div>

                <!-- Sign up Link -->
                <div class="mt-4 pt-3 border-t border-[#EADFD3] text-center text-xs text-[#6B5B52]">
                    Need a new physician or resident account? 
                    <a href="/signup.html" id="gate-signup-link" class="text-[#C8512D] font-semibold hover:underline">
                        Create account &rarr;
                    </a>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
    gateModalEl = modal;

    // Close button
    document.getElementById('gate-close-btn').addEventListener('click', closeAccessGate);

    // Close on outside click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeAccessGate();
    });

    // Close on Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
            closeAccessGate();
        }
    });

    // Sign in redirect
    document.getElementById('gate-signin-btn').addEventListener('click', () => {
        window.location.href = `/login.html?next=${encodeURIComponent(currentDestination)}`;
    });

    // Sign up redirect
    document.getElementById('gate-signup-link').addEventListener('click', (e) => {
        e.preventDefault();
        window.location.href = `/signup.html?next=${encodeURIComponent(currentDestination)}`;
    });

    // 1-Click Demo Doctor Access
    document.getElementById('gate-demo-login-btn').addEventListener('click', async () => {
        const btnText = document.getElementById('gate-demo-btn-text');
        const spinner = document.getElementById('gate-demo-spinner');
        const btn = document.getElementById('gate-demo-login-btn');

        btn.disabled = true;
        btnText.textContent = 'Authenticating Demo Doctor...';
        spinner.classList.remove('hidden');

        try {
            const res = await fetch(`${API_BASE}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    email: 'demo@verifact.ai',
                    password: 'DemoDoctor2026!'
                })
            });

            if (res.ok) {
                const data = await res.json();
                if (data.access_token) sessionStorage.setItem('verifact_token', data.access_token);
                if (data.user) sessionStorage.setItem('verifact_user', JSON.stringify(data.user));

                btnText.textContent = 'Access Granted! Entering...';
                setTimeout(() => {
                    window.location.href = currentDestination;
                }, 250);
            } else {
                // If demo login fails on API, navigate to login page
                window.location.href = `/login.html?next=${encodeURIComponent(currentDestination)}`;
            }
        } catch (err) {
            window.location.href = `/login.html?next=${encodeURIComponent(currentDestination)}`;
        }
    });
}

// Intercept all protected links on the landing page
export function setupProtectedInterceptors() {
    // Protected destination keywords
    const protectedPages = [
        'upload.html', 'worklist.html', 'viewer.html', 'findings.html',
        'sign-off.html', 'analytics.html', 'audit-log.html', 'profile.html',
        'scan-in-progress.html', 'privacy-check.html',
        '/upload', '/worklist', '/viewer', '/findings',
        '/sign-off', '/analytics', '/audit-log', '/profile'
    ];

    document.addEventListener('click', (e) => {
        // Find anchor or button with destination
        const link = e.target.closest('a, button[data-destination], .vf-card');
        if (!link) return;

        let target = link.getAttribute('href') || link.getAttribute('data-destination') || '';

        // If it's a sample card with an onclick redirect
        if (link.classList.contains('vf-card') && !isUserLoggedIn()) {
            e.preventDefault();
            e.stopImmediatePropagation();
            openAccessGate('/scan-in-progress.html');
            return;
        }

        // If href matches a protected page
        const isProtected = protectedPages.some(page => target.includes(page));
        if (isProtected) {
            if (!isUserLoggedIn()) {
                e.preventDefault();
                e.stopPropagation();
                openAccessGate(target);
            }
        }
    }, true); // Use capture phase so we intercept before inline onclicks
}

// Global hooks
if (typeof window !== 'undefined') {
    window.openAccessGate = openAccessGate;
    window.closeAccessGate = closeAccessGate;
    window.isUserLoggedIn = isUserLoggedIn;
}

// Initialize on DOM ready
if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupProtectedInterceptors);
    } else {
        setupProtectedInterceptors();
    }
}
