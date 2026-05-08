import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Shield, Users, HelpCircle } from 'lucide-react'
import Tooltip from '../components/Tooltip'

const teamMembers = [
  { name: 'Dr. Jane Smith', email: 'jane@smithortho.com', role: 'Owner', status: 'Active' },
  { name: 'Maria Garcia', email: 'maria@smithortho.com', role: 'Office Manager', status: 'Active' },
  { name: 'Tom Wilson', email: 'tom@smithortho.com', role: 'Bookkeeper', status: 'Active' },
]

const roleDescriptions: Record<string, string> = {
  Owner: 'Full access — approve all invoices, manage team, view analytics, configure settings',
  'Office Manager': 'Upload invoices, approve up to threshold, view dashboard',
  Bookkeeper: 'View-only access, export reports for accountant',
}

export default function Account() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-[#f5f5f7]">
      <header className="bg-white/80 backdrop-blur-xl border-b border-gray-200/50 sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-4">
          <button onClick={() => navigate('/')} className="w-8 h-8 bg-gray-100 hover:bg-gray-200 rounded-lg flex items-center justify-center transition-colors">
            <ArrowLeft size={16} className="text-gray-600" />
          </button>
          <div>
            <h1 className="text-lg font-semibold text-gray-900">Account</h1>
            <p className="text-xs text-gray-500">Profile & team management</p>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* Profile */}
        <div className="bg-white rounded-2xl border border-gray-200/80 p-6 shadow-sm mb-6">
          <h3 className="text-sm font-medium text-gray-800 mb-4">Your Profile</h3>
          <div className="flex items-center gap-4 mb-6">
            <div className="w-14 h-14 bg-blue-100 rounded-full flex items-center justify-center">
              <span className="text-xl font-semibold text-blue-600">JS</span>
            </div>
            <div>
              <p className="font-medium text-gray-900">Dr. Jane Smith</p>
              <p className="text-sm text-gray-500">jane@smithortho.com</p>
              <p className="text-xs text-blue-600 mt-0.5">Owner</p>
            </div>
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Full Name</label>
              <input type="text" defaultValue="Dr. Jane Smith" className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Email</label>
              <input type="email" defaultValue="jane@smithortho.com" className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm" />
            </div>
          </div>
          <button className="mt-4 px-5 py-2.5 bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium rounded-xl transition-colors">Update Profile</button>
        </div>

        {/* Team */}
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden mb-6">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Users size={16} className="text-gray-400" />
              <h3 className="text-sm font-medium text-gray-800">Team Members</h3>
              <Tooltip content="Each team member gets role-based access. Only owners can add/remove team members.">
                <HelpCircle size={13} className="text-gray-400" />
              </Tooltip>
            </div>
            <button className="px-4 py-2 text-xs font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors border border-blue-200">
              Invite Member
            </button>
          </div>
          <div className="divide-y divide-gray-50">
            {teamMembers.map(m => (
              <div key={m.email} className="px-6 py-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 bg-gray-100 rounded-full flex items-center justify-center">
                    <span className="text-xs font-medium text-gray-600">{m.name.split(' ').map(n => n[0]).join('')}</span>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-800">{m.name}</p>
                    <p className="text-xs text-gray-400">{m.email}</p>
                  </div>
                </div>
                <Tooltip content={roleDescriptions[m.role]}>
                  <span className="px-3 py-1 bg-gray-100 text-gray-600 text-xs font-medium rounded-full cursor-help">
                    {m.role}
                  </span>
                </Tooltip>
              </div>
            ))}
          </div>
        </div>

        {/* Security */}
        <div className="bg-white rounded-2xl border border-gray-200/80 p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <Shield size={16} className="text-gray-400" />
            <h3 className="text-sm font-medium text-gray-800">Security</h3>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between py-2">
              <div>
                <p className="text-sm text-gray-700">Two-Factor Authentication</p>
                <p className="text-xs text-gray-400">Add an extra layer of security to your account</p>
              </div>
              <button className="px-4 py-2 text-xs font-medium text-emerald-600 bg-emerald-50 rounded-lg border border-emerald-200">Enabled</button>
            </div>
            <div className="flex items-center justify-between py-2">
              <div>
                <p className="text-sm text-gray-700">Change Password</p>
                <p className="text-xs text-gray-400">Last changed 30 days ago</p>
              </div>
              <button className="px-4 py-2 text-xs font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg border border-blue-200 transition-colors">Change</button>
            </div>
            <div className="flex items-center justify-between py-2">
              <div>
                <p className="text-sm text-gray-700">Audit Log</p>
                <p className="text-xs text-gray-400">View all account activity (HIPAA compliant)</p>
              </div>
              <button className="px-4 py-2 text-xs font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg border border-blue-200 transition-colors">View Log</button>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
