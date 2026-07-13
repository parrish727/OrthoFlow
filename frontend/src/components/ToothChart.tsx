import { useState } from 'react'
import { X } from 'lucide-react'

interface ToothData {
  bracket_type?: string
  wire?: string
  band?: boolean
  condition?: string
  notes?: string
}

interface ToothChartProps {
  teethData: Record<string, ToothData>
  upperWire: string | null
  lowerWire: string | null
  upperWireDate: string | null
  lowerWireDate: string | null
  appliances: Array<{ name: string; placed_date?: string }>
  onUpdate?: (data: {
    teeth_data: Record<string, ToothData>
    upper_wire?: string
    lower_wire?: string
    appliances?: Array<{ name: string; placed_date?: string }>
  }) => void
  readOnly?: boolean
}

// Universal orthodontic numbering (1-32)
const UPPER_TEETH = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
const LOWER_TEETH = [32, 31, 30, 29, 28, 27, 26, 25, 24, 23, 22, 21, 20, 19, 18, 17]

const BRACKET_TYPES = ['Standard', 'Self-Ligating', 'Ceramic', 'Lingual']
const CONDITIONS = ['Healthy', 'Decayed', 'Missing', 'Impacted', 'Extracted', 'Crown', 'Implant']

export default function ToothChart({
  teethData,
  upperWire,
  lowerWire,
  upperWireDate,
  lowerWireDate,
  appliances,
  onUpdate,
  readOnly = false,
}: ToothChartProps) {
  const [selectedTooth, setSelectedTooth] = useState<number | null>(null)
  const [localTeeth, setLocalTeeth] = useState<Record<string, ToothData>>(teethData)

  function getToothStyle(toothNum: number): string {
    const data = localTeeth[String(toothNum)]
    if (!data) return 'bg-white border-gray-300 hover:border-blue-400'
    if (data.condition === 'Missing' || data.condition === 'Extracted') return 'bg-red-50 border-red-300'
    if (data.bracket_type && data.bracket_type !== 'None') return 'bg-blue-50 border-blue-400'
    if (data.condition === 'Decayed') return 'bg-amber-50 border-amber-400'
    return 'bg-white border-gray-300 hover:border-blue-400'
  }

  function isExtracted(toothNum: number): boolean {
    const data = localTeeth[String(toothNum)]
    return data?.condition === "Missing" || data?.condition === "Extracted"
  }

  function hasBand(toothNum: number): boolean {
    const data = localTeeth[String(toothNum)]
    return !!data?.band
  }

  function hasBracket(toothNum: number): boolean {
    const data = localTeeth[String(toothNum)]
    return !!data?.bracket_type && data.bracket_type !== 'None'
  }

  function handleToothUpdate(toothNum: number, field: string, value: string | boolean) {
    if (readOnly) return
    const key = String(toothNum)
    const updated = { ...localTeeth, [key]: { ...localTeeth[key], [field]: value } }
    setLocalTeeth(updated)
    onUpdate?.({ teeth_data: updated })
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-5">
      <h3 className="text-sm font-semibold text-gray-800 mb-4">Tooth Chart</h3>

      {/* Wire Info */}
      <div className="flex flex-wrap gap-4 mb-4 text-xs">
        {upperWire && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 bg-violet-50 rounded-lg border border-violet-200">
            <span className="font-medium text-violet-700">Upper:</span>
            <span className="text-violet-600">{upperWire}</span>
            {upperWireDate && <span className="text-violet-400 ml-1">({upperWireDate})</span>}
          </div>
        )}
        {lowerWire && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 bg-indigo-50 rounded-lg border border-indigo-200">
            <span className="font-medium text-indigo-700">Lower:</span>
            <span className="text-indigo-600">{lowerWire}</span>
            {lowerWireDate && <span className="text-indigo-400 ml-1">({lowerWireDate})</span>}
          </div>
        )}
      </div>

      {/* Tooth Grid */}
      <div className="space-y-3">
        {/* Upper arch */}
        <div>
          <p className="text-[10px] uppercase text-gray-400 font-medium tracking-wider mb-1.5">Upper Arch</p>
          <div className="flex gap-1 justify-center flex-wrap">
            {UPPER_TEETH.map(num => (
              <button
                key={num}
                onClick={() => !readOnly && setSelectedTooth(num === selectedTooth ? null : num)}
                className={`w-8 h-10 rounded-lg border-2 flex flex-col items-center justify-center text-[10px] font-medium transition-all relative ${getToothStyle(num)} ${selectedTooth === num ? 'ring-2 ring-blue-500 ring-offset-1' : ''}`}
                aria-label={`Tooth ${num}`}
              >
                <span className="text-gray-600">{num}</span>
                {hasBracket(num) && (
                  <div className="w-2 h-2 bg-blue-500 rounded-sm absolute bottom-1" />
                )}
                {hasBand(num) && (
                  <div className="absolute inset-0 rounded-lg border-2 border-amber-500 pointer-events-none" />
                )}
                {isExtracted(num) && (
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    <span className="text-red-500 font-bold text-sm">✕</span>
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Lower arch */}
        <div>
          <p className="text-[10px] uppercase text-gray-400 font-medium tracking-wider mb-1.5">Lower Arch</p>
          <div className="flex gap-1 justify-center flex-wrap">
            {LOWER_TEETH.map(num => (
              <button
                key={num}
                onClick={() => !readOnly && setSelectedTooth(num === selectedTooth ? null : num)}
                className={`w-8 h-10 rounded-lg border-2 flex flex-col items-center justify-center text-[10px] font-medium transition-all relative ${getToothStyle(num)} ${selectedTooth === num ? 'ring-2 ring-blue-500 ring-offset-1' : ''}`}
                aria-label={`Tooth ${num}`}
              >
                <span className="text-gray-600">{num}</span>
                {hasBracket(num) && (
                  <div className="w-2 h-2 bg-blue-500 rounded-sm absolute top-1" />
                )}
                {hasBand(num) && (
                  <div className="absolute inset-0 rounded-lg border-2 border-amber-500 pointer-events-none" />
                )}
                {isExtracted(num) && (
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    <span className="text-red-500 font-bold text-sm">✕</span>
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Tooth Edit Panel */}
      {selectedTooth !== null && !readOnly && (
        <div className="mt-4 p-4 bg-gray-50 rounded-xl border border-gray-200 relative">
          <button
            onClick={() => setSelectedTooth(null)}
            className="absolute top-2 right-2 p-1 hover:bg-gray-200 rounded-lg transition-colors"
            aria-label="Close"
          >
            <X size={14} className="text-gray-500" />
          </button>
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-xs font-semibold text-gray-700">Tooth #{selectedTooth}</h4>
            <button
              onClick={() => {
                const key = String(selectedTooth)
                const updated = { ...localTeeth }
                delete updated[key]
                setLocalTeeth(updated)
                onUpdate?.({ teeth_data: updated })
              }}
              className="text-[10px] px-2 py-0.5 text-red-600 hover:bg-red-50 rounded transition-colors"
            >
              Clear
            </button>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] uppercase text-gray-500 font-medium">Bracket Type</label>
              <select
                value={localTeeth[String(selectedTooth)]?.bracket_type || ''}
                onChange={e => handleToothUpdate(selectedTooth, 'bracket_type', e.target.value)}
                className="w-full mt-1 px-2 py-1.5 text-xs border border-gray-200 rounded-lg bg-white"
              >
                <option value="">None</option>
                {BRACKET_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="text-[10px] uppercase text-gray-500 font-medium">Condition</label>
              <select
                value={localTeeth[String(selectedTooth)]?.condition || ''}
                onChange={e => handleToothUpdate(selectedTooth, 'condition', e.target.value)}
                className="w-full mt-1 px-2 py-1.5 text-xs border border-gray-200 rounded-lg bg-white"
              >
                <option value="">Healthy</option>
                {CONDITIONS.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div className="col-span-2">
              <label className="flex items-center gap-2 text-xs text-gray-600 cursor-pointer">
                <input
                  type="checkbox"
                  checked={localTeeth[String(selectedTooth)]?.band || false}
                  onChange={e => handleToothUpdate(selectedTooth, 'band', e.target.checked)}
                  className="rounded border-gray-300"
                />
                Band placed
              </label>
            </div>
          </div>
        </div>
      )}

      {/* Appliances */}
      {appliances.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <h4 className="text-xs font-semibold text-gray-700 mb-2">Appliances</h4>
          <div className="flex flex-wrap gap-2">
            {appliances.map((a, i) => (
              <span key={i} className="px-2.5 py-1 text-xs bg-gray-100 text-gray-600 rounded-lg border border-gray-200">
                {a.name} {a.placed_date && <span className="text-gray-400">({a.placed_date})</span>}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
