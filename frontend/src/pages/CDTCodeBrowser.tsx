/**
 * CDTCodeBrowser — searchable CDT code catalog with category filtering.
 * Used standalone as a reference page and as a picker in treatment planning.
 * Fetches from /api/v1/catalog/cdt-codes and /api/v1/catalog/cdt-codes/categories
 */
import { useState, useEffect, useCallback } from 'react'
import { Search, Filter, BookOpen, DollarSign } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
function authFetch(path: string, opts: RequestInit = {}) {
  const token = localStorage.getItem('token')
  return fetch(`${API}${path}`, {
    ...opts,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...opts.headers },
  })
}

interface CDTCode {
  code: string
  category: string
  subcategory: string
  description: string
  short_description: string
  specialty: string
  is_common: boolean
  avg_fee: number
  tooth_specific: boolean
  surface_specific: boolean
}

interface CDTCategory {
  name: string
  count: number
}

const SPECIALTY_COLORS: Record<string, string> = {
  general: 'bg-blue-50 text-blue-700',
  ortho: 'bg-teal-50 text-teal-700',
  perio: 'bg-orange-50 text-orange-700',
  surgery: 'bg-red-50 text-red-700',
  endo: 'bg-purple-50 text-purple-700',
  prosth: 'bg-amber-50 text-amber-700',
}

interface CDTCodeBrowserProps {
  /** If provided, renders as a picker with select callback */
  onSelect?: (code: CDTCode) => void
  /** Compact mode for embedding in modals */
  compact?: boolean
}

export default function CDTCodeBrowser({ onSelect, compact }: CDTCodeBrowserProps) {
  const [codes, setCodes] = useState<CDTCode[]>([])
  const [categories, setCategories] = useState<CDTCategory[]>([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [selectedSpecialty, setSelectedSpecialty] = useState<string>('')
  const [commonOnly, setCommonOnly] = useState(false)

  const fetchCategories = useCallback(async () => {
    try {
      const res = await authFetch('/api/v1/catalog/cdt-codes/categories')
      if (res.ok) {
        const data = await res.json()
        setCategories(data.categories || [])
      }
    } catch { /* silent */ }
  }, [])

  const fetchCodes = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (query) params.set('q', query)
      if (selectedCategory) params.set('category', selectedCategory)
      if (selectedSpecialty) params.set('specialty', selectedSpecialty)
      if (commonOnly) params.set('common_only', 'true')
      params.set('limit', '50')

      const res = await authFetch(`/api/v1/catalog/cdt-codes?${params.toString()}`)
      if (res.ok) {
        const data = await res.json()
        setCodes(data.codes || [])
      }
    } catch { /* silent */ }
    setLoading(false)
  }, [query, selectedCategory, selectedSpecialty, commonOnly])

  useEffect(() => { fetchCategories() }, [fetchCategories])
  useEffect(() => {
    const debounce = setTimeout(fetchCodes, 300)
    return () => clearTimeout(debounce)
  }, [fetchCodes])

  return (
    <div className={`space-y-4 ${compact ? '' : 'p-0'}`}>
      {/* Header (non-compact only) */}
      {!compact && (
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">CDT Code Catalog</h1>
            <p className="text-xs text-gray-500 mt-0.5">Search and browse dental procedure codes</p>
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <BookOpen size={14} />
            <span>{codes.length} codes shown</span>
          </div>
        </div>
      )}

      {/* Search & Filters */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search by code or description..."
            value={query}
            onChange={e => setQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-xs border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400"
          />
        </div>

        <select
          value={selectedCategory}
          onChange={e => setSelectedCategory(e.target.value)}
          className="text-xs border border-gray-200 rounded-lg px-3 py-2 bg-white"
        >
          <option value="">All Categories</option>
          {categories.map(cat => (
            <option key={cat.name} value={cat.name}>
              {cat.name} ({cat.count})
            </option>
          ))}
        </select>

        <select
          value={selectedSpecialty}
          onChange={e => setSelectedSpecialty(e.target.value)}
          className="text-xs border border-gray-200 rounded-lg px-3 py-2 bg-white"
        >
          <option value="">All Specialties</option>
          <option value="general">General</option>
          <option value="ortho">Orthodontics</option>
          <option value="perio">Periodontics</option>
          <option value="surgery">Oral Surgery</option>
          <option value="endo">Endodontics</option>
          <option value="prosth">Prosthodontics</option>
        </select>

        <label className="flex items-center gap-1.5 text-xs text-gray-600 cursor-pointer">
          <input
            type="checkbox"
            checked={commonOnly}
            onChange={e => setCommonOnly(e.target.checked)}
            className="rounded border-gray-300 text-teal-600 focus:ring-teal-500"
          />
          Common only
        </label>
      </div>

      {/* Code List */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-sm text-gray-400">Loading CDT codes...</div>
        ) : codes.length === 0 ? (
          <div className="p-8 text-center">
            <BookOpen size={20} className="mx-auto text-gray-300 mb-2" />
            <p className="text-sm text-gray-400">No codes match your search</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100 max-h-[500px] overflow-y-auto">
            {codes.map(code => (
              <div
                key={code.code}
                onClick={onSelect ? () => onSelect(code) : undefined}
                className={`flex items-center gap-3 px-4 py-2.5 ${
                  onSelect ? 'cursor-pointer hover:bg-teal-50' : 'hover:bg-gray-50'
                } transition-colors`}
              >
                <div className="w-16 shrink-0">
                  <span className="text-xs font-mono font-semibold text-gray-900">{code.code}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-gray-700 truncate">{code.description}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[9px] text-gray-400">{code.category}</span>
                    {code.specialty && (
                      <span className={`px-1.5 py-0.5 text-[8px] font-medium rounded ${SPECIALTY_COLORS[code.specialty] || 'bg-gray-100 text-gray-600'}`}>
                        {code.specialty}
                      </span>
                    )}
                    {code.is_common && (
                      <span className="text-[8px] text-teal-600">★ common</span>
                    )}
                  </div>
                </div>
                {code.avg_fee > 0 && (
                  <div className="text-right shrink-0">
                    <span className="text-xs font-medium text-gray-700">${(code.avg_fee / 100).toFixed(0)}</span>
                  </div>
                )}
                {onSelect && (
                  <div className="shrink-0">
                    <span className="text-[9px] text-teal-600 font-medium">Select →</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
