import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { ArrowLeft, Users, Edit2, Save, X, Clock, FileText, CalendarDays, Wand2, AlertCircle, CheckCircle, Undo2 } from 'lucide-react'
import { api } from '../lib/api'
import ToothChart from '../components/ToothChart'

interface Patient {
  id: string
  first_name: string
  last_name: string
  date_of_birth: string | null
  email: string | null
  phone: string | null
  status: string | null
  treatment_phase: string | null
  referring_doctor: string | null
  notes: string | null
  created_at: string | null
}

interface Appointment {
  id: string
  appointment_date: string
  start_time: string
  end_time: string
  status: string
  appointment_type: string | null
  notes: string | null
}

interface TreatmentNote {
  id: string
  note_text: string
  ai_summary: string | null
  note_type: string
  created_at: string | null
}

interface ChartData {
  teeth_data: Record<string, { bracket_type?: string; wire?: string; band?: boolean; condition?: string }>
  upper_wire: string | null
  lower_wire: string | null
  upper_wire_date: string | null
  lower_wire_date: string | null
  appliances: Array<{ name: string; placed_date?: string }>
}

const PHASE_CONFIG: Record<string, { label: string; color: string }> = {
  consultation: { label: 'Consultation', color: 'bg-gray-100 text-gray-700' },
  pending: { label: 'Pending', color: 'bg-gray-200 text-gray-700' },
  records: { label: 'Records', color: 'bg-amber-100 text-amber-700' },
  treatment_planning: { label: 'Treatment Planning', color: 'bg-blue-100 text-blue-700' },
  active_treatment: { label: 'Active Treatment', color: 'bg-violet-100 text-violet-700' },
  retention: { label: 'Retention', color: 'bg-emerald-100 text-emerald-700' },
  completed: { label: 'Completed', color: 'bg-green-100 text-green-700' },
}

function renderNoteText(text: string) {
  const sentences = text.split(/\. |\n/).filter(s => s.trim())
  if (sentences.length < 2) {
    return <p className="text-xs text-gray-700 leading-relaxed">{text}</p>
  }
  return (
    <ul className="list-disc ml-3 space-y-0.5">
      {sentences.map((sentence, i) => (
        <li key={i} className="text-xs text-gray-700 leading-relaxed">{sentence.trim()}</li>
      ))}
    </ul>
  )
}

