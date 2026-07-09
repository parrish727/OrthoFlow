import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Users, FileText, Upload, CheckCircle, AlertCircle, Loader2, ChevronRight, Database, FileSpreadsheet } from 'lucide-react'
import { api } from '../lib/api'

interface SourceSystem {
  id: string
  name: string
  description: string
  file_types: string[]
}

interface FieldMapping {
  source_column: string
  target_field: string
}

interface ValidationRow {
  row_number: number
  status: 'valid' | 'error'
  errors: string[]
}

interface JobStatus {
  id: string
  status: string
  total: number
  imported: number
  failed: number
  skipped: number
  progress: number
}

const STEPS = ['Select Source', 'Upload', 'Map Fields', 'Validate', 'Import']

const ORTHOFLOW_FIELDS = [
  'patient_id', 'first_name', 'last_name', 'date_of_birth', 'email', 'phone',
  'address', 'city', 'state', 'zip', 'insurance_provider', 'insurance_id',
  'treatment_type', 'treatment_start', 'treatment_end', 'provider', 'notes', '-- skip --',
]

export default function Migration() {
  const [step, setStep] = useState(1)
  const [systems, setSystems] = useState<SourceSystem[]>([])
  const [selectedSystem, setSelectedSystem] = useState<string | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [jobId, setJobId] = useState<string | null>(null)
  const [sourceColumns, setSourceColumns] = useState<string[]>([])
  const [mappings, setMappings] = useState<FieldMapping[]>([])
  const [validationResults, setValidationResults] = useState<ValidationRow[]>([])
  const [validating, setValidating] = useState(false)
  const [executing, setExecuting] = useState(false)
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const navigate = useNavigate()
useEffect(() => {
    api.migrationSystems().then(async res => {
      if (res.ok) {
        const data = await res.json()
        setSystems(data.systems || [])
      }
    })
  }, [])

  async function handleUpload() {
    if (!file) return
    setUploading(true)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('source_system', selectedSystem || 'csv')
    const res = await api.migrationUpload(formData)
    if (res.ok) {
      const data = await res.json()
      setJobId(data.job_id)
      setSourceColumns(data.columns || [])
      setMappings((data.columns || []).map((col: string) => ({ source_column: col, target_field: '-- skip --' })))
      setStep(3)
    }
    setUploading(false)
  }

  async function handleSaveMappings() {
    if (!jobId) return
    const res = await api.migrationMapping(jobId, mappings)
    if (res.ok) {
      setStep(4)
      handleValidate()
    }
  }

  async function handleValidate() {
    if (!jobId) return
    setValidating(true)
    const res = await api.migrationValidate(jobId)
    if (res.ok) {
      const data = await res.json()
      setValidationResults(data.rows || [])
    }
    setValidating(false)
  }

  async function handleExecute() {
    if (!jobId) return
    setExecuting(true)
    setStep(5)
    const res = await api.migrationExecute(jobId)
    if (res.ok) {
      const data = await res.json()
      setJobStatus(data)
    }
    // Poll for progress
    const interval = setInterval(async () => {
      const statusRes = await api.migrationJobStatus(jobId)
      if (statusRes.ok) {
        const s = await statusRes.json()
        setJobStatus(s)
        if (s.status === 'completed' || s.status === 'failed') {
          clearInterval(interval)
          setExecuting(false)
        }
      }
    }, 2000)
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f) setFile(f)
  }

  function updateMapping(index: number, targetField: string) {
    setMappings(prev => prev.map((m, i) => i === index ? { ...m, target_field: targetField } : m))
  }

  const systemIcons: Record<string, string> = {
    dolphin: '🐬',
    ortho2: '🦷',
    eaglesoft: '🦅',
    csv: '📄',
  }

  return (
    <>
        {/* Step Indicator */}
        <div className="mb-8">
          <div className="flex items-center justify-between max-w-2xl mx-auto">
            {STEPS.map((s, i) => (
              <div key={s} className="flex items-center">
                <div className="flex flex-col items-center">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                    step > i + 1 ? 'bg-emerald-500 text-white' :
                    step === i + 1 ? 'bg-teal-600 text-white' :
                    'bg-gray-200 text-gray-500'
                  }`}>
                    {step > i + 1 ? <CheckCircle size={16} /> : i + 1}
                  </div>
                  <span className={`text-xs mt-1 ${step === i + 1 ? 'text-blue-600 font-medium' : 'text-gray-400'}`}>{s}</span>
                </div>
                {i < STEPS.length - 1 && (
                  <div className={`w-12 sm:w-20 h-0.5 mx-1 ${step > i + 1 ? 'bg-emerald-500' : 'bg-gray-200'}`} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Step 1: Select Source */}
        {step === 1 && (
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Select Source System</h2>
            <p className="text-sm text-gray-500 mb-6">Choose the practice management software you're migrating from</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {(systems.length > 0 ? systems : [
                { id: 'dolphin', name: 'Dolphin Imaging', description: 'Dolphin Management & Imaging', file_types: ['.csv', '.xml'] },
                { id: 'ortho2', name: 'Ortho2', description: 'Ortho2 Practice Management', file_types: ['.csv', '.txt'] },
                { id: 'eaglesoft', name: 'Eaglesoft', description: 'Patterson Eaglesoft', file_types: ['.csv', '.xml'] },
                { id: 'csv', name: 'Generic CSV', description: 'Standard CSV export from any system', file_types: ['.csv'] },
              ]).map(sys => (
                <button
                  key={sys.id}
                  onClick={() => { setSelectedSystem(sys.id); setStep(2) }}
                  className={`bg-white rounded-2xl border p-5 text-left transition-all hover:border-blue-300 hover:shadow-md ${
                    selectedSystem === sys.id ? 'border-blue-400 ring-2 ring-blue-100' : 'border-gray-200/80 shadow-sm'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <span className="text-2xl">{systemIcons[sys.id] || '📄'}</span>
                    <div>
                      <p className="font-medium text-gray-800">{sys.name}</p>
                      <p className="text-sm text-gray-500 mt-0.5">{sys.description}</p>
                      <p className="text-xs text-gray-400 mt-2">Accepts: {sys.file_types.join(', ')}</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 2: Upload */}
        {step === 2 && (
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Upload Patient Data</h2>
            <p className="text-sm text-gray-500 mb-6">Upload your exported file from {systems.find(s => s.id === selectedSystem)?.name || selectedSystem}</p>

            <div
              onDragOver={e => { e.preventDefault(); setDragOver(true) }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-2xl p-12 text-center transition-all ${
                dragOver ? 'border-blue-400 bg-blue-50/50' : 'border-gray-200 bg-white hover:border-gray-300'
              }`}
            >
              <div className="w-14 h-14 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Upload size={24} className="text-gray-400" />
              </div>
              {file ? (
                <div>
                  <p className="text-gray-700 font-medium">{file.name}</p>
                  <p className="text-xs text-gray-400 mt-1">{(file.size / 1024).toFixed(1)} KB</p>
                </div>
              ) : (
                <div>
                  <p className="text-gray-700 font-medium">Drop your file here</p>
                  <p className="text-xs text-gray-400 mt-1">Accepts .csv, .txt, .xml</p>
                </div>
              )}
              <input
                type="file"
                accept=".csv,.txt,.xml"
                onChange={e => { if (e.target.files?.[0]) setFile(e.target.files[0]) }}
                className="hidden"
                id="migration-file"
              />
              <label
                htmlFor="migration-file"
                className="inline-block mt-4 px-5 py-2.5 bg-teal-600 hover:bg-teal-700 text-white rounded-full cursor-pointer text-sm font-medium transition-colors"
              >
                Choose File
              </label>
            </div>

            <div className="flex gap-3 mt-6">
              <button onClick={() => setStep(1)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
                Back
              </button>
              <button
                onClick={handleUpload}
                disabled={!file || uploading}
                className="px-5 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
              >
                {uploading ? 'Uploading...' : 'Upload & Continue'}
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Map Fields */}
        {step === 3 && (
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Map Fields</h2>
            <p className="text-sm text-gray-500 mb-6">Match your source columns to OrthoFlow fields</p>

            <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50/50">
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Source Column</th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">→</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">OrthoFlow Field</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {mappings.map((m, i) => (
                      <tr key={i} className="hover:bg-gray-50/50">
                        <td className="px-6 py-3 font-medium text-gray-700">{m.source_column}</td>
                        <td className="px-6 py-3 text-center text-gray-400"><ChevronRight size={14} /></td>
                        <td className="px-6 py-3">
                          <select
                            value={m.target_field}
                            onChange={e => updateMapping(i, e.target.value)}
                            className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-200"
                          >
                            {ORTHOFLOW_FIELDS.map(f => (
                              <option key={f} value={f}>{f}</option>
                            ))}
                          </select>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button onClick={() => setStep(2)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
                Back
              </button>
              <button
                onClick={handleSaveMappings}
                className="px-5 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                Save Mappings & Validate
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Validation */}
        {step === 4 && (
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Validation Results</h2>
            <p className="text-sm text-gray-500 mb-6">Review data quality before importing</p>

            {validating ? (
              <div className="flex flex-col items-center py-12">
                <Loader2 size={32} className="animate-spin text-blue-500 mb-3" />
                <p className="text-sm text-gray-500">Validating data...</p>
              </div>
            ) : (
              <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
                  <span className="text-sm text-gray-600">
                    {validationResults.filter(r => r.status === 'valid').length} valid / {validationResults.filter(r => r.status === 'error').length} errors
                  </span>
                </div>
                <div className="max-h-96 overflow-y-auto">
                  <table className="w-full text-sm">
                    <thead className="sticky top-0 bg-gray-50">
                      <tr>
                        <th className="px-6 py-2 text-left text-xs font-medium text-gray-500">Row</th>
                        <th className="px-6 py-2 text-left text-xs font-medium text-gray-500">Status</th>
                        <th className="px-6 py-2 text-left text-xs font-medium text-gray-500">Issues</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {validationResults.map(row => (
                        <tr key={row.row_number} className={row.status === 'error' ? 'bg-red-50/30' : ''}>
                          <td className="px-6 py-2 text-gray-700">{row.row_number}</td>
                          <td className="px-6 py-2">
                            {row.status === 'valid' ? (
                              <span className="inline-flex items-center gap-1 text-emerald-600 text-xs font-medium">
                                <CheckCircle size={12} /> Valid
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-red-600 text-xs font-medium">
                                <AlertCircle size={12} /> Error
                              </span>
                            )}
                          </td>
                          <td className="px-6 py-2 text-xs text-gray-500">{row.errors.join('; ')}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            <div className="flex gap-3 mt-6">
              <button onClick={() => setStep(3)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
                Back
              </button>
              <button
                onClick={handleExecute}
                disabled={validating || validationResults.every(r => r.status === 'error')}
                className="px-5 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
              >
                Start Import
              </button>
            </div>
          </div>
        )}

        {/* Step 5: Import */}
        {step === 5 && (
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Importing Data</h2>
            <p className="text-sm text-gray-500 mb-6">
              {jobStatus?.status === 'completed' ? 'Import complete!' : 'Please wait while your data is being imported...'}
            </p>

            <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-6">
              {/* Progress bar */}
              <div className="mb-6">
                <div className="flex justify-between text-sm text-gray-600 mb-2">
                  <span>{jobStatus?.status === 'completed' ? 'Complete' : 'Importing...'}</span>
                  <span>{jobStatus?.progress || 0}%</span>
                </div>
                <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      jobStatus?.status === 'completed' ? 'bg-emerald-500' :
                      jobStatus?.status === 'failed' ? 'bg-red-500' : 'bg-blue-500'
                    }`}
                    style={{ width: `${jobStatus?.progress || 0}%` }}
                  />
                </div>
              </div>

              {/* Stats */}
              {jobStatus && (
                <div className="grid grid-cols-3 gap-4">
                  <div className="text-center p-4 bg-emerald-50 rounded-xl">
                    <p className="text-2xl font-semibold text-emerald-600">{jobStatus.imported}</p>
                    <p className="text-xs text-emerald-700 mt-1">Imported</p>
                  </div>
                  <div className="text-center p-4 bg-red-50 rounded-xl">
                    <p className="text-2xl font-semibold text-red-600">{jobStatus.failed}</p>
                    <p className="text-xs text-red-700 mt-1">Failed</p>
                  </div>
                  <div className="text-center p-4 bg-gray-50 rounded-xl">
                    <p className="text-2xl font-semibold text-gray-600">{jobStatus.skipped}</p>
                    <p className="text-xs text-gray-700 mt-1">Skipped</p>
                  </div>
                </div>
              )}

              {jobStatus?.status === 'completed' && (
                <div className="mt-6 text-center">
                  <CheckCircle size={32} className="text-emerald-500 mx-auto mb-2" />
                  <p className="font-medium text-gray-800">Migration Complete</p>
                  <p className="text-sm text-gray-500 mt-1">
                    Successfully imported {jobStatus.imported} of {jobStatus.total} records
                  </p>
                  <button
                    onClick={() => navigate('/patients')}
                    className="mt-4 px-5 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    View Patients
                  </button>
                </div>
              )}

              {executing && jobStatus?.status !== 'completed' && (
                <div className="mt-4 flex items-center justify-center gap-2 text-sm text-gray-500">
                  <Loader2 size={14} className="animate-spin" /> Processing...
                </div>
              )}
            </div>
          </div>
        )}
          </>
  )
}
