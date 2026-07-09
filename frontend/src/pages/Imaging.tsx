import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Image, ChevronDown, Users, LayoutDashboard, CalendarDays, BookOpen,
  Shield, FileText, Banknote, User, LogOut, Upload, Search, Filter,
  X, Trash2, Download, Eye, ChevronRight, MessageSquare, MessagesSquare,
  Camera, Bell,
} from 'lucide-react'
import { api } from '../lib/api'

interface PatientImage {
  id: string
  patient_id: string
  image_type: string
  description: string | null
  tooth_numbers: string | null
  file_name: string
  file_size: number
  modality: string | null
  source_device: string | null
  captured_at: string
  created_at: string
  thumbnail_url: string | null
  series_id: string | null
  series_name: string | null
}

interface ImageSeries {
  id: string
  name: string
  images: PatientImage[]
  created_at: string
}

interface Patient {
  id: string
  first_name: string
  last_name: string
}

const TYPE_BADGES: Record<string, string> = {
  pano: 'bg-blue-100 text-blue-700',
  ceph: 'bg-violet-100 text-violet-700',
  pa: 'bg-emerald-100 text-emerald-700',
  intraoral_photo: 'bg-amber-100 text-amber-700',
  cbct: 'bg-rose-100 text-rose-700',
  other: 'bg-gray-100 text-gray-700',
}

const TYPE_LABELS: Record<string, string> = {
  pano: 'Pano',
  ceph: 'Ceph',
  pa: 'PA',
  intraoral_photo: 'Photo',
  cbct: 'CBCT',
  other: 'Other',
}

