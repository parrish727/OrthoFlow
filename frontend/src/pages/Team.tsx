import { useState, useEffect, useCallback } from 'react'
import { Users, UserPlus, Shield, Loader2, X, Trash2, ChevronDown } from 'lucide-react'
import { api } from '../lib/api'
import { useAuth } from '../hooks/useAuth'

interface StaffMember {
  id: string
  full_name: string
  email: string
  role: string
  is_active: boolean
  created_at: string | null
}

interface PendingInvite {
  id: string
  email: string
  role: string
  expires_at: string | null
  created_at: string | null
}

const ROLES = ['owner', 'doctor', 'office_manager', 'dental_assistant', 'front_desk', 'bookkeeper'] as const

const ROLE_LABELS: Record<string, string> = {
  owner: 'Owner',
  doctor: 'Doctor',
  office_manager: 'Office Manager',
  dental_assistant: 'Dental Assistant',
  front_desk: 'Front Desk',
  bookkeeper: 'Bookkeeper',
}

const ROLE_BADGE_COLORS: Record<string, string> = {
  owner: 'bg-teal-100 text-teal-700',
  doctor: 'bg-blue-100 text-blue-700',
  office_manager: 'bg-violet-100 text-violet-700',
  dental_assistant: 'bg-amber-100 text-amber-700',
  front_desk: 'bg-emerald-100 text-emerald-700',
  bookkeeper: 'bg-gray-100 text-gray-700',
}

