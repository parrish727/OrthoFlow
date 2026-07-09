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
  getPractice: () => request('/api/v1/practices/me'),
  uploadInvoice: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request('/api/v1/invoices/upload', { method: 'POST', body: form })
  },
  approveInvoice: (id: string) => request(`/api/v1/invoices/${id}/approve`, { method: 'POST' }),
  rejectInvoice: (id: string) => request(`/api/v1/invoices/${id}/reject`, { method: 'POST' }),

  // Clinical — Phase 1
  getPatients: (params: { search?: string; status?: string; page?: number }) => {
    const q = new URLSearchParams()
    if (params.search) q.set('search', params.search)
    if (params.status) q.set('status', params.status)
    if (params.page) q.set('page', String(params.page))
    return request(`/api/v1/patients?${q.toString()}`)
  },
  getPatient: (id: string) => request(`/api/v1/patients/${id}`),
  updatePatient: (id: string, data: Record<string, unknown>) =>
    request(`/api/v1/patients/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  getSchedule: (date: string) => request(`/api/v1/schedule?schedule_date=${date}`),
  getAppointments: (params: { patient_id?: string; start_date?: string; end_date?: string }) => {
    const q = new URLSearchParams()
    if (params.patient_id) q.set('patient_id', params.patient_id)
    if (params.start_date) q.set('start_date', params.start_date)
    if (params.end_date) q.set('end_date', params.end_date)
    return request(`/api/v1/appointments?${q.toString()}`)
  },
  getPatientNotes: (patientId: string) => request(`/api/v1/patients/${patientId}/notes`),
  createNote: (data: { patient_id: string; note_text: string; appointment_id?: string }) =>
    request('/api/v1/notes', { method: 'POST', body: JSON.stringify(data) }),
  getToothChart: (patientId: string) => request(`/api/v1/patients/${patientId}/tooth-chart`),
  updateToothChart: (patientId: string, data: Record<string, unknown>) =>
    request(`/api/v1/patients/${patientId}/tooth-chart`, { method: 'PUT', body: JSON.stringify(data) }),

  // Schedule — drag-and-drop
  getDentalAssistants: () => request('/api/v1/dental-assistants'),
  updateAppointment: (id: string, data: Record<string, unknown>) =>
    request(`/api/v1/appointments/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

  // AI Assistant
  aiNoteAssist: (data: { patient_id: string; raw_input: string; appointment_type?: string }) =>
    request('/api/v1/ai/notes/assist', { method: 'POST', body: JSON.stringify(data) }),
  aiPrepBrief: (appointmentId: string) =>
    request('/api/v1/ai/appointments/prep', { method: 'POST', body: JSON.stringify({ appointment_id: appointmentId }) }),

  // Finance & Insurance — Phase 2
  getLedger: (patientId: string) => request(`/api/v1/finance/ledger/${patientId}`),
  getLedgerSummary: (patientId: string) => request(`/api/v1/finance/ledger/${patientId}/summary`),
  postLedgerEntry: (data: Record<string, unknown>) =>
    request('/api/v1/finance/ledger', { method: 'POST', body: JSON.stringify(data) }),
  getInsurancePlans: (patientId: string) => request(`/api/v1/finance/insurance/${patientId}`),
  addInsurancePlan: (data: Record<string, unknown>) =>
    request('/api/v1/finance/insurance', { method: 'POST', body: JSON.stringify(data) }),
  checkEligibility: (data: Record<string, unknown>) =>
    request('/api/v1/eligibility/check', { method: 'POST', body: JSON.stringify(data) }),
  getClaims: (params?: { status?: string }) => {
    const q = new URLSearchParams()
    if (params?.status) q.set('status', params.status)
    return request(`/api/v1/claims/?${q.toString()}`)
  },
  getClaim: (id: string) => request(`/api/v1/claims/${id}`),
  submitClaim: (id: string) => request(`/api/v1/claims/${id}/submit`, { method: 'PATCH' }),
  aiDenialReview: (data: Record<string, unknown>) =>
    request('/api/v1/ai/claims/denial-review', { method: 'POST', body: JSON.stringify(data) }),
  getPaymentPostings: () => request('/api/v1/payments/postings'),
  createPaymentPosting: (data: Record<string, unknown>) =>
    request('/api/v1/payments/postings', { method: 'POST', body: JSON.stringify(data) }),
  importEra: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request('/api/v1/payments/era/import', { method: 'POST', body: form })
  },

  // Generic request (for flexibility)
  request: (path: string, options?: RequestInit) => request(path, options),

  // Communications — Phase 3
  getTemplates: () => request('/api/v1/communications/templates'),
  createTemplate: (data: { name: string; channel: string; body: string }) =>
    request('/api/v1/communications/templates', { method: 'POST', body: JSON.stringify(data) }),
  sendMessage: (data: { patient_id: string; template_id?: string; channel: string; custom_body?: string }) =>
    request('/api/v1/communications/reminders/send-now', { method: 'POST', body: JSON.stringify(data) }),
  getScheduledMessages: () => request('/api/v1/communications/reminders/scheduled'),
  cancelScheduledMessage: (id: string) =>
    request(`/api/v1/communications/reminders/scheduled/${id}`, { method: 'DELETE' }),
  getMessageLog: (params?: Record<string, string>) => {
    const q = new URLSearchParams()
    if (params) Object.entries(params).forEach(([k, v]) => { if (v) q.set(k, v) })
    return request(`/api/v1/communications/messages?${q.toString()}`)
  },
  getMessageStats: () => request('/api/v1/communications/messages/stats'),

  // Imaging — Phase 4a
  uploadImage: (formData: FormData) =>
    request('/api/v1/imaging/upload', { method: 'POST', body: formData }),
  getPatientImages: (patientId: string, params?: { image_type?: string; start_date?: string; end_date?: string }) => {
    const q = new URLSearchParams()
    if (params?.image_type) q.set('image_type', params.image_type)
    if (params?.start_date) q.set('start_date', params.start_date)
    if (params?.end_date) q.set('end_date', params.end_date)
    return request(`/api/v1/imaging/patients/${patientId}?${q.toString()}`)
  },
  getImageViewUrl: async (imageId: string): Promise<string> => {
    const res = await request(`/api/v1/imaging/view/${imageId}`)
    const blob = await res.blob()
    return URL.createObjectURL(blob)
  },
  deleteImage: (imageId: string) =>
    request(`/api/v1/imaging/${imageId}`, { method: 'DELETE' }),
  getImagingAlerts: (params?: { status?: string }) => {
    const q = new URLSearchParams()
    if (params?.status) q.set('status', params.status)
    return request(`/api/v1/imaging/alerts?${q.toString()}`)
  },
  generateImagingAlerts: () =>
    request('/api/v1/imaging/alerts/generate', { method: 'POST' }),
  dismissAlert: (id: string) =>
    request(`/api/v1/imaging/alerts/${id}/dismiss`, { method: 'PATCH' }),
  completeAlert: (id: string) =>
    request(`/api/v1/imaging/alerts/${id}/complete`, { method: 'PATCH' }),

  // AI Intelligence — Phase 5
  aiBatchInsights: (data: { patient_ids: string[] }) =>
    request('/api/v1/ai/intelligence/batch-insights', { method: 'POST', body: JSON.stringify(data) }),
  aiTimelinePredict: (patientId: string) =>
    request(`/api/v1/ai/timeline/predict/${patientId}`, { method: 'POST' }),
  aiDenialPatterns: () =>
    request('/api/v1/ai/denial-patterns/analyze'),
  aiBenchmarks: () =>
    request('/api/v1/ai/timeline/benchmarks'),
  aiSummarize: (patientId: string) =>
    request(`/api/v1/ai/intelligence/summarize/${patientId}`, { method: 'POST' }),
  aiReferralLetter: (data: { patient_id: string; referral_to: { name: string; specialty: string; address: string }; reason: string }) =>
    request('/api/v1/ai/referrals/generate-letter', { method: 'POST', body: JSON.stringify(data) }),
  aiImagingReasoning: (patientId: string) =>
    request(`/api/v1/ai/referrals/imaging-reasoning/${patientId}`, { method: 'POST' }),
  aiNextVisit: (patientId: string) =>
    request(`/api/v1/ai/intelligence/next-visit/${patientId}`, { method: 'POST' }),
}
