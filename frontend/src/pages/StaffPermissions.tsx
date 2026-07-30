import { useState, useEffect, useCallback } from 'react'
import { Shield, Users, ChevronDown, Check, X, Loader2, RotateCw } from 'lucide-react'
import { api } from '../lib/api'

interface PermissionDef {
  category: string
  label: string
  description: string
}

interface StaffMember {
  id: string
  full_name: string
  email: string
  role: string
  permissions: Record<string, boolean>
  has_overrides: boolean
}

interface PermissionSchema {
  categories: Record<string, string>
  permissions: Record<string, PermissionDef>
  role_templates: Record<string, string[]>
}

const ROLE_LABELS: Record<string, string> = {
  owner: 'Owner',
  doctor: 'Doctor',
  office_manager: 'Office Manager',
  dental_assistant: 'Dental Assistant',
  front_desk: 'Front Desk',
  bookkeeper: 'Bookkeeper',
}

const ROLE_COLORS: Record<string, string> = {
  owner: 'bg-teal-100 text-teal-700',
  doctor: 'bg-blue-100 text-blue-700',
  office_manager: 'bg-violet-100 text-violet-700',
  dental_assistant: 'bg-amber-100 text-amber-700',
  front_desk: 'bg-emerald-100 text-emerald-700',
  bookkeeper: 'bg-gray-100 text-gray-700',
}

