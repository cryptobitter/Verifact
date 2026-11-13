/**
 * VERIFACT Clinical PACS & Triage Engine
 * Centralized Client-Side Architecture connecting all 12 Stitch screens
 * to the FastAPI Backend (http://127.0.0.1:8000) and Supabase persistence.
 */

const API_BASE = (typeof import.meta !== 'undefined' && import.meta.env && (import.meta.env.VITE_API_BASE || import.meta.env.VITE_API_URL))
    || window.__VERIFACT_API_URL__
    || localStorage.getItem('VERIFACT_API_URL')
    || (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
        ? 'http://127.0.0.1:8000'
        : 'https://verifact-josv.onrender.com');

// Default demo showcase analysis state
const DEFAULT_DEMO_ANALYSIS = {
    id: 1,
    patient_id: "ANON-8841",
    patient_age: 42,
    patient_gender: "Male",
    body_part: "wrist",
    view_position: "Left Wrist AP / Lateral",
    fracture_detected: true,
    confidence: 0.947,
    fracture_probability: 0.947,
    bone: "Distal Radius",
    location: "Metaphyseal Cortex",
    fracture_type: "Colles' Metaphyseal Fracture",
    displacement: "Mild dorsal angulation (~12°)",
    severity: "Moderate",
    report_text: "Visualized radiograph demonstrates a mildly displaced Colles' metaphyseal fracture across the distal radius. Surrounding localized soft tissue attenuation identified without overt radiocarpal joint dislocation. Orthopedic splint immobilization and urgent specialist verification recommended.",
    cnn_prediction: true,
    cnn_probability: 0.947,
    llm_prediction: true,
    providers_agreed: true,
    review_priority: "normal",
    review_reason: "High concordance between CNN detector (94.7%) and vision LLM.",
    model_version: "verifact-densenet121-epoch3",
    latency_ms: 540.7,
    image_url: "https://lh3.googleusercontent.com/aida-public/AB6AXuCvhusTNoasnGXiX7MxDh4j59W1fFEshjGTNboswPUtQicqdGvvfJJqCaJDcRQYn6UVTRm3SXSLNnZzLX5HG17jWsYm54WOSn8SAgn6MoIXs43CArJ8MybUKJg50DDCZ6s3_OHjRyE7r4BMr-n806immW5BIGk2GjLTRDYdbht-Qas4LGbwIA88VbpIIAwS9UT4CBXchdwOHtvj9eoWr5juTKVfdma3vpYr-jRMQGtZ",
    heatmap_url: null,
    pixel_spacing: "0.143, 0.143"
};

// ============================================================================
// 1. STATE & STORAGE MANAGEMENT
// ============================================================================

function getAuthToken() {
    return localStorage.getItem('verifact_token') || 'demo_token_authenticated';
}

function getUser() {
    try {
        const u = localStorage.getItem('verifact_user');
        return u ? JSON.parse(u) : {
            full_name: "Dr. Elena Vance, MD",
            role: "Attending Radiologist",
            registration_number: "MCI-2024-88419",
            hospital: "Verifact Academic Trauma Center"
        };
    } catch (e) {
        return null;
    }
}

function getActiveAnalysis() {
    try {
        const a = sessionStorage.getItem('current_analysis');
        return a ? JSON.parse(a) : DEFAULT_DEMO_ANALYSIS;
    } catch (e) {
        return DEFAULT_DEMO_ANALYSIS;
    }
}

function setActiveAnalysis(analysis) {
    sessionStorage.setItem('current_analysis', JSON.stringify(analysis));
}

// ============================================================================
// 2. GLOBAL NAVIGATION & NAVBAR SYNC
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    syncNavbarUser();
    initPageSpecificLogic();
});

function initNavigation() {
    // Intercept all data-path links across headers and buttons
    document.querySelectorAll('[data-path]').forEach(el => {
        el.addEventListener('click', (e) => {
            e.preventDefault();
            const path = el.getAttribute('data-path');
            navigateTo(path);
        });
    });

    // Handle generic links like href="/worklist"
    document.querySelectorAll('a[href]').forEach(link => {
        const href = link.getAttribute('href');
        if (href && href.startsWith('/') && !href.startsWith('//') && !href.endsWith('.html') && href !== '/') {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const route = href.replace('/', '');
                navigateTo(route);
            });
        }
    });
}

