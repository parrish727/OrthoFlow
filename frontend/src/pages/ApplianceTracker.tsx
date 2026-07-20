import { useState, useEffect, useCallback } from 'react'
import {
  Building2, Plus, Edit3, Phone, Mail, Globe, Clock, AlertTriangle,
  CheckCircle2, Package, Truck, ArrowRight, Filter, RefreshCw, X,
  FlaskConical, BarChart3, ExternalLink,
} from 'lucide-react'
import { api } from '../lib/api'

// ── Types ────────────────────────────────────────────────────────────────────

interface Lab {
  id: string
  name: string
  contact_name: string | null
  phone: string | null
  email: string | null
  address: string | null
  website: string | null
  account_number: string | null
  avg_turnaround_days: number
  notes: string | null
  is_active: boolean
}

interface Prescription {
  id: string
  patient_id: string
  lab_id: string
  lab_name: string | null
  appliance_type: string
  appliance_name: string
  arch: string
  status: string
  priority: string
  date_prescribed: string
  expected_delivery_date: string | null
  tracking_number: string | null
  is_remake: boolean
  lab_fee: number | null
}

interface Summary {
  status_counts: Record<string, number>
  overdue_count: number
  due_this_week: number
  total_active: number
}

interface QualityMetrics {
  lab_name: string
  total_orders: number
  completed_orders: number
  remake_count: number
  remake_rate: number
  avg_turnaround_actual: number | null
  on_time_rate: number
  total_spend: number
}

// ── Constants ────────────────────────────────────────────────────────────────

const STATUS_LABELS: Record<string, string> = {
  draft: 'Draft',
  submitted: 'Sent to Lab',
  received_by_lab: 'At Lab',
  in_fabrication: 'Fabricating',
  shipped: 'Shipped',
  received: 'Received',
  quality_check: 'QC Check',
  placed: 'Placed',
  rejected: 'Rejected',
  cancelled: 'Cancelled',
}

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  submitted: 'bg-blue-100 text-blue-700',
  received_by_lab: 'bg-indigo-100 text-indigo-700',
  in_fabrication: 'bg-purple-100 text-purple-700',
  shipped: 'bg-amber-100 text-amber-700',
  received: 'bg-emerald-100 text-emerald-700',
  quality_check: 'bg-cyan-100 text-cyan-700',
  placed: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-700',
  cancelled: 'bg-gray-100 text-gray-500',
}

const APPLIANCE_TYPES: Record<string, string> = {
  expander: 'Expander',
  retainer: 'Retainer',
  aligner: 'Aligner',
  space_maintainer: 'Space Maintainer',
  herbst: 'Herbst',
  mara: 'MARA',
  headgear: 'Headgear',
  splint: 'Splint',
  positioner: 'Positioner',
  spring_aligner: 'Spring Aligner',
  habit_breaker: 'Habit Breaker',
  surgical_splint: 'Surgical Splint',
  indirect_bond_tray: 'IDB Tray',
  other: 'Other',
}

type TabView = 'tracker' | 'labs'

// ── Component ────────────────────────────────────────────────────────────────

