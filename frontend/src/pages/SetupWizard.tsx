import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  CheckCircle, Circle, SkipForward, ArrowRight, ArrowLeft,
  Building2, Users, Shield, UserPlus, ClipboardCheck, Monitor,
  Loader2, Upload, Plus, Trash2
} from 'lucide-react'
import { api } from '../lib/api'

interface StepInfo {
  order: number
  name: string
  status: 'pending' | 'completed' | 'skipped'
}

interface OnboardingStatus {
  practice_id: string
  source_system: string | null
  started_at: string | null
  completed_at: string | null
  steps: StepInfo[]
  progress: { total: number; completed: number; percent: number }
  imported_staff_count: number
  imported_patients_count: number
}

interface StaffEntry {
  name: string
  email: string
  role: string
}

interface PatientEntry {
  first_name: string
  last_name: string
  date_of_birth: string
  email: string
  phone: string
}

const SOURCE_SYSTEMS = [
  { id: 'tops_ortho', name: 'TOPS Ortho', description: 'TOPS Orthodontic Practice Management' },
  { id: 'cloud_9', name: 'Cloud 9', description: 'Cloud 9 Ortho Software' },
  { id: 'dolphin', name: 'Dolphin Imaging', description: 'Dolphin Management & Imaging' },
  { id: 'ortho2', name: 'Ortho2', description: 'Ortho2 Edge Cloud' },
  { id: 'dentrix', name: 'Dentrix', description: 'Henry Schein Dentrix' },
  { id: 'other', name: 'Other', description: 'Another system not listed' },
]

const STEP_META = [
  { name: 'source_system', label: 'Source System', icon: Monitor, description: 'Which software are you migrating from?' },
  { name: 'practice_info', label: 'Practice Info', icon: Building2, description: 'Confirm your practice details' },
  { name: 'import_staff', label: 'Import Staff', icon: Users, description: 'Add your team members' },
  { name: 'configure_roles', label: 'Configure Roles', icon: Shield, description: 'Set up role-based permissions' },
  { name: 'import_patients', label: 'Import Patients', icon: UserPlus, description: 'Bring your patient records over' },
  { name: 'verify', label: 'Verify', icon: ClipboardCheck, description: 'Review and confirm your setup' },
]

const ROLE_TEMPLATES: Record<string, string[]> = {
  tops_ortho: ['Doctor', 'Treatment Coordinator', 'Clinical Assistant', 'Front Desk', 'Office Manager'],
  cloud_9: ['Orthodontist', 'TC', 'Assistant', 'Scheduling', 'Billing'],
  dolphin: ['Provider', 'Clinical Staff', 'Admin', 'Imaging Tech'],
  ortho2: ['Doctor', 'Staff', 'Front Office', 'Back Office'],
  dentrix: ['Dentist', 'Hygienist', 'Assistant', 'Office Manager', 'Front Desk'],
  other: ['Doctor', 'Assistant', 'Front Desk', 'Office Manager'],
}

