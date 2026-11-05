const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export function getAuthToken() {
  let token = localStorage.getItem('verifact_token');
  if (!token) {
    const legacy = localStorage.getItem('fractoes_token');
    if (legacy) {
      token = legacy;
      localStorage.setItem('verifact_token', legacy);
      localStorage.removeItem('fractoes_token');
    }
  }
  return token || '';
}

export function setAuthToken(token) {
  if (token) {
    localStorage.setItem('verifact_token', token);
  } else {
    localStorage.removeItem('verifact_token');
  }
  localStorage.removeItem('fractoes_token');
}

export function getCurrentUser() {
  let raw = localStorage.getItem('verifact_user');
  if (!raw) {
    const legacy = localStorage.getItem('fractoes_user');
    if (legacy) {
      raw = legacy;
      localStorage.setItem('verifact_user', legacy);
      localStorage.removeItem('fractoes_user');
    }
  }
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function setCurrentUser(user) {
  if (user) {
    localStorage.setItem('verifact_user', JSON.stringify(user));
  } else {
    localStorage.removeItem('verifact_user');
  }
  localStorage.removeItem('fractoes_user');
}

async function request(endpoint, options = {}) {
  const token = getAuthToken();
  const headers = {
    ...(options.headers || {})
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || errData.message || `Request failed with status ${res.status}`);
  }

  return res.json();
}

export const api = {
  // Auth
  async login(email, password) {
    const res = await request('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    setAuthToken(res.access_token);
    setCurrentUser(res.user);
    return res;
  },

  async signup(payload) {
    return request('/auth/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
  },

  async verifyOtp(email, otp_code) {
    return request('/auth/verify-otp', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, otp_code })
    });
  },

  async getProfile() {
    return request('/auth/me');
  },

  async updateProfile(payload) {
    return request('/auth/profile', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
  },

  // Analyses
  async getSamples() {
    return request('/samples');
  },

  async analyzeSample(sampleId) {
    return request(`/analyze/sample/${sampleId}`, { method: 'POST' });
  },

  async uploadAndAnalyze(file) {
    const formData = new FormData();
    formData.append('file', file);
    return request('/analyze', {
      method: 'POST',
      body: formData
    });
  },

  async uploadDualView(apFile, lateralFile, clinicalMeta = {}) {
    const formData = new FormData();
    formData.append('ap_file', apFile);
    if (lateralFile) {
      formData.append('lateral_file', lateralFile);
    }
    if (clinicalMeta.patient_id) formData.append('patient_id', clinicalMeta.patient_id);
    if (clinicalMeta.patient_age) formData.append('patient_age', clinicalMeta.patient_age);
    if (clinicalMeta.patient_gender) formData.append('patient_gender', clinicalMeta.patient_gender);
    if (clinicalMeta.mechanism_of_injury) formData.append('mechanism_of_injury', clinicalMeta.mechanism_of_injury);

    return request('/analyze/dual-view', {
      method: 'POST',
      body: formData
    });
  },

  async updateAnalysis(id, payload) {
    return request(`/analysis/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
  },

  async getHistory() {
    return request('/analysis/history');
  },

  async getPriorityReviewQueue() {
    return request('/analysis/priority-queue');
  },

  async uploadAndAnalyzeAsync(file) {
    const formData = new FormData();
    formData.append('file', file);
    return request('/analyze/async', {
      method: 'POST',
      body: formData
    });
  },

  async getJobStatus(jobId) {
    return request(`/jobs/${jobId}`);
  },

  async getAnalysis(id) {
    return request(`/analysis/${id}`);
  },

  async getFhirReport(id) {
    return request(`/analysis/${id}/fhir`);
  },

  async sendEmailReport(id, payload) {
    return request(`/analysis/${id}/email`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
  },

  getPdfUrl(id) {
    return `${API_BASE}/analysis/${id}/pdf`;
  }
};