export default function Imaging() {
  const [images, setImages] = useState<PatientImage[]>([])
  const [series, setSeries] = useState<ImageSeries[]>([])
  const [patients, setPatients] = useState<Patient[]>([])
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null)
  const [patientSearch, setPatientSearch] = useState('')
  const [showPatientList, setShowPatientList] = useState(false)
  const [loading, setLoading] = useState(false)
  const [filterType, setFilterType] = useState('')
  const [filterStartDate, setFilterStartDate] = useState('')
  const [filterEndDate, setFilterEndDate] = useState('')
  const [viewingImage, setViewingImage] = useState<PatientImage | null>(null)
  const [viewingUrl, setViewingUrl] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadType, setUploadType] = useState('pano')
  const [uploadDesc, setUploadDesc] = useState('')
  const [uploadTeeth, setUploadTeeth] = useState('')
  const [expandedSeries, setExpandedSeries] = useState<string[]>([])
  const [practiceName, setPracticeName] = useState('OrthoFlow')
  const [practiceLogo, setPracticeLogo] = useState('')
  const [menuOpen, setMenuOpen] = useState(false)
  const navigate = useNavigate()
  const menuRef = useRef<HTMLDivElement>(null)
  const patientRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false)
      if (patientRef.current && !patientRef.current.contains(e.target as Node)) setShowPatientList(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  useEffect(() => {
    api.getPractice().then(async res => {
      if (res.ok) { const data = await res.json(); setPracticeName(data.name || 'OrthoFlow'); setPracticeLogo(data.logo_url || '') }
    })
  }, [])

  useEffect(() => {
    if (!patientSearch || patientSearch.length < 2) { setPatients([]); return }
    const timer = setTimeout(async () => {
      const res = await api.getPatients({ search: patientSearch })
      if (res.ok) {
        const data = await res.json()
        setPatients(data.patients || data || [])
        setShowPatientList(true)
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [patientSearch])

  const loadImages = useCallback(async () => {
    if (!selectedPatient) return
    setLoading(true)
    const res = await api.getPatientImages(selectedPatient.id, {
      image_type: filterType || undefined,
      start_date: filterStartDate || undefined,
      end_date: filterEndDate || undefined,
    })
    if (res.ok) {
      const data = await res.json()
      setImages(data.images || [])
      setSeries(data.series || [])
    }
    setLoading(false)
  }, [selectedPatient, filterType, filterStartDate, filterEndDate])

  useEffect(() => { loadImages() }, [loadImages])

  async function handleViewImage(img: PatientImage) {
    setViewingImage(img)
    const url = await api.getImageViewUrl(img.id)
    setViewingUrl(url)
  }

  function closeViewer() {
    if (viewingUrl) URL.revokeObjectURL(viewingUrl)
    setViewingUrl('')
    setViewingImage(null)
  }

  async function handleDelete(id: string) {
    if (!confirm('Delete this image permanently?')) return
    const res = await api.deleteImage(id)
    if (res.ok) loadImages()
  }

  async function handleUpload(files: FileList | null) {
    if (!files?.length || !selectedPatient) return
    setUploading(true)
    for (const file of Array.from(files)) {
      const form = new FormData()
      form.append('file', file)
      form.append('patient_id', selectedPatient.id)
      form.append('image_type', uploadType)
      if (uploadDesc) form.append('description', uploadDesc)
      if (uploadTeeth) form.append('tooth_numbers', uploadTeeth)
      await api.uploadImage(form)
    }
    setUploading(false)
    setUploadDesc('')
    setUploadTeeth('')
    loadImages()
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragOver(false)
    handleUpload(e.dataTransfer.files)
  }

  function formatBytes(bytes: number): string {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / 1048576).toFixed(1) + ' MB'
  }

  function toggleSeries(id: string) {
    setExpandedSeries(prev => prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id])
  }

  return (
    <div className="min-h-screen bg-[#f5f5f7]">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-xl border-b border-gray-200/50 sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {practiceLogo ? (
              <img src={practiceLogo} alt="" className="w-8 h-8 rounded-lg object-contain" />
            ) : (
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
                <Camera size={16} className="text-white" />
              </div>
            )}
            <div>
              <h1 className="text-lg font-semibold text-gray-900 tracking-tight">{practiceName}</h1>
              <p className="text-xs text-gray-500">Imaging</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="relative" ref={menuRef}>
              <button onClick={() => setMenuOpen(!menuOpen)} className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors">
                Menu <ChevronDown size={14} className={`transition-transform ${menuOpen ? 'rotate-180' : ''}`} />
              </button>
              {menuOpen && (
                <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl border border-gray-200 shadow-lg py-2 z-50">
                  <DropdownItem icon={LayoutDashboard} label="Dashboard" description="Overview & upload" onClick={() => { setMenuOpen(false); navigate('/') }} />
                  <DropdownItem icon={CalendarDays} label="Schedule" description="Daily appointment board" onClick={() => { setMenuOpen(false); navigate('/schedule') }} />
                  <DropdownItem icon={Users} label="Patients" description="Patient records" onClick={() => { setMenuOpen(false); navigate('/patients') }} />
                  <DropdownItem icon={BookOpen} label="Ledger" description="Patient financials" onClick={() => { setMenuOpen(false); navigate('/ledger') }} />
                  <DropdownItem icon={Shield} label="Insurance" description="Plans & eligibility" onClick={() => { setMenuOpen(false); navigate('/insurance') }} />
                  <DropdownItem icon={FileText} label="Claims" description="Claims management" onClick={() => { setMenuOpen(false); navigate('/claims') }} />
                  <DropdownItem icon={Banknote} label="Payments" description="Payment posting" onClick={() => { setMenuOpen(false); navigate('/payments') }} />
                  <DropdownItem icon={MessageSquare} label="Communications" description="Templates & send" onClick={() => { setMenuOpen(false); navigate('/communications') }} />
                  <DropdownItem icon={MessagesSquare} label="Messages" description="Delivery log" onClick={() => { setMenuOpen(false); navigate('/messages') }} />
                  <DropdownItem icon={Camera} label="Imaging" description="Patient images" onClick={() => { setMenuOpen(false); navigate('/imaging') }} />
                  <DropdownItem icon={Bell} label="Imaging Alerts" description="Overdue imaging" onClick={() => { setMenuOpen(false); navigate('/imaging/alerts') }} />
                  <div className="border-t border-gray-100 my-2" />
                  <DropdownItem icon={User} label="Account" description="Profile & team" onClick={() => { setMenuOpen(false); navigate('/account') }} />
                  <DropdownItem icon={LogOut} label="Sign Out" description="" onClick={() => { localStorage.clear(); navigate('/login') }} />
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-semibold text-gray-900">Imaging</h2>
            <p className="text-sm text-gray-500 mt-0.5">Patient imaging gallery & upload</p>
          </div>
        </div>

        {/* Patient Selector */}
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-5 mb-6">
          <label className="text-sm font-medium text-gray-700 mb-2 block">Select Patient</label>
          <div className="relative" ref={patientRef}>
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search patients by name..."
              value={patientSearch}
              onChange={e => { setPatientSearch(e.target.value); setSelectedPatient(null) }}
              className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400"
            />
            {showPatientList && patients.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-xl shadow-lg z-20 max-h-48 overflow-y-auto">
                {patients.map(p => (
                  <button
                    key={p.id}
                    onClick={() => { setSelectedPatient(p); setPatientSearch(`${p.first_name} ${p.last_name}`); setShowPatientList(false) }}
                    className="w-full px-4 py-2.5 text-left text-sm hover:bg-gray-50 transition-colors"
                  >
                    {p.first_name} {p.last_name}
                  </button>
                ))}
              </div>
            )}
          </div>
          {selectedPatient && (
            <p className="text-xs text-emerald-600 mt-2">Selected: {selectedPatient.first_name} {selectedPatient.last_name}</p>
          )}
        </div>

        {selectedPatient && (
          <>
            {/* Filter Bar */}
            <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-5 mb-6">
              <div className="flex items-center gap-2 mb-3">
                <Filter size={14} className="text-gray-400" />
                <span className="text-sm font-medium text-gray-700">Filters</span>
              </div>
              <div className="flex flex-wrap gap-3">
                <select
                  value={filterType}
                  onChange={e => setFilterType(e.target.value)}
                  className="px-3 py-2 rounded-lg border border-gray-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                >
                  <option value="">All Types</option>
                  <option value="pano">Panoramic</option>
                  <option value="ceph">Cephalometric</option>
                  <option value="pa">Periapical</option>
                  <option value="intraoral_photo">Intraoral Photo</option>
                  <option value="cbct">CBCT</option>
                  <option value="other">Other</option>
                </select>
                <input type="date" value={filterStartDate} onChange={e => setFilterStartDate(e.target.value)} className="px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20" placeholder="Start date" />
                <input type="date" value={filterEndDate} onChange={e => setFilterEndDate(e.target.value)} className="px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20" placeholder="End date" />
                {(filterType || filterStartDate || filterEndDate) && (
                  <button onClick={() => { setFilterType(''); setFilterStartDate(''); setFilterEndDate('') }} className="px-3 py-2 text-sm text-gray-500 hover:text-gray-700 transition-colors">
                    Clear
                  </button>
                )}
              </div>
            </div>

            {/* Upload Zone */}
            <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-5 mb-6">
              <h3 className="text-sm font-medium text-gray-700 mb-3">Upload Images</h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
                <select value={uploadType} onChange={e => setUploadType(e.target.value)} className="px-3 py-2 rounded-lg border border-gray-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20">
                  <option value="pano">Panoramic</option>
                  <option value="ceph">Cephalometric</option>
                  <option value="pa">Periapical</option>
                  <option value="intraoral_photo">Intraoral Photo</option>
                  <option value="cbct">CBCT</option>
                  <option value="other">Other</option>
                </select>
                <input type="text" placeholder="Description (optional)" value={uploadDesc} onChange={e => setUploadDesc(e.target.value)} className="px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20" />
                <input type="text" placeholder="Tooth #s (optional)" value={uploadTeeth} onChange={e => setUploadTeeth(e.target.value)} className="px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20" />
              </div>
              <div
                onDragOver={e => { e.preventDefault(); setDragOver(true) }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all duration-200 ${dragOver ? 'border-blue-400 bg-blue-50/50 scale-[1.01]' : 'border-gray-200 hover:border-gray-300 bg-gray-50/50'}`}
              >
                <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <Upload className="text-gray-400" size={18} />
                </div>
                <p className="text-gray-700 font-medium text-sm">{uploading ? 'Uploading...' : 'Drop images here'}</p>
                <p className="text-gray-400 text-xs mt-1 mb-3">DICOM, PNG, JPG, or PDF</p>
                <input type="file" multiple accept=".dcm,.png,.jpg,.jpeg,.pdf,.tiff" onChange={e => handleUpload(e.target.files)} className="hidden" id="imaging-upload" />
                <label htmlFor="imaging-upload" className="inline-block px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-full cursor-pointer text-sm font-medium transition-colors shadow-sm">
                  Choose Files
                </label>
              </div>
            </div>

            {/* Image Gallery */}
            <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden mb-6">
              <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
                <h3 className="font-medium text-gray-800">Image Gallery</h3>
                <span className="text-xs text-gray-400">{images.length} image{images.length !== 1 ? 's' : ''}</span>
              </div>
              {loading ? (
                <div className="px-6 py-16 text-center"><p className="text-gray-400 text-sm">Loading images...</p></div>
              ) : images.length === 0 ? (
                <div className="px-6 py-16 text-center">
                  <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Image className="text-gray-300" size={28} />
                  </div>
                  <p className="text-gray-500 font-medium">No images found</p>
                  <p className="text-gray-400 text-sm mt-1">Upload images above or adjust your filters</p>
                </div>
              ) : (
                <div className="p-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
                  {images.filter(img => !img.series_id).map(img => (
                    <div key={img.id} className="group relative">
                      <div
                        onClick={() => handleViewImage(img)}
                        className="aspect-square rounded-xl overflow-hidden bg-gray-100 cursor-pointer border border-gray-200/50 hover:border-blue-300 transition-colors"
                      >
                        {img.thumbnail_url ? (
                          <img src={img.thumbnail_url} alt={img.description || img.image_type} className="w-full h-full object-cover" />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            <Image size={24} className="text-gray-300" />
                          </div>
                        )}
                        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors rounded-xl flex items-center justify-center">
                          <Eye size={20} className="text-white opacity-0 group-hover:opacity-100 transition-opacity" />
                        </div>
                      </div>
                      <div className="mt-2 flex items-center justify-between">
                        <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${TYPE_BADGES[img.image_type] || TYPE_BADGES.other}`}>
                          {TYPE_LABELS[img.image_type] || img.image_type}
                        </span>
                        <span className="text-xs text-gray-400">{new Date(img.captured_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Series Section */}
            {series.length > 0 && (
              <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden mb-6">
                <div className="px-6 py-4 border-b border-gray-100">
                  <h3 className="font-medium text-gray-800">Image Series</h3>
                </div>
                <div className="divide-y divide-gray-50">
                  {series.map(s => (
                    <div key={s.id}>
                      <button
                        onClick={() => toggleSeries(s.id)}
                        className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50/50 transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <ChevronRight size={16} className={`text-gray-400 transition-transform ${expandedSeries.includes(s.id) ? 'rotate-90' : ''}`} />
                          <div className="text-left">
                            <p className="text-sm font-medium text-gray-800">{s.name}</p>
                            <p className="text-xs text-gray-400">{s.images.length} images • {new Date(s.created_at).toLocaleDateString()}</p>
                          </div>
                        </div>
                      </button>
                      {expandedSeries.includes(s.id) && (
                        <div className="px-6 pb-4 grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 gap-3">
                          {s.images.map(img => (
                            <div key={img.id} onClick={() => handleViewImage(img)} className="aspect-square rounded-lg overflow-hidden bg-gray-100 cursor-pointer border border-gray-200/50 hover:border-blue-300 transition-colors">
                              {img.thumbnail_url ? (
                                <img src={img.thumbnail_url} alt="" className="w-full h-full object-cover" />
                              ) : (
                                <div className="w-full h-full flex items-center justify-center"><Image size={16} className="text-gray-300" /></div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </main>

      {/* Full-screen Image Viewer */}
      {viewingImage && (
        <div className="fixed inset-0 bg-black/80 z-50 flex">
          <div className="flex-1 flex items-center justify-center p-4">
            {viewingUrl ? (
              <img src={viewingUrl} alt={viewingImage.description || ''} className="max-w-full max-h-full object-contain rounded-lg" />
            ) : (
              <p className="text-white text-sm">Loading...</p>
            )}
          </div>
          <div className="w-80 bg-white p-6 overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h3 className="font-semibold text-gray-900">Image Details</h3>
              <button onClick={closeViewer} className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
                <X size={18} className="text-gray-500" />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <p className="text-xs text-gray-500 mb-1">Type</p>
                <span className={`inline-flex px-2.5 py-1 rounded-full text-xs font-medium ${TYPE_BADGES[viewingImage.image_type] || TYPE_BADGES.other}`}>
                  {TYPE_LABELS[viewingImage.image_type] || viewingImage.image_type}
                </span>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Captured</p>
                <p className="text-sm text-gray-800">{new Date(viewingImage.captured_at).toLocaleString()}</p>
              </div>
              {viewingImage.modality && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Modality</p>
                  <p className="text-sm text-gray-800">{viewingImage.modality}</p>
                </div>
              )}
              <div>
                <p className="text-xs text-gray-500 mb-1">File Size</p>
                <p className="text-sm text-gray-800">{formatBytes(viewingImage.file_size)}</p>
              </div>
              {viewingImage.source_device && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Source Device</p>
                  <p className="text-sm text-gray-800">{viewingImage.source_device}</p>
                </div>
              )}
              {viewingImage.description && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Description</p>
                  <p className="text-sm text-gray-800">{viewingImage.description}</p>
                </div>
              )}
              {viewingImage.tooth_numbers && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Tooth Numbers</p>
                  <p className="text-sm text-gray-800">{viewingImage.tooth_numbers}</p>
                </div>
              )}
              <div className="pt-4 border-t border-gray-100 flex gap-2">
                <a href={viewingUrl} download={viewingImage.file_name} className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-600 hover:text-gray-900 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                  <Download size={14} /> Download
                </a>
                <button onClick={() => { closeViewer(); handleDelete(viewingImage.id) }} className="flex items-center gap-1.5 px-3 py-2 text-sm text-red-600 hover:text-red-700 border border-red-200 rounded-lg hover:bg-red-50 transition-colors">
                  <Trash2 size={14} /> Delete
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function DropdownItem({ icon: Icon, label, description, onClick }: { icon: React.ComponentType<{ size?: number; className?: string }>; label: string; description: string; onClick: () => void }) {
  return (
    <button onClick={onClick} className="w-full px-4 py-2.5 flex items-center gap-3 hover:bg-gray-50 transition-colors text-left">
      <Icon size={16} className="text-gray-400 flex-shrink-0" />
      <div>
        <p className="text-sm font-medium text-gray-700">{label}</p>
        {description && <p className="text-xs text-gray-400">{description}</p>}
      </div>
    </button>
  )
}