export default function PatientDetail() {
  const { id } = useParams<{ id: string }>()
  const [patient, setPatient] = useState<Patient | null>(null)
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [notes, setNotes] = useState<TreatmentNote[]>([])
  const [chart, setChart] = useState<ChartData | null>(null)
  const [editing, setEditing] = useState(false)
  const [editForm, setEditForm] = useState<Partial<Patient>>({})
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
  const loadPatient = useCallback(async () => {
    if (!id) return
    setLoading(true)
    const [patientRes, apptsRes, notesRes, chartRes] = await Promise.all([
      api.getPatient(id),
      api.getAppointments({ patient_id: id }),
      api.getPatientNotes(id),
      api.getToothChart(id),
    ])
    if (patientRes.ok) {
      const data = await patientRes.json()
      setPatient(data)
      setEditForm(data)
    }
    if (apptsRes.ok) {
      const data = await apptsRes.json()
      setAppointments(data.appointments || [])
    }
    if (notesRes.ok) {
      const data = await notesRes.json()
      setNotes(data.notes || [])
    }
    if (chartRes.ok) {
      const data = await chartRes.json()
      setChart(data)
    }
    setLoading(false)
  }, [id])

  useEffect(() => { loadPatient() }, [loadPatient])

  async function handleSave() {
    if (!id) return
    const res = await api.updatePatient(id, editForm)
    if (res.ok) {
      const updated = await res.json()
      setPatient(updated)
      setEditing(false)
    }
  }

  async function handleChartUpdate(data: { teeth_data: Record<string, unknown> }) {
    if (!id) return
    await api.updateToothChart(id, data)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-pulse text-gray-400">Loading patient...</div>
      </div>
    )
  }

  if (!patient) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-500">Patient not found</div>
      </div>
    )
  }

  const phase = patient.treatment_phase ? PHASE_CONFIG[patient.treatment_phase] : null

  return (
    <>
        {/* Back + Patient Name */}
        <div className="flex items-center gap-3 mb-6">
          <button
            onClick={() => navigate('/patients')}
            className="p-2 hover:bg-white rounded-lg transition-colors"
            aria-label="Back to patients"
          >
            <ArrowLeft size={20} className="text-gray-600" />
          </button>
          <div className="flex-1">
            <h2 className="text-2xl font-semibold text-gray-900">
              {patient.first_name} {patient.last_name}
            </h2>
            <div className="flex items-center gap-2 mt-1">
              {phase && (
                <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${phase.color}`}>
                  {phase.label}
                </span>
              )}
              {patient.status && (
                <span className="text-xs text-gray-400 capitalize">{patient.status}</span>
              )}
            </div>
          </div>
          <button
            onClick={() => editing ? handleSave() : setEditing(true)}
            className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-colors shadow-sm ${
              editing
                ? 'bg-emerald-500 hover:bg-emerald-600 text-white'
                : 'bg-white hover:bg-gray-50 text-gray-700 border border-gray-200'
            }`}
          >
            {editing ? <><Save size={14} /> Save</> : <><Edit2 size={14} /> Edit</>}
          </button>
          {editing && (
            <button
              onClick={() => { setEditing(false); setEditForm(patient) }}
              className="p-2 hover:bg-gray-200 rounded-lg transition-colors"
              aria-label="Cancel editing"
            >
              <X size={18} className="text-gray-500" />
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column — Demographics + Tooth Chart */}
          <div className="lg:col-span-2 space-y-6">
            {/* Demographics */}
            <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-5">
              <h3 className="text-sm font-semibold text-gray-800 mb-4">Demographics</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Field label="First Name" value={editForm.first_name || ''} editing={editing} onChange={v => setEditForm(f => ({ ...f, first_name: v }))} />
                <Field label="Last Name" value={editForm.last_name || ''} editing={editing} onChange={v => setEditForm(f => ({ ...f, last_name: v }))} />
                <Field label="Date of Birth" value={editForm.date_of_birth || ''} editing={editing} onChange={v => setEditForm(f => ({ ...f, date_of_birth: v }))} type="date" />
                <Field label="Email" value={editForm.email || ''} editing={editing} onChange={v => setEditForm(f => ({ ...f, email: v }))} type="email" />
                <Field label="Phone" value={editForm.phone || ''} editing={editing} onChange={v => setEditForm(f => ({ ...f, phone: v }))} />
                <Field label="Referring Doctor" value={editForm.referring_doctor || ''} editing={editing} onChange={v => setEditForm(f => ({ ...f, referring_doctor: v }))} />
              </div>
              {(patient.notes || editing) && (
                <div className="mt-4">
                  <Field label="Notes" value={editForm.notes || ''} editing={editing} onChange={v => setEditForm(f => ({ ...f, notes: v }))} multiline />
                </div>
              )}
            </div>

            {/* Tooth Chart */}
            {chart && (
              <ToothChart
                teethData={chart.teeth_data || {}}
                upperWire={chart.upper_wire}
                lowerWire={chart.lower_wire}
                upperWireDate={chart.upper_wire_date}
                lowerWireDate={chart.lower_wire_date}
                appliances={chart.appliances || []}
                onUpdate={handleChartUpdate}
              />
            )}
          </div>

          {/* Right Column — Appointments + Notes + Next Visit */}
          <div className="space-y-6">
            {/* Appointments */}
            <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
              <div className="px-5 py-3 border-b border-gray-100 flex items-center gap-2">
                <CalendarDays size={14} className="text-gray-400" />
                <h3 className="text-sm font-semibold text-gray-800">Appointments</h3>
                <span className="text-xs text-gray-400 ml-auto">{appointments.length}</span>
              </div>
              <div className="max-h-64 overflow-y-auto divide-y divide-gray-50">
                {appointments.length === 0 ? (
                  <p className="px-5 py-6 text-xs text-gray-400 text-center">No appointments</p>
                ) : (
                  appointments.map(appt => (
                    <div key={appt.id} className="px-5 py-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-gray-700">{appt.appointment_date}</span>
                        <span className="text-[10px] uppercase text-gray-400">{appt.status.replace('_', ' ')}</span>
                      </div>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <Clock size={11} className="text-gray-300" />
                        <span className="text-xs text-gray-500">{appt.start_time.slice(0, 5)} – {appt.end_time.slice(0, 5)}</span>
                        {appt.appointment_type && (
                          <span className="text-xs text-gray-400 ml-1">• {appt.appointment_type}</span>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Treatment Notes + Assistant */}
            <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
              <div className="px-5 py-3 border-b border-gray-100 flex items-center gap-2">
                <FileText size={14} className="text-gray-400" />
                <h3 className="text-sm font-semibold text-gray-800">Treatment Notes</h3>
                <span className="text-xs text-gray-400 ml-auto">{notes.length}</span>
              </div>

              {/* Add Note with Assist */}
              <NoteInput
                patientId={id || ''}
                onNoteAdded={note => setNotes(prev => [note, ...prev])}
              />

              <div className="max-h-80 overflow-y-auto divide-y divide-gray-50">
                {notes.length === 0 ? (
                  <p className="px-5 py-6 text-xs text-gray-400 text-center">No notes yet</p>
                ) : (
                  notes.map(note => (
                    <div key={note.id} className="px-5 py-3">
                      {renderNoteText(note.note_text)}
                      {note.ai_summary && (
                        <p className="text-[10px] text-violet-500 mt-1 italic">Summary: {note.ai_summary}</p>
                      )}
                      <p className="text-[10px] text-gray-400 mt-1">
                        {note.created_at ? new Date(note.created_at).toLocaleDateString() : ''}
                        {note.note_type !== 'clinical' && ` • ${note.note_type}`}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Next Visit Section */}
            <NextVisitSection patientId={id || ''} patientName={`${patient.first_name} ${patient.last_name}`} />
          </div>
        </div>
          </>
  )
}

function NextVisitSection({ patientId, patientName }: { patientId: string; patientName: string }) {
  const [nextNotes, setNextNotes] = useState('')
  const [weeks, setWeeks] = useState(4)

  return (
    <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
      <div className="px-5 py-3 border-b border-gray-100 flex items-center gap-2">
        <CalendarDays size={14} className="text-gray-400" />
        <h3 className="text-sm font-semibold text-gray-800">Next Visit</h3>
      </div>
      <div className="px-5 py-4 space-y-3">
        <div>
          <label className="text-[10px] uppercase text-gray-500 font-medium tracking-wider">Next visit notes</label>
          <textarea
            value={nextNotes}
            onChange={e => setNextNotes(e.target.value)}
            placeholder="What to do next time..."
            rows={3}
            className="w-full mt-1 text-xs border border-gray-200 rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300"
          />
        </div>
        <div className="flex items-center gap-3">
          <div className="flex-1">
            <label className="text-[10px] uppercase text-gray-500 font-medium tracking-wider">Weeks out</label>
            <select
              value={weeks}
              onChange={e => setWeeks(Number(e.target.value))}
              className="w-full mt-1 px-2 py-1.5 text-xs border border-gray-200 rounded-lg bg-white"
            >
              {Array.from({ length: 12 }, (_, i) => i + 1).map(w => (
                <option key={w} value={w}>{w} week{w > 1 ? 's' : ''}</option>
              ))}
            </select>
          </div>
          <div className="flex-1 flex items-end">
            <Link
              to={`/schedule`}
              className="w-full mt-5 py-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-medium rounded-lg transition-colors text-center block"
            >
              Schedule
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

function NoteInput({ patientId, onNoteAdded }: { patientId: string; onNoteAdded: (note: TreatmentNote) => void }) {
  const [rawInput, setRawInput] = useState('')
  const [structuredNote, setStructuredNote] = useState('')
  const [savedRawInput, setSavedRawInput] = useState('')
  const [nextVisit, setNextVisit] = useState<string | null>(null)
  const [flags, setFlags] = useState<string[]>([])
  const [assisting, setAssisting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [mode, setMode] = useState<'raw' | 'assisted'>('raw')

  async function handleAIAssist() {
    if (!rawInput.trim()) return
    setAssisting(true)
    const res = await api.aiNoteAssist({ patient_id: patientId, raw_input: rawInput.trim() })
    if (res.ok) {
      const data = await res.json()
      setSavedRawInput(rawInput)
      setStructuredNote(data.structured_note)
      setNextVisit(data.next_visit_suggestion || null)
      setFlags(data.completeness_flags || [])
      setMode('assisted')
    }
    setAssisting(false)
  }

  async function handleSave() {
    const noteText = mode === 'assisted' ? structuredNote : rawInput
    if (!noteText.trim()) return
    setSaving(true)
    const res = await api.createNote({ patient_id: patientId, note_text: noteText.trim() })
    if (res.ok) {
      const note = await res.json()
      onNoteAdded(note)
      setRawInput('')
      setStructuredNote('')
      setSavedRawInput('')
      setNextVisit(null)
      setFlags([])
      setMode('raw')
    }
    setSaving(false)
  }

  function handleReset() {
    setMode('raw')
    setStructuredNote('')
    setNextVisit(null)
    setFlags([])
  }

  function handleRevert() {
    setMode('raw')
    setRawInput(savedRawInput)
    setStructuredNote('')
    setSavedRawInput('')
    setNextVisit(null)
    setFlags([])
  }

  return (
    <div className="px-5 py-3 border-b border-gray-50">
      {mode === 'raw' ? (
        <>
          <textarea
            value={rawInput}
            onChange={e => setRawInput(e.target.value)}
            placeholder="Type your notes (shorthand OK)... e.g. 'adj upper 18ss, elastics 3/16 med, pt compliant'"
            rows={3}
            className="w-full text-xs border border-gray-200 rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300"
          />
          {rawInput.trim() && (
            <div className="flex items-center gap-2 mt-2">
              <button
                onClick={handleAIAssist}
                disabled={assisting}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-violet-500 hover:bg-violet-600 text-white text-xs rounded-lg font-medium transition-colors disabled:opacity-50"
              >
                <Wand2 size={12} />
                {assisting ? 'Processing...' : 'Assist'}
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-3 py-1.5 bg-teal-600 hover:bg-teal-700 text-white text-xs rounded-lg font-medium transition-colors disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save Raw'}
              </button>
            </div>
          )}
            </>
  ) : (
        <>
          {/* Structured note */}
          <div className="bg-violet-50/50 border border-violet-200 rounded-lg p-3 mb-2">
            <div className="flex items-center gap-1.5 mb-2">
              <Wand2 size={12} className="text-violet-500" />
              <span className="text-[10px] uppercase font-medium text-violet-600 tracking-wide">Structured Note</span>
            </div>
            <textarea
              value={structuredNote}
              onChange={e => setStructuredNote(e.target.value)}
              rows={4}
              className="w-full text-xs bg-white border border-violet-200 rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-violet-500/20"
            />
          </div>

          {/* Next visit suggestion */}
          {nextVisit && (
            <div className="flex items-start gap-1.5 mb-2 text-xs text-blue-700 bg-blue-50 border border-blue-200 rounded-lg px-3 py-2">
              <CalendarDays size={12} className="mt-0.5 flex-shrink-0" />
              <span><span className="font-medium">Next visit:</span> {nextVisit}</span>
            </div>
          )}

          {/* Completeness flags */}
          {flags.length > 0 && (
            <div className="flex items-start gap-1.5 mb-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
              <AlertCircle size={12} className="mt-0.5 flex-shrink-0" />
              <span><span className="font-medium">Missing info:</span> {flags.join(', ')}</span>
            </div>
          )}
          {flags.length === 0 && (
            <div className="flex items-center gap-1.5 mb-2 text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2">
              <CheckCircle size={12} />
              <span>Note is complete</span>
            </div>
          )}

          <div className="flex items-center gap-2">
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500 hover:bg-emerald-600 text-white text-xs rounded-lg font-medium transition-colors disabled:opacity-50"
            >
              <CheckCircle size={12} />
              {saving ? 'Saving...' : 'Save Note'}
            </button>
            <button
              onClick={handleRevert}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-amber-700 hover:bg-amber-50 border border-amber-200 rounded-lg transition-colors"
            >
              <Undo2 size={12} />
              Revert
            </button>
            <button
              onClick={handleReset}
              className="px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            >
              Edit raw
            </button>
          </div>
            </>
  )}
    </div>
  )
}

function Field({ label, value, editing, onChange, type = 'text', multiline = false }: {
  label: string; value: string; editing: boolean; onChange: (v: string) => void; type?: string; multiline?: boolean
}) {
  if (!editing) {
    return (
      <div>
        <p className="text-[10px] uppercase text-gray-400 font-medium tracking-wider">{label}</p>
        <p className="text-sm text-gray-800 mt-0.5">{value || '—'}</p>
      </div>
    )
  }

  if (multiline) {
    return (
      <div>
        <p className="text-[10px] uppercase text-gray-400 font-medium tracking-wider mb-1">{label}</p>
        <textarea
          value={value}
          onChange={e => onChange(e.target.value)}
          rows={3}
          className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300"
        />
      </div>
    )
  }

  return (
    <div>
      <p className="text-[10px] uppercase text-gray-400 font-medium tracking-wider mb-1">{label}</p>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300"
      />
    </div>
  )
}