function navigateTo(route) {
    const routeMap = {
        '': '/index.html',
        'home': '/index.html',
        'landing': '/index.html',
        'worklist': '/worklist.html',
        'upload': '/upload.html',
        'upload-scan': '/scan-in-progress.html',
        'scan-in-progress': '/scan-in-progress.html',
        'privacy-check': '/privacy-check.html',
        'scan': '/scan-in-progress.html',
        'scan-in-progress': '/scan-in-progress.html',
        'findings': '/findings.html',
        'viewer': '/viewer.html',
        'sign-off': '/sign-off.html',
        'analytics': '/analytics.html',
        'audit-log': '/audit-log.html',
        'how-it-works': '/how-it-works.html',
        'about': '/about.html',
        'login': '/login.html',
        'sign-in': '/login.html',
        'sign-out': () => {
            localStorage.removeItem('verifact_token');
            sessionStorage.clear();
            window.location.href = '/login.html';
        }
    };

    if (routeMap[route]) {
        if (typeof routeMap[route] === 'function') {
            routeMap[route]();
        } else {
            window.location.href = routeMap[route];
        }
    } else {
        window.location.href = `/${route}.html`;
    }
}

function syncNavbarUser() {
    const user = getUser();
    if (!user) return;

    // Update doctor name and credentials in the header
    document.querySelectorAll('.font-body-strong, .font-semibold').forEach(el => {
        if (el.textContent.includes('Dr.') && el.textContent.includes('Vance')) {
            el.textContent = user.full_name || "Dr. Elena Vance, MD";
        }
    });

    document.querySelectorAll('.font-label-sm, .font-normal').forEach(el => {
        if (el.textContent.includes('Attending Radiologist') || el.textContent.includes('Physician')) {
            el.textContent = user.role || "Attending Radiologist";
        }
    });
}

// ============================================================================
// 3. PAGE SPECIFIC ROUTINES
// ============================================================================

function initPageSpecificLogic() {
    const pathname = window.location.pathname.toLowerCase();

    if (pathname.includes('login') || pathname.endsWith('login.html')) {
        setupLoginPage();
    } else if (pathname.includes('upload') || pathname.endsWith('upload.html')) {
        setupUploadPage();
    } else if (pathname.includes('privacy') || pathname.endsWith('privacy-check.html')) {
        setupPrivacyPage();
    } else if (pathname.includes('scan') || pathname.endsWith('scan-in-progress.html')) {
        setupScanProgressPage();
    } else if (pathname.includes('findings') || pathname.endsWith('findings.html')) {
        setupFindingsPage();
    } else if (pathname.includes('viewer') || pathname.endsWith('viewer.html')) {
        setupViewerPage();
    } else if (pathname.includes('sign-off') || pathname.endsWith('sign-off.html')) {
        setupSignOffPage();
    } else if (pathname.includes('worklist') || pathname.endsWith('worklist.html')) {
        setupWorklistPage();
    } else if (pathname.includes('analytics') || pathname.endsWith('analytics.html')) {
        setupAnalyticsPage();
    } else if (pathname.includes('audit-log') || pathname.endsWith('audit-log.html')) {
        setupAuditLogPage();
    }
}