export default function ApplianceTracker() {
  const [activeTab, setActiveTab] = useState<TabView>('tracker')
  const [labs, setLabs] = useState<Lab[]>([])
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [showLabModal, setShowLabModal] = useState(false)
  const [editingLab, setEditingLab] = useState<Lab | null>(null)
  const [showMetrics, setShowMetrics] = useState<QualityMetrics | null>(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [labsRes, rxRes, summaryRes] = await Promise.all([
        fetch_api('/api/appliances/labs'),
        fetch_api(`/api/appliances/prescriptions${statusFilter ? `?status=${statusFilter}` : ''}`),
        fetch_api('/api/appliances/summary'),
      ])
      setLabs(labsRes)
      setPrescriptions(rxRes)
      setSummary(summaryRes)
    } catch (e) {
      console.error('Failed to fetch appliance data:', e)
    }
    setLoading(false)
  }, [statusFilter])

  useEffect(() => { fetchData() }, [fetchData])

  const isOverdue = (rx: Prescription): boolean => {
    if (!rx.expected_delivery_date) return false
    if (['placed', 'received', 'quality_check', 'rejected', 'cancelled'].includes(rx.status)) return false
    return new Date(rx.expected_delivery_date) < new Date()
  }

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Lab & Appliances</h1>
          <p className="text-sm text-gray-500 mt-1">Track prescriptions from order to placement</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={fetchData} className="p-2 rounded-lg hover:bg-gray-100 transition-colors" title="Refresh">
            <RefreshCw className="h-4 w-4 text-gray-500" />
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          <SummaryCard label="Active Orders" value={summary.total_active} icon={Package} color="text-blue-600" />
          <SummaryCard label="Overdue" value={summary.overdue_count} icon={AlertTriangle} color="text-red-600" />
          <SummaryCard label="Due This Week" value={summary.due_this_week} icon={Truck} color="text-amber-600" />
          <SummaryCard label="Completed" value={summary.status_counts.placed || 0} icon={CheckCircle2} color="text-green-600" />
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-gray-200 mb-6">
        <TabButton active={activeTab === 'tracker'} onClick={() => setActiveTab('tracker')} icon={Package} label="Appliance Tracker" />
        <TabButton active={activeTab === 'labs'} onClick={() => setActiveTab('labs')} icon={Building2} label="Lab Vendors" />
      </div>

      {/* Content */}
      {activeTab === 'tracker' ? (
        <TrackerView
          prescriptions={prescriptions}
          statusFilter={statusFilter}
          setStatusFilter={setStatusFilter}
          isOverdue={isOverdue}
          onRefresh={fetchData}
        />
      ) : (
        <LabsView
          labs={labs}
          onAdd={() => { setEditingLab(null); setShowLabModal(true) }}
          onEdit={(lab) => { setEditingLab(lab); setShowLabModal(true) }}
          onViewMetrics={async (lab) => {
            const metrics = await fetch_api(`/api/appliances/labs/${lab.id}/metrics`)
            setShowMetrics(metrics)
          }}
        />
      )}

      {/* Lab Modal */}
      {showLabModal && (
        <LabFormModal
          lab={editingLab}
          onClose={() => setShowLabModal(false)}
          onSave={async (data) => {
            if (editingLab) {
              await fetch_api(`/api/appliances/labs/${editingLab.id}`, 'PATCH', data)
            } else {
              await fetch_api('/api/appliances/labs', 'POST', data)
            }
            setShowLabModal(false)
            fetchData()
          }}
        />
      )}

      {/* Metrics Modal */}
      {showMetrics && (
        <MetricsModal metrics={showMetrics} onClose={() => setShowMetrics(null)} />
      )}
    </div>
  )
}

// ── Sub-Components ───────────────────────────────────────────────────────────

function SummaryCard({ label, value, icon: Icon, color }: { label: string; value: number; icon: typeof Package; color: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500">{label}</span>
        <Icon className={`h-5 w-5 ${color}`} />
      </div>
      <p className={`text-2xl font-bold mt-1 ${color}`}>{value}</p>
    </div>
  )
}