export default function Team() {
  const { isOwner, isManager } = useAuth()
  const [staff, setStaff] = useState<StaffMember[]>([])
  const [invites, setInvites] = useState<PendingInvite[]>([])
  const [loading, setLoading] = useState(true)
  const [showInviteForm, setShowInviteForm] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('dental_assistant')
  const [inviting, setInviting] = useState(false)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  const [editingRole, setEditingRole] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    const [staffRes, invitesRes] = await Promise.all([
      api.getTeam(),
      api.getInvites(),
    ])
    if (staffRes.ok) {
      const data = await staffRes.json()
      setStaff(data.staff || [])
    }
    if (invitesRes.ok) {
      const data = await invitesRes.json()
      setInvites(data.invites || [])
    }
    setLoading(false)
  }, [])

  useEffect(() => { loadData() }, [loadData])

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault()
    if (!inviteEmail.trim()) return
    setInviting(true)
    setError('')
    setSuccessMsg('')

    const res = await api.inviteStaff({ email: inviteEmail, role: inviteRole })
    if (res.ok) {
      const data = await res.json()
      setSuccessMsg(`Invite sent to ${data.email}`)
      setInviteEmail('')
      setShowInviteForm(false)
      loadData()
    } else {
      const err = await res.json().catch(() => ({ detail: 'Failed to send invite' }))
      setError(err.detail || 'Failed to send invite')
    }
    setInviting(false)
  }

  async function handleChangeRole(userId: string, newRole: string) {
    setError('')
    const res = await api.changeRole(userId, newRole)
    if (res.ok) {
      setEditingRole(null)
      loadData()
    } else {
      const err = await res.json().catch(() => ({ detail: 'Failed to change role' }))
      setError(err.detail || 'Failed to change role')
    }
  }

  async function handleDeactivate(userId: string) {
    if (!confirm('Are you sure you want to deactivate this staff member?')) return
    setError('')
    const res = await api.deactivateStaff(userId)
    if (res.ok) {
      loadData()
    } else {
      const err = await res.json().catch(() => ({ detail: 'Failed to deactivate' }))
      setError(err.detail || 'Failed to deactivate')
    }
  }

  async function handleRevokeInvite(inviteId: string) {
    if (!confirm('Revoke this invite?')) return
    setError('')
    const res = await api.revokeInvite(inviteId)
    if (res.ok) {
      loadData()
    } else {
      const err = await res.json().catch(() => ({ detail: 'Failed to revoke invite' }))
      setError(err.detail || 'Failed to revoke invite')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-6 w-6 animate-spin text-teal-600" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Users className="h-6 w-6 text-teal-600" />
          <h1 className="text-xl font-bold text-gray-900">Team Management</h1>
        </div>
        {(isOwner || isManager) && (
          <button
            onClick={() => setShowInviteForm(true)}
            className="flex items-center gap-2 px-4 py-2 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors"
          >
            <UserPlus className="h-4 w-4" />
            Invite Staff
          </button>
        )}
      </div>

      {/* Messages */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}
      {successMsg && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm">
          {successMsg}
        </div>
      )}

      {/* Invite Form Modal */}
      {showInviteForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/20" onClick={() => setShowInviteForm(false)} />
          <div className="relative bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
            <button
              onClick={() => setShowInviteForm(false)}
              className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
            >
              <X className="h-5 w-5" />
            </button>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Invite Team Member</h2>
            <form onSubmit={handleInvite} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input
                  type="email"
                  value={inviteEmail}
                  onChange={e => setInviteEmail(e.target.value)}
                  placeholder="staff@example.com"
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
                <select
                  value={inviteRole}
                  onChange={e => setInviteRole(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
                >
                  {ROLES.filter(r => r !== 'owner').map(r => (
                    <option key={r} value={r}>{ROLE_LABELS[r]}</option>
                  ))}
                </select>
              </div>
              <button
                type="submit"
                disabled={inviting}
                className="w-full py-2 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
              >
                {inviting && <Loader2 className="h-4 w-4 animate-spin" />}
                Send Invite
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Staff Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100">
          <h2 className="text-sm font-semibold text-gray-900">Staff Members ({staff.length})</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600">
              <tr>
                <th className="text-left px-5 py-3 font-medium">Name</th>
                <th className="text-left px-5 py-3 font-medium">Email</th>
                <th className="text-left px-5 py-3 font-medium">Role</th>
                <th className="text-left px-5 py-3 font-medium">Status</th>
                <th className="text-left px-5 py-3 font-medium">Joined</th>
                {(isOwner || isManager) && (
                  <th className="text-right px-5 py-3 font-medium">Actions</th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {staff.map(member => (
                <tr key={member.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-medium text-gray-900">{member.full_name}</td>
                  <td className="px-5 py-3 text-gray-600">{member.email}</td>
                  <td className="px-5 py-3">
                    {isOwner && editingRole === member.id ? (
                      <select
                        value={member.role}
                        onChange={e => handleChangeRole(member.id, e.target.value)}
                        onBlur={() => setEditingRole(null)}
                        autoFocus
                        className="px-2 py-1 border border-gray-300 rounded text-xs focus:ring-2 focus:ring-teal-500 outline-none"
                      >
                        {ROLES.map(r => (
                          <option key={r} value={r}>{ROLE_LABELS[r]}</option>
                        ))}
                      </select>
                    ) : (
                      <button
                        onClick={() => isOwner && setEditingRole(member.id)}
                        disabled={!isOwner}
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${ROLE_BADGE_COLORS[member.role] || 'bg-gray-100 text-gray-700'} ${isOwner ? 'cursor-pointer hover:opacity-80' : 'cursor-default'}`}
                      >
                        {ROLE_LABELS[member.role] || member.role}
                        {isOwner && <ChevronDown className="h-3 w-3" />}
                      </button>
                    )}
                  </td>
                  <td className="px-5 py-3">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${member.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                      {member.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-gray-500">
                    {member.created_at ? new Date(member.created_at).toLocaleDateString() : '—'}
                  </td>
                  {(isOwner || isManager) && (
                    <td className="px-5 py-3 text-right">
                      {member.is_active && (
                        <button
                          onClick={() => handleDeactivate(member.id)}
                          className="text-xs text-red-600 hover:text-red-800 font-medium"
                        >
                          Deactivate
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
              {staff.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-gray-500">
                    No team members yet. Invite staff to get started.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pending Invites */}
      {invites.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100">
            <h2 className="text-sm font-semibold text-gray-900">Pending Invites ({invites.length})</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-600">
                <tr>
                  <th className="text-left px-5 py-3 font-medium">Email</th>
                  <th className="text-left px-5 py-3 font-medium">Role</th>
                  <th className="text-left px-5 py-3 font-medium">Expires</th>
                  <th className="text-left px-5 py-3 font-medium">Sent</th>
                  <th className="text-right px-5 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {invites.map(inv => (
                  <tr key={inv.id} className="hover:bg-gray-50">
                    <td className="px-5 py-3 text-gray-900">{inv.email}</td>
                    <td className="px-5 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${ROLE_BADGE_COLORS[inv.role] || 'bg-gray-100 text-gray-700'}`}>
                        {ROLE_LABELS[inv.role] || inv.role}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-gray-500">
                      {inv.expires_at ? new Date(inv.expires_at).toLocaleDateString() : '—'}
                    </td>
                    <td className="px-5 py-3 text-gray-500">
                      {inv.created_at ? new Date(inv.created_at).toLocaleDateString() : '—'}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <button
                        onClick={() => handleRevokeInvite(inv.id)}
                        className="inline-flex items-center gap-1 text-xs text-red-600 hover:text-red-800 font-medium"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        Revoke
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