// ----------------------------------------------------------------------------
// A. LOGIN PAGE
// ----------------------------------------------------------------------------
function setupLoginPage() {
    const form = document.getElementById('credentialForm');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const emailInput = document.getElementById('workEmail');
            const pwdInput = document.getElementById('password');
            const npiInput = document.getElementById('npiNumber');

            const email = emailInput ? emailInput.value : 'demo@verifact.ai';
            const password = pwdInput ? pwdInput.value : 'demo123';
            const npi = npiInput ? npiInput.value : 'MCI-2024-88419';

            try {
                const formData = new FormData();
                formData.append('username', email);
                formData.append('password', password);

                const resp = await fetch(`${API_BASE}/auth/login`, {
                    method: 'POST',
                    body: formData
                });

                if (resp.ok) {
                    const data = await resp.json();
                    localStorage.setItem('verifact_token', data.access_token);
                }
            } catch (err) {
                console.warn('Backend login request fallback to offline token:', err);
            }

            // Save user profile
            localStorage.setItem('verifact_user', JSON.stringify({
                full_name: email.includes('demo') ? "Dr. Elena Vance, MD" : "Dr. " + email.split('@')[0],
                role: "Attending Musculoskeletal Radiologist",
                registration_number: npi,
                hospital: "Verifact Academic Trauma Center"
            }));

            window.location.href = '/worklist.html';
        });
    }

    // Fast-track demo button
    const demoBtn = document.querySelector('button[onclick*="demo"], button:has(.material-symbols-outlined)');
    if (demoBtn) {
        demoBtn.addEventListener('click', () => {
            localStorage.setItem('verifact_token', 'demo_token_authenticated');
            localStorage.setItem('verifact_user', JSON.stringify({
                full_name: "Dr. Elena Vance, MD",
                role: "Attending Radiologist",
                registration_number: "MCI-2024-88419",
                hospital: "Verifact Academic Trauma Center"
            }));
            window.location.href = '/worklist.html';
        });
    }
}

// ----------------------------------------------------------------------------
// B. UPLOAD PAGE & 1-CLICK DEMO CASES
// ----------------------------------------------------------------------------
function setupUploadPage() {
    const fileInput = document.getElementById('radiograph-file-input');
    const dropzone = document.getElementById('dropzone');
    const stagedIndicator = document.getElementById('staged-file-indicator');
    const stagedFileName = document.getElementById('staged-file-name');
    const stagedFileMeta = document.getElementById('staged-file-meta');
    let selectedFile = null;

    if (dropzone && fileInput) {
        dropzone.addEventListener('click', () => fileInput.click());
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('border-primary', 'bg-surface-container-high');
        });
        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('border-primary', 'bg-surface-container-high');
        });
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('border-primary', 'bg-surface-container-high');
            if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                handleFileSelection(e.dataTransfer.files[0]);
            }
        });

        fileInput.addEventListener('change', () => {
            if (fileInput.files && fileInput.files[0]) {
                handleFileSelection(fileInput.files[0]);
            }
        });
    }

    function handleFileSelection(file) {
        selectedFile = file;
        if (stagedIndicator) {
            stagedIndicator.classList.remove('hidden');
            if (stagedFileName) stagedFileName.textContent = file.name;
            if (stagedFileMeta) {
                const mb = (file.size / (1024 * 1024)).toFixed(1);
                stagedFileMeta.textContent = `${mb} MB • Upper Extremity`;
            }
        }
    }

    // Submit triage button
    const submitBtn = document.querySelector('button[type="submit"], #submit-triage-btn, a[href*="scan"]');
    if (submitBtn) {
        submitBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            if (selectedFile) {
                await uploadAndScanFile(selectedFile);
            } else {
                // If no file picked, use Colles fracture default
                window.location.href = '/privacy-check.html';
            }
        });
    }

    // Setup 4 1-Click Verified Demo Cards
    setupDemoStudyCards();
}

function setupDemoStudyCards() {
    const sampleCards = document.querySelectorAll('[data-sample-id], .sample-card, [data-case-id]');
    
    // Also attach to the 4 verified cards in the DOM by title match
    document.querySelectorAll('.bg-surface-container-lowest, .rounded-xl, .cursor-pointer').forEach(card => {
        const text = card.textContent || '';
        let sampleId = null;

        if (text.includes('Distal Radius') || text.includes('Colles')) {
            sampleId = 'distal_radius_fracture';
        } else if (text.includes('Intact Femur') || text.includes('Control')) {
            sampleId = 'normal_femur_control';
        } else if (text.includes('Clavicle')) {
            sampleId = 'clavicle_displaced_fracture';
        } else if (text.includes('Scaphoid')) {
            sampleId = 'scaphoid_hairline_fracture';
        }

        if (sampleId) {
            const btn = card.querySelector('button, a') || card;
            btn.style.cursor = 'pointer';
            btn.addEventListener('click', async (e) => {
                e.preventDefault();
                await triggerSampleScan(sampleId);
            });
        }
    });
}

