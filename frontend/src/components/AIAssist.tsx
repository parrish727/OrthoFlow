import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Sparkles, AlertTriangle, Info, ChevronRight, CheckCircle2 } from 'lucide-react'
import { api } from '../lib/api'
import { useAuth } from '../hooks/useAuth'

interface AIAction {
  severity: 'critical' | 'warning' | 'info'
  category: string
  title: string
  detail: string
  count: number
  action_route: string
}

const SEV_STYLE: Record<string, { ring: string; icon: typeof Info; iconColor: string }> = {
  critical: { ring: 'border-l-red-400 bg-red-50/40', icon: AlertTriangle, iconColor: 'text-red-500' },
  warning: { ring: 'border-l-amber-400 bg-amber-50/40', icon: AlertTriangle, iconColor: 'text-amber-500' },
  info: { ring: 'border-l-sky-400 bg-sky-50/40', icon: Info, iconColor: 'text-sky-500' },
}

// Map JWT roles → AI assist role keys.
const ROLE_MAP: Record<string, string> = {
  owner: 'owner', doctor: 'doctor', office_manager: 'office_manager',
  front_desk: 'front_desk', dental_assistant: 'doctor',
}

export default function AIAssist() {
  const navigate = useNavigate()
  const { role } = useAuth()
  const [actions, setActions] = useState<AIAction[]>([])
  const [headline, setHeadline] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const assistRole = ROLE_MAP[role] || 'owner'
    api.getAIAssist(assistRole).then(async r => {
      if (r.ok) {
        const d = await r.json()
        setActions(d.actions || [])
        setHeadline(d.headline || '')
      }
    }).catch(() => {}).finally(() => setLoading(false))
  }, [role])

  return (
    <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden" data-testid="ai-assist">
      <div className="px-5 py-3 border-b border-gray-100 flex items-center gap-2 bg-gradient-to-r from-violet-50 to-white">
        <Sparkles size={16} className="text-violet-500" />
        <h3 className="text-sm font-semibold text-gray-900">OrthoFlow AI — What needs attention</h3>
        {actions.length > 0 && (
          <span className="ml-auto text-[10px] font-semibold px-2 py-0.5 rounded-full bg-violet-100 text-violet-700">
            {actions.length}
          </span>
        )}
      </div>
      <div className="p-3 space-y-2">
        {loading ? (
          <div className="space-y-2">{[1, 2, 3].map(i => <div key={i} className="h-14 bg-gray-50 rounded-xl animate-pulse" />)}</div>
        ) : actions.length === 0 ? (
          <div className="flex items-center gap-2 text-sm text-gray-500 py-4 px-2">
            <CheckCircle2 size={16} className="text-emerald-500" />
            {headline || "You're all caught up — nothing needs attention right now."}
          </div>
        ) : (
          actions.map((a, i) => {
            const s = SEV_STYLE[a.severity] || SEV_STYLE.info
            const Icon = s.icon
            return (
              <button
                key={i}
                data-testid={`ai-action-${a.category}`}
                onClick={() => navigate(a.action_route)}
                className={`w-full text-left flex items-start gap-2.5 rounded-xl border border-gray-200/70 border-l-4 px-3 py-2.5 hover:shadow-sm transition-all ${s.ring}`}
              >
                <Icon size={15} className={`shrink-0 mt-0.5 ${s.iconColor}`} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900">{a.title}</p>
                  <p className="text-xs text-gray-500 leading-snug">{a.detail}</p>
                </div>
                <ChevronRight size={15} className="text-gray-300 shrink-0 mt-0.5" />
              </button>
            )
          })
        )}
      </div>
    </div>
  )
}
