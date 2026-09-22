import { useState } from 'react'
import { Filter, Play, Send, Loader2, X, Users, Shield } from 'lucide-react'
import { api } from '../lib/api'

type Tab = 'patient' | 'insurance'

interface Row {
  patient_id: string
  first_name: string
  last_name: string
  gender?: string | null
  age?: number | null
  status?: string
  payer_name?: string | null
  balance?: number
  remaining_benefit?: number | null
  plan_type?: string | null
  email?: string | null
  phone?: string | null
}

function money(n: number | null | undefined) {
  return n == null ? '—' : n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

const GENDERS = ['', 'male', 'female', 'non_binary', 'other']
const PAY_STATUS = [['', 'Any balance'], ['owes', 'Owes money'], ['paid_up', 'Paid up']]
const INSURANCE = [['', 'Any'], ['has', 'Has insurance'], ['none', 'No insurance']]
const TREAT_STATUS = ['', 'new_patient', 'scheduled_patient', 'pending', 'treatment_refused', 'active', 'inactive']

// Customizable report builder — filter patients across many dimensions, view as Patient or
// Insurance tab, and act on the result set (flagship: bundle-message everyone who didn't pay).
export default function ReportBuilder() {
  const [tab, setTab] = useState<Tab>('patient')
  const [filters, setFilters] = useState<Record<string, string>>({})
  const [rows, setRows] = useState<Row[]>([])
  const [ran, setRan] = useState(false)
  const [loading, setLoading] = useState(false)
  const [showBundle, setShowBundle] = useState(false)

  function setF(k: string, v: string) { setFilters(f => ({ ...f, [k]: v })) }

  function payload() {
    const p: Record<string, unknown> = {}
    if (filters.gender) p.gender = filters.gender
    if (filters.min_age) p.min_age = Number(filters.min_age)
    if (filters.max_age) p.max_age = Number(filters.max_age)
    if (filters.treatment_status) p.treatment_status = filters.treatment_status
    if (filters.payment_status) p.payment_status = filters.payment_status
    if (filters.insurance) p.insurance = filters.insurance
    if (filters.appointment_type) p.appointment_type = filters.appointment_type
    if (filters.procedure_cdt) p.procedure_cdt = filters.procedure_cdt
    if (filters.referral) p.referral = filters.referral
    if (filters.missing_appointments === 'yes') p.missing_appointments = true
    if (filters.missing_appointments === 'no') p.missing_appointments = false
    return p
  }

  async function run() {
    setLoading(true); setRan(true)
    const res = tab === 'patient' ? await api.reportBuilderPatient(payload()) : await api.reportBuilderInsurance(payload())
    if (res.ok) { const d = await res.json(); setRows(d.rows || []) } else setRows([])
    setLoading(false)
  }

  return (
    <div data-testid="report-builder">
      {/* Patient vs Insurance tabs */}
      <div className="flex gap-1 mb-4 bg-gray-100 rounded-lg p-1 w-fit">
        <button data-testid="builder-tab-patient" onClick={() => { setTab('patient'); setRan(false) }} className={`flex items-center gap-1.5 px-4 py-2 text-xs font-medium rounded-md ${tab === 'patient' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'}`}><Users size={13} /> Patient</button>
        <button data-testid="builder-tab-insurance" onClick={() => { setTab('insurance'); setRan(false) }} className={`flex items-center gap-1.5 px-4 py-2 text-xs font-medium rounded-md ${tab === 'insurance' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'}`}><Shield size={13} /> Insurance</button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-5 mb-4">
        <div className="flex items-center gap-2 mb-4 text-sm font-semibold text-gray-800"><Filter size={15} className="text-teal-600" /> Filters</div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          <Sel label="Gender" value={filters.gender || ''} onChange={v => setF('gender', v)} opts={GENDERS.map(g => [g, g || 'Any'])} />
          <Inp label="Min age" value={filters.min_age || ''} onChange={v => setF('min_age', v)} type="number" />
          <Inp label="Max age" value={filters.max_age || ''} onChange={v => setF('max_age', v)} type="number" />
          <Sel label="Treatment status" value={filters.treatment_status || ''} onChange={v => setF('treatment_status', v)} opts={TREAT_STATUS.map(s => [s, s ? s.replace('_', ' ') : 'Any'])} />
          <Sel label="Payment" testid="filter-payment" value={filters.payment_status || ''} onChange={v => setF('payment_status', v)} opts={PAY_STATUS} />
          <Sel label="Insurance" value={filters.insurance || ''} onChange={v => setF('insurance', v)} opts={INSURANCE} />
          <Sel label="Missing appts" testid="filter-missing-appts" value={filters.missing_appointments || ''} onChange={v => setF('missing_appointments', v)} opts={[['', 'Any'], ['yes', 'Yes — no upcoming'], ['no', 'No — has upcoming']]} />
          <label className="block"><span className="text-[11px] text-gray-500">Appt type</span>
            <input
              data-testid="filter-appt-type"
              list="appt-type-options"
              value={filters.appointment_type || ''}
              onChange={e => setF('appointment_type', e.target.value)}
              placeholder="Search or type…"
              className="mt-1 w-full border border-gray-200 rounded-lg px-2.5 py-1.5 text-sm"
            />
            <datalist id="appt-type-options">
              {['Adjustment','Bonding','Consultation','Deband','Elastic Check','Emergency','IPR','Observation','Progress Photos','Records','Retainer Check','Wire Change','Aligner Check','Aligner Delivery','Appliance Check','Virtual Visit'].map(t => <option key={t} value={t} />)}
            </datalist>
          </label>
          <Inp label="Procedure CDT" value={filters.procedure_cdt || ''} onChange={v => setF('procedure_cdt', v)} />
          <Inp label="Referral" value={filters.referral || ''} onChange={v => setF('referral', v)} />
        </div>
        <div className="flex items-center gap-2 mt-4">
          <button data-testid="run-report" onClick={run} disabled={loading} className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium bg-teal-600 text-white rounded-lg hover:bg-teal-700 disabled:opacity-50">
            {loading ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />} Run Report
          </button>
          {ran && rows.length > 0 && tab === 'patient' && (
            <button data-testid="bundle-message-open" onClick={() => setShowBundle(true)} className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium bg-violet-50 text-violet-700 border border-violet-200 rounded-lg hover:bg-violet-100">
              <Send size={14} /> Bundle Message ({rows.length})
            </button>
          )}
        </div>
      </div>

      {/* Results */}
      {ran && (
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden" data-testid="report-results">
          <div className="px-5 py-3 border-b border-gray-100 text-sm font-semibold text-gray-800">{rows.length} result{rows.length === 1 ? '' : 's'}</div>
          {rows.length === 0 ? (
            <p className="px-5 py-8 text-sm text-gray-400 text-center">No matches for these filters.</p>
          ) : (
            <div className="max-h-[480px] overflow-y-auto divide-y divide-gray-50">
              {rows.map(r => (
                <div key={r.patient_id} className="px-5 py-2.5 flex items-center justify-between gap-3 text-sm" data-testid="report-row">
                  <div className="min-w-0">
                    <span className="font-medium text-gray-800">{r.last_name}, {r.first_name}</span>
                    <span className="text-xs text-gray-400 ml-2">{r.gender || ''}{r.age != null ? ` · ${r.age}y` : ''}{r.status ? ` · ${r.status.replace('_', ' ')}` : ''}</span>
                  </div>
                  <div className="text-right shrink-0">
                    {tab === 'patient'
                      ? <span className={r.balance && r.balance > 0 ? 'text-amber-700 font-medium' : 'text-gray-600'}>{money(r.balance)}</span>
                      : <span className="text-gray-600">{r.payer_name} · {money(r.remaining_benefit)} left</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {showBundle && <BundleModal filters={payload()} count={rows.length} onClose={() => setShowBundle(false)} />}
    </div>
  )
}

function BundleModal({ filters, count, onClose }: { filters: Record<string, unknown>; count: number; onClose: () => void }) {
  const [channel, setChannel] = useState('sms')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [sending, setSending] = useState(false)
  const [result, setResult] = useState<string | null>(null)

  async function send() {
    if (!body.trim()) return
    setSending(true)
    const res = await api.reportBundleMessage({ filters, channel, subject: subject || undefined, body })
    if (res.ok) { const d = await res.json(); setResult(`Queued ${d.messages_queued} of ${d.recipients_matched} ${channel} messages.`) }
    else setResult('Failed to queue messages.')
    setSending(false)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" data-testid="bundle-modal">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-md">
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-gray-100">
          <h3 className="text-sm font-semibold text-gray-900">Bundle Message · {count} recipients</h3>
          <button onClick={onClose} aria-label="Close" className="p-1 hover:bg-gray-100 rounded-lg"><X size={18} className="text-gray-500" /></button>
        </div>
        <div className="p-5 space-y-3">
          {result ? (
            <p className="text-sm text-emerald-700 bg-emerald-50 border border-emerald-100 rounded-lg px-3 py-2" data-testid="bundle-result">{result}</p>
          ) : (
            <>
              <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit">
                <button onClick={() => setChannel('sms')} className={`px-3 py-1.5 text-xs rounded ${channel === 'sms' ? 'bg-white shadow-sm' : 'text-gray-500'}`}>SMS</button>
                <button onClick={() => setChannel('email')} className={`px-3 py-1.5 text-xs rounded ${channel === 'email' ? 'bg-white shadow-sm' : 'text-gray-500'}`}>Email</button>
              </div>
              {channel === 'email' && <input value={subject} onChange={e => setSubject(e.target.value)} placeholder="Subject" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />}
              <textarea data-testid="bundle-body" value={body} onChange={e => setBody(e.target.value)} rows={4} placeholder="Message to all matched patients…" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
              <button data-testid="bundle-send" disabled={sending} onClick={send} className="w-full py-2.5 bg-violet-600 text-white rounded-lg text-sm font-medium hover:bg-violet-700 disabled:opacity-50">
                {sending ? 'Sending…' : `Send to ${count} recipients`}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function Inp({ label, value, onChange, type = 'text' }: { label: string; value: string; onChange: (v: string) => void; type?: string }) {
  return (
    <label className="block"><span className="text-[11px] text-gray-500">{label}</span>
      <input type={type} value={value} onChange={e => onChange(e.target.value)} className="mt-1 w-full border border-gray-200 rounded-lg px-2.5 py-1.5 text-sm" />
    </label>
  )
}
function Sel({ label, value, onChange, opts, testid }: { label: string; value: string; onChange: (v: string) => void; opts: string[][]; testid?: string }) {
  return (
    <label className="block"><span className="text-[11px] text-gray-500">{label}</span>
      <select data-testid={testid} value={value} onChange={e => onChange(e.target.value)} className="mt-1 w-full border border-gray-200 rounded-lg px-2.5 py-1.5 text-sm">
        {opts.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
    </label>
  )
}