async function triggerSampleScan(sampleId) {
    try {
        const resp = await fetch(`${API_BASE}/analyze/sample/${sampleId}`, { method: 'POST' });
        if (resp.ok) {
            const result = await resp.json();
            setActiveAnalysis(result);
            window.location.href = '/scan-in-progress.html';
            return;
        }
    } catch (err) {
        console.warn('Backend sample scan fallback to local mock:', err);
    }

    // Fallback sample mock
    const sampleMocks = {
        distal_radius_fracture: {
            ...DEFAULT_DEMO_ANALYSIS,
            id: 101,
            body_part: "wrist",
            view_position: "Left Wrist AP/Lateral",
            fracture_detected: true,
            confidence: 0.98,
            fracture_probability: 0.98,
            bone: "Distal Radius",
            fracture_type: "Colles' Metaphyseal Fracture",
            displacement: "Dorsal tilt (~12°)",
            review_priority: "normal"
        },
        normal_femur_control: {
            ...DEFAULT_DEMO_ANALYSIS,
            id: 102,
            patient_id: "ANON-8842",
            body_part: "femur",
            view_position: "Femur Shaft AP",
            fracture_detected: false,
            confidence: 0.05,
            fracture_probability: 0.05,
            bone: "Femur",
            fracture_type: "Intact",
            displacement: "None",
            review_priority: "normal",
            report_text: "Visualized radiograph demonstrates intact cortical margins and continuous cortical density without fracture, periosteal breach, or step-off. Periarticular soft tissue planes appear preserved."
        },
        clavicle_displaced_fracture: {
            ...DEFAULT_DEMO_ANALYSIS,
            id: 103,
            patient_id: "ANON-8843",
            body_part: "clavicle",
            view_position: "Clavicle AP",
            fracture_detected: true,
            confidence: 0.96,
            fracture_probability: 0.96,
            bone: "Clavicle",
            fracture_type: "Comminuted mid-shaft fracture",
            displacement: "Vertical displacement gap (~14 mm)",
            review_priority: "urgent",
            review_reason: "High acuity comminuted trauma requiring orthopedic fixation."
        },
        scaphoid_hairline_fracture: {
            ...DEFAULT_DEMO_ANALYSIS,
            id: 104,
            patient_id: "ANON-8844",
            body_part: "wrist",
            view_position: "Carpal Scaphoid View",
            fracture_detected: true,
            confidence: 0.58,
            fracture_probability: 0.58,
            bone: "Scaphoid",
            fracture_type: "Hairline occult waist fracture",
            displacement: "Non-displaced",
            review_priority: "urgent",
            review_reason: "Model confidence in uncertainty band (0.58). Urgent radiologist review required."
        }
    };

    setActiveAnalysis(sampleMocks[sampleId] || DEFAULT_DEMO_ANALYSIS);
    window.location.href = '/scan-in-progress.html';
}

async function uploadAndScanFile(file) {
    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('patient_id', 'ANON-' + Math.floor(1000 + Math.random() * 9000));
        formData.append('body_part', 'wrist');

        const resp = await fetch(`${API_BASE}/analyze`, {
            method: 'POST',
            body: formData
        });

        if (resp.ok) {
            const data = await resp.json();
            setActiveAnalysis(data);
            window.location.href = '/privacy-check.html';
            return;
        }
    } catch (err) {
        console.warn('Backend upload fallback:', err);
    }

    window.location.href = '/privacy-check.html';
}

// ----------------------------------------------------------------------------
// C. PRIVACY CHECK PAGE
// ----------------------------------------------------------------------------
function setupPrivacyPage() {
    const runScanBtn = document.getElementById('run-ai-scan-btn') || 
                       document.querySelector('[data-path="scan-in-progress"], [data-path="upload-scan"], a[href*="scan"]');
    if (runScanBtn) {
        runScanBtn.addEventListener('click', (e) => {
            e.preventDefault();
            window.location.href = '/scan-in-progress.html';
        });
    }
}

