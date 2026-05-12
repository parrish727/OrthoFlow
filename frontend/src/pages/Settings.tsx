import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Link2, CheckCircle, AlertCircle, HelpCircle } from 'lucide-react'
import Tooltip from '../components/Tooltip'
import { api } from '../lib/api'

const integrations = [
  { name: 'QuickBooks Online', status: 'available', description: 'Sync approved invoices as Bills automatically', icon: '📗' },
  { name: 'Dentrix', status: 'available', description: 'Sync patient data and treatment plans', icon: '🦷' },
  { name: 'Email Forwarding', status: 'connected', description: 'invoices@yourpractice.orthoflow.ai', icon: '📧' },
  { name: 'Plaid (ACH Payments)', status: 'available', description: 'Pay vendors directly from OrthoFlow', icon: '🏦' },
]

export default function SettingsPage() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-[#f5f5f7]">
      <header className="bg-white/80 backdrop-blur-xl border-b border-gray-200/50 sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-4">
          <button onClick={() => navigate('/')} className="w-8 h-8 bg-gray-100 hover:bg-gray-200 rounded-lg flex items-center justify-center transition-colors">
            <ArrowLeft size={16} className="text-gray-600" />
          </button>
          <div>
            <h1 className="text-lg font-semibold text-gray-900">Settings</h1>
            <p className="text-xs text-gray-500">Practice configuration & integrations</p>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {/* Practice Info */}
        <div className="bg-white rounded-2xl border border-gray-200/80 p-6 shadow-sm mb-6">
          <h3 className="text-sm font-medium text-gray-800 mb-4">Practice Information</h3>
          <div className="mb-4">
            <label className="block text-xs text-gray-500 mb-2">Practice Logo</label>
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 bg-gray-100 rounded-xl flex items-center justify-center overflow-hidden">
                <span className="text-gray-400 text-xs">Logo</span>
              </div>
              <input
                type="file"
                accept="image/*"
                onChange={async (e) => {
                  const file = e.target.files?.[0]
                  if (!file) return
                  const form = new FormData()
                  form.append('file', file)
                  await fetch('https://api.orthoflowsolutions.com/api/v1/practices/logo', {
                    method: 'POST',
                    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
                    body: form,
                  })
                }}
                className="text-sm text-gray-500"
              />
            </div>
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Practice Name</label>
              <input type="text" defaultValue="Smith Orthodontics" className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">NPI Number</label>
              <input type="text" defaultValue="1234567890" className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Address</label>
              <input type="text" defaultValue="123 Main St, Charlotte, NC 28202" className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Phone</label>
              <input type="text" defaultValue="(704) 555-0123" className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm" />
            </div>
          </div>
          <button className="mt-4 px-5 py-2.5 bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium rounded-xl transition-colors">Save Changes</button>
        </div>

        {/* Approval Thresholds */}
        <div className="bg-white rounded-2xl border border-gray-200/80 p-6 shadow-sm mb-6">
          <div className="flex items-center gap-2 mb-4">
            <h3 className="text-sm font-medium text-gray-800">Approval Thresholds</h3>
            <Tooltip content="Set dollar amounts that determine who can approve invoices. Invoices above the threshold require the practice owner's approval.">
              <HelpCircle size={13} className="text-gray-400" />
            </Tooltip>
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Office Manager auto-approve up to</label>
              <div className="flex items-center gap-2">
                <span className="text-gray-400">$</span>
                <input type="number" defaultValue="500" className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm" />
              </div>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">AI auto-approve confidence above</label>
              <div className="flex items-center gap-2">
                <input type="number" defaultValue="95" className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm" />
                <span className="text-gray-400">%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Integrations */}
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-2">
            <Link2 size={16} className="text-gray-400" />
            <h3 className="text-sm font-medium text-gray-800">Integrations</h3>
          </div>
          <div className="divide-y divide-gray-50">
            {integrations.map(i => (
              <div key={i.name} className="px-6 py-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{i.icon}</span>
                  <div>
                    <p className="text-sm font-medium text-gray-800">{i.name}</p>
                    <p className="text-xs text-gray-400">{i.description}</p>
                  </div>
                </div>
                {i.status === 'connected' ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-50 text-emerald-700 text-xs font-medium rounded-full border border-emerald-200">
                    <CheckCircle size={12} /> Connected
                  </span>
                ) : (
                  <button
                    onClick={async () => {
                      if (i.name === 'QuickBooks Online') {
                        const res = await api.getInvoices().then(() => fetch('https://api.orthoflowsolutions.com/api/v1/integrations/quickbooks/connect', { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }))
                        if (res.ok) {
                          const data = await res.json()
                          window.location.href = data.auth_url
                        }
                      }
                    }}
                    className="px-4 py-2 text-xs font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors border border-blue-200"
                  >
                    Connect
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  )
}
