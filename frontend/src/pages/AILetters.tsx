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
  const [suggestions, setSuggestions] = useState<{ letter_type: string; use_count: number; has_saved_style: boolean }[]>([])
  const [contacts, setContacts] = useState<{ id: string; name: string; practice_name: string | null; email: string | null }[]>([])
  const [toEmail, setToEmail] = useState('')
  const [sendMsg, setSendMsg] = useState<string | null>(null)

  useEffect(() => {
    api.getLetterTypes().then(async r => { if (r.ok) setTypes((await r.json()).types || []) })
    loadSuggestions()
    api.getReferringContacts().then(async r => { if (r.ok) setContacts((await r.json()).contacts || []) }).catch(() => {})
  }, [])

  async function sendLetterEmail() {
    if (!toEmail.trim() || !text.trim()) { setSendMsg('Pick a recipient and generate a letter first.'); return }
    setBusy('send'); setSendMsg(null)
    const r = await api.sendLetter({
      to_email: toEmail.trim(),
      subject: (types.find(t => t.key === letterType)?.description || 'Letter from your orthodontic office'),
      body: text,
      thank_you: 'Thank you,',
    })
    if (r.ok) {
      const d = await r.json()
      setSendMsg(d.sent ? `Sent to ${toEmail} ✓` : (d.message || 'Email relay not configured — set SMTP to send.'))
    } else setSendMsg('Send failed.')
    setBusy(null)
  }

  async function loadSuggestions() {
    try {
      const r = await api.getLetterSuggestions()
      if (r.ok) { const d = await r.json(); setSuggestions((d.suggestions || []).filter((s: { use_count: number }) => s.use_count > 0).slice(0, 4)) }
    } catch { /* silent */ }
  }

  async function generate() {
    setBusy('generate'); setSaved(false)
    const r = await api.generateLetter({ letter_type: letterType, context, tone })
    if (r.ok) { const d = await r.json(); setText(d.letter_text || ''); setPersonalized(!!d.personalized); loadSuggestions() }
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

      {/* AI usage-based suggestions — your most-used letter types, one click to select */}
      {suggestions.length > 0 && (
        <div data-testid="letter-suggestions" className="mb-5 bg-violet-50/60 border border-violet-100 rounded-2xl px-4 py-3">
          <div className="flex items-center gap-1.5 mb-2">
            <Sparkles size={14} className="text-violet-600" />
            <span className="text-xs font-semibold text-violet-800">You use these most</span>
            <span className="text-[11px] text-violet-500">— one click to start</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {suggestions.map(s => (
              <button
                key={s.letter_type}
                data-testid={`suggestion-${s.letter_type}`}
                onClick={() => setLetterType(s.letter_type)}
                className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border transition-colors ${
                  letterType === s.letter_type
                    ? 'bg-violet-600 text-white border-violet-600'
                    : 'bg-white text-violet-700 border-violet-200 hover:bg-violet-100'
                }`}
              >
                {s.letter_type.replace(/_/g, ' ')}
                <span className={`text-[9px] rounded-full px-1.5 ${letterType === s.letter_type ? 'bg-violet-500' : 'bg-violet-100 text-violet-600'}`}>{s.use_count}×</span>
                {s.has_saved_style && <Check size={10} className={letterType === s.letter_type ? 'text-white' : 'text-violet-500'} />}
              </button>
            ))}
          </div>
        </div>
      )}

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

          {/* Send to a recipient email via the built-in relay (e.g. a referring doctor) */}
          <div className="mt-4 pt-4 border-t border-gray-100" data-testid="letter-send-panel">
            <div className="flex items-center gap-1.5 mb-2">
              <Mail size={13} className="text-teal-600" />
              <span className="text-xs font-semibold text-gray-700">Send this letter by email</span>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <select
                data-testid="letter-contact-select"
                value={toEmail}
                onChange={e => setToEmail(e.target.value)}
                className="text-xs border border-gray-200 rounded-lg px-2 py-1.5 bg-white"
              >
                <option value="">Referring doctor…</option>
                {contacts.filter(c => c.email).map(c => (
                  <option key={c.id} value={c.email as string}>{c.name}{c.practice_name ? ` — ${c.practice_name}` : ''}</option>
                ))}
              </select>
              <input
                data-testid="letter-to-email"
                type="email"
                value={toEmail}
                onChange={e => setToEmail(e.target.value)}
                placeholder="or type an email…"
                className="flex-1 min-w-[180px] text-xs border border-gray-200 rounded-lg px-2.5 py-1.5"
              />
              <button
                data-testid="letter-send"
                onClick={sendLetterEmail}
                disabled={busy !== null || !text.trim() || !toEmail.trim()}
                className="text-xs px-3 py-1.5 rounded-lg bg-teal-600 text-white font-medium hover:bg-teal-700 disabled:opacity-40"
              >{busy === 'send' ? 'Sending…' : 'Send'}</button>
            </div>
            {sendMsg && <p data-testid="letter-send-msg" className="text-[11px] text-gray-600 mt-1.5">{sendMsg}</p>}
          </div>
        </div>
      </div>
    </div>
  )
}