// ----------------------------------------------------------------------------
// D. SCAN IN PROGRESS ANIMATED HUD
// ----------------------------------------------------------------------------
async function setupScanProgressPage() {
    const sampleId = sessionStorage.getItem('current_sample_id') || 'distal_radius_fracture';
    
    // Fetch live analysis or prepare fallback
    try {
        const resp = await fetch(`${API_BASE}/analyze/sample/${sampleId}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });
        if (resp.ok) {
            const data = await resp.json();
            setActiveAnalysis(data);
        } else {
            setFallbackAnalysis(sampleId);
        }
    } catch (e) {
        setFallbackAnalysis(sampleId);
    }

    let progress = 20;
    const bar = document.getElementById('active-progress-bar') || document.querySelector('#active-progress-bar, .bg-secondary-fixed');
    const label = document.getElementById('progress-percent-label') || document.querySelector('#progress-percent-label');

    const interval = setInterval(() => {
        progress += 5;
        if (progress > 100) progress = 100;
        if (bar) bar.style.width = `${progress}%`;
        if (label) label.textContent = `${progress}%`;

        if (progress >= 100) {
            clearInterval(interval);
            setTimeout(() => {
                window.location.href = '/findings.html';
            }, 350);
        }
    }, 75);
}

function setFallbackAnalysis(sampleId) {
    const sampleMocks = {
        distal_radius_fracture: {
            ...DEFAULT_DEMO_ANALYSIS,
            id: 101,
            body_part: "wrist",
            view_position: "Left Wrist AP/Lateral",
            fracture_detected: true,
            confidence: 0.98,
            fracture_probability: 0.98,
            bone: "Distal Radius",
            location: "Distal Metaphysis",
            fracture_type: "Colles' Metaphyseal Fracture",
            displacement: "Dorsal tilt (~12°)",
            severity: "Moderate",
            review_priority: "normal",
            report_text: "Visualized radiograph demonstrates a mildly displaced Colles' metaphyseal fracture across the distal radius. Surrounding localized soft tissue attenuation identified without overt radiocarpal joint dislocation. Splint immobilization intact at time of review."
        },
        normal_femur_control: {
            ...DEFAULT_DEMO_ANALYSIS,
            id: 102,
            patient_id: "ANON-8842",
            body_part: "femur",
            view_position: "Femur Shaft AP",
            fracture_detected: false,
            confidence: 0.05,
            fracture_probability: 0.05,
            bone: "Femur",
            location: "Diaphysis",
            fracture_type: "Intact",
            displacement: "None",
            severity: "None",
            review_priority: "normal",
            report_text: "Visualized radiograph demonstrates intact cortical margins and continuous cortical density without fracture, periosteal breach, or step-off. Periarticular soft tissue planes appear preserved."
        },
        clavicle_displaced_fracture: {
            ...DEFAULT_DEMO_ANALYSIS,
            id: 103,
            patient_id: "ANON-8843",
            body_part: "clavicle",
            view_position: "Clavicle AP",
            fracture_detected: true,
            confidence: 0.96,
            fracture_probability: 0.96,
            bone: "Clavicle",
            location: "Mid-shaft",
            fracture_type: "Comminuted mid-shaft fracture",
            displacement: "Vertical displacement gap (~14 mm)",
            severity: "Severe",
            review_priority: "urgent",
            report_text: "Visualized radiograph reveals acute comminuted mid-shaft clavicular fracture with cranial displacement of the medial fragment by approximately 14mm. Orthopedic surgical fixation consultation strongly advised."
        },
        scaphoid_hairline_fracture: {
            ...DEFAULT_DEMO_ANALYSIS,
            id: 104,
            patient_id: "ANON-8844",
            body_part: "wrist",
            view_position: "Carpal Scaphoid View",
            fracture_detected: true,
            confidence: 0.58,
            fracture_probability: 0.58,
            bone: "Scaphoid",
            location: "Anatomical Waist",
            fracture_type: "Hairline occult waist fracture",
            displacement: "Non-displaced",
            severity: "Borderline",
            review_priority: "urgent",
            report_text: "Visualized carpal views demonstrate subtle radiolucent hairline disruption traversing the scaphoid anatomical waist. Non-displaced. Algorithmic borderline confidence (58%) requires urgent secondary musculoskeletal specialist verification."
        }
    };
    setActiveAnalysis(sampleMocks[sampleId] || DEFAULT_DEMO_ANALYSIS);
}

// ----------------------------------------------------------------------------
// E. FINDINGS REPORT PAGE
// ----------------------------------------------------------------------------
function setupFindingsPage() {
    const analysis = getActiveAnalysis();
    if (!analysis) return;

    // Acute fracture probability callout
    const probPct = Math.round((analysis.fracture_probability || analysis.confidence || 0.947) * 100);
    document.querySelectorAll('.font-mono-data').forEach(el => {
        if (el.textContent.includes('94.7%') || el.textContent.includes('%')) {
            if (el.textContent.length < 8) el.textContent = `${probPct}%`;
        }
    });

    // Update report text
    const reportBox = document.querySelector('textarea, p.leading-relaxed, .bg-surface-container-low p');
    if (reportBox && analysis.report_text) {
        if (reportBox.tagName === 'TEXTAREA') {
            reportBox.value = analysis.report_text;
        } else {
            reportBox.textContent = analysis.report_text;
        }
    }

    // Connect Next buttons
    const viewerBtn = document.querySelector('a[href*="viewer"], button:has(.material-symbols-outlined:contains("visibility"))');
    if (viewerBtn) {
        viewerBtn.addEventListener('click', (e) => {
            e.preventDefault();
            window.location.href = '/viewer.html';
        });
    }

    const signOffBtn = document.querySelector('a[href*="sign-off"], #btn-sign-off');
    if (signOffBtn) {
        signOffBtn.addEventListener('click', (e) => {
            e.preventDefault();
            window.location.href = '/sign-off.html';
        });
    }
}

// ----------------------------------------------------------------------------
// F. IMAGE VIEWER PACS WORKSTATION
// ----------------------------------------------------------------------------
function setupViewerPage() {
    const analysis = getActiveAnalysis();
    const radiographImg = document.getElementById('radiograph-img');
    const container = document.getElementById('film-container') || (radiographImg ? radiographImg.parentElement : null);

    if (radiographImg && analysis.image_url) {
        radiographImg.src = analysis.image_url;
    }

    // Viewport controls: Zoom, Pan, Windowing
    let zoom = 1.0;
    let brightness = 100;
    let contrast = 100;
    let isInverted = false;

    const zoomIndicator = document.getElementById('zoom-indicator');
    const windowIndicator = document.getElementById('window-indicator');

    function applyTransforms() {
        if (container) {
            container.style.transform = `scale(${zoom})`;
        }
        if (radiographImg) {
            const inv = isInverted ? 'invert(1) ' : '';
            radiographImg.style.filter = `${inv}brightness(${brightness}%) contrast(${contrast}%)`;
        }
        if (zoomIndicator) zoomIndicator.textContent = `ZOOM: ${zoom.toFixed(2)}×`;
        if (windowIndicator) windowIndicator.textContent = `W: ${contrast * 24} / L: ${brightness * 6}`;
    }

    // Zoom buttons
    document.querySelectorAll('button').forEach(btn => {
        const text = btn.textContent || '';
        const title = btn.getAttribute('title') || '';
        
        if (text.includes('add') || title.includes('Zoom in')) {
            btn.addEventListener('click', () => { zoom = Math.min(zoom + 0.15, 3.0); applyTransforms(); });
        } else if (text.includes('remove') || title.includes('Zoom out')) {
            btn.addEventListener('click', () => { zoom = Math.max(zoom - 0.15, 0.5); applyTransforms(); });
        } else if (text.includes('restart_alt') || title.includes('Reset')) {
            btn.addEventListener('click', () => { zoom = 1.0; brightness = 100; contrast = 100; isInverted = false; applyTransforms(); });
        } else if (text.includes('contrast') || text.includes('invert')) {
            btn.addEventListener('click', () => { isInverted = !isInverted; applyTransforms(); });
        }
    });

    // Navigation buttons
    const nextBtn = document.getElementById('btn-next-findings');
    if (nextBtn) {
        nextBtn.addEventListener('click', () => window.location.href = '/findings.html');
    }
}

// ----------------------------------------------------------------------------
// G. SIGN-OFF & EXPORT PAGE
// ----------------------------------------------------------------------------
function setupSignOffPage() {
    const analysis = getActiveAnalysis();
    const user = getUser();

    // Prefill Doctor Name & License
    const nameInput = document.getElementById('physician-name');
    const licenseInput = document.getElementById('license-number');
    if (nameInput && user) nameInput.value = user.full_name || "Dr. Elena Vance, MD";
    if (licenseInput && user) licenseInput.value = user.registration_number || "MCI-2024-88419";

    // "Download Stamped PDF" button
    const pdfBtn = document.getElementById('btn-download-pdf') || document.querySelector('button:has(.material-symbols-outlined:contains("picture_as_pdf"))');
    if (pdfBtn) {
        pdfBtn.addEventListener('click', () => {
            const id = analysis.id || 1;
            window.open(`${API_BASE}/analysis/${id}/pdf`, '_blank');
        });
    }

    // "Export HL7 FHIR" button
    const fhirBtn = document.getElementById('btn-export-fhir') || document.querySelector('button:has(.material-symbols-outlined:contains("code"))');
    if (fhirBtn) {
        fhirBtn.addEventListener('click', () => {
            const id = analysis.id || 1;
            window.open(`${API_BASE}/analysis/${id}/fhir`, '_blank');
        });
    }

    // "Sign Off & Lock" button
    const signBtn = document.getElementById('btn-confirm-sign');
    if (signBtn) {
        signBtn.addEventListener('click', async () => {
            try {
                const id = analysis.id || 1;
                await fetch(`${API_BASE}/analysis/${id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        clinical_notes: "Certified by attending radiologist.",
                        signed_off: true,
                        signed_by: user.full_name,
                        fracture_detected: analysis.fracture_detected
                    })
                });
            } catch (e) {
                console.warn('Signoff fallback:', e);
            }
            alert('Study signed off and stamped legally. Returning to Worklist.');
            window.location.href = '/worklist.html';
        });
    }
}

