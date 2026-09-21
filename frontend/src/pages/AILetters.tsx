import { useState, useEffect } from 'react'
import { Mail, Sparkles, Wand2, Save, Loader2, Check } from 'lucide-react'
import { api } from '../lib/api'

interface LetterType { key: string; description: string }

const TONES = ['professional', 'warm', 'firm', 'concise']
const POLISH_TONES = ['professional', 'warm', 'firm', 'concise', 'shorter', 'friendlier']

export default function AILetters() {
  const [types, setTypes] = useState<LetterType[]>([])
  const [letterType, setLetterType] = useState('school')
  const [tone, setTone] = useState('professional')
  const [context, setContext] = useState('')
  const [text, setText] = useState('')
  const [busy, setBusy] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [personalized, setPersonalized] = useState(false)

  useEffect(() => {
    api.getLetterTypes().then(async r => { if (r.ok) setTypes((await r.json()).types || []) })
  }, [])

  async function generate() {
    setBusy('generate'); setSaved(false)
    const r = await api.generateLetter({ letter_type: letterType, context, tone })
    if (r.ok) { const d = await r.json(); setText(d.letter_text || ''); setPersonalized(!!d.personalized) }
    else setText('AI is not available right now. Please try again.')
    setBusy(null)
  }

  async function polish(polishTone: string) {
    if (!text.trim()) return
    setBusy('polish')
    const r = await api.polishLetter({ text, tone: polishTone, letter_type: letterType })
    if (r.ok) { const d = await r.json(); setText(d.letter_text || text) }
    setBusy(null)
  }

  async function saveStyle() {
    if (text.trim().length < 20) return
    setBusy('save')
    const r = await api.saveLetterStyle({ letter_type: letterType, sample_text: text, tone })
    if (r.ok) setSaved(true)
    setBusy(null)
  }

  return (
    <div data-testid="ai-letters-page">
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-gray-900 flex items-center gap-2"><Mail size={22} className="text-teal-600" /> AI Letters</h2>
        <p className="text-sm text-gray-500 mt-0.5">Draft any letter type, then polish it in one click. OrthoFlow learns your writing style over time.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Controls */}
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-5 space-y-3">
          <label className="block"><span className="text-xs text-gray-500">Letter type</span>
            <select data-testid="letter-type" value={letterType} onChange={e => setLetterType(e.target.value)} className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm">
              {types.map(t => <option key={t.key} value={t.key}>{t.key.replace(/_/g, ' ')}</option>)}
            </select>
          </label>
          <label className="block"><span className="text-xs text-gray-500">Tone</span>
            <select value={tone} onChange={e => setTone(e.target.value)} className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm">
              {TONES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </label>
          <label className="block"><span className="text-xs text-gray-500">Context (optional)</span>
            <textarea value={context} onChange={e => setContext(e.target.value)} rows={4} placeholder="e.g. seen today for adjustment; treatment is medically necessary…" className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
          </label>
          <button data-testid="generate-letter" onClick={generate} disabled={busy !== null} className="w-full flex items-center justify-center gap-1.5 py-2.5 bg-teal-600 text-white rounded-lg text-sm font-medium hover:bg-teal-700 disabled:opacity-50">
            {busy === 'generate' ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />} Generate
          </button>
        </div>

        {/* Output + polish */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-gray-200/80 shadow-sm p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-gray-800">Letter</span>
            {personalized && <span className="text-[10px] text-violet-600 bg-violet-50 border border-violet-100 rounded-full px-2 py-0.5">Personalized to your style</span>}
          </div>
          <textarea data-testid="letter-text" value={text} onChange={e => { setText(e.target.value); setSaved(false) }} rows={16} placeholder="Generated letter appears here — edit freely, then polish or save your style." className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono" />
          <div className="flex flex-wrap items-center gap-2 mt-3">
            <span className="text-xs text-gray-500 flex items-center gap-1"><Wand2 size={13} /> Polish:</span>
            {POLISH_TONES.map(t => (
              <button key={t} data-testid={`polish-${t}`} onClick={() => polish(t)} disabled={busy !== null || !text.trim()} className="text-xs px-2.5 py-1 rounded-full border border-gray-200 hover:border-teal-300 hover:text-teal-700 disabled:opacity-40">
                {busy === 'polish' ? '…' : t}
              </button>
            ))}
            <button data-testid="save-style" onClick={saveStyle} disabled={busy !== null || text.trim().length < 20} className="ml-auto flex items-center gap-1 text-xs px-2.5 py-1 rounded-lg bg-violet-50 text-violet-700 border border-violet-200 hover:bg-violet-100 disabled:opacity-40">
              {saved ? <><Check size={12} /> Saved</> : <><Save size={12} /> Teach my style</>}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
