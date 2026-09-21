import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileSignature, Plus, ShieldCheck, CheckCircle2, Archive, Loader2, Printer, X } from 'lucide-react'
import { api } from '../lib/api'
import { localToday } from '../lib/dates'

interface Contract {
  id: string
  patient_id: string
  total_treatment_fee: number
  fee_type: string
  discount_amount: number
  expected_first_charges: number
  down_payment: number
  patient_portion: number
  policy_notes: string | null
  insurance_verified_at: string | null
  payer_kind: string
  billing_cadence: string
  status: string
}

interface PatientLite { id: string; first_name: string; last_name: string; status?: string }

const FEE_TYPES = ['standard', 'phase_1', 'phase_2', 'limited', 'records_only', 'custom']
const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700', active: 'bg-emerald-100 text-emerald-700',
  completed: 'bg-blue-100 text-blue-700', cancelled: 'bg-red-100 text-red-700', archived: 'bg-amber-100 text-amber-700',
}

function money(n: number | null | undefined) {
  if (n == null) return '$0.00'
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

export default function Contracts() {
  const navigate = useNavigate()
  const [contracts, setContracts] = useState<Contract[]>([])
  const [patients, setPatients] = useState<Record<string, PatientLite>>({})
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [showEOD, setShowEOD] = useState(false)
  const [busy, setBusy] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [cRes, pRes] = await Promise.all([api.getContracts(), api.getPatients({ page: 1, size: 100 })])
      if (cRes.ok) setContracts((await cRes.json()).contracts || [])
      if (pRes.ok) {
        const d = await pRes.json()
        const list: PatientLite[] = d.patients || d.items || d || []
        const map: Record<string, PatientLite> = {}
        list.forEach(p => { map[p.id] = p })
        setPatients(map)
      }
    } catch { /* ignore */ }
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  async function verify(id: string) {
    setBusy(id)
    const res = await api.verifyContractInsurance(id)
    if (res.ok) { const d = await res.json(); if (!d.verified) alert(d.reason || 'Could not verify insurance') }
    await load(); setBusy(null)
  }
  async function place(id: string) {
    setBusy(id)
    const res = await api.placeContract(id)
    if (!res.ok) { const e = await res.json().catch(() => ({})); alert(e.detail || 'Could not place contract') }
    await load(); setBusy(null)
  }
  async function archive(id: string) {
    setBusy(id); await api.archiveContract(id); await load(); setBusy(null)
  }

  const pname = (id: string) => { const p = patients[id]; return p ? `${p.first_name} ${p.last_name}` : id.slice(0, 8) }

  return (
    <div data-testid="contracts-page">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900">Contracts</h2>
          <p className="text-sm text-gray-500 mt-0.5">Treatment contracts — verify insurance, place, and connect to the ledger.</p>
        </div>
        <div className="flex items-center gap-2">
          <button data-testid="open-eod" onClick={() => setShowEOD(true)} className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium bg-white border border-gray-200 rounded-lg hover:border-teal-300 hover:text-teal-700">
            <Printer size={15} /> EOD Report
          </button>
          <button data-testid="new-contract" onClick={() => setShowCreate(true)} className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium bg-teal-600 text-white rounded-lg hover:bg-teal-700">
            <Plus size={15} /> New Contract
          </button>
        </div>
      </div>

      {loading ? (
        <div className="py-16 text-center"><Loader2 size={22} className="animate-spin text-gray-400 mx-auto" /></div>
      ) : contracts.length === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm py-16 text-center">
          <FileSignature size={32} className="mx-auto text-gray-300 mb-3" />
          <p className="text-sm text-gray-500">No contracts yet. Create one from an accepted TC proposal.</p>
        </div>
      ) : (
        <div className="space-y-3" data-testid="contracts-list">
          {contracts.map(c => (
            <div key={c.id} className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-5" data-testid={`contract-row-${c.id}`}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <button onClick={() => navigate(`/patients/${c.patient_id}`)} className="font-semibold text-gray-900 hover:text-teal-700">{pname(c.patient_id)}</button>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${STATUS_COLORS[c.status] || 'bg-gray-100 text-gray-600'}`}>{c.status}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600">{c.fee_type.replace('_', ' ')}</span>
                    {c.insurance_verified_at && <span className="flex items-center gap-1 text-[10px] text-emerald-600"><ShieldCheck size={11} /> Insurance verified</span>}
                  </div>
                  <div className="flex flex-wrap gap-4 mt-2 text-xs text-gray-500">
                    <span>Fee <b className="text-gray-800">{money(c.total_treatment_fee)}</b></span>
                    {c.discount_amount > 0 && <span>Discount <b className="text-gray-800">{money(c.discount_amount)}</b></span>}
                    <span>First charges <b className="text-gray-800">{money(c.expected_first_charges)}</b></span>
                    <span>Down <b className="text-gray-800">{money(c.down_payment)}</b></span>
                    <span>Cadence <b className="text-gray-800">{c.billing_cadence}</b></span>
                  </div>
                  {c.policy_notes && <p className="text-xs text-gray-400 mt-1.5">{c.policy_notes}</p>}
                </div>
                <div className="flex flex-col gap-1.5 shrink-0">
                  {!c.insurance_verified_at && c.status !== 'archived' && (
                    <button data-testid={`verify-${c.id}`} disabled={busy === c.id} onClick={() => verify(c.id)} className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 rounded-lg hover:bg-blue-100 disabled:opacity-50">
                      {busy === c.id ? <Loader2 size={12} className="animate-spin" /> : <ShieldCheck size={12} />} Verify Insurance
                    </button>
                  )}
                  {c.status !== 'active' && c.status !== 'archived' && (
                    <button data-testid={`place-${c.id}`} disabled={busy === c.id} onClick={() => place(c.id)} className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-lg hover:bg-emerald-100 disabled:opacity-50">
                      <CheckCircle2 size={12} /> Place
                    </button>
                  )}
                  {c.status !== 'archived' && (
                    <button data-testid={`archive-${c.id}`} disabled={busy === c.id} onClick={() => archive(c.id)} className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium bg-white text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50">
                      <Archive size={12} /> Archive
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreate && <CreateContractModal patients={Object.values(patients)} onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); load() }} />}
      {showEOD && <EODModal onClose={() => setShowEOD(false)} />}
    </div>
  )
}

function CreateContractModal({ patients, onClose, onCreated }: { patients: PatientLite[]; onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState({
    patient_id: '', total_treatment_fee: '5000', fee_type: 'standard', discount_amount: '0',
    expected_first_charges: '0', down_payment: '0', payer_kind: 'insurance', billing_cadence: 'monthly', policy_notes: '',
  })
  const [saving, setSaving] = useState(false)

  async function save() {
    if (!form.patient_id) { alert('Select a patient'); return }
    setSaving(true)
    const res = await api.createContract({
      patient_id: form.patient_id,
      total_treatment_fee: Number(form.total_treatment_fee),
      fee_type: form.fee_type,
      discount_amount: Number(form.discount_amount),
      expected_first_charges: Number(form.expected_first_charges),
      down_payment: Number(form.down_payment),
      payer_kind: form.payer_kind,
      billing_cadence: form.billing_cadence,
      policy_notes: form.policy_notes || null,
    })
    setSaving(false)
    if (res.ok) onCreated(); else alert('Could not create contract')
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" data-testid="create-contract-modal">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[85vh] overflow-y-auto">
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-gray-100">
          <h3 className="text-sm font-semibold text-gray-900">New Contract</h3>
          <button onClick={onClose} aria-label="Close" className="p-1 hover:bg-gray-100 rounded-lg"><X size={18} className="text-gray-500" /></button>
        </div>
        <div className="p-5 space-y-3">
          <label className="block">
            <span className="text-xs text-gray-500">Patient</span>
            <select data-testid="contract-patient" value={form.patient_id} onChange={e => setForm(f => ({ ...f, patient_id: e.target.value }))} className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm">
              <option value="">Select patient…</option>
              {patients.map(p => <option key={p.id} value={p.id}>{p.first_name} {p.last_name}</option>)}
            </select>
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block"><span className="text-xs text-gray-500">Fee type</span>
              <select value={form.fee_type} onChange={e => setForm(f => ({ ...f, fee_type: e.target.value }))} className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm">
                {FEE_TYPES.map(t => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
              </select>
            </label>
            <label className="block"><span className="text-xs text-gray-500">Payer</span>
              <select data-testid="contract-payer" value={form.payer_kind} onChange={e => setForm(f => ({ ...f, payer_kind: e.target.value }))} className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm">
                <option value="insurance">Insurance</option><option value="private">Private pay</option><option value="direct">Direct</option>
              </select>
            </label>
            <Num label="Total treatment fee" v={form.total_treatment_fee} on={v => setForm(f => ({ ...f, total_treatment_fee: v }))} />
            <Num label="Discount" v={form.discount_amount} on={v => setForm(f => ({ ...f, discount_amount: v }))} />
            <Num label="Expected first charges" v={form.expected_first_charges} on={v => setForm(f => ({ ...f, expected_first_charges: v }))} />
            <Num label="Down payment" v={form.down_payment} on={v => setForm(f => ({ ...f, down_payment: v }))} />
          </div>
          <label className="block"><span className="text-xs text-gray-500">Policy notes</span>
            <textarea value={form.policy_notes} onChange={e => setForm(f => ({ ...f, policy_notes: e.target.value }))} rows={2} className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
          </label>
          <button data-testid="save-contract" disabled={saving} onClick={save} className="w-full py-2.5 bg-teal-600 text-white rounded-lg text-sm font-medium hover:bg-teal-700 disabled:opacity-50">
            {saving ? 'Saving…' : 'Save Contract'}
          </button>
        </div>
      </div>
    </div>
  )
}

function Num({ label, v, on }: { label: string; v: string; on: (v: string) => void }) {
  return (
    <label className="block"><span className="text-xs text-gray-500">{label}</span>
      <input type="number" value={v} onChange={e => on(e.target.value)} className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
    </label>
  )
}

function EODModal({ onClose }: { onClose: () => void }) {
  const [data, setData] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    api.getEODReport(localToday()).then(async r => { if (r.ok) setData(await r.json()); setLoading(false) }).catch(() => setLoading(false))
  }, [])
  const appts = (data?.appointments as { total?: number; by_status?: Record<string, number> }) || {}
  const fin = (data?.financials as { total_collected?: number; total_charged?: number; payments_collected_count?: number }) || {}
  const contractsPlaced = (data?.contracts_placed as unknown[]) || []
  const claims = (data?.claims_submitted as unknown[]) || []
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" data-testid="eod-modal">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[85vh] overflow-y-auto print:shadow-none">
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-gray-100 print:hidden">
          <h3 className="text-sm font-semibold text-gray-900">End-of-Day Report</h3>
          <div className="flex items-center gap-3">
            <button onClick={() => window.print()} className="flex items-center gap-1 text-xs font-medium text-teal-600 hover:text-teal-700"><Printer size={12} /> Print</button>
            <button onClick={onClose} aria-label="Close" className="p-1 hover:bg-gray-100 rounded-lg"><X size={18} className="text-gray-500" /></button>
          </div>
        </div>
        <div className="p-5">
          {loading ? <div className="py-8 text-center"><Loader2 size={18} className="animate-spin text-gray-400 mx-auto" /></div> : (
            <div className="space-y-4 text-sm">
              <p className="text-xs text-gray-400">{String(data?.date || '')}</p>
              <Section title="Appointments">
                <p>{appts.total || 0} total</p>
                <p className="text-xs text-gray-500">{Object.entries(appts.by_status || {}).map(([k, v]) => `${v} ${k}`).join(' · ')}</p>
              </Section>
              <Section title="Financials">
                <p>Collected <b>{money(fin.total_collected)}</b> ({fin.payments_collected_count || 0} payments)</p>
                <p>Charged <b>{money(fin.total_charged)}</b></p>
              </Section>
              <Section title="Contracts placed"><p>{contractsPlaced.length}</p></Section>
              <Section title="Claims submitted"><p>{claims.length}</p></Section>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-b border-gray-100 pb-3">
      <p className="text-[10px] uppercase tracking-wider font-semibold text-gray-400 mb-1">{title}</p>
      {children}
    </div>
  )
}