function TabButton({ active, onClick, icon: Icon, label }: { active: boolean; onClick: () => void; icon: typeof Package; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
        active ? 'border-teal-600 text-teal-700' : 'border-transparent text-gray-500 hover:text-gray-700'
      }`}
    >
      <Icon className="h-4 w-4" />
      {label}
    </button>
  )
}

function TrackerView({ prescriptions, statusFilter, setStatusFilter, isOverdue, onRefresh }: {
  prescriptions: Prescription[]
  statusFilter: string
  setStatusFilter: (s: string) => void
  isOverdue: (rx: Prescription) => boolean
  onRefresh: () => void
}) {
  return (
    <div>
      {/* Status Filters */}
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <Filter className="h-4 w-4 text-gray-400" />
        <FilterPill label="All" active={!statusFilter} onClick={() => setStatusFilter('')} />
        {['submitted', 'received_by_lab', 'in_fabrication', 'shipped', 'received', 'placed'].map(s => (
          <FilterPill key={s} label={STATUS_LABELS[s] || s} active={statusFilter === s} onClick={() => setStatusFilter(s)} />
        ))}
      </div>

      {/* Prescriptions Table */}
      {prescriptions.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <Package className="h-12 w-12 mx-auto mb-3 opacity-50" />
          <p className="font-medium">No appliance orders yet</p>
          <p className="text-sm mt-1">Create a prescription from a patient's chart to get started</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden overflow-x-auto">
          <table className="w-full text-sm min-w-[600px]">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Appliance</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Lab</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Expected</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Priority</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {prescriptions.map(rx => (
                <tr key={rx.id} className={`hover:bg-gray-50 ${isOverdue(rx) ? 'bg-red-50/50' : ''}`}>
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{rx.appliance_name}</div>
                    <div className="text-xs text-gray-500">{APPLIANCE_TYPES[rx.appliance_type] || rx.appliance_type} · {rx.arch}</div>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{rx.lab_name || '—'}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[rx.status] || 'bg-gray-100'}`}>
                      {isOverdue(rx) && <AlertTriangle className="h-3 w-3" />}
                      {STATUS_LABELS[rx.status] || rx.status}
                    </span>
                    {rx.is_remake && <span className="ml-1 text-xs text-red-500 font-medium">REMAKE</span>}
                  </td>
                  <td className="px-4 py-3">
                    {rx.expected_delivery_date ? (
                      <span className={isOverdue(rx) ? 'text-red-600 font-medium' : 'text-gray-600'}>
                        {new Date(rx.expected_delivery_date).toLocaleDateString()}
                      </span>
                    ) : '—'}
                  </td>
                  <td className="px-4 py-3">
                    {rx.priority === 'rush' && <span className="text-xs font-bold text-orange-600 uppercase">Rush</span>}
                    {rx.priority === 'emergency' && <span className="text-xs font-bold text-red-600 uppercase">Emergency</span>}
                    {rx.priority === 'normal' && <span className="text-xs text-gray-400">Normal</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function FilterPill({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
        active ? 'bg-teal-100 text-teal-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
      }`}
    >
      {label}
    </button>
  )
}

function LabsView({ labs, onAdd, onEdit, onViewMetrics }: {
  labs: Lab[]
  onAdd: () => void
  onEdit: (lab: Lab) => void
  onViewMetrics: (lab: Lab) => void
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-500">{labs.length} lab vendor{labs.length !== 1 ? 's' : ''}</p>
        <button
          onClick={onAdd}
          className="flex items-center gap-2 px-4 py-2 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Add Lab
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {labs.map(lab => (
          <div key={lab.id} className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="font-semibold text-gray-900">{lab.name}</h3>
                {lab.contact_name && <p className="text-sm text-gray-500">{lab.contact_name}</p>}
              </div>
              <div className="flex items-center gap-1">
                <button onClick={() => onViewMetrics(lab)} className="p-1.5 rounded hover:bg-gray-100" title="Quality metrics">
                  <BarChart3 className="h-4 w-4 text-gray-400" />
                </button>
                <button onClick={() => onEdit(lab)} className="p-1.5 rounded hover:bg-gray-100" title="Edit">
                  <Edit3 className="h-4 w-4 text-gray-400" />
                </button>
              </div>
            </div>
            <div className="space-y-1.5 text-sm text-gray-600">
              {lab.phone && <div className="flex items-center gap-2"><Phone className="h-3.5 w-3.5 text-gray-400" />{lab.phone}</div>}
              {lab.email && <div className="flex items-center gap-2"><Mail className="h-3.5 w-3.5 text-gray-400" />{lab.email}</div>}
              {lab.website && <div className="flex items-center gap-2"><Globe className="h-3.5 w-3.5 text-gray-400" />{lab.website}</div>}
              <div className="flex items-center gap-2"><Clock className="h-3.5 w-3.5 text-gray-400" />Avg {lab.avg_turnaround_days} business days</div>
            </div>
            {!lab.is_active && <span className="inline-block mt-2 text-xs font-medium text-gray-400 bg-gray-100 px-2 py-0.5 rounded">Inactive</span>}
          </div>
        ))}
      </div>
    </div>
  )
}

function LabFormModal({ lab, onClose, onSave }: { lab: Lab | null; onClose: () => void; onSave: (data: Record<string, unknown>) => void }) {
  const [form, setForm] = useState({
    name: lab?.name || '',
    contact_name: lab?.contact_name || '',
    phone: lab?.phone || '',
    email: lab?.email || '',
    address: lab?.address || '',
    website: lab?.website || '',
    account_number: lab?.account_number || '',
    avg_turnaround_days: lab?.avg_turnaround_days || 10,
    notes: lab?.notes || '',
    is_active: lab?.is_active ?? true,
  })
  const [saving, setSaving] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    await onSave(form)
    setSaving(false)
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold text-gray-900">{lab ? 'Edit Lab' : 'Add Lab Vendor'}</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100"><X className="h-5 w-5 text-gray-400" /></button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input label="Lab Name *" value={form.name} onChange={v => setForm(f => ({ ...f, name: v }))} required />
          <Input label="Contact Name" value={form.contact_name} onChange={v => setForm(f => ({ ...f, contact_name: v }))} />
          <div className="grid grid-cols-2 gap-3">
            <Input label="Phone" value={form.phone} onChange={v => setForm(f => ({ ...f, phone: v }))} />
            <Input label="Email" value={form.email} onChange={v => setForm(f => ({ ...f, email: v }))} type="email" />
          </div>
          <Input label="Address" value={form.address} onChange={v => setForm(f => ({ ...f, address: v }))} />
          <div className="grid grid-cols-2 gap-3">
            <Input label="Website" value={form.website} onChange={v => setForm(f => ({ ...f, website: v }))} />
            <Input label="Account #" value={form.account_number} onChange={v => setForm(f => ({ ...f, account_number: v }))} />
          </div>
          <Input label="Avg Turnaround (days)" value={String(form.avg_turnaround_days)} onChange={v => setForm(f => ({ ...f, avg_turnaround_days: parseInt(v) || 10 }))} type="number" />
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
            <textarea
              value={form.notes}
              onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-teal-500 focus:border-transparent outline-none resize-none"
              rows={3}
            />
          </div>
          {lab && (
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.is_active} onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))} className="rounded" />
              Active
            </label>
          )}
          <button
            type="submit"
            disabled={saving || !form.name.trim()}
            className="w-full py-2.5 bg-teal-600 text-white font-medium rounded-lg hover:bg-teal-700 disabled:opacity-50 transition-colors"
          >
            {saving ? 'Saving...' : lab ? 'Update Lab' : 'Add Lab'}
          </button>
        </form>
      </div>
    </div>
  )
}

function MetricsModal({ metrics, onClose }: { metrics: QualityMetrics; onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold text-gray-900">{metrics.lab_name} — Quality</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100"><X className="h-5 w-5 text-gray-400" /></button>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <MetricTile label="Total Orders" value={String(metrics.total_orders)} />
          <MetricTile label="Completed" value={String(metrics.completed_orders)} />
          <MetricTile label="Remake Rate" value={`${metrics.remake_rate}%`} warn={metrics.remake_rate > 5} />
          <MetricTile label="On-Time Rate" value={`${metrics.on_time_rate}%`} warn={metrics.on_time_rate < 80} />
          <MetricTile label="Avg Turnaround" value={metrics.avg_turnaround_actual ? `${metrics.avg_turnaround_actual} days` : 'N/A'} />
          <MetricTile label="Total Spend" value={`$${metrics.total_spend.toLocaleString()}`} />
        </div>
      </div>
    </div>
  )
}

function MetricTile({ label, value, warn = false }: { label: string; value: string; warn?: boolean }) {
  return (
    <div className="bg-gray-50 rounded-lg p-3">
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`text-lg font-bold ${warn ? 'text-red-600' : 'text-gray-900'}`}>{value}</p>
    </div>
  )
}

function Input({ label, value, onChange, type = 'text', required = false }: {
  label: string; value: string; onChange: (v: string) => void; type?: string; required?: boolean
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        required={required}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-teal-500 focus:border-transparent outline-none"
      />
    </div>
  )
}

// ── API Helper ───────────────────────────────────────────────────────────────

async function fetch_api(path: string, method = 'GET', body?: unknown) {
  const token = localStorage.getItem('token')
  const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}
