import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileText } from 'lucide-react'
import { api } from '../lib/api'

export default function Login() {
  const [isRegister, setIsRegister] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [practiceName, setPracticeName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const res = isRegister
        ? await api.register({ email, password, full_name: fullName, practice_name: practiceName })
        : await api.login(email, password)

      if (!res.ok) {
        const data = await res.json()
        setError(data.detail || 'Something went wrong')
        return
      }

      const data = await res.json()
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('practice_id', data.practice_id)
      // Auto clock-in on login
      try { await api.request('/api/v1/time-clock/clock-in', { method: 'POST' }) } catch { /* best effort */ }
      navigate('/')
    } catch {
      setError('Unable to connect. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex bg-[#f5f5f7]">
      {/* Left panel — branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-teal-600 to-teal-700 items-center justify-center p-12">
        <div className="max-w-md text-center">
          <div className="w-16 h-16 bg-white/10 backdrop-blur rounded-2xl flex items-center justify-center mx-auto mb-8">
            <img src="/brand/mark-teal.svg" alt="OrthoFlow" className="w-10 h-10" />
          </div>
          <h2 className="text-3xl font-semibold text-white mb-4">OrthoFlow AI</h2>
          <p className="text-teal-100 text-lg leading-relaxed">
            Automate your accounts payable. Upload invoices, let AI classify them, approve with one tap.
          </p>
          <div className="mt-12 grid grid-cols-3 gap-6 text-center">
            <div>
              <p className="text-2xl font-semibold text-white">2 min</p>
              <p className="text-teal-200 text-xs mt-1">Avg. processing time</p>
            </div>
            <div>
              <p className="text-2xl font-semibold text-white">97%</p>
              <p className="text-teal-200 text-xs mt-1">AI accuracy</p>
            </div>
            <div>
              <p className="text-2xl font-semibold text-white">14 hrs</p>
              <p className="text-teal-200 text-xs mt-1">Saved per week</p>
            </div>
          </div>
        </div>
      </div>

      {/* Right panel — form */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          <div className="lg:hidden text-center mb-8">
            <div className="w-12 h-12 bg-teal-50 rounded-xl flex items-center justify-center mx-auto mb-3">
              <img src="/brand/mark-teal.svg" alt="OrthoFlow" className="w-7 h-7" />
            </div>
            <h1 className="text-xl font-semibold text-gray-900">OrthoFlow AI</h1>
          </div>

          <h2 className="text-2xl font-semibold text-gray-900 mb-1">
            {isRegister ? 'Create your account' : 'Welcome back'}
          </h2>
          <p className="text-sm text-gray-500 mb-8">
            {isRegister ? 'Set up your practice in under a minute' : 'Sign in to manage your invoices'}
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            {isRegister && (
              <>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1.5">Full Name</label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={e => setFullName(e.target.value)}
                    required
                    className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-teal-500 focus:border-transparent outline-none transition-shadow"
                    placeholder="Dr. Jane Smith"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1.5">Practice Name</label>
                  <input
                    type="text"
                    value={practiceName}
                    onChange={e => setPracticeName(e.target.value)}
                    required
                    className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-teal-500 focus:border-transparent outline-none transition-shadow"
                    placeholder="Smith Orthodontics"
                  />
                </div>
              </>
            )}

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Email</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-teal-500 focus:border-transparent outline-none transition-shadow"
                placeholder="you@practice.com"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Password</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-teal-500 focus:border-transparent outline-none transition-shadow"
                placeholder="••••••••"
              />
            </div>

            {error && (
              <div className="px-4 py-3 bg-red-50 border border-red-100 rounded-xl">
                <p className="text-red-600 text-xs">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-teal-600 hover:bg-teal-700 text-white font-medium rounded-xl transition-colors text-sm disabled:opacity-50 shadow-sm"
            >
              {loading ? 'Please wait...' : isRegister ? 'Create Account' : 'Sign In'}
            </button>
          </form>

          <p className="text-center text-xs text-gray-500 mt-6">
            {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
            <button onClick={() => { setIsRegister(!isRegister); setError('') }} className="text-teal-600 font-medium hover:text-teal-700">
              {isRegister ? 'Sign In' : 'Create one'}
            </button>
          </p>

          {/* Demo Role Picker — for client demonstrations */}
          <div className="mt-8 pt-6 border-t border-gray-200">
            <p className="text-xs text-gray-500 text-center mb-3 font-medium">Try a demo account by role:</p>
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: '👩‍⚕️ Doctor', email: 'demo-doctor@orthoflowsolutions.com', color: 'bg-blue-50 hover:bg-blue-100 text-blue-700 border-blue-200' },
                { label: '📋 Manager', email: 'demo-manager@orthoflowsolutions.com', color: 'bg-violet-50 hover:bg-violet-100 text-violet-700 border-violet-200' },
                { label: '🦷 Dental Asst', email: 'demo-da@orthoflowsolutions.com', color: 'bg-amber-50 hover:bg-amber-100 text-amber-700 border-amber-200' },
                { label: '🖥️ Front Desk', email: 'demo-frontdesk@orthoflowsolutions.com', color: 'bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border-emerald-200' },
              ].map(demo => (
                <button
                  key={demo.email}
                  type="button"
                  disabled={loading}
                  onClick={async () => {
                    setLoading(true)
                    setError('')
                    try {
                      const res = await api.login(demo.email, 'Demo2026!')
                      if (res.ok) {
                        const data = await res.json()
                        localStorage.setItem('token', data.access_token)
                        localStorage.setItem('practice_id', data.practice_id)
                        navigate('/')
                      } else {
                        setError('Demo account not available. Contact support.')
                      }
                    } catch { setError('Connection error') }
                    setLoading(false)
                  }}
                  className={`px-3 py-2.5 text-xs font-medium rounded-lg border transition-colors disabled:opacity-50 ${demo.color}`}
                >
                  {demo.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