export default function StaffPermissions() {
  const [schema, setSchema] = useState<PermissionSchema | null>(null)
  const [staff, setStaff] = useState<StaffMember[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedStaff, setSelectedStaff] = useState<string | null>(null)
  const [saving, setSaving] = useState<string | null>(null)
  const [showTemplateDropdown, setShowTemplateDropdown] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [schemaRes, staffRes] = await Promise.all([
        api.request('/api/v1/staff-permissions/schema'),
        api.request('/api/v1/staff-permissions/staff'),
      ])

      if (schemaRes.ok) {
        setSchema(await schemaRes.json())
      } else {
        const err = await schemaRes.json().catch(() => ({ detail: 'Access denied' }))
        setError(typeof err.detail === 'string' ? err.detail : 'Failed to load permission schema')
        setLoading(false)
        return
      }

      if (staffRes.ok) {
        const data = await staffRes.json()
        setStaff(data.staff || [])
      }
    } catch {
      setError('Connection error')
    }
    setLoading(false)
  }, [])

  useEffect(() => { loadData() }, [loadData])

  async function handleTogglePermission(userId: string, key: string, currentValue: boolean) {
    setSaving(key)
    try {
      const res = await api.request('/api/v1/staff-permissions/update', {
        method: 'PATCH',
        body: JSON.stringify({ user_id: userId, permission_key: key, granted: !currentValue }),
      })
      if (res.ok) {
        setStaff(prev =>
          prev.map(s => s.id === userId
            ? { ...s, permissions: { ...s.permissions, [key]: !currentValue }, has_overrides: true }
            : s
          )
        )
      }
    } catch { /* silent */ }
    setSaving(null)
  }

  async function handleApplyTemplate(userId: string, roleTemplate: string) {
    setSaving('template')
    setShowTemplateDropdown(null)
    try {
      const res = await api.request('/api/v1/staff-permissions/apply-template', {
        method: 'POST',
        body: JSON.stringify({ user_id: userId, role_template: roleTemplate }),
      })
      if (res.ok) {
        // Reload to get fresh effective permissions
        const staffRes = await api.request('/api/v1/staff-permissions/staff')
        if (staffRes.ok) {
          const data = await staffRes.json()
          setStaff(data.staff || [])
        }
      }
    } catch { /* silent */ }
    setSaving(null)
  }

  // Group permissions by category
  function groupedPermissions(): { category: string; label: string; keys: string[] }[] {
    if (!schema) return []
    const groups: Record<string, string[]> = {}
    for (const [key, def] of Object.entries(schema.permissions)) {
      if (!groups[def.category]) groups[def.category] = []
      groups[def.category].push(key)
    }
    return Object.entries(schema.categories).map(([catKey, catLabel]) => ({
      category: catKey,
      label: catLabel,
      keys: groups[catKey] || [],
    }))
  }

  const selectedMember = staff.find(s => s.id === selectedStaff)
  const groups = groupedPermissions()

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <Loader2 size={24} className="animate-spin text-teal-600 mb-3" />
        <p className="text-sm text-gray-500">Loading permissions…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <Shield size={32} className="text-red-400 mb-3" />
        <p className="text-sm text-red-600 font-medium">{error}</p>
        <p className="text-xs text-gray-500 mt-1">Only Owner, Doctor, and Office Manager can access this page.</p>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900">Staff Permissions</h2>
          <p className="text-sm text-gray-500 mt-0.5">Configure access levels for each team member</p>
        </div>
        <button
          onClick={loadData}
          className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <RotateCw size={14} />
          Refresh
        </button>
      </div>

      <div className="flex gap-6">
        {/* Staff List — Left Panel */}
        <div className="w-72 flex-shrink-0">
          <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100">
              <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
                <Users size={16} className="text-teal-600" />
                Staff Members
              </h3>
            </div>
            <div className="divide-y divide-gray-50">
              {staff.map(member => (
                <button
                  key={member.id}
                  onClick={() => setSelectedStaff(member.id)}
                  className={`w-full text-left px-4 py-3 transition-colors hover:bg-gray-50 ${
                    selectedStaff === member.id ? 'bg-teal-50 border-l-2 border-l-teal-500' : ''
                  }`}
                >
                  <p className="text-sm font-medium text-gray-900 truncate">{member.full_name}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${ROLE_COLORS[member.role] || 'bg-gray-100 text-gray-600'}`}>
                      {ROLE_LABELS[member.role] || member.role}
                    </span>
                    {member.has_overrides && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-orange-100 text-orange-700 font-medium">
                        Custom
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Permission Grid — Right Panel */}
        <div className="flex-1 min-w-0">
          {selectedMember ? (
            <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
              {/* Selected Staff Header */}
              <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
                <div>
                  <h3 className="text-base font-semibold text-gray-900">{selectedMember.full_name}</h3>
                  <p className="text-xs text-gray-500 mt-0.5">{selectedMember.email}</p>
                </div>
                {/* Apply Template Button */}
                <div className="relative">
                  <button
                    onClick={() => setShowTemplateDropdown(showTemplateDropdown === selectedMember.id ? null : selectedMember.id)}
                    className="flex items-center gap-2 px-3 py-2 text-xs font-medium text-teal-700 bg-teal-50 hover:bg-teal-100 rounded-lg transition-colors"
                  >
                    Apply Role Template
                    <ChevronDown size={12} />
                  </button>
                  {showTemplateDropdown === selectedMember.id && (
                    <div className="absolute right-0 top-full mt-1 w-48 bg-white border border-gray-200 rounded-xl shadow-lg z-10 py-1">
                      {Object.entries(ROLE_LABELS).map(([role, label]) => (
                        <button
                          key={role}
                          onClick={() => handleApplyTemplate(selectedMember.id, role)}
                          className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Permission Categories */}
              <div className="divide-y divide-gray-100">
                {groups.map(group => (
                  <div key={group.category} className="px-5 py-4">
                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                      {group.label}
                    </h4>
                    <div className="space-y-2">
                      {group.keys.map(key => {
                        const def = schema!.permissions[key]
                        const granted = selectedMember.permissions[key] ?? false
                        const isSaving = saving === key
                        // Check if this deviates from the role template
                        const templatePerms = schema!.role_templates[selectedMember.role] || []
                        const templateDefault = templatePerms.includes(key)
                        const isOverride = granted !== templateDefault

                        return (
                          <div
                            key={key}
                            className="flex items-center justify-between py-1.5 group"
                          >
                            <div className="min-w-0 flex-1 pr-4">
                              <div className="flex items-center gap-2">
                                <p className="text-sm text-gray-900">{def.label}</p>
                                {isOverride && (
                                  <span className="text-[9px] px-1 py-0.5 rounded bg-orange-50 text-orange-600 font-medium">
                                    override
                                  </span>
                                )}
                              </div>
                              <p className="text-xs text-gray-400 mt-0.5">{def.description}</p>
                            </div>
                            <button
                              onClick={() => handleTogglePermission(selectedMember.id, key, granted)}
                              disabled={isSaving}
                              className={`w-10 h-6 rounded-full relative transition-colors flex-shrink-0 ${
                                granted
                                  ? 'bg-teal-500'
                                  : 'bg-gray-200'
                              } ${isSaving ? 'opacity-50' : ''}`}
                              aria-label={`${granted ? 'Revoke' : 'Grant'} ${def.label}`}
                            >
                              <span
                                className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${
                                  granted ? 'left-[18px]' : 'left-0.5'
                                }`}
                              />
                            </button>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm flex flex-col items-center justify-center py-24">
              <Shield size={40} className="text-gray-300 mb-3" />
              <p className="text-sm font-medium text-gray-500">Select a staff member</p>
              <p className="text-xs text-gray-400 mt-1">Choose a team member from the left to configure their permissions</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
