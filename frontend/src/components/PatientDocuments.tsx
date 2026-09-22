import { useState, useEffect, useCallback } from 'react'
import { FileText, ExternalLink, Loader2 } from 'lucide-react'
import { api } from '../lib/api'

interface PatientDocument {
  id: string
  document_type: string
  title: string
  file_url: string | null
  mime_type: string | null
  notes: string | null
  created_at: string | null
}

const TYPE_LABELS: Record<string, string> = {
  tc_proposal: 'TC Proposal',
  contract: 'Contract',
  consent: 'Consent',
  insurance: 'Insurance',
  letter: 'Letter',
  general: 'Document',
}

// Lists documents associated with a patient. Lives in the patient's Administrative tab
// (Frontdesk/Finance view). TC proposals and contracts save into here in later phases.
export default function PatientDocuments({ patientId, testId = 'patient-documents' }: { patientId: string; testId?: string }) {
  const [docs, setDocs] = useState<PatientDocument[]>([])
  const [loading, setLoading] = useState(true)

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

  return (
    <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden" data-testid={testId}>
      <div className="px-5 py-3 border-b border-gray-100 flex items-center gap-2">
        <FileText size={14} className="text-gray-400" />
        <h3 className="text-sm font-semibold text-gray-800">Documents</h3>
        <span className="text-xs text-gray-400 ml-auto">{docs.length}</span>
      </div>
      {loading ? (
        <div className="px-5 py-8 text-center">
          <Loader2 size={18} className="animate-spin text-gray-400 mx-auto" />
        </div>
      ) : docs.length === 0 ? (
        <div className="px-5 py-8 text-center">
          <FileText size={24} className="mx-auto text-gray-300 mb-2" />
          <p className="text-xs text-gray-500">No documents on file</p>
          <p className="text-[10px] text-gray-400 mt-1">Saved TC proposals, contracts, and letters appear here</p>
        </div>
      ) : (
        <div className="divide-y divide-gray-50 max-h-96 overflow-y-auto">
          {docs.map(doc => (
            <div key={doc.id} className="px-5 py-3 flex items-center justify-between gap-3" data-testid="patient-document-row">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] uppercase tracking-wider font-medium text-teal-600 bg-teal-50 px-1.5 py-0.5 rounded">
                    {TYPE_LABELS[doc.document_type] || doc.document_type}
                  </span>
                  <p className="text-sm font-medium text-gray-800 truncate">{doc.title}</p>
                </div>
                {doc.notes && <p className="text-xs text-gray-500 mt-0.5 truncate">{doc.notes}</p>}
                <p className="text-[10px] text-gray-400 mt-0.5">
                  {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : ''}
                </p>
              </div>
              {doc.file_url && (
                <a href={doc.file_url} target="_blank" rel="noreferrer"
                   className="flex items-center gap-1 text-xs font-medium text-teal-600 hover:text-teal-700 whitespace-nowrap">
                  <ExternalLink size={12} /> Open
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
