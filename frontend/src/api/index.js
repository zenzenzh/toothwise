import axios from 'axios';

const apiBase = (process.env.REACT_APP_API_URL || (window.location.hostname === 'localhost' ? 'http://localhost:8000' : `http://${window.location.hostname}:8000`)).replace(/\/$/, '');

// Friendly, consistent messaging for the response statuses every screen
// might hit, so individual pages don't each need to special-case these.
// Pages can still catch and show their own message for anything else.
//
// This never passes raw backend payloads straight to the UI: FastAPI's
// own validation errors (422) come back as an array of {loc, msg, type}
// objects, not a string, and other backends/proxies can return HTML error
// pages or stack traces. Only a plain string `detail` is ever surfaced
// directly; anything else falls back to a safe generic message.
function friendlyErrorMessage(err) {
  const status = err.response?.status;
  const detail = err.response?.data?.detail;

  if (!err.response) return 'Could not reach the server. Check your connection.';
  if (status === 400) return typeof detail === 'string' ? detail : 'Please check the information you entered.';
  if (status === 401) return 'Your session has expired. Please log in again.';
  if (status === 403) return "You don't have permission to do that.";
  if (status === 404) return 'The requested resource could not be found.';
  if (status === 422) {
    if (Array.isArray(detail) && detail.length > 0) {
      // Pydantic validation errors - pull out just the human message(s),
      // never the raw object/array, and never internal field paths.
      const msgs = detail.map(d => d?.msg).filter(Boolean);
      if (msgs.length) return msgs.slice(0, 2).join(' ');
    }
    return 'Please check the information you entered.';
  }
  if (status === 429) return 'Too many attempts. Please wait a moment and try again.';
  if (status >= 500) return 'Something went wrong on our end. Please try again later.';
  return typeof detail === 'string' ? detail : 'Something went wrong.';
}

const api = axios.create({ baseURL: apiBase + '/api' });

api.interceptors.request.use(cfg => {
  const t = localStorage.getItem('tw_token');
  if (t) cfg.headers.Authorization = 'Bearer ' + t;
  return cfg;
});

api.interceptors.response.use(r => r, err => {
  if (err.response?.status === 401) {
    const isLoginPage = window.location.pathname === '/login';
    const isLoginRequest = err.config?.url?.includes('/auth/login');
    if (!isLoginPage && !isLoginRequest) {
      // Only clear the staff session, not a patient session that might
      // also be active in the same browser (separate token/localStorage
      // keys by design - see the patient axios instance below).
      localStorage.removeItem('tw_token');
      localStorage.removeItem('tw_dentist');
      window.location.replace('/login');
    }
  }
  err.friendlyMessage = friendlyErrorMessage(err);
  return Promise.reject(err);
});

export const authAPI = {
  login: (d) => api.post('/auth/login', d),
  me: () => api.get('/auth/me'),
};

export const patientsAPI = {
  list: (s) => api.get('/patients', { params: { search: s || undefined } }),
  get: (id) => api.get('/patients/' + id),
  create: (d) => api.post('/patients', d),
  update: (id, d) => api.put('/patients/' + id, d),
  delete: (id) => api.delete('/patients/' + id),
  screenings: (id) => api.get('/patients/' + id + '/screenings'),
  riskTrend: (id) => api.get('/patients/' + id + '/risk-trend'),
};

// Fetches an image through an authenticated endpoint and hands back a
// local object URL, instead of a plain <img src="..."> pointed at a
// public path. <img> tags can't carry an Authorization header, and these
// are patient dental photos - there is no unauthenticated route for them
// (see app/routers/screenings.py get_screening_image /
// get_my_screening_image). Callers MUST revoke the returned URL
// (URL.revokeObjectURL) when done with it, typically in a useEffect
// cleanup, to avoid leaking memory across screening views.
async function fetchImageObjectUrl(client, path) {
  const res = await client.get(path, { responseType: 'blob' });
  return window.URL.createObjectURL(res.data);
}

// Backend runs detection synchronously inside a single multipart request -
// there is no separate "create" + "detect" step.
export const screeningsAPI = {
  create: (patientId, imageFile) => {
    const fm = new FormData();
    fm.append('file', imageFile);
    return api.post('/patients/' + patientId + '/screening', fm, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  get: (id) => api.get('/screenings/' + id),
  compare: (id) => api.get('/screenings/' + id + '/compare'),
  addNote: (id, body) => api.post('/screenings/' + id + '/notes', { body }),
  delete: (id) => api.delete('/screenings/' + id),
  imageObjectUrl: (id) => fetchImageObjectUrl(api, '/screenings/' + id + '/image'),
  // Auth is required for the PDF route, so a plain <a href> won't carry
  // the JWT - fetch as a blob (interceptor attaches the token) and hand
  // the caller an object URL + filename to trigger the download with.
  downloadReportPdf: async (id) => {
    const res = await api.get('/screenings/' + id + '/report/pdf', { responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
    return { url, filename: `toothwise_screening_${id}_report.pdf` };
  },
};

export const dentistsAPI = {
  list: (s) => api.get('/dentists', { params: { search: s || undefined } }),
  get: (id) => api.get('/dentists/' + id),
  create: (d) => api.post('/dentists', d),
  update: (id, d) => api.put('/dentists/' + id, d),
  delete: (id) => api.delete('/dentists/' + id),
  deactivate: (id) => api.post('/dentists/' + id + '/deactivate'),
  resetPassword: (id, newPassword) =>
    api.put('/dentists/' + id + '/password', { new_password: newPassword }),
};

export const dashboardAPI = {
  stats: () => api.get('/dashboard/summary'),
};

export const auditAPI = {
  list: (params) => api.get('/audit-logs', { params }),
};

export const chatbotAPI = {
  chat: (message, history = []) => {
    const url = process.env.REACT_APP_CHATBOT_URL || (process.env.NODE_ENV === 'production' ? '/api/chatbot' : apiBase + '/api/chatbot');
    return axios.post(url, {
    message,
    history: history.slice(-8).map(item => ({ role: item.from === 'bot' ? 'model' : 'user', content: item.text })),
    });
  },
};

// ---------- Patient portal (self-service) ----------
// Separate axios instance + token key from the staff `api` above, so a
// patient session and a staff (dentist/admin) session can't collide or
// overwrite each other, e.g. in the same browser.
const patientApi = axios.create({ baseURL: apiBase + '/api' });

patientApi.interceptors.request.use(cfg => {
  const t = localStorage.getItem('tw_patient_token');
  if (t) cfg.headers.Authorization = 'Bearer ' + t;
  return cfg;
});

patientApi.interceptors.response.use(r => r, err => {
  if (err.response?.status === 401) {
    const isPortalLogin = window.location.pathname === '/patient-portal';
    const isAuthRequest = err.config?.url?.includes('/auth/patient/');
    if (!isPortalLogin && !isAuthRequest) {
      localStorage.removeItem('tw_patient_token');
      localStorage.removeItem('tw_patient');
      window.location.replace('/patient-portal');
    }
  }
  err.friendlyMessage = friendlyErrorMessage(err);
  return Promise.reject(err);
});

export const patientAuthAPI = {
  register: (d) => patientApi.post('/auth/patient/register', d),
  login: (d) => patientApi.post('/auth/patient/login', d),
  me: () => patientApi.get('/auth/patient/me'),
};

export const patientScreeningsAPI = {
  mine: () => patientApi.get('/screenings/mine'),
  get: (id) => patientApi.get('/screenings/self/' + id),
  imageObjectUrl: (id) => fetchImageObjectUrl(patientApi, '/screenings/self/' + id + '/image'),
};

export default api;