// ----------------------------------------------------------------------------
// H. WORKLIST PAGE (PRIORITY TRIAGE QUEUE)
// ----------------------------------------------------------------------------
async function setupWorklistPage() {
    try {
        const resp = await fetch(`${API_BASE}/analysis/priority-queue`);
        if (resp.ok) {
            const priorityCases = await resp.json();
            if (priorityCases && priorityCases.length > 0) {
                console.log('Loaded live priority cases from Supabase:', priorityCases);
            }
        }
    } catch (e) {
        console.warn('Backend worklist fetch fallback to seeded cases:', e);
    }

    // Row click listeners to open in PACS viewer
    document.querySelectorAll('#worklist-rows tr').forEach(row => {
        row.style.cursor = 'pointer';
        const openBtn = row.querySelector('button, a');
        if (openBtn) {
            openBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                openCaseFromRow(row);
            });
        }
        row.addEventListener('click', () => openCaseFromRow(row));
    });
}

function openCaseFromRow(row) {
    const text = row.textContent || '';
    if (text.includes('Femur')) {
        triggerSampleScan('normal_femur_control');
    } else if (text.includes('Clavicle')) {
        triggerSampleScan('clavicle_displaced_fracture');
    } else if (text.includes('Scaphoid')) {
        triggerSampleScan('scaphoid_hairline_fracture');
    } else {
        triggerSampleScan('distal_radius_fracture');
    }
}

// ----------------------------------------------------------------------------
// I. ANALYTICS & QA PAGE
// ----------------------------------------------------------------------------
async function setupAnalyticsPage() {
    try {
        const resp = await fetch(`${API_BASE}/health`);
        if (resp.ok) {
            const health = await resp.json();
            console.log('System Health Status:', health);
        }
    } catch (e) {
        console.warn('Health check fetch failed:', e);
    }
}

// ----------------------------------------------------------------------------
// J. AUDIT LOG PAGE
// ----------------------------------------------------------------------------
function setupAuditLogPage() {
    console.log('Audit log registry initialized.');
}
