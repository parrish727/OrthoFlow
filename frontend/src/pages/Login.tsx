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
            <FileText size={28} className="text-white" />
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
            <div className="w-12 h-12 bg-teal-600 rounded-xl flex items-center justify-center mx-auto mb-3">
              <FileText size={20} className="text-white" />
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
        </div>
      </div>
    </div>
  )
}
