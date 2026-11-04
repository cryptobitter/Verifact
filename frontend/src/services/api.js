const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export function getAuthToken() {
  return localStorage.getItem('verifact_token') || localStorage.getItem('fractoes_token') || '';
}

export function setAuthToken(token) {
  if (token) {
    localStorage.setItem('verifact_token', token);
  } else {
    localStorage.removeItem('verifact_token');
    localStorage.removeItem('fractoes_token');
  }
}

export function getCurrentUser() {
  const raw = localStorage.getItem('verifact_user') || localStorage.getItem('fractoes_user');
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
    localStorage.removeItem('fractoes_user');
  }
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
    let errorDetail = 'API request failed';
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || errJson.message || errorDetail;
    } catch {
      errorDetail = `Error ${res.status}: ${res.statusText}`;
    }
    throw new Error(errorDetail);
  }

  return res;
}

export const api = {
  // Auth
  async login(email, password) {
    const res = await request('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();
    setAuthToken(data.access_token);
    setCurrentUser(data.user);
    return data;
  },

  async signup(profile) {
    const res = await request('/auth/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profile)
    });
    return res.json();
  },

  async verifyOtp(email, otp_code) {
    const res = await request('/auth/verify-otp', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, otp_code })
    });
    return res.json();
  },

  async getProfile() {
    const res = await request('/auth/me');
    const user = await res.json();
    setCurrentUser(user);
    return user;
  },

  // Samples
  async getSamples() {
    const res = await request('/samples');
    return res.json();
  },

  // Analysis
  async analyzeSample(sampleId) {
    const res = await request(`/analyze/sample/${sampleId}`, {
      method: 'POST'
    });
    return res.json();
  },

  async analyzeFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await request('/analyze', {
      method: 'POST',
      body: formData
    });
    return res.json();
  },

  async analyzeDualView(formData) {
    const res = await request('/analyze/dual-view', {
      method: 'POST',
      body: formData
    });
    return res.json();
  },

  async sendEmailReport(id, dispatchData) {
    const res = await request(`/analysis/${id}/email`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(dispatchData)
    });
    return res.json();
  },

  async getFhirExport(id) {
    const res = await request(`/analysis/${id}/fhir`);
    return res.json();
  },

  async getHistory() {
    const res = await request('/analysis/history');
    return res.json();
  },

  async getAnalysis(id) {
    const res = await request(`/analysis/${id}`);
    return res.json();
  },

  async updateAndSignAnalysis(id, updateData) {
    const res = await request(`/analysis/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updateData)
    });
    return res.json();
  },

  async getPdfBlob(id) {
    const res = await request(`/analysis/${id}/pdf`);
    return res.blob();
  }
};
