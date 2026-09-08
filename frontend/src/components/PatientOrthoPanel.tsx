import { useState, useEffect, useCallback } from 'react'
import { MessageSquare, Receipt, Plus, Loader2, CheckCircle2, Pin } from 'lucide-react'
import { api } from '../lib/api'

interface Comment {
  id: string; chart: string; body: string; is_pinned: boolean
  author_name: string | null; created_at: string | null
}
interface ChartCharge {
  id: string; cdt_code: string; description: string | null; fee: number
  status: string; created_at: string | null
}

function money(n: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n)
}

export default function PatientOrthoPanel({ patientId }: { patientId: string }) {
  const [comments, setComments] = useState<Comment[]>([])
  const [charges, setCharges] = useState<ChartCharge[]>([])
  const [chargeTotal, setChargeTotal] = useState(0)
  const [commentChart, setCommentChart] = useState<'info' | 'clinical'>('info')
  const [newComment, setNewComment] = useState('')
  const [newCharge, setNewCharge] = useState({ cdt_code: '', description: '', fee: '' })
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    const [cRes, chRes] = await Promise.all([
      api.getPatientComments(patientId),
      api.getChartCharges(patientId),
    ])
    if (cRes.ok) { const d = await cRes.json(); setComments(d.comments || []) }
    if (chRes.ok) { const d = await chRes.json(); setCharges(d.chart_charges || []); setChargeTotal(d.total || 0) }
  }, [patientId])

  useEffect(() => { load() }, [load])

  async function addComment() {
    if (!newComment.trim()) return
    setBusy(true)
    const r = await api.addPatientComment(patientId, { chart: commentChart, body: newComment.trim() })
    if (r.ok) { setNewComment(''); await load() }
    setBusy(false)
  }

  async function addCharge() {
    if (!newCharge.cdt_code || !newCharge.fee) return
    setBusy(true)
    const r = await api.addChartCharge(patientId, {
      cdt_code: newCharge.cdt_code, description: newCharge.description,
      fee: parseFloat(newCharge.fee),
    })
    if (r.ok) { setNewCharge({ cdt_code: '', description: '', fee: '' }); await load() }
    setBusy(false)
  }

  async function collect(id: string) {
    setBusy(true)
    const r = await api.collectChartCharge(id)
    if (r.ok) await load()
    setBusy(false)
  }

  const shown = comments.filter(c => c.chart === commentChart)

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid="patient-ortho-panel">
      {/* Comments — info + clinical */}
      <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-gray-800">
            <MessageSquare size={15} className="text-teal-600" /> Comments
          </div>
          <div className="flex gap-1 bg-gray-100 rounded-lg p-0.5">
            <button data-testid="comments-tab-info" onClick={() => setCommentChart('info')} className={`px-2.5 py-1 text-[11px] font-medium rounded-md ${commentChart === 'info' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500'}`}>Info Chart</button>
            <button data-testid="comments-tab-clinical" onClick={() => setCommentChart('clinical')} className={`px-2.5 py-1 text-[11px] font-medium rounded-md ${commentChart === 'clinical' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500'}`}>Clinical Chart</button>
          </div>
        </div>
        <div className="flex gap-2 mb-3">
          <input
            data-testid="comment-input"
            value={newComment}
            onChange={e => setNewComment(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') addComment() }}
            placeholder={`Add a ${commentChart} note…`}
            className="flex-1 text-sm px-3 py-2 rounded-lg border border-gray-200 focus:ring-2 focus:ring-teal-100 focus:border-teal-300 outline-none"
          />
          <button data-testid="comment-add" onClick={addComment} disabled={busy} className="px-3 py-2 rounded-lg bg-teal-600 text-white text-sm font-medium hover:bg-teal-700 disabled:opacity-50">Add</button>
        </div>
        <div className="space-y-2 max-h-56 overflow-y-auto">
          {shown.length === 0 ? (
            <p className="text-xs text-gray-400 py-2">No {commentChart} comments yet.</p>
          ) : shown.map(c => (
            <div key={c.id} className="text-sm bg-gray-50 rounded-lg px-3 py-2">
              <div className="flex items-center gap-1.5 mb-0.5">
                {c.is_pinned && <Pin size={11} className="text-gray-400" />}
                <span className="text-[11px] text-gray-400">{c.author_name || 'Staff'} · {c.created_at?.slice(0, 10)}</span>
              </div>
              <p className="text-gray-700">{c.body}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Chart charges — add under next appointment, collect at checkout */}
      <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-gray-800">
            <Receipt size={15} className="text-teal-600" /> Chart Charges
          </div>
          <span className="text-xs text-gray-500">Queued: {money(chargeTotal)}</span>
        </div>
        <div className="grid grid-cols-[1fr_1fr_80px_auto] gap-2 mb-3">
          <input data-testid="charge-cdt" value={newCharge.cdt_code} onChange={e => setNewCharge(v => ({ ...v, cdt_code: e.target.value.toUpperCase() }))} placeholder="CDT (e.g. D8670)" className="text-sm px-2.5 py-2 rounded-lg border border-gray-200 outline-none focus:ring-2 focus:ring-teal-100" />
          <input value={newCharge.description} onChange={e => setNewCharge(v => ({ ...v, description: e.target.value }))} placeholder="Description" className="text-sm px-2.5 py-2 rounded-lg border border-gray-200 outline-none focus:ring-2 focus:ring-teal-100" />
          <input data-testid="charge-fee" value={newCharge.fee} onChange={e => setNewCharge(v => ({ ...v, fee: e.target.value }))} placeholder="Fee" inputMode="decimal" className="text-sm px-2.5 py-2 rounded-lg border border-gray-200 outline-none focus:ring-2 focus:ring-teal-100" />
          <button data-testid="charge-add" onClick={addCharge} disabled={busy} className="px-2.5 py-2 rounded-lg bg-teal-600 text-white text-sm hover:bg-teal-700 disabled:opacity-50 flex items-center"><Plus size={14} /></button>
        </div>
        <div className="space-y-1.5 max-h-56 overflow-y-auto">
          {charges.length === 0 ? (
            <p className="text-xs text-gray-400 py-2">No queued charges. Add CDT charges here; admin collects at checkout.</p>
          ) : charges.map(ch => (
            <div key={ch.id} className="flex items-center justify-between text-sm bg-gray-50 rounded-lg px-3 py-2">
              <div className="min-w-0">
                <span className="font-medium text-gray-800">{ch.cdt_code}</span>
                <span className="text-gray-500 text-xs ml-2 truncate">{ch.description}</span>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className="text-gray-700">{money(ch.fee)}</span>
                <button data-testid={`charge-collect-${ch.id}`} onClick={() => collect(ch.id)} disabled={busy} className="flex items-center gap-1 text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 rounded px-2 py-1 hover:bg-emerald-100 disabled:opacity-50">
                  {busy ? <Loader2 size={11} className="animate-spin" /> : <CheckCircle2 size={11} />} Collect
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
