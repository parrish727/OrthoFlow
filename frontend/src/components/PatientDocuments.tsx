import { useState, useEffect, useCallback, useRef } from 'react'
import { FileText, ExternalLink, Loader2, Folder, FolderOpen, ChevronRight, ChevronDown, Upload, ArrowUpFromLine } from 'lucide-react'
import { api } from '../lib/api'

interface PatientDocument {
  id: string
  document_type: string
  title: string
  file_url: string | null
  original_filename: string | null
  mime_type: string | null
  uploaded_by_type: string
  direction: string
  notes: string | null
  created_at: string | null
}

const TYPE_LABELS: Record<string, string> = {
  tc_proposal: 'TC Proposals',
  contract: 'Contracts',
  consent: 'Consents',
  insurance: 'Insurance',
  letter: 'Letters',
  records: 'Records',
  patient_upload: 'Patient Uploads',
  general: 'Documents',
}

const ACCEPT = 'image/*,.pdf,.heic,.heif'

// Lists documents associated with a patient as a Finder-style folder tree, grouped by type.
// Supports secure office→patient upload (ClamAV-scanned, stored in MinIO) and presigned download.
// Patient-uploaded documents are flagged so staff can tell at a glance.
export default function PatientDocuments({ patientId, testId = 'patient-documents' }: { patientId: string; testId?: string }) {
  const [docs, setDocs] = useState<PatientDocument[]>([])
  const [loading, setLoading] = useState(true)
  const [openFolders, setOpenFolders] = useState<Record<string, boolean>>({})
  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState('')
  const [downloadingId, setDownloadingId] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.getPatientDocuments(patientId)
      if (res.ok) setDocs(await res.json())
    } catch {
      // silently handle
    }
    setLoading(false)
  }, [patientId])

  useEffect(() => { load() }, [load])

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setUploadMsg('')
    try {
      // Infer a reasonable document type/title; staff can re-file later.
      const title = file.name
      const res = await api.uploadPatientDocument(patientId, file, 'records', title)
      if (res.ok) {
        setUploadMsg('Uploaded ✓')
        await load()
      } else {
        const err = await res.json().catch(() => ({}))
        setUploadMsg(err.detail || 'Upload failed')
      }
    } catch {
      setUploadMsg('Upload failed')
    }
    setUploading(false)
    if (fileRef.current) fileRef.current.value = ''
  }

  async function openDoc(doc: PatientDocument) {
    setDownloadingId(doc.id)
    try {
      const res = await api.getDocumentDownloadUrl(patientId, doc.id)
      if (res.ok) {
        const { url } = await res.json()
        if (url) window.open(url, '_blank', 'noopener')
      }
    } catch {
      // silently handle
    }
    setDownloadingId(null)
  }

  const folders = docs.reduce<Record<string, PatientDocument[]>>((acc, d) => {
    const key = d.document_type || 'general'
    ;(acc[key] ||= []).push(d)
    return acc
  }, {})
  const folderKeys = Object.keys(folders).sort()

  function toggle(key: string) {
    setOpenFolders(prev => ({ ...prev, [key]: !prev[key] }))
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden" data-testid={testId}>
      <div className="px-5 py-3 border-b border-gray-100 flex items-center gap-2">
        <FileText size={14} className="text-gray-400" />
        <h3 className="text-sm font-semibold text-gray-800">Documents</h3>
        <span className="text-xs text-gray-400">{docs.length}</span>
        <div className="ml-auto flex items-center gap-2">
          {uploadMsg && <span className="text-[11px] text-gray-500" data-testid="doc-upload-msg">{uploadMsg}</span>}
          <input ref={fileRef} type="file" accept={ACCEPT} className="hidden" onChange={handleUpload} data-testid="doc-upload-input" />
          <button
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            className="flex items-center gap-1.5 text-xs font-medium text-white bg-teal-600 hover:bg-teal-700 disabled:opacity-60 px-2.5 py-1.5 rounded-lg transition-colors"
            data-testid="doc-upload-btn"
          >
            {uploading ? <Loader2 size={12} className="animate-spin" /> : <Upload size={12} />}
            {uploading ? 'Uploading…' : 'Upload'}
          </button>
        </div>
      </div>
      {loading ? (
        <div className="px-5 py-8 text-center">
          <Loader2 size={18} className="animate-spin text-gray-400 mx-auto" />
        </div>
      ) : docs.length === 0 ? (
        <div className="px-5 py-8 text-center">
          <FileText size={24} className="mx-auto text-gray-300 mb-2" />
          <p className="text-xs text-gray-500">No documents on file</p>
          <p className="text-[10px] text-gray-400 mt-1">Upload records or share with the patient — PDF, PNG, JPG, HEIC</p>
        </div>
      ) : (
        <div className="py-2 max-h-96 overflow-y-auto" data-testid="patient-documents-tree">
          {folderKeys.map(key => {
            const isOpen = openFolders[key] ?? true
            const items = folders[key]
            return (
              <div key={key} data-testid={`doc-folder-${key}`}>
                <button
                  onClick={() => toggle(key)}
                  className="w-full flex items-center gap-1.5 px-4 py-2 hover:bg-gray-50 transition-colors text-left"
                >
                  {isOpen ? <ChevronDown size={13} className="text-gray-400" /> : <ChevronRight size={13} className="text-gray-400" />}
                  {isOpen ? <FolderOpen size={15} className="text-teal-500" /> : <Folder size={15} className="text-teal-500" />}
                  <span className="text-sm font-medium text-gray-800">{TYPE_LABELS[key] || key}</span>
                  <span className="text-[10px] text-gray-400 ml-auto">{items.length}</span>
                </button>
                {isOpen && (
                  <div className="pl-8 pr-4 divide-y divide-gray-50">
                    {items.map(doc => {
                      const fromPatient = doc.direction === 'patient_to_office' || doc.uploaded_by_type === 'patient'
                      const hasFile = Boolean(doc.file_url) || doc.uploaded_by_type !== undefined
                      return (
                        <div key={doc.id} className="py-2 flex items-center justify-between gap-3" data-testid="patient-document-row">
                          <div className="min-w-0 flex items-center gap-2">
                            <FileText size={13} className="text-gray-400 shrink-0" />
                            <div className="min-w-0">
                              <p className="text-sm text-gray-800 truncate flex items-center gap-1.5">
                                {doc.title}
                                {fromPatient && (
                                  <span className="inline-flex items-center gap-0.5 text-[9px] font-semibold text-amber-700 bg-amber-100 px-1.5 py-0.5 rounded-full" data-testid="doc-from-patient">
                                    <ArrowUpFromLine size={9} /> From patient
                                  </span>
                                )}
                              </p>
                              {doc.notes && <p className="text-xs text-gray-500 truncate">{doc.notes}</p>}
                              <p className="text-[10px] text-gray-400">{doc.created_at ? new Date(doc.created_at).toLocaleDateString() : ''}</p>
                            </div>
                          </div>
                          <button
                            onClick={() => openDoc(doc)}
                            disabled={downloadingId === doc.id || !hasFile}
                            className="flex items-center gap-1 text-xs font-medium text-teal-600 hover:text-teal-700 whitespace-nowrap disabled:opacity-40"
                            data-testid="doc-open-btn"
                          >
                            {downloadingId === doc.id ? <Loader2 size={12} className="animate-spin" /> : <ExternalLink size={12} />} Open
                          </button>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
