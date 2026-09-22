import { useState, useEffect, useCallback } from 'react'
import { FileText, ExternalLink, Loader2, Folder, FolderOpen, ChevronRight, ChevronDown } from 'lucide-react'
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
  tc_proposal: 'TC Proposals',
  contract: 'Contracts',
  consent: 'Consents',
  insurance: 'Insurance',
  letter: 'Letters',
  records: 'Records',
  general: 'Documents',
}

// Lists documents associated with a patient as a Finder-style folder tree, grouped by type.
// Lives in the patient's Administrative tab. TC proposals, contracts, and letters save here.
export default function PatientDocuments({ patientId, testId = 'patient-documents' }: { patientId: string; testId?: string }) {
  const [docs, setDocs] = useState<PatientDocument[]>([])
  const [loading, setLoading] = useState(true)
  const [openFolders, setOpenFolders] = useState<Record<string, boolean>>({})

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

  // Group documents into folders by type (the patient's document folder tree).
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
                    {items.map(doc => (
                      <div key={doc.id} className="py-2 flex items-center justify-between gap-3" data-testid="patient-document-row">
                        <div className="min-w-0 flex items-center gap-2">
                          <FileText size={13} className="text-gray-400 shrink-0" />
                          <div className="min-w-0">
                            <p className="text-sm text-gray-800 truncate">{doc.title}</p>
                            {doc.notes && <p className="text-xs text-gray-500 truncate">{doc.notes}</p>}
                            <p className="text-[10px] text-gray-400">{doc.created_at ? new Date(doc.created_at).toLocaleDateString() : ''}</p>
                          </div>
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
          })}
        </div>
      )}
    </div>
  )
}
