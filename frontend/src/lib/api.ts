const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function request(path: string, options: RequestInit = {}) {
  const token = localStorage.getItem('token')
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      ...options.headers,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
    },
  })
  if (res.status === 401) {
    localStorage.removeItem('token')
    window.location.href = '/login'
  }
  return res
}

export const api = {
  login: (email: string, password: string) =>
    request('/api/v1/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  register: (data: { email: string; password: string; full_name: string; practice_name: string }) =>
    request('/api/v1/auth/register', { method: 'POST', body: JSON.stringify(data) }),
  getInvoices: () => request('/api/v1/invoices/'),
  getInvoice: (id: string) => request(`/api/v1/invoices/${id}`),
  uploadInvoice: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request('/api/v1/invoices/upload', { method: 'POST', body: form })
  },
  approveInvoice: (id: string) => request(`/api/v1/invoices/${id}/approve`, { method: 'POST' }),
  rejectInvoice: (id: string) => request(`/api/v1/invoices/${id}/reject`, { method: 'POST' }),
}