export default function SetupWizard() {
  const [currentStep, setCurrentStep] = useState(0)
  const [status, setStatus] = useState<OnboardingStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [selectedSource, setSelectedSource] = useState<string | null>(null)
  const [staffEntries, setStaffEntries] = useState<StaffEntry[]>([{ name: '', email: '', role: '' }])
  const [staffJson, setStaffJson] = useState('')
  const [staffMode, setStaffMode] = useState<'manual' | 'json'>('manual')
  const [patientJson, setPatientJson] = useState('')
  const [patientFile, setPatientFile] = useState<File | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    fetchStatus()
  }, [])

  async function fetchStatus() {
    setLoading(true)
    try {
      const res = await api.request('/api/v1/onboarding/status')
      if (res.ok) {
        const data = await res.json()
        setStatus(data)
        if (data.source_system) setSelectedSource(data.source_system)
        // Set current step to first incomplete step
        const firstPending = data.steps.findIndex((s: StepInfo) => s.status === 'pending')
        if (firstPending >= 0) setCurrentStep(firstPending)
        else setCurrentStep(5) // all done, show verify
      }
    } catch (e) {
      console.error('Failed to fetch onboarding status', e)
    }
    setLoading(false)
  }

  async function handleStartOnboarding() {
    if (!selectedSource) return
    setSaving(true)
    try {
      const res = await api.request('/api/v1/onboarding/start', {
        method: 'POST',
        body: JSON.stringify({ source_system: selectedSource }),
      })
      if (res.ok) {
        await fetchStatus()
        setCurrentStep(1)
      }
    } catch (e) {
      console.error('Failed to start onboarding', e)
    }
    setSaving(false)
  }

  async function markStep(stepName: string, stepStatus: 'completed' | 'skipped') {
    setSaving(true)
    try {
      const res = await api.request(`/api/v1/onboarding/step/${stepName}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: stepStatus }),
      })
      if (res.ok) {
        await fetchStatus()
        if (currentStep < 5) setCurrentStep(currentStep + 1)
      }
    } catch (e) {
      console.error('Failed to update step', e)
    }
    setSaving(false)
  }

  async function handleImportStaff() {
    setSaving(true)
    try {
      let staffList: StaffEntry[] = []
      if (staffMode === 'json') {
        staffList = JSON.parse(staffJson)
      } else {
        staffList = staffEntries.filter(s => s.name && s.email && s.role)
      }
      if (staffList.length === 0) {
        setSaving(false)
        return
      }
      const res = await api.request('/api/v1/onboarding/import-staff', {
        method: 'POST',
        body: JSON.stringify({ staff: staffList }),
      })
      if (res.ok) {
        await fetchStatus()
        setCurrentStep(3)
      }
    } catch (e) {
      console.error('Failed to import staff', e)
    }
    setSaving(false)
  }

  async function handleImportPatients() {
    setSaving(true)
    try {
      let patients: PatientEntry[] = []
      if (patientFile) {
        const text = await patientFile.text()
        patients = JSON.parse(text)
      } else if (patientJson) {
        patients = JSON.parse(patientJson)
      }
      if (patients.length === 0) {
        setSaving(false)
        return
      }
      const res = await api.request('/api/v1/onboarding/import-patients', {
        method: 'POST',
        body: JSON.stringify({ patients }),
      })
      if (res.ok) {
        await fetchStatus()
        setCurrentStep(5)
      }
    } catch (e) {
      console.error('Failed to import patients', e)
    }
    setSaving(false)
  }

  function addStaffRow() {
    setStaffEntries([...staffEntries, { name: '', email: '', role: '' }])
  }

  function removeStaffRow(index: number) {
    setStaffEntries(staffEntries.filter((_, i) => i !== index))
  }

  function updateStaffRow(index: number, field: keyof StaffEntry, value: string) {
    setStaffEntries(staffEntries.map((s, i) => i === index ? { ...s, [field]: value } : s))
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-teal-600" />
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Welcome to OrthoFlow</h1>
        <p className="text-gray-500 mt-2">Let&apos;s get your practice set up. This wizard will guide you through the migration process.</p>
      </div>

      {/* Step Indicator */}
      <div className="mb-10">
        <div className="flex items-center justify-between">
          {STEP_META.map((meta, i) => {
            const stepStatus = status?.steps[i]?.status || 'pending'
            const isActive = i === currentStep
            const Icon = meta.icon
            return (
              <div key={meta.name} className="flex flex-col items-center flex-1">
                <button
                  onClick={() => setCurrentStep(i)}
                  className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${
                    stepStatus === 'completed' ? 'bg-teal-500 text-white' :
                    stepStatus === 'skipped' ? 'bg-gray-300 text-gray-600' :
                    isActive ? 'bg-teal-600 text-white ring-4 ring-teal-100' :
                    'bg-gray-200 text-gray-400'
                  }`}
                >
                  {stepStatus === 'completed' ? <CheckCircle size={18} /> :
                   stepStatus === 'skipped' ? <SkipForward size={14} /> :
                   <Icon size={16} />}
                </button>
                <span className={`text-xs mt-2 text-center max-w-[80px] ${
                  isActive ? 'text-teal-700 font-semibold' : 'text-gray-400'
                }`}>{meta.label}</span>
                {i < STEP_META.length - 1 && (
                  <div className="hidden" /> // connector handled by flex spacing
                )}
              </div>
            )
          })}
        </div>
        {/* Progress bar */}
        <div className="mt-4 h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-teal-500 transition-all duration-500 rounded-full"
            style={{ width: `${status?.progress.percent || 0}%` }}
          />
        </div>
      </div>

      {/* Step Content */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">

        {/* Step 0: Source System */}
        {currentStep === 0 && (
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Which software are you coming from?</h2>
            <p className="text-gray-500 mb-6">We&apos;ll customize your migration based on your current system.</p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {SOURCE_SYSTEMS.map(sys => (
                <button
                  key={sys.id}
                  onClick={() => setSelectedSource(sys.id)}
                  className={`p-4 rounded-xl border-2 transition-all text-left ${
                    selectedSource === sys.id
                      ? 'border-teal-500 bg-teal-50 ring-2 ring-teal-200'
                      : 'border-gray-200 hover:border-teal-300 hover:bg-gray-50'
                  }`}
                >
                  <div className="font-medium text-gray-900">{sys.name}</div>
                  <div className="text-xs text-gray-500 mt-1">{sys.description}</div>
                </button>
              ))}
            </div>
            <div className="mt-8 flex justify-end gap-3">
              <button
                onClick={handleStartOnboarding}
                disabled={!selectedSource || saving}
                className="px-6 py-2.5 bg-teal-600 text-white rounded-lg font-medium hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {saving ? <Loader2 size={16} className="animate-spin" /> : <ArrowRight size={16} />}
                Continue
              </button>
            </div>
          </div>
        )}

        {/* Step 1: Practice Info */}
        {currentStep === 1 && (
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Practice Information</h2>
            <p className="text-gray-500 mb-6">Confirm or update your practice details. These may already be set from registration.</p>
            <div className="space-y-4 max-w-md">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Practice Name</label>
                <input type="text" className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent" placeholder="Your Practice Name" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Address</label>
                <input type="text" className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent" placeholder="123 Main St, City, ST 12345" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">NPI Number</label>
                <input type="text" className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent" placeholder="1234567890" maxLength={10} />
              </div>
            </div>
            <div className="mt-8 flex justify-between">
              <button onClick={() => setCurrentStep(0)} className="px-4 py-2 text-gray-600 hover:text-gray-900 flex items-center gap-1">
                <ArrowLeft size={16} /> Back
              </button>
              <div className="flex gap-3">
                <button
                  onClick={() => markStep('practice_info', 'skipped')}
                  disabled={saving}
                  className="px-4 py-2 text-gray-500 hover:text-gray-700 border border-gray-300 rounded-lg flex items-center gap-1"
                >
                  <SkipForward size={14} /> Skip
                </button>
                <button
                  onClick={() => markStep('practice_info', 'completed')}
                  disabled={saving}
                  className="px-6 py-2.5 bg-teal-600 text-white rounded-lg font-medium hover:bg-teal-700 disabled:opacity-50 flex items-center gap-2"
                >
                  {saving ? <Loader2 size={16} className="animate-spin" /> : <ArrowRight size={16} />}
                  Continue
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Import Staff */}
        {currentStep === 2 && (
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Import Staff</h2>
            <p className="text-gray-500 mb-4">Add your team members manually or paste a JSON array.</p>

            <div className="flex gap-2 mb-4">
              <button
                onClick={() => setStaffMode('manual')}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium ${staffMode === 'manual' ? 'bg-teal-100 text-teal-700' : 'bg-gray-100 text-gray-600'}`}
              >
                Manual Entry
              </button>
              <button
                onClick={() => setStaffMode('json')}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium ${staffMode === 'json' ? 'bg-teal-100 text-teal-700' : 'bg-gray-100 text-gray-600'}`}
              >
                Paste JSON
              </button>
            </div>

            {staffMode === 'manual' ? (
              <div className="space-y-3">
                {staffEntries.map((entry, i) => (
                  <div key={i} className="flex gap-2 items-center">
                    <input
                      type="text" placeholder="Name" value={entry.name}
                      onChange={e => updateStaffRow(i, 'name', e.target.value)}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                    />
                    <input
                      type="email" placeholder="Email" value={entry.email}
                      onChange={e => updateStaffRow(i, 'email', e.target.value)}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                    />
                    <input
                      type="text" placeholder="Role" value={entry.role}
                      onChange={e => updateStaffRow(i, 'role', e.target.value)}
                      className="w-36 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                    />
                    {staffEntries.length > 1 && (
                      <button onClick={() => removeStaffRow(i)} className="text-red-400 hover:text-red-600">
                        <Trash2 size={16} />
                      </button>
                    )}
                  </div>
                ))}
                <button onClick={addStaffRow} className="text-teal-600 hover:text-teal-700 text-sm font-medium flex items-center gap-1">
                  <Plus size={14} /> Add another
                </button>
              </div>
            ) : (
              <textarea
                value={staffJson}
                onChange={e => setStaffJson(e.target.value)}
                placeholder={'[\n  { "name": "Jane Smith", "email": "jane@practice.com", "role": "Office Manager" }\n]'}
                className="w-full h-40 px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              />
            )}

            <div className="mt-8 flex justify-between">
              <button onClick={() => setCurrentStep(1)} className="px-4 py-2 text-gray-600 hover:text-gray-900 flex items-center gap-1">
                <ArrowLeft size={16} /> Back
              </button>
              <div className="flex gap-3">
                <button
                  onClick={() => markStep('import_staff', 'skipped')}
                  disabled={saving}
                  className="px-4 py-2 text-gray-500 hover:text-gray-700 border border-gray-300 rounded-lg flex items-center gap-1"
                >
                  <SkipForward size={14} /> Skip
                </button>
                <button
                  onClick={handleImportStaff}
                  disabled={saving}
                  className="px-6 py-2.5 bg-teal-600 text-white rounded-lg font-medium hover:bg-teal-700 disabled:opacity-50 flex items-center gap-2"
                >
                  {saving ? <Loader2 size={16} className="animate-spin" /> : <Users size={16} />}
                  Import Staff
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Configure Roles */}
        {currentStep === 3 && (
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Configure Roles</h2>
            <p className="text-gray-500 mb-6">
              Based on your source system ({selectedSource ? SOURCE_SYSTEMS.find(s => s.id === selectedSource)?.name : 'unknown'}), we suggest these role templates:
            </p>
            <div className="space-y-2">
              {(ROLE_TEMPLATES[selectedSource || 'other'] || ROLE_TEMPLATES.other).map(role => (
                <div key={role} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                  <Shield size={16} className="text-teal-600" />
                  <span className="text-gray-800 font-medium">{role}</span>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-400 mt-4">You can customize roles further in Settings → Permissions after setup.</p>
            <div className="mt-8 flex justify-between">
              <button onClick={() => setCurrentStep(2)} className="px-4 py-2 text-gray-600 hover:text-gray-900 flex items-center gap-1">
                <ArrowLeft size={16} /> Back
              </button>
              <div className="flex gap-3">
                <button
                  onClick={() => markStep('configure_roles', 'skipped')}
                  disabled={saving}
                  className="px-4 py-2 text-gray-500 hover:text-gray-700 border border-gray-300 rounded-lg flex items-center gap-1"
                >
                  <SkipForward size={14} /> Skip
                </button>
                <button
                  onClick={() => markStep('configure_roles', 'completed')}
                  disabled={saving}
                  className="px-6 py-2.5 bg-teal-600 text-white rounded-lg font-medium hover:bg-teal-700 disabled:opacity-50 flex items-center gap-2"
                >
                  {saving ? <Loader2 size={16} className="animate-spin" /> : <ArrowRight size={16} />}
                  Continue
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Step 4: Import Patients */}
        {currentStep === 4 && (
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Import Patients</h2>
            <p className="text-gray-500 mb-6">Upload a JSON file or paste patient data below.</p>

            <div className="space-y-4">
              {/* File upload */}
              <div
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
                  patientFile ? 'border-teal-400 bg-teal-50' : 'border-gray-300 hover:border-teal-300'
                }`}
              >
                <Upload size={24} className="mx-auto text-gray-400 mb-2" />
                <label className="cursor-pointer">
                  <span className="text-teal-600 font-medium hover:underline">Choose a file</span>
                  <input
                    type="file"
                    accept=".json"
                    className="hidden"
                    onChange={e => setPatientFile(e.target.files?.[0] || null)}
                  />
                </label>
                {patientFile && (
                  <p className="text-sm text-teal-700 mt-2">Selected: {patientFile.name}</p>
                )}
              </div>

              <div className="text-center text-gray-400 text-sm">— or paste JSON —</div>

              <textarea
                value={patientJson}
                onChange={e => setPatientJson(e.target.value)}
                placeholder={'[\n  { "first_name": "John", "last_name": "Doe", "date_of_birth": "1990-05-15", "email": "john@email.com", "phone": "555-0100" }\n]'}
                className="w-full h-32 px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              />
            </div>

            <div className="mt-8 flex justify-between">
              <button onClick={() => setCurrentStep(3)} className="px-4 py-2 text-gray-600 hover:text-gray-900 flex items-center gap-1">
                <ArrowLeft size={16} /> Back
              </button>
              <div className="flex gap-3">
                <button
                  onClick={() => markStep('import_patients', 'skipped')}
                  disabled={saving}
                  className="px-4 py-2 text-gray-500 hover:text-gray-700 border border-gray-300 rounded-lg flex items-center gap-1"
                >
                  <SkipForward size={14} /> Skip
                </button>
                <button
                  onClick={handleImportPatients}
                  disabled={saving || (!patientFile && !patientJson)}
                  className="px-6 py-2.5 bg-teal-600 text-white rounded-lg font-medium hover:bg-teal-700 disabled:opacity-50 flex items-center gap-2"
                >
                  {saving ? <Loader2 size={16} className="animate-spin" /> : <UserPlus size={16} />}
                  Import Patients
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Step 5: Verify */}
        {currentStep === 5 && (
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Setup Summary</h2>
            <p className="text-gray-500 mb-6">Review what was configured during onboarding.</p>

            <div className="space-y-3">
              {status?.steps.map(step => {
                const meta = STEP_META.find(m => m.name === step.name)
                return (
                  <div key={step.name} className="flex items-center justify-between p-3 rounded-lg bg-gray-50">
                    <div className="flex items-center gap-3">
                      {step.status === 'completed' ? (
                        <CheckCircle size={18} className="text-teal-500" />
                      ) : step.status === 'skipped' ? (
                        <SkipForward size={18} className="text-gray-400" />
                      ) : (
                        <Circle size={18} className="text-gray-300" />
                      )}
                      <span className="text-gray-800 font-medium">{meta?.label || step.name}</span>
                    </div>
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                      step.status === 'completed' ? 'bg-teal-100 text-teal-700' :
                      step.status === 'skipped' ? 'bg-gray-200 text-gray-600' :
                      'bg-yellow-100 text-yellow-700'
                    }`}>
                      {step.status}
                    </span>
                  </div>
                )
              })}
            </div>

            {status && (
              <div className="mt-6 p-4 bg-teal-50 rounded-xl border border-teal-100">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">Source System:</span>
                    <span className="ml-2 font-medium text-gray-900">{SOURCE_SYSTEMS.find(s => s.id === status.source_system)?.name || '—'}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Staff Imported:</span>
                    <span className="ml-2 font-medium text-gray-900">{status.imported_staff_count}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Patients Imported:</span>
                    <span className="ml-2 font-medium text-gray-900">{status.imported_patients_count}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Progress:</span>
                    <span className="ml-2 font-medium text-gray-900">{status.progress.percent}%</span>
                  </div>
                </div>
              </div>
            )}

            <div className="mt-8 flex justify-between">
              <button onClick={() => setCurrentStep(4)} className="px-4 py-2 text-gray-600 hover:text-gray-900 flex items-center gap-1">
                <ArrowLeft size={16} /> Back
              </button>
              <div className="flex gap-3">
                {status?.steps.some(s => s.status === 'pending') && (
                  <button
                    onClick={() => markStep('verify', 'completed')}
                    disabled={saving}
                    className="px-6 py-2.5 bg-teal-600 text-white rounded-lg font-medium hover:bg-teal-700 disabled:opacity-50 flex items-center gap-2"
                  >
                    {saving ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle size={16} />}
                    Complete Setup
                  </button>
                )}
                <button
                  onClick={() => navigate('/')}
                  className="px-6 py-2.5 bg-teal-600 text-white rounded-lg font-medium hover:bg-teal-700 flex items-center gap-2"
                >
                  Go to Dashboard <ArrowRight size={16} />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
