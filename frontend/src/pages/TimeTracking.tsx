import { useState, useEffect, useCallback } from 'react'
import { Clock, Play, Square, User, Calendar, DollarSign, Edit2, X, Check } from 'lucide-react'
import { api } from '../lib/api'
import { useAuth } from '../hooks/useAuth'

interface TimeEntry {
  id: string
  staff_id: string
  clock_in: string
  clock_out: string | null
  total_hours: number | null
  entry_type: string
  status: string
  notes: string | null
  edited_by: string | null
  edited_at: string | null
}

interface MyStatus {
  is_clocked_in: boolean
  clock_in_time: string | null
  today_hours: number
  current_entry_id: string | null
}

interface StaffHoursEntry {
  staff_id: string
  staff_name: string
  total_hours: number
  entries: TimeEntry[]
}

interface PayrollSummaryEntry {
  staff_id: string
  staff_name: string
  hours: number
  rate: number
  pay: number
  worker_type: string
}

interface PayRateEntry {
  id: string
  staff_id: string
  staff_name: string | null
  hourly_rate: number
  worker_type: string
  effective_date: string
  end_date: string | null
}

interface TeamMember {
  id: string
  full_name: string
  role: string
}

export default function TimeTracking() {
  const { isOwner, isDoctor, isManager, role } = useAuth()
  const isAdmin = isOwner || isDoctor || isManager

  const [status, setStatus] = useState<MyStatus | null>(null)
  const [myHours, setMyHours] = useState<TimeEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [clockLoading, setClockLoading] = useState(false)

  // Admin state
  const [staffHours, setStaffHours] = useState<StaffHoursEntry[]>([])
  const [payrollSummary, setPayrollSummary] = useState<PayrollSummaryEntry[]>([])
  const [payRates, setPayRates] = useState<PayRateEntry[]>([])
  const [team, setTeam] = useState<TeamMember[]>([])
  const [startDate, setStartDate] = useState(() => {
    const d = new Date()
    d.setDate(d.getDate() - 13)
    return d.toISOString().split('T')[0]
  })
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split('T')[0])

  // Edit modal state
  const [editEntry, setEditEntry] = useState<TimeEntry | null>(null)
  const [editClockIn, setEditClockIn] = useState('')
  const [editClockOut, setEditClockOut] = useState('')
  const [editNotes, setEditNotes] = useState('')

  // Pay rate form
  const [rateStaffId, setRateStaffId] = useState('')
  const [rateAmount, setRateAmount] = useState('')
  const [rateWorkerType, setRateWorkerType] = useState('permanent')
  const [rateLoading, setRateLoading] = useState(false)

  const fetchStatus = useCallback(async () => {
    try {
      const res = await api.request('/api/v1/time/my-status')
      if (res.ok) setStatus(await res.json())
    } catch (e) { /* silent */ }
  }, [])

  const fetchMyHours = useCallback(async () => {
    try {
      const res = await api.request('/api/v1/time/my-hours')
      if (res.ok) setMyHours(await res.json())
    } catch (e) { /* silent */ }
  }, [])

  const fetchAdminData = useCallback(async () => {
    if (!isAdmin) return
    const params = `start_date=${startDate}&end_date=${endDate}`
    try {
      const [hoursRes, payrollRes, ratesRes, teamRes] = await Promise.all([
        api.request(`/api/v1/time/staff-hours?${params}`),
        api.request(`/api/v1/time/payroll-summary?${params}`),
        api.request('/api/v1/time/pay-rates'),
        api.request('/api/v1/team/'),
      ])
      if (hoursRes.ok) setStaffHours(await hoursRes.json())
      if (payrollRes.ok) setPayrollSummary(await payrollRes.json())
      if (ratesRes.ok) setPayRates(await ratesRes.json())
      if (teamRes.ok) {
        const teamData = await teamRes.json()
        setTeam(Array.isArray(teamData) ? teamData : teamData.members || [])
      }
    } catch (e) { /* silent */ }
  }, [isAdmin, startDate, endDate])

  useEffect(() => {
    async function init() {
      setLoading(true)
      await Promise.all([fetchStatus(), fetchMyHours()])
      await fetchAdminData()
      setLoading(false)
    }
    init()
  }, [fetchStatus, fetchMyHours, fetchAdminData])

  async function handleClockIn() {
    setClockLoading(true)
    try {
      const res = await api.request('/api/v1/time/clock-in', { method: 'POST' })
      if (res.ok) {
        await fetchStatus()
        await fetchMyHours()
      } else {
        const err = await res.json()
        alert(err.detail || 'Failed to clock in')
      }
    } finally {
      setClockLoading(false)
    }
  }

  async function handleClockOut() {
    setClockLoading(true)
    try {
      const res = await api.request('/api/v1/time/clock-out', { method: 'POST' })
      if (res.ok) {
        await fetchStatus()
        await fetchMyHours()
        if (isAdmin) await fetchAdminData()
      } else {
        const err = await res.json()
        alert(err.detail || 'Failed to clock out')
      }
    } finally {
      setClockLoading(false)
    }
  }

  async function handleEditSave() {
    if (!editEntry) return
    const body: Record<string, string> = {}
    if (editClockIn) body.clock_in = new Date(editClockIn).toISOString()
    if (editClockOut) body.clock_out = new Date(editClockOut).toISOString()
    if (editNotes !== editEntry.notes) body.notes = editNotes

    const res = await api.request(`/api/v1/time/time-entries/${editEntry.id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    })
    if (res.ok) {
      setEditEntry(null)
      await fetchAdminData()
      await fetchMyHours()
    } else {
      const err = await res.json()
      alert(err.detail || 'Failed to save edit')
    }
  }

  async function handleSetPayRate(e: React.FormEvent) {
    e.preventDefault()
    if (!rateStaffId || !rateAmount) return
    setRateLoading(true)
    try {
      const res = await api.request('/api/v1/time/pay-rates', {
        method: 'POST',
        body: JSON.stringify({
          staff_id: rateStaffId,
          hourly_rate: rateAmount,
          worker_type: rateWorkerType,
          effective_date: new Date().toISOString().split('T')[0],
        }),
      })
      if (res.ok) {
        setRateStaffId('')
        setRateAmount('')
        await fetchAdminData()
      } else {
        const err = await res.json()
        alert(err.detail || 'Failed to set pay rate')
      }
    } finally {
      setRateLoading(false)
    }
  }

  function openEditModal(entry: TimeEntry) {
    setEditEntry(entry)
    setEditClockIn(entry.clock_in ? toLocalInput(entry.clock_in) : '')
    setEditClockOut(entry.clock_out ? toLocalInput(entry.clock_out) : '')
    setEditNotes(entry.notes || '')
  }

  function toLocalInput(iso: string): string {
    const d = new Date(iso)
    const offset = d.getTimezoneOffset()
    const local = new Date(d.getTime() - offset * 60000)
    return local.toISOString().slice(0, 16)
  }

  function formatTime(iso: string): string {
    return new Date(iso).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
  }

  function formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString([], { month: 'short', day: 'numeric' })
  }

  // Calculate week total from myHours
  const weekStart = new Date()
  weekStart.setDate(weekStart.getDate() - weekStart.getDay())
  weekStart.setHours(0, 0, 0, 0)
  const weekTotal = myHours
    .filter(e => new Date(e.clock_in) >= weekStart && e.status !== 'missed')
    .reduce((sum, e) => sum + (e.total_hours || 0), 0)

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* ── Clock In/Out Section ── */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm">
        <div className="flex flex-col items-center gap-4">
          <div className="flex items-center gap-2 text-gray-500">
            <Clock size={18} />
            <span className="text-sm font-medium">Time Clock</span>
          </div>

          {/* Status */}
          <p className="text-lg font-medium text-gray-700">
            {status?.is_clocked_in
              ? `Clocked in since ${status.clock_in_time ? formatTime(status.clock_in_time) : '--'}`
              : 'Not clocked in'}
          </p>

          {/* Big Clock Button */}
          <button
            onClick={status?.is_clocked_in ? handleClockOut : handleClockIn}
            disabled={clockLoading}
            className={`w-36 h-36 rounded-full flex flex-col items-center justify-center gap-2 text-white font-bold text-lg shadow-lg transition-all hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed ${
              status?.is_clocked_in
                ? 'bg-red-500 hover:bg-red-600'
                : 'bg-teal-500 hover:bg-teal-600'
            }`}
          >
            {status?.is_clocked_in ? (
              <>
                <Square size={28} fill="white" />
                <span>Clock Out</span>
              </>
            ) : (
              <>
                <Play size={28} fill="white" />
                <span>Clock In</span>
              </>
            )}
          </button>

          {/* Stats */}
          <div className="flex gap-8 mt-2">
            <div className="text-center">
              <p className="text-2xl font-bold text-gray-900">{status?.today_hours.toFixed(1) || '0.0'}</p>
              <p className="text-xs text-gray-500">Today</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-gray-900">{weekTotal.toFixed(1)}</p>
              <p className="text-xs text-gray-500">This Week</p>
            </div>
          </div>
        </div>
      </div>

      {/* ── Recent Entries ── */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Recent Entries</h3>
        {myHours.length === 0 ? (
          <p className="text-sm text-gray-400">No entries yet</p>
        ) : (
          <div className="space-y-2">
            {myHours.slice(0, 14).map(entry => (
              <div
                key={entry.id}
                className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="text-xs text-gray-500 w-16">{formatDate(entry.clock_in)}</div>
                  <div>
                    <span className="text-sm text-gray-700">{formatTime(entry.clock_in)}</span>
                    <span className="text-gray-400 mx-1">→</span>
                    <span className="text-sm text-gray-700">
                      {entry.clock_out ? formatTime(entry.clock_out) : '—'}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium text-gray-900">
                    {entry.total_hours ? `${entry.total_hours.toFixed(1)}h` : '—'}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    entry.status === 'clocked_in' ? 'bg-green-100 text-green-700' :
                    entry.status === 'missed' ? 'bg-red-100 text-red-700' :
                    entry.status === 'edited' ? 'bg-amber-100 text-amber-700' :
                    'bg-gray-100 text-gray-600'
                  }`}>
                    {entry.status}
                  </span>
                  {isAdmin && (
                    <button
                      onClick={() => openEditModal(entry)}
                      className="p-1 text-gray-400 hover:text-teal-600 transition-colors"
                    >
                      <Edit2 size={14} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Admin Sections ── */}
      {isAdmin && (
        <>
          {/* Staff Hours Table */}
          <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
                <User size={16} />
                Staff Hours
              </h3>
              <div className="flex items-center gap-2">
                <input
                  type="date"
                  value={startDate}
                  onChange={e => setStartDate(e.target.value)}
                  className="text-xs border border-gray-200 rounded-lg px-2 py-1"
                />
                <span className="text-gray-400">—</span>
                <input
                  type="date"
                  value={endDate}
                  onChange={e => setEndDate(e.target.value)}
                  className="text-xs border border-gray-200 rounded-lg px-2 py-1"
                />
              </div>
            </div>
            {staffHours.length === 0 ? (
              <p className="text-sm text-gray-400">No staff hours in this period</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100">
                      <th className="text-left py-2 font-medium text-gray-600">Name</th>
                      <th className="text-right py-2 font-medium text-gray-600">Total Hours</th>
                      <th className="text-right py-2 font-medium text-gray-600">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {staffHours.map(staff => {
                      const isClockedIn = staff.entries.some(e => e.status === 'clocked_in')
                      return (
                        <tr key={staff.staff_id} className="border-b border-gray-50">
                          <td className="py-2.5 text-gray-900">{staff.staff_name}</td>
                          <td className="py-2.5 text-right font-medium text-gray-700">{staff.total_hours.toFixed(1)}h</td>
                          <td className="py-2.5 text-right">
                            <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${
                              isClockedIn ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                            }`}>
                              <span className={`w-1.5 h-1.5 rounded-full ${isClockedIn ? 'bg-green-500' : 'bg-gray-400'}`} />
                              {isClockedIn ? 'Clocked In' : 'Out'}
                            </span>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Payroll Summary */}
          <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2 mb-4">
              <DollarSign size={16} />
              Payroll Summary
            </h3>
            {payrollSummary.length === 0 ? (
              <p className="text-sm text-gray-400">No payroll data for this period</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100">
                      <th className="text-left py-2 font-medium text-gray-600">Staff</th>
                      <th className="text-right py-2 font-medium text-gray-600">Hours</th>
                      <th className="text-right py-2 font-medium text-gray-600">Rate</th>
                      <th className="text-right py-2 font-medium text-gray-600">Pay</th>
                      <th className="text-right py-2 font-medium text-gray-600">Type</th>
                    </tr>
                  </thead>
                  <tbody>
                    {payrollSummary.map(item => (
                      <tr key={item.staff_id} className="border-b border-gray-50">
                        <td className="py-2.5 text-gray-900">{item.staff_name}</td>
                        <td className="py-2.5 text-right text-gray-700">{item.hours.toFixed(1)}</td>
                        <td className="py-2.5 text-right text-gray-700">${item.rate.toFixed(2)}</td>
                        <td className="py-2.5 text-right font-medium text-gray-900">${item.pay.toFixed(2)}</td>
                        <td className="py-2.5 text-right">
                          <span className={`text-xs px-2 py-0.5 rounded-full ${
                            item.worker_type === 'permanent'
                              ? 'bg-teal-100 text-teal-700'
                              : 'bg-amber-100 text-amber-700'
                          }`}>
                            {item.worker_type}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="border-t border-gray-200">
                      <td className="py-2.5 font-semibold text-gray-900">Total</td>
                      <td className="py-2.5 text-right font-semibold text-gray-900">
                        {payrollSummary.reduce((s, i) => s + i.hours, 0).toFixed(1)}
                      </td>
                      <td />
                      <td className="py-2.5 text-right font-semibold text-gray-900">
                        ${payrollSummary.reduce((s, i) => s + i.pay, 0).toFixed(2)}
                      </td>
                      <td />
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </div>

          {/* Set Pay Rate Form */}
          <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2 mb-4">
              <Calendar size={16} />
              Set Pay Rate
            </h3>
            <form onSubmit={handleSetPayRate} className="flex flex-wrap items-end gap-3">
              <div className="flex-1 min-w-[160px]">
                <label className="text-xs text-gray-500 block mb-1">Staff Member</label>
                <select
                  value={rateStaffId}
                  onChange={e => setRateStaffId(e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  required
                >
                  <option value="">Select staff...</option>
                  {team.map(m => (
                    <option key={m.id} value={m.id}>{m.full_name}</option>
                  ))}
                </select>
              </div>
              <div className="w-28">
                <label className="text-xs text-gray-500 block mb-1">Rate ($/hr)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={rateAmount}
                  onChange={e => setRateAmount(e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  placeholder="25.00"
                  required
                />
              </div>
              <div className="w-36">
                <label className="text-xs text-gray-500 block mb-1">Worker Type</label>
                <select
                  value={rateWorkerType}
                  onChange={e => setRateWorkerType(e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                >
                  <option value="permanent">Permanent</option>
                  <option value="temporary">Temporary</option>
                </select>
              </div>
              <button
                type="submit"
                disabled={rateLoading}
                className="px-4 py-2 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors disabled:opacity-50"
              >
                {rateLoading ? 'Saving...' : 'Set Rate'}
              </button>
            </form>

            {/* Current pay rates */}
            {payRates.length > 0 && (
              <div className="mt-4 pt-4 border-t border-gray-100">
                <p className="text-xs text-gray-500 mb-2">Current Rates</p>
                <div className="space-y-1">
                  {payRates.map(r => (
                    <div key={r.id} className="flex items-center justify-between text-sm py-1">
                      <span className="text-gray-700">{r.staff_name}</span>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-gray-900">${r.hourly_rate.toFixed(2)}/hr</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          r.worker_type === 'permanent'
                            ? 'bg-teal-100 text-teal-700'
                            : 'bg-amber-100 text-amber-700'
                        }`}>
                          {r.worker_type}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {/* ── Edit Time Entry Modal ── */}
      {editEntry && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-gray-900">Edit Time Entry</h3>
              <button onClick={() => setEditEntry(null)} className="p-1 text-gray-400 hover:text-gray-600">
                <X size={18} />
              </button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-gray-500 block mb-1">Clock In</label>
                <input
                  type="datetime-local"
                  value={editClockIn}
                  onChange={e => setEditClockIn(e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 block mb-1">Clock Out</label>
                <input
                  type="datetime-local"
                  value={editClockOut}
                  onChange={e => setEditClockOut(e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 block mb-1">Notes</label>
                <input
                  type="text"
                  value={editNotes}
                  onChange={e => setEditNotes(e.target.value)}
                  placeholder="Optional notes..."
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-5">
              <button
                onClick={() => setEditEntry(null)}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleEditSave}
                className="px-4 py-2 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors flex items-center gap-1"
              >
                <Check size={14} />
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
